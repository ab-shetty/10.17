import { load, findReplays, daysBetween, addDays } from './data.js';
import { createMap, buildFrames, escapeHtml } from './map.js';
import { createChart } from './forecastChart.js';
import { renderExplain, fmtDay } from './explain.js';

const $ = (id) => document.getElementById(id);
const FRAME_MS = 1000 / 6; // 10-minute frames, 6 per second = 1 hour per second

async function main() {
  const [daily, preds, metrics, news, episodes] = await Promise.all(
    ['daily', 'preds', 'metrics', 'news', 'episodes'].map(load));
  if (!daily || !preds) {
    document.body.insertAdjacentHTML('afterbegin', '<p class="err">Missing shared/daily.json or shared/preds.json.</p>');
    return;
  }
  const D = daily.data, P = preds.data, N = news?.data ?? [], E = episodes?.data ?? [];
  const first = D[0].date, last = D.at(-1).date;
  const clamp = (d) => (d < first ? first : d > last ? last : d);

  renderTiles(metrics?.data, metrics?.mock || preds.mock);
  $('episodes-mock').hidden = !episodes?.mock;

  const state = { h: 1, day: null, replay: null, frame: 0, timer: null, episode: null };
  const { map, ready } = createMap($('map'));
  const chart = createChart($('chart'), { daily: D, preds: P, news: N, onPick: (d) => selectDay(d) });

  // Replay days: every day inside an episode that has a replay file.
  const epReplays = await Promise.all(E.map((ep) => findReplays(daysBetween(ep.start, ep.end))));
  const replayDays = [...new Map(epReplays.flat().map((r) => [r.day, r])).values()].sort((a, b) => a.day.localeCompare(b.day));
  const sel = $('replay-select');
  sel.innerHTML = replayDays.length
    ? replayDays.map((r) => `<option value="${r.day}">${fmtDay(r.day)}${r.mock ? ' (mock)' : ''}</option>`).join('')
    : '<option>no replay files yet</option>';
  sel.onchange = () => selectDay(sel.value);
  $('replay-day').onclick = () => state.replay && selectDay(state.replay.day);

  function explain() {
    renderExplain($('explain'), { day: state.day, h: state.h, preds: P, daily: D, news: N });
    $('explain-day').textContent = fmtDay(state.day);
  }

  // Never await the map here: the chart and explanation must work even if WebGL or tiles are slow.
  function selectDay(day) {
    state.day = day;
    explain();
    if (state.replay?.day === day) return showFrame(state.frame);
    stop();
    chart.setCursor(day, 0.5);
    if (replayDays.some((r) => r.day === day)) loadReplay(day);
  }

  async function loadReplay(day) {
    stop();
    state.loading = day;
    const r = await load(`replay/${day}`);
    await ready;
    if (state.loading !== day || !r || !r.data.length) return; // a newer pick won
    state.replay = { day, frames: buildFrames(r.data), mock: r.mock };
    $('scrub').max = state.replay.frames.length - 1;
    $('replay-day').textContent = fmtDay(day);
    $('replay-mock').hidden = !r.mock;
    $('map-empty').hidden = true;
    sel.value = day;
    showFrame(0);
  }

  function showFrame(i) {
    const R = state.replay;
    if (!R) return;
    state.frame = i;
    const f = R.frames[i];
    map.getSource('ships').setData(f.fc);
    for (const k of ['anchored', 'moored', 'underway']) $(`cnt-${k}`).textContent = f.counts[k];
    $('clock').textContent = `${f.t.slice(11, 16)} UTC`;
    $('scrub').value = i;
    const mins = +f.t.slice(11, 13) * 60 + +f.t.slice(14, 16);
    if (R.day === state.day) chart.setCursor(R.day, mins / 1440);
  }

  function stop() {
    clearInterval(state.timer);
    state.timer = null;
    $('play').textContent = '▶';
  }
  $('play').onclick = () => {
    if (!state.replay) return;
    if (state.timer) return stop();
    if (state.day !== state.replay.day) { state.day = state.replay.day; explain(); }
    if (state.frame >= state.replay.frames.length - 1) state.frame = 0;
    $('play').textContent = '❚❚';
    state.timer = setInterval(() => {
      if (state.frame >= state.replay.frames.length - 1) return stop();
      showFrame(state.frame + 1);
    }, FRAME_MS);
  };
  $('scrub').oninput = (e) => { stop(); showFrame(+e.target.value); };

  segmented('horizon', (b) => { state.h = +b.dataset.h; chart.setHorizon(state.h); explain(); });
  const ranges = { year: [first, last], test: [P[0]?.date ?? first, P.at(-1)?.date ?? last] };
  segmented('range', (b) => { chart.setRange(...ranges[b.dataset.r]); });

  // Story mode: pick an episode -> chart zooms to it, map loads its first replay day.
  $('episodes').innerHTML = E.length ? E.map((ep, i) => `
    <button class="episode" data-i="${i}">
      <span class="when">${fmtDay(ep.start, false)} – ${fmtDay(ep.end, false)}</span>
      <b>${escapeHtml(ep.title)}</b><span class="why">${escapeHtml(ep.why)}</span>
      <span class="rp">${epReplays[i].length ? `${epReplays[i].length} replay day${epReplays[i].length > 1 ? 's' : ''}` : 'no replay'}</span>
    </button>`).join('') : '<p class="fine">No episodes yet.</p>';
  $('episodes').onclick = (e) => {
    const b = e.target.closest('.episode');
    if (!b) return;
    const ep = E[+b.dataset.i];
    document.querySelectorAll('.episode').forEach((x) => x.classList.toggle('on', x === b));
    document.querySelectorAll('#range button').forEach((x) => x.classList.remove('on'));
    chart.setEpisode(ep);
    chart.setRange(clamp(addDays(ep.start, -10)), clamp(addDays(ep.end, 10)));
    selectDay(epReplays[+b.dataset.i][0]?.day ?? ep.start);
  };

  // Start on the test period, on the day with the biggest model win at h=1; preload the first replay.
  chart.setRange(...ranges.test);
  const h1 = P.filter((p) => p.h === 1);
  const best = h1.reduce((a, p) => {
    const gain = Math.abs(p.baseline - p.actual) - Math.abs(p.pred - p.actual);
    return gain > a.gain ? { gain, day: p.date } : a;
  }, { gain: -Infinity, day: h1[0]?.date ?? last });
  selectDay(best.day);
  if (!replayDays.length) { $('map-empty').hidden = false; $('map-empty').textContent = 'No replay files in shared/replay yet.'; }
  else if (!replayDays.some((r) => r.day === best.day)) loadReplay(replayDays[0].day);
}

function segmented(id, onPick) {
  const root = $(id);
  root.onclick = (e) => {
    const b = e.target.closest('button');
    if (!b) return;
    root.querySelectorAll('button').forEach((x) => x.classList.toggle('on', x === b));
    onPick(b);
  };
}

function renderTiles(m, mock) {
  if (!m) { $('tiles').innerHTML = ''; return; }
  $('tiles').innerHTML = ['1', '2', '3'].filter((h) => m[h]).map((h) => {
    const t = m[h];
    const win = t.skill_pct > 0;
    return `<div class="tile ${win ? 'win' : 'lose'}">
      <span class="lbl">Day +${h}</span>
      <b>${win ? '' : '−'}${Math.abs(t.skill_pct).toFixed(1)}%</b>
      <span class="lbl">${win ? 'better' : 'worse'} than “tomorrow = today”</span>
      <small>MAE ${t.mae_model.toFixed(2)} vs ${t.mae_baseline.toFixed(2)} ships · ${t.n_test} test days</small>
    </div>`;
  }).join('') + (mock ? '<span class="badge mock">MOCK</span>' : '');
}

main();
