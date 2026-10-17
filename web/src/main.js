import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { Chart, registerables } from 'chart.js';
import { load, mockFiles, datesBetween } from './data.js';

Chart.register(...registerables);

const $ = (id) => document.getElementById(id);
const css = (v) => getComputedStyle(document.documentElement).getPropertyValue(v).trim();

// Approximate boxes from CLAUDE.md, drawn as context only.
const ANCHORAGE = [[-118.30, 33.60], [-118.00, 33.60], [-118.00, 33.72], [-118.30, 33.72]];

const FEATURE_LABELS = {
  arrivals_24h: 'arrivals in the last 24 h',
  arrivals_48h: 'arrivals in the last 48 h',
  departures_24h: 'departures in the last 24 h',
  anchored_chg_3d: '3-day change in the queue',
  n_anchored: 'ships at anchor today',
  n_moored: 'ships at berth today',
  avg_wait_h: 'average wait (h)',
  wind_max_kts: 'max wind (kt)',
  gust_max_kts: 'max gust (kt)',
  vis_min_m: 'min visibility (m)',
  visibility_min_m: 'min visibility (m)',
  dow: 'day of week',
  is_holiday: 'holiday',
  news_score: 'news disruption score',
};
const label = (name) => FEATURE_LABELS[name] ?? name.replaceAll('_', ' ');
const fmt = (v, d = 1) => (v == null || Number.isNaN(v) ? 'n/a' : (+v).toFixed(d));

const state = { h: 1, replay: null, day: null, minute: 0, playing: false, selected: null };
let daily = [], preds = [], metrics = {}, episodes = [], chart, map;

// ---------- header tiles ----------
function renderTiles() {
  $('tiles').innerHTML = Object.entries(metrics)
    .sort(([a], [b]) => a - b)
    .map(([h, m]) => {
      const skill = m.skill_pct ?? (100 * (1 - m.mae_model / m.mae_baseline));
      const win = m.mae_model < m.mae_baseline;
      return `<div class="tile ${win ? 'win' : 'lose'}" data-h="${h}">
        <div class="tile-h">${h}-day ahead</div>
        <div class="tile-v">${fmt(m.mae_model, 2)} <small>MAE</small></div>
        <div class="tile-s">vs ${fmt(m.mae_baseline, 2)} for "tomorrow = today"
          · <b>${win ? 'beats' : 'loses to'} baseline ${fmt(Math.abs(skill), 0)}%</b> · n=${m.n_test}</div>
      </div>`;
    })
    .join('');
}

// ---------- chart ----------
const markerPlugin = {
  id: 'marker',
  afterDraw(c) {
    const i = c.data.labels.indexOf(state.selected ?? state.day);
    if (i < 0) return;
    const x = c.scales.x.getPixelForValue(i);
    const { top, bottom } = c.chartArea;
    c.ctx.save();
    c.ctx.strokeStyle = css('--ink-2');
    c.ctx.setLineDash([4, 4]);
    c.ctx.beginPath(); c.ctx.moveTo(x, top); c.ctx.lineTo(x, bottom); c.ctx.stroke();
    c.ctx.restore();
  },
};

function buildChart() {
  const labels = daily.map((d) => d.date);
  chart = new Chart($('chart'), {
    type: 'line',
    data: { labels, datasets: [] },
    plugins: [markerPlugin],
    options: {
      responsive: true, maintainAspectRatio: false, animation: false,
      interaction: { mode: 'index', intersect: false },
      elements: { point: { radius: 0, hitRadius: 6 } },
      scales: {
        x: { ticks: { maxTicksLimit: 12, color: css('--ink-2') }, grid: { display: false } },
        y: { beginAtZero: true, title: { display: true, text: 'ships at anchor', color: css('--ink-2') },
             ticks: { color: css('--ink-2') }, grid: { color: css('--grid') } },
      },
      plugins: { legend: { labels: { boxWidth: 14, color: css('--ink') } } },
      onClick(_, els) {
        if (!els.length) return;
        selectDate(labels[els[0].index]);
      },
    },
  });
  updateChart();
}

function updateChart() {
  const labels = chart.data.labels;
  const byDate = new Map(preds.filter((p) => p.h === state.h).map((p) => [p.date, p]));
  const col = (k) => labels.map((d) => byDate.get(d)?.[k] ?? null);
  chart.data.datasets = [
    { label: 'Actual', data: daily.map((d) => d.n_anchored), borderColor: css('--ink'), borderWidth: 1.5 },
    { label: `Model (${state.h}-day ahead)`, data: col('pred'), borderColor: css('--model'), borderWidth: 2 },
    { label: 'Baseline: tomorrow = today', data: col('baseline'), borderColor: css('--base'),
      borderWidth: 1.5, borderDash: [5, 4] },
  ];
  chart.update();
}

