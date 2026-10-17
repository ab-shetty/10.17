import { load, findReplays, daysBetween, addDays, exists } from './data.js';
import { createMap, buildFrames, escapeHtml, VIEWS } from './map.js';
import { createChart } from './forecastChart.js';
import { renderExplain, fmtDay, baselineLabel } from './explain.js';
import { createWaitChart, underShare } from './waitChart.js';

const $ = (id) => document.getElementById(id);
const FRAME_MS = 1000 / 6; // 10-minute frames, 6 per second = 1 hour per second

// Two datasets with the same contract shapes: 2024 in shared/, the 2021–22 backlog in shared/crisis/.
const YEARS = {
  2021: { dir: 'crisis/', open: '2021-10-19', title: 'Ships waiting off San Pedro Bay', note: '2021 replay, not live.', view: 'approach', all: 'Full period',
    what: 'The 2021–22 backlog: ships waiting at anchor plus loitering within 60 nm.',
    foot: 'AIS: NOAA MarineCadastre 2021–22. Waiting = anchored in the bay + loitering (< 3 kn) within 60 nm.' },
  2024: { dir: '', note: '2024 replay, not live.', view: 'bay', all: '2024' },
};
// 2021-11-16: new queuing process, container ships told to wait far offshore instead of at the anchorage.
const MARKS = {
  2021: [{ date: '2021-11-16', label: 'Nov 16: ships told to wait 150 nm out' }],
};
const TARGET_LABEL = { n_anchored: 'ships at anchor', n_waiting: 'ships waiting (anchored + loitering < 60 nm)' };
const AXIS_LABEL = { n_anchored: 'ships at anchor (daily mean)', n_waiting: 'ships waiting, anchor + offshore',
  big_cargo_waiting: 'container-size ships waiting (end of day)' };
TARGET_LABEL.big_cargo_waiting = 'container-size ships waiting (end of day)';

