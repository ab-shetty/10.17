import { escapeHtml } from './map.js';

const DOW = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']; // pandas dayofweek
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const n = (v, d = 1) => Number(v).toFixed(d).replace(/\.0+$/, '');
const chg = (v, span) => (v === 0 ? `no change in the queue ${span}`
  : `the queue ${v > 0 ? 'up' : 'down'} ${n(Math.abs(v))} ships ${span}`);

// One plain-English phrase per model feature (names from model/train.py).
const PHRASE = {
  anchored_today: (v) => `${n(v)} ships at anchor on the issue day`,
  anchored_max_today: (v) => `a peak of ${n(v)} at anchor on the issue day`,
  anchored_chg_1d: (v) => chg(v, 'since the day before'),
  anchored_chg_2d: (v) => chg(v, 'over 2 days'),
  anchored_chg_3d: (v) => chg(v, 'over 3 days'),
  anchored_chg_7d: (v) => chg(v, 'over a week'),
  anchored_vs_7d_mean: (v) => `the queue ${n(Math.abs(v))} ships ${v >= 0 ? 'above' : 'below'} its 7-day average`,
  moored_today: (v) => `${n(v)} ships at berth`,
  arrivals_24h: (v) => `${n(v, 0)} arrivals in the last 24 h`,
  arrivals_48h: (v) => `${n(v, 0)} arrivals in the last 48 h`,
  departures_24h: (v) => `${n(v, 0)} departures in the last 24 h`,
  departures_yday: (v) => `${n(v, 0)} departures the day before`,
  inbound_60nm: (v) => `${n(v, 0)} ships inbound within 60 nm`,
  offshore_waiting: (v) => `${n(v, 0)} ships loitering offshore within 60 nm`,
  fc_gust_target: (v) => `gusts of ${n(v, 0)} kn forecast for that day`,
  fc_gust_tomorrow: (v) => `gusts of ${n(v, 0)} kn forecast for tomorrow`,
  net_inflow_3d: (v) => `net ${v >= 0 ? '+' : '−'}${n(Math.abs(v), 0)} ships over 3 days (arrivals minus departures)`,
  avg_wait_h: (v) => `an average wait of ${n(v, 0)} h for a berth`,
  wind_max_kts: (v) => `wind up to ${n(v)} kts`,
  gust_max_kts: (v) => `gusts up to ${n(v)} kts`,
  wind_max_3d: (v) => `wind up to ${n(v)} kts over 3 days`,
  visibility_min_m: (v) => `visibility down to ${n(v / 1000)} km`,
  klgb_vis_min_mi: (v) => `Long Beach airport visibility down to ${n(v)} mi`,
  klgb_fog_hours: (v) => `${n(v, 0)} h of fog at Long Beach airport`,
  wave_hs_max_m: (v) => `waves up to ${n(v)} m at the harbor buoy`,
  wave_period_max_s: (v) => `swell period up to ${n(v, 0)} s`,
  is_holiday: (v) => (v ? 'a public holiday' : 'not a holiday'),
  target_dow: (v) => `the target day being a ${DOW[v] ?? v}`,
  news_score: (v) => `a news risk score of ${n(v, 2)}`,
};

// A's preds.json carries its own direction-aware `phrase`; the local table is the fallback for older files.
export function phrase(f) {
  if (f.phrase) return f.phrase;
  const name = f.label ?? f.name.replaceAll('_', ' ');
  if (f.value == null) return `${name} (missing that day)`;
  return (PHRASE[f.name] ?? ((v) => `${name} = ${n(v)}`))(f.value);
}

// `baseline` in preds/metrics is the best naive rule on the test set, named by baseline_name.
const BASELINES = {
  persistence: '“Tomorrow = today”',
  ma7: '7-day average',
  blend: 'Today / 7-day average blend',
};
export const baselineLabel = (name) => BASELINES[name] ?? BASELINES.persistence;

export function fmtDay(d, weekday = true) {
  const t = new Date(d + 'T00:00:00Z');
  const wd = weekday ? DOW[(t.getUTCDay() + 6) % 7].slice(0, 3) + ' ' : '';
  return `${wd}${MON[t.getUTCMonth()]} ${t.getUTCDate()}`;
}