function renderHorizons() {
  $('horizons').innerHTML = [1, 2, 3]
    .map((h) => `<button data-h="${h}" class="${h === state.h ? 'on' : ''}">h = ${h}</button>`).join('');
  $('horizons').onclick = (e) => {
    const h = +e.target.dataset.h;
    if (!h) return;
    state.h = h;
    renderHorizons(); updateChart(); renderExplain();
  };
}

// ---------- explanation ----------
function renderExplain() {
  const d = state.selected;
  if (!d) return;
  const p = preds.find((r) => r.date === d && r.h === state.h);
  const actual = daily.find((r) => r.date === d);
  if (!p) {
    $('explain').innerHTML = `<p><b>${d}</b>: ${fmt(actual?.n_anchored)} ships at anchor.</p>
      <p class="muted">No ${state.h}-day forecast for this date (the test period is Oct–Dec 2024).</p>`;
    return;
  }
  const drivers = (p.top_features ?? []).map((f) => {
    const dir = f.shap >= 0 ? 'up' : 'down';
    return `<li><span class="${dir}">${f.shap >= 0 ? '▲' : '▼'} ${fmt(Math.abs(f.shap), 2)} ships</span>
      ${label(f.name)}${f.value == null ? '' : ` = <b>${fmt(f.value, f.value % 1 ? 1 : 0)}</b>`}</li>`;
  }).join('');
  const err = Math.abs(p.pred - p.actual), errB = Math.abs(p.baseline - p.actual);
  $('explain').innerHTML = `
    <p>Issued <b>${p.issued ?? `${state.h} day(s) before`}</b>, for <b>${d}</b>:</p>
    <div class="nums">
      <div><small>model</small><b style="color:var(--model)">${fmt(p.pred)}</b></div>
      <div><small>baseline</small><b style="color:var(--base)">${fmt(p.baseline)}</b></div>
      <div><small>actual</small><b>${fmt(p.actual)}</b></div>
    </div>
    <p>The model moved its forecast ${p.pred >= p.baseline ? 'above' : 'below'} "tomorrow = today" mainly because of:</p>
    <ul class="drivers">${drivers}</ul>
    <p class="muted">Off by ${fmt(err)} ships vs ${fmt(errB)} for the baseline
      (${err <= errB ? 'model closer' : 'baseline closer'}).</p>`;
}

function selectDate(d) {
  state.selected = d;
  renderExplain();
  chart.update('none');
  const opt = [...$('day').options].find((o) => o.value === d);
  if (opt) setDay(d);
}

// ---------- episodes / story mode ----------
async function renderEpisodes() {
  $('episodes').innerHTML = episodes.length
    ? episodes.map((e, i) => `<button class="ep" data-i="${i}"><b>${e.title}</b>
        <span>${e.start} → ${e.end}</span><p>${e.why}</p></button>`).join('')
    : '<p class="muted">No episodes yet.</p>';
  $('episodes').onclick = (ev) => {
    const btn = ev.target.closest('.ep');
    if (!btn) return;
    const e = episodes[+btn.dataset.i];
    document.querySelectorAll('.ep').forEach((b) => b.classList.toggle('on', b === btn));
    const first = [...$('day').options].find((o) => o.value >= e.start && o.value <= e.end);
    if (first) setDay(first.value);
    selectDate(first?.value ?? e.start);
    if (!state.playing) togglePlay();
  };
}

// ---------- map replay ----------
const replayCache = new Map();

async function discoverReplayDays() {
  const candidates = new Set(episodes.flatMap((e) => datesBetween(e.start, e.end)));
  const found = [];
  await Promise.all([...candidates].map(async (d) => {
    const rows = await load(`replay/${d}`);
    if (rows?.length) { replayCache.set(d, indexReplay(rows)); found.push(d); }
  }));
  return found.sort();
}

// Group pings per vessel, sorted by time, as minutes since UTC midnight.
function indexReplay(rows) {
  const ships = new Map();
  for (const r of rows) {
    const m = (Date.parse(r.t) % 86_400_000) / 60_000;
    if (!ships.has(r.mmsi)) ships.set(r.mmsi, { mmsi: r.mmsi, name: r.name, pts: [] });
    ships.get(r.mmsi).pts.push({ ...r, m });
  }
  for (const s of ships.values()) s.pts.sort((a, b) => a.m - b.m);
  return [...ships.values()];
}

// Latest ping at or before minute m, if within 30 min.
function frame(ships, m) {
  const feats = [];
  for (const s of ships) {
    let lo = 0, hi = s.pts.length - 1, k = -1;
    while (lo <= hi) { const mid = (lo + hi) >> 1; if (s.pts[mid].m <= m) { k = mid; lo = mid + 1; } else hi = mid - 1; }
    if (k < 0 || m - s.pts[k].m > 30) continue;
    const p = s.pts[k];
    feats.push({ type: 'Feature', geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
      properties: { name: s.name, mmsi: s.mmsi, status: p.status, sog: p.sog } });
  }
  return { type: 'FeatureCollection', features: feats };
}