// ?year=2021|2024 picks the dataset; default is the crisis once A has published shared/crisis/daily.json or wait.json.
async function pickYear() {
  const hasCrisis = (await exists('crisis/daily.json')) || (await exists('crisis/wait.json'));
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

  const [dailyFile, preds, metrics, news, episodes, waitFile, briefsFile] = await Promise.all([
    load(`${Y.dir}daily`), load(`${Y.dir}preds`), load(`${Y.dir}metrics`), load('news'), load(`${Y.dir}episodes`),
    load(`${Y.dir}wait`), load('briefs')]);
  // Claude morning briefs (signals/morning_brief.py), pre-generated for the story days of this dataset.
  const briefs = new Map((briefsFile?.data ?? []).filter((b) => b.year === year).map((b) => [b.date, { ...b, mock: briefsFile.mock }]));
  const wait = year === '2021' ? waitFile?.data : null;
  const waitControl = year === '2024' ? waitFile?.data : null;
  // Until crisis/daily.json lands, the 2021 queue line comes from wait.json (container-size ships, end of day).
  const daily = dailyFile ?? (wait && { data: wait.daily.map((r) => ({ date: r.date, big_cargo_waiting: r.ships_waiting_eod })) });
  if (!daily) {
    document.body.insertAdjacentHTML('afterbegin', `<p class="err">Missing shared/${Y.dir}daily.json.</p>`);
    return;
  }
  // preds may lag daily (crisis run lands in stages): then the chart shows actuals only.
  const D = daily.data, P = preds?.data ?? [], N = news?.data ?? [], E = episodes?.data ?? [];
  const target = dailyFile ? metrics?.data?.['1']?.target ?? (year === '2021' ? 'n_waiting' : 'n_anchored') : 'big_cargo_waiting';
  const targetLabel = TARGET_LABEL[target] ?? target.replaceAll('_', ' ');
  const first = D[0].date, last = D.at(-1).date;
  const clamp = (d) => (d < first ? first : d > last ? last : d);

  renderTiles(metrics?.data, metrics?.mock || preds?.mock);
  if (waitControl) renderWaitControl(waitControl);
  if (!P.length) { // no queue forecast for this dataset (yet): it's a plain history chart
    $('horizon').hidden = true;
    $('chart-title').textContent = year === '2021' ? 'Ships waiting' : 'Ships at anchor';
  }
  // Wait forecast (2021): the result is bias, not day-to-day accuracy. See OVERSEER.md 2:05.
  const waitByDate = new Map((wait?.daily ?? []).map((r) => [r.date, r]));
  if (wait) {
    document.body.classList.add('wait');
    $('wait-panel').hidden = false;
    renderWaitTiles(wait, metrics?.data);
    createWaitChart($('wait-chart'), wait);
    $('wait-note').textContent = `Container-size ships (cargo ≥ 200 m), weekly means, ${fmtDay(wait.window[0], false)} – ${fmtDay(wait.window[1], false)} 2021. `
      + 'Wait = joining the queue (anchored, or loitering within 60 nm) → first berth. Ours = ships waiting ÷ ships berthed per day (last 7 days), '
      + `known the evening before. Published = average wait of ships that berthed in the last 7 days. ${cap(wait.censoring_note ?? '')}.`;
  }
  $('episodes-mock').hidden = !episodes?.mock;

  const state = { h: 1, day: null, replay: null, frame: 0, timer: null, episode: null };
  const { map, ready } = createMap($('map'), VIEWS[Y.view]);
  $('view').querySelectorAll('button').forEach((b) => b.classList.toggle('on', b.dataset.v === Y.view));
  const chart = createChart($('chart'), { daily: D, preds: P, news: N, target, yLabel: AXIS_LABEL[target] ?? targetLabel, spill: year === '2021', actualLabel: year === '2021' ? 'Total waiting' : 'Actual', marks: MARKS[year] ?? [], onPick: (d) => selectDay(d) });

  // Replay days: the episode's replay_days (contract), else every day inside it, kept if a file exists.
  const epReplays = await Promise.all(E.map((ep) => findReplays(ep.replay_days ?? daysBetween(ep.start, ep.end), Y.dir)));
  // Plus any other replay file A exported (e.g. the 2021-10-25 peak), found by checking every date in the dataset.
  const otherReplays = await findReplays(D.map((r) => r.date), Y.dir);
  const replayDays = [...new Map([...epReplays.flat(), ...otherReplays].map((r) => [r.day, r])).values()].sort((a, b) => a.day.localeCompare(b.day));
  const sel = $('replay-select');
  sel.innerHTML = replayDays.length
    ? replayDays.map((r) => `<option value="${r.day}">${fmtDay(r.day)}${r.mock ? ' (mock)' : ''}</option>`).join('')
    : '<option>no replay files yet</option>';
  sel.onchange = () => selectDay(sel.value);
  $('replay-day').onclick = () => state.replay && selectDay(state.replay.day);

  function explain() {
    // wait.json row t = known at end of t, actual = ships joining t+1: a ship joining on `day` uses row day-1.
    const waitRow = waitByDate.get(addDays(state.day, -1));
    renderExplain($('explain'), { day: state.day, h: state.h, preds: P, daily: D, news: N, target, noun: targetLabel, waitRow,
      brief: briefs.get(state.day) });
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
  const testSpan = P.length ? [P[0].date, P.at(-1).date] : wait ? wait.window : [first, last];
  const ranges = { year: [first, last], test: testSpan };
  $('range-test').textContent = `${fmtDay(testSpan[0], false)} – ${fmtDay(testSpan[1], false)}${P.length ? ' (test)' : ''}`;
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
  // 2021 without crisis forecasts: show the whole backlog (the spill-over and Nov 16 are the story).
  const openFull = year === '2021' && !P.length && dailyFile;
  chart.setRange(...(openFull ? ranges.year : ranges.test));
  if (openFull) document.querySelectorAll('#range button').forEach((x) => x.classList.toggle('on', x.dataset.r === 'year'));
  const h1 = P.filter((p) => p.h === 1);
  const best = h1.reduce((a, p) => {
    const gain = Math.abs(p.baseline - p.actual) - Math.abs(p.pred - p.actual);
    return gain > a.gain ? { gain, day: p.date } : a;
  }, { gain: -Infinity, day: h1[0]?.date ?? last });
  const askedDay = new URLSearchParams(location.search).get('day'); // ?day=YYYY-MM-DD, e.g. for the demo video
  if (askedDay && D.some((r) => r.date === askedDay)) best.day = askedDay;
  else if (Y.open && D.some((r) => r.date === Y.open)) best.day = Y.open; // OVERSEER 2:55: crisis opens on Oct 19
  else if (wait) { // otherwise: the join day where ours beat the published wait by most
    best.gain = -Infinity;
    for (const r of wait.daily) {
      const real = r.actual_wait_of_ships_joining_next_day;
      if (r.date < wait.window[0] || r.date > wait.window[1] || real == null || r.reported_wait_7d == null || r.little_wait_d == null) continue;
      const gap = Math.abs(r.reported_wait_7d - real) - Math.abs(r.little_wait_d - real);
      if (gap > best.gain) Object.assign(best, { gain: gap, day: addDays(r.date, 1) });
    }
  }
  selectDay(best.day);
  if (!replayDays.length) { $('map-empty').hidden = false; $('map-empty').textContent = `No replay files in shared/${Y.dir}replay yet.`; }
  else if (!replayDays.some((r) => r.day === best.day)) { // nearest replay day to the opening day
    const dist = (r) => Math.abs(Date.parse(r.day) - Date.parse(best.day));
    loadReplay(replayDays.reduce((a, r) => (dist(r) < dist(a) ? r : a)).day);
  }
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

const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);

function renderWaitTiles(w, queueMetrics) {
  const s = w.big_cargo_daily_mean ?? w.big_cargo ?? w.all;
  const u = underShare(w);
  const pct = (x) => `${Math.round(100 * x)}%`;
  const d = (x) => `${x > 0 ? '+' : x < 0 ? '−' : ''}${Math.abs(x).toFixed(1)} d`;
  const weeksShort = w.weekly?.length ? [w.weekly.filter((x) => x.reported_d < x.real_d).length, w.weekly.length] : null;
  const g = w.gap_cost?.net_understatement;
  const tiles = [
    `<div class="tile lose"><span class="lbl">Published wait</span><b>${d(s.bias_reported_d)}</b>
      <span class="lbl">vs the real wait, on average</span>
      <small>${weeksShort ? `too low in ${weeksShort[0]} of ${weeksShort[1]} weeks` : `too low on ${pct(u.reported)} of days`} · lags a growing queue</small></div>`,
    `<div class="tile win"><span class="lbl">Ours: queue ÷ berthing rate</span><b>${d(s.bias_little_d)}</b>
      <span class="lbl">vs the real wait, on average</span>
      <small>too low on ${pct(u.little)} of days · from AIS alone</small></div>`,
    `<div class="tile tie"><span class="lbl">Day to day (MAE)</span><b>${s.mae_little_d.toFixed(1)} vs ${s.mae_reported_d.toFixed(1)} d</b>
      <span class="lbl">ours vs published: published is closer</span>
      <small>ours is unbiased, not more precise · ${s.n} days</small></div>`,
    // Net understatement (A: headline this, not the per-ship sums): waiting captains weren't told about, priced at anchor.
    g && g.ship_days > 0 ? `<div class="tile lose"><span class="lbl">Waiting nobody planned for</span><b>$${g.fuel_usd_m.toFixed(1)}M</b>
      <span class="lbl">of fuel, ${g.ship_days.toLocaleString()} ship-days beyond the published wait</span>
      <small>${Math.round(g.nox_t)} t NOx · net, Sep–Oct 2021 · fuel at $780/t</small></div>` : '',
  ];
  $('tiles').innerHTML = tiles.join('');
  // Keep the queue result visible and honest once crisis metrics exist (it may lose to "tomorrow = today").
  if (queueMetrics) $('tiles').insertAdjacentHTML('beforeend', '<span class="tiles-sep"></span>' + queueTile(queueMetrics, '1', 'Queue, day +1'));
}

function renderTiles(m, mock) {
  if (!m) { $('tiles').innerHTML = ''; return; }
  $('tiles').innerHTML = ['1', '2', '3'].filter((h) => m[h]).map((h) => queueTile(m, h)).join('')
    + (mock ? '<span class="badge mock">MOCK</span>' : '');
}

// 2024 control for the wait claim (shared/wait.json): the published figure is fine in calm weeks and drifts only
// when the queue moves. Our estimate runs high in 2024, and the tile says so.
function renderWaitControl(w) {
  const r = w.by_regime;
  if (!r?.steady) return;
  const d = (x) => `${x > 0 ? '+' : x < 0 ? '−' : ''}${Math.abs(x).toFixed(1)} d`;
  $('tiles').insertAdjacentHTML('beforeend', `<span class="tiles-sep"></span><div class="tile tie">
    <span class="lbl">Published wait, 2024 control</span><b>${d(r.steady.bias_reported_d)}</b>
    <span class="lbl">bias in steady weeks</span>
    <small>${d(r.growing.bias_reported_d)} when the queue grew · ${d(r.shrinking.bias_reported_d)} when it shrank ·
      ours runs high: ${d(r.steady.bias_little_d)}</small></div>`);
}

function queueTile(m, h, label = `Day +${h}`) {
  const t = m[h];
  if (!t) return '';
  // skill_pct is vs the best naive rule (t.baseline). If the 90% CI spans 0 it's a tie, not a win or loss.
  const ci = t.skill_ci90;
  const tie = ci && ci[0] <= 0 && ci[1] >= 0;
  const win = !tie && t.skill_pct > 0;
  // "No detectable difference", not "tie": a CI of about −10..+15 % can't rule out a real loss or win.
  const verdict = tie ? 'no detectable difference vs' : win ? 'better than' : 'worse than';
  const pct = `${t.skill_pct < 0 ? '−' : t.skill_pct > 0 ? '+' : ''}${Math.abs(t.skill_pct).toFixed(1)}%`;
  return `<div class="tile ${tie ? 'tie' : win ? 'win' : 'lose'}">
    <span class="lbl">${label}</span>
    <b>${pct}</b>
    <span class="lbl">${verdict} ${escapeHtml(baselineLabel(t.baseline))}</span>
    <small>MAE ${t.mae_model.toFixed(2)} vs ${t.mae_baseline.toFixed(2)} ships · ${t.n_test} test days${
      ci ? ` · 90% CI ${ci[0]}…${ci[1]}%` : ''}</small>
  </div>`;
}

main();