export function renderExplain(el, { day, h, preds, daily, news, target = 'n_anchored', noun = 'ships at anchor', waitRow, brief }) {
  const p = preds.find((r) => r.date === day && r.h === h);
  const d = daily.find((r) => r.date === day);
  const parts = [];

  if (brief) {
    parts.push(`<div class="brief"><div class="brief-head">Morning brief${brief.mock ? ' <span class="badge mock">MOCK</span>' : ''}</div>
      <b class="brief-title">${escapeHtml(brief.headline)}</b>
      <p>${escapeHtml(brief.brief)}</p>
      <p class="brief-watch"><span>Watch:</span> ${escapeHtml(brief.watch)}</p>
      <p class="fine">${brief.mock || brief.scorer === 'template'
        ? 'Template text, not Claude: run signals/morning_brief.py to generate the real briefs.'
        : `Written by Claude (${escapeHtml(brief.scorer)}) ahead of time, from only the numbers known that morning.`}</p></div>`);
  }

  // Wait for a container-size ship joining the queue on `day` (wait.json row for the evening before).
  const w = waitRow;
  if (w && d?.regime === 'after_150nm_rule') {
    // After the 150 nm rule the queue is beyond shore AIS, so queue ÷ berthing rate undercounts (OVERSEER 2:55).
    parts.push(`<div class="wait-block"><p>After Nov 16 2021, container ships waited 150+ nm out, beyond shore AIS.
      Our wait estimate covers Jun 1 – Nov 15.</p></div>`);
  } else if (w && w.little_wait_d != null) {
    const real = w.actual_wait_of_ships_joining_next_day;
    parts.push(`<div class="wait-block"><p class="lead">A container ship joining the queue on ${fmtDay(day)}:</p>
      <p>Ships were told (port's 7-day average) <b class="num">${n(w.reported_wait_7d)} d</b>.
        Ours, ${n(w.ships_waiting_eod, 0)} ships waiting ÷ ${n(w.berths_per_day_7d)} berthed per day, said
        <b class="num model">${n(w.little_wait_d)} d</b>.
        ${real == null ? '' : `Ships that joined that day really waited <b class="num">${n(real)} d</b>.`}</p>
      ${real == null ? '<p class="fine">No measured wait for this day (outside Sep–Oct, or berth not seen in the data).</p>'
        : `<p class="verdict ${Math.abs(w.little_wait_d - real) < Math.abs(w.reported_wait_7d - real) ? 'good' : 'fine'}">
          ${Math.abs(w.little_wait_d - real) < Math.abs(w.reported_wait_7d - real) ? 'Ours was closer' : 'Published was closer'}:
          ours off by ${n(Math.abs(w.little_wait_d - real))} d, published by ${n(Math.abs(w.reported_wait_7d - real))} d.</p>`}
    </div>`);
  }

  if (p) {
    const errM = Math.abs(p.pred - p.actual), errB = Math.abs(p.baseline - p.actual);
    const better = errM < errB;
    parts.push(`<p class="lead">Issued ${fmtDay(p.issued)}, ${h} day${h > 1 ? 's' : ''} ahead, the model expected
      <b class="num model">${n(p.pred)}</b> ${escapeHtml(noun)} on ${fmtDay(day)}.
      The best simple rule (${escapeHtml(baselineLabel(p.baseline_name))}) said <b class="num">${n(p.baseline)}</b>.
      Actual: <b class="num">${n(p.actual)}</b>.</p>`);
    parts.push(`<p class="verdict ${better ? 'good' : 'bad'}">${better ? 'Model was closer' : 'Baseline was closer'}:
      off by ${n(errM)} vs ${n(errB)} ships.</p>`);
    const max = Math.max(...p.top_features.map((f) => Math.abs(f.shap)), 0.01);
    parts.push('<h3>What moved the forecast</h3><ul class="drivers">' + p.top_features.map((f) => `
      <li><span class="bar ${f.shap >= 0 ? 'up' : 'down'}" style="--w:${(100 * Math.abs(f.shap) / max).toFixed(0)}%"></span>
        <span class="eff ${f.shap >= 0 ? 'up' : 'down'}">${f.shap >= 0 ? '+' : '−'}${n(Math.abs(f.shap), 2)}</span>
        ${escapeHtml(phrase(f))}</li>`).join('') + '</ul>');
    parts.push('<p class="fine">Numbers are SHAP contributions, in ships, to how far the model moved away from the simple rule.</p>');
  } else if (d && w) {
    parts.push(`<p><b class="num">${n(d[target] ?? d.n_anchored)}</b> ${escapeHtml(noun)} on ${fmtDay(day)}.</p>`);
  } else if (d) {
    parts.push(`<p class="lead"><b class="num">${n(d[target] ?? d.n_anchored)}</b> ${escapeHtml(noun)} on ${fmtDay(day)} (daily mean).</p>
      <p class="fine">Forecasts exist only for the test period, ${preds.length ? `${fmtDay(preds[0].date, false)} – ${fmtDay(preds.at(-1).date, false)}` : 'none yet'}.
      ${target === 'n_anchored' ? 'The model trained on Jan–Sep.' : ''}</p>`);
  }

  if (d) {
    const cell = (label, v) => `<div><span>${label}</span><b>${v}</b></div>`;
    const opt = (label, v, fmt) => (v == null ? '' : cell(label, fmt(v))); // crisis tables lack weather
    parts.push('<div class="facts">' +
      (target !== 'n_anchored' ? opt('at anchor', d.n_anchored, (v) => n(v)) : '') +
      opt('loitering offshore', d.offshore_waiting, (v) => n(v)) +
      opt('inbound < 60 nm', d.inbound_60nm, (v) => n(v)) +
      opt('at berth', d.n_moored, (v) => n(v)) +
      opt('arrivals 24 h', d.arrivals_24h, (v) => n(v, 0)) +
      opt('departures 24 h', d.departures_24h, (v) => n(v, 0)) +
      opt('avg wait', d.avg_wait_h, (v) => `${n(v, 0)} h`) +
      opt('max wind', d.wind_max_kts, (v) => `${n(v)} kts`) +
      opt('min visibility', d.vis_min_m, (v) => `${n(v / 1000)} km`) + '</div>');
  }

  const t = Date.parse(day);
  const recent = news.filter((x) => { const dt = (t - Date.parse(x.date)) / 864e5; return dt >= 0 && dt <= 30; })
    .sort((a, b) => b.date.localeCompare(a.date)).slice(0, 3);
  if (recent.length) {
    parts.push('<h3>News in the 30 days before</h3><ul class="news">' + recent.map((x) => `
      <li><span class="score" style="--s:${x.score}">${n(x.score, 2)}</span>
        <div><a href="${escapeHtml(x.url)}" target="_blank" rel="noopener">${escapeHtml(x.title)}</a>
        <small>${fmtDay(x.date, false)} · ${escapeHtml(x.reason)}</small></div></li>`).join('') + '</ul>');
  }
  el.innerHTML = parts.join('');
}