function drawFrame() {
  if (!state.replay) return;
  const fc = frame(state.replay, state.minute);
  map?.getSource('ships')?.setData(fc);
  const n = (st) => fc.features.filter((f) => f.properties.status === st).length;
  const hh = String(Math.floor(state.minute / 60)).padStart(2, '0');
  const mm = String(Math.floor(state.minute % 60)).padStart(2, '0');
  $('clock').textContent = `${state.day}  ${hh}:${mm} UTC`;
  $('counts').innerHTML = `<b>${n(1)}</b> at anchor · ${n(5)} moored · ${fc.features.length} in view`;
  $('scrub').value = Math.floor(state.minute);
}

function setDay(d) {
  if (!replayCache.has(d)) return;
  state.day = d;
  state.replay = replayCache.get(d);
  state.minute = 0;
  $('day').value = d;
  drawFrame();
  chart?.update('none');
}

let last = 0;
function tick(ts) {
  if (state.playing) {
    const dt = last ? (ts - last) / 1000 : 0;
    state.minute += dt * 60; // 1 hour of replay per second
    if (state.minute >= 1440) {
      const days = [...$('day').options].map((o) => o.value);
      const next = days[days.indexOf(state.day) + 1];
      if (next) setDay(next); else { state.minute = 1439; togglePlay(); }
    }
    drawFrame();
  }
  last = ts;
  requestAnimationFrame(tick);
}

function togglePlay() {
  state.playing = !state.playing;
  $('play').textContent = state.playing ? '❚❚' : '▶';
}

function initMap() {
  map = new maplibregl.Map({
    container: 'map',
    style: 'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    center: [-118.17, 33.68], zoom: 10.6, attributionControl: { compact: true },
    preserveDrawingBuffer: true, // lets screenshots / video capture grab the canvas
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');
  map.on('load', () => {
    map.addSource('anchorage', { type: 'geojson', data: { type: 'Feature',
      geometry: { type: 'Polygon', coordinates: [[...ANCHORAGE, ANCHORAGE[0]]] } } });
    map.addLayer({ id: 'anchorage', type: 'line', source: 'anchorage',
      paint: { 'line-color': css('--anch'), 'line-width': 1, 'line-dasharray': [3, 3], 'line-opacity': 0.6 } });
    map.addSource('ships', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addLayer({ id: 'ships', type: 'circle', source: 'ships', paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 3, 13, 7],
      'circle-color': ['match', ['get', 'status'], 1, css('--anch'), 5, css('--moor'), css('--way')],
      'circle-stroke-color': '#fff', 'circle-stroke-width': 1,
    } });
    const pop = new maplibregl.Popup({ closeButton: false, closeOnClick: false });
    map.on('mousemove', 'ships', (e) => {
      const p = e.features[0].properties;
      pop.setLngLat(e.lngLat).setHTML(`<b>${p.name}</b><br>MMSI ${p.mmsi} · ${p.sog} kn`).addTo(map);
    });
    map.on('mouseleave', 'ships', () => pop.remove());
    drawFrame();
  });
}

// ---------- boot ----------
async function main() {
  [daily, preds, metrics, episodes] = await Promise.all(
    ['daily', 'preds', 'metrics', 'episodes'].map(async (n) => (await load(n)) ?? (n === 'metrics' ? {} : [])));
  daily.sort((a, b) => a.date.localeCompare(b.date));

  renderTiles();
  renderHorizons();
  buildChart();
  initMap();

  const days = await discoverReplayDays();
  $('day').innerHTML = days.map((d) => `<option>${d}</option>`).join('');
  $('day').onchange = (e) => selectDate(e.target.value);
  $('play').onclick = togglePlay;
  $('scrub').oninput = (e) => { state.minute = +e.target.value; drawFrame(); };
  window.addEventListener('keydown', (e) => {
    if (e.code === 'Space' && e.target.tagName !== 'INPUT') { e.preventDefault(); togglePlay(); }
  });
  await renderEpisodes();
  if (days[0]) setDay(days[0]);
  else $('clock').textContent = 'No replay days in shared/replay/ yet';

  if (mockFiles.size) {
    $('mocknote').hidden = false;
    $('mocknote').textContent = `Mock data in use: ${[...mockFiles].filter((f) => !f.startsWith('replay/')).concat(
      [...mockFiles].some((f) => f.startsWith('replay/')) ? ['replay'] : []).join(', ')}`;
  }
  requestAnimationFrame(tick);
}

main();
