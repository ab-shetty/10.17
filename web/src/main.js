import { load, findReplays, daysBetween, addDays, exists } from './data.js';
import { createMap, buildFrames, escapeHtml, VIEWS } from './map.js';
import { createChart } from './forecastChart.js';
import { renderExplain, fmtDay, baselineLabel } from './explain.js';

const $ = (id) => document.getElementById(id);
const FRAME_MS = 1000 / 6; // 10-minute frames, 6 per second = 1 hour per second

// Two datasets with the same contract shapes: 2024 in shared/, the 2021–22 backlog in shared/crisis/.
const YEARS = {
  2021: { dir: 'crisis/', title: 'Ships waiting off San Pedro Bay', note: '2021 replay, not live.', view: 'approach', all: 'Full period',
    what: 'The 2021–22 backlog: ships waiting at anchor plus loitering within 60 nm.',
    foot: 'AIS: NOAA MarineCadastre 2021–22. Waiting = anchored in the bay + loitering (< 3 kn) within 60 nm.' },
  2024: { dir: '', note: '2024 replay, not live.', view: 'bay', all: '2024' },
};
const TARGET_LABEL = { n_anchored: 'ships at anchor', n_waiting: 'ships waiting (anchored + loitering < 60 nm)' };
const AXIS_LABEL = { n_anchored: 'ships at anchor (daily mean)', n_waiting: 'ships waiting, anchor + offshore' };

// ?year=2021|2024 picks the dataset; default is the crisis once A has published shared/crisis/daily.json.
async function pickYear() {
  const hasCrisis = await exists('crisis/daily.json');
  const asked = new URLSearchParams(location.search).get('year');
  const year = asked in YEARS && (asked !== '2021' || hasCrisis) ? asked : hasCrisis ? '2021' : '2024';
  const seg = $('year');
  seg.hidden = !hasCrisis;
  seg.querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.y === year));
  seg.onclick = (e) => {
    const y = e.target.closest('button')?.dataset.y;
    if (y && y !== year) location.search = `?year=${y}`; // reload: each dataset starts from a clean state
  };
  return year;
}

async function main() {
  const year = await pickYear();
  const Y = YEARS[year];
  $('replay-note').textContent = Y.note;
  if (Y.what) $('sub-what').textContent = Y.what;
  if (Y.title) $('title').textContent = Y.title;
  if (Y.foot) $('foot').textContent = Y.foot;
  $('range-all').textContent = Y.all;

  const [daily, preds, metrics, news, episodes] = await Promise.all([
    load(`${Y.dir}daily`), load(`${Y.dir}preds`), load(`${Y.dir}metrics`), load('news'), load(`${Y.dir}episodes`)]);
  if (!daily) {
    document.body.insertAdjacentHTML('afterbegin', `<p class="err">Missing shared/${Y.dir}daily.json.</p>`);
    return;
  }
  // preds may lag daily (crisis run lands in stages): then the chart shows actuals only.
  const D = daily.data, P = preds?.data ?? [], N = news?.data ?? [], E = episodes?.data ?? [];
  const target = metrics?.data?.['1']?.target ?? (year === '2021' ? 'n_waiting' : 'n_anchored');
  const targetLabel = TARGET_LABEL[target] ?? target.replaceAll('_', ' ');
  const first = D[0].date, last = D.at(-1).date;
  const clamp = (d) => (d < first ? first : d > last ? last : d);

  renderTiles(metrics?.data, metrics?.mock || preds?.mock);
  $('episodes-mock').hidden = !episodes?.mock;

  const state = { h: 1, day: null, replay: null, frame: 0, timer: null, episode: null };
  const { map, ready } = createMap($('map'), VIEWS[Y.view]);
  $('view').querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.v === Y.view));
  const chart = createChart($('chart'), { daily: D, preds: P, news: N, target, yLabel: AXIS_LABEL[target] ?? targetLabel, onPick: (d) => selectDay(d) });

  // Replay days: the episode's replay_days (contract), else every day inside it, kept if a file exists.
  const epReplays = await Promise.all(E.map((ep) => findReplays(ep.replay_days ?? daysBetween(ep.start, ep.end), Y.dir)));
  const replayDays = [...new Map(epReplays.flat().map((r) => [r.day, r])).values()].sort((a, b) => a.day.localeCompare(b.day));
  const sel = $('replay-select');
  sel.innerHTML = replayDays.length
    ? replayDays.map((r) => `<option value="${r.day}">${fmtDay(r.day)}${r.mock ? ' (mock)' : ''}</option>`).join('')
    : '<option>no replay files yet</option>';
  sel.onchange = () => selectDay(sel.value);
  $('replay-day').onclick = () => state.replay && selectDay(state.replay.day);

  function explain() {
    renderExplain($('explain'), { day: state.day, h: state.h, preds: P, daily: D, news: N, target, noun: targetLabel });
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
    const r = await load(`${Y.dir}replay/${day}`);
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
    for (const k of ['anchored', 'moored', 'underway', 'inbound', 'waiting_offshore']) $(`cnt-${k}`).textContent = f.counts[k];
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
  segmented('view', (b) => map.fitBounds(VIEWS[b.dataset.v], { padding: 12, duration: 600 }));
  const ranges = { year: [first, last], test: [P[0]?.date ?? first, P.at(-1)?.date ?? last] };
  $('range-test').textContent = P.length ? `${fmtDay(P[0].date, false)} – ${fmtDay(P.at(-1).date, false)} (test)` : 'Test';
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
  if (!replayDays.length) { $('map-empty').hidden = false; $('map-empty').textContent = `No replay files in shared/${Y.dir}replay yet.`; }
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
    // skill_pct is vs the best naive rule (t.baseline). If the 90% CI spans 0 it's a tie, not a win or loss.
    const ci = t.skill_ci90;
    const tie = ci && ci[0] <= 0 && ci[1] >= 0;
    const win = !tie && t.skill_pct > 0;
    // "No detectable difference", not "tie": a CI of about −10..+15 % can't rule out a real loss or win.
    const verdict = tie ? 'no detectable difference vs' : win ? 'better than' : 'worse than';
    const pct = `${t.skill_pct < 0 ? '−' : t.skill_pct > 0 ? '+' : ''}${Math.abs(t.skill_pct).toFixed(1)}%`;
    return `<div class="tile ${tie ? 'tie' : win ? 'win' : 'lose'}">
      <span class="lbl">Day +${h}</span>
      <b>${pct}</b>
      <span class="lbl">${verdict} ${escapeHtml(baselineLabel(t.baseline))}</span>
      <small>MAE ${t.mae_model.toFixed(2)} vs ${t.mae_baseline.toFixed(2)} ships · ${t.n_test} test days${
        ci ? ` · 90% CI ${ci[0]}…${ci[1]}%` : ''}</small>
    </div>`;
  }).join('') + (mock ? '<span class="badge mock">MOCK</span>' : '');
}

main();
