import Chart from 'chart.js/auto';
import { baselineLabel } from './explain.js';

const C = { actual: '#e6edf3', model: '#f5a524', base: '#7d8794', grid: 'rgba(255,255,255,0.06)', tick: '#8b96a3',
  anchored: 'rgba(245,165,36,0.30)', offshore: 'rgba(192,132,252,0.32)' };

// Shading, cursor and news ticks drawn on top of the line chart.
const overlay = {
  id: 'overlay',
  beforeDatasetsDraw(chart, _a, o) {
    const { ctx, chartArea: a, scales: { x } } = chart;
    const span = (i0, i1, fill, label) => {
      if (i0 == null || i1 == null) return;
      const x0 = Math.max(a.left, x.getPixelForValue(i0) - 2), x1 = Math.min(a.right, x.getPixelForValue(i1) + 2);
      if (x1 <= x0) return;
      ctx.save();
      ctx.fillStyle = fill;
      ctx.fillRect(x0, a.top, x1 - x0, a.bottom - a.top);
      if (label) { ctx.fillStyle = C.tick; ctx.font = '11px system-ui'; ctx.fillText(label, x0 + 6, a.top + 14); }
      ctx.restore();
    };
    span(o.test?.[0], o.test?.[1], 'rgba(255,255,255,0.035)', 'test period');
    span(o.episode?.[0], o.episode?.[1], 'rgba(245,165,36,0.10)', o.episode?.[2]);
  },
  afterDatasetsDraw(chart, _a, o) {
    const { ctx, chartArea: a, scales: { x } } = chart;
    ctx.save();
    for (const n of o.news || []) {
      const px = x.getPixelForValue(n.i);
      if (px < a.left || px > a.right) continue;
      ctx.fillStyle = `rgba(245,165,36,${0.35 + 0.65 * n.score})`;
      ctx.fillRect(px - 1.5, a.bottom - 4 - 14 * n.score, 3, 4 + 14 * n.score);
    }
    for (const m of o.marks || []) {
      const px = x.getPixelForValue(m.i);
      if (px < a.left || px > a.right) continue;
      ctx.strokeStyle = '#e6edf3';
      ctx.lineWidth = 1;
      ctx.setLineDash([]);
      ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      ctx.fillStyle = '#e6edf3'; ctx.font = '11px system-ui';
      const w = ctx.measureText(m.label).width;
      ctx.fillText(m.label, px + w + 6 > a.right ? px - w - 4 : px + 4, a.top + 28);
    }
    if (o.cursor != null) {
      const px = x.getPixelForValue(o.cursor);
      if (px >= a.left && px <= a.right) {
        ctx.strokeStyle = '#f5a524';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(px, a.top); ctx.lineTo(px, a.bottom); ctx.stroke();
      }
    }
    ctx.restore();
  },
};

// spill: stack n_anchored + offshore_waiting under the total (2021: "the queue spilled into the ocean").
// marks: [{date, label}] vertical event lines.
export function createChart(canvas, { daily, preds, news, onPick, target = 'n_anchored', yLabel = 'ships at anchor (daily mean)',
  spill = false, marks = [], actualLabel = 'Actual' }) {
  // Continuous daily axis: a missing date is a gap in the line, not a squashed x-axis.
  const labels = [];
  for (let t = Date.parse(daily[0].date + 'T00:00:00Z'); t <= Date.parse(daily.at(-1).date + 'T00:00:00Z'); t += 864e5) {
    labels.push(new Date(t).toISOString().slice(0, 10));
  }
  const index = new Map(labels.map((d, i) => [d, i]));
  const byDate = new Map(daily.map((d) => [d.date, d]));
  const col = (f) => labels.map((d) => { const r = byDate.get(d); return r ? f(r) ?? null : null; });
  const actual = col((d) => d[target] ?? d.n_anchored);
  spill = spill && daily.some((d) => d.offshore_waiting != null && d.n_anchored != null);
  const anchored = spill ? col((d) => d.n_anchored) : [];
  const anchoredPlusOffshore = spill ? col((d) => (d.n_anchored == null || d.offshore_waiting == null ? null : d.n_anchored + d.offshore_waiting)) : [];
  const testIdx = preds.length ? [index.get(preds[0].date), index.get(preds.at(-1).date)] : null;
  const newsMarks = news.filter((n) => index.has(n.date)).map((n) => ({ i: index.get(n.date), score: n.score }));

  const baseName = (h) => baselineLabel(preds.find((p) => p.h === h)?.baseline_name);
  const series = (h, key) => {
    const out = new Array(labels.length).fill(null);
    for (const p of preds) if (p.h === h && index.has(p.date)) out[index.get(p.date)] = p[key];
    return out;
  };

  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels,
      datasets: [
        { label: actualLabel, data: actual, borderColor: C.actual, borderWidth: 1.6, pointRadius: 0, tension: 0.2 },
        { label: 'Model', data: series(1, 'pred'), borderColor: C.model, borderWidth: 2.2, pointRadius: 0, tension: 0.2, spanGaps: false },
        { label: baseName(1), data: series(1, 'baseline'), borderColor: C.base, borderWidth: 1.4, borderDash: [5, 4], pointRadius: 0, tension: 0 },
        ...(spill ? [
          { label: 'At anchor in the bay', data: anchored, borderColor: 'rgba(245,165,36,0.8)', borderWidth: 1, backgroundColor: C.anchored,
            fill: 'origin', pointRadius: 0, tension: 0.2, order: 10 },
          // plotted as anchored + offshore so it stacks; the tooltip shows the offshore count itself
          { label: 'Loitering offshore (< 60 nm)', data: anchoredPlusOffshore, borderColor: 'rgba(192,132,252,0.8)', borderWidth: 1,
            backgroundColor: C.offshore, fill: '-1', pointRadius: 0, tension: 0.2, order: 11, offshore: true },
        ] : []),
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { ticks: { color: C.tick, maxRotation: 0, autoSkipPadding: 24,
               callback(v) { return fmtTick(labels[v]); } }, grid: { color: C.grid } },
        y: { beginAtZero: true, title: { display: true, text: yLabel, color: C.tick },
             ticks: { color: C.tick }, grid: { color: C.grid } },
      },
      plugins: {
        legend: { labels: { color: '#c9d1d9', boxWidth: 18, boxHeight: 2,
          filter: (item, data) => data.datasets[item.datasetIndex].data.some((v) => v != null) } }, // no empty series
        tooltip: { callbacks: { title: (it) => labels[it[0].dataIndex],
          label: (it) => {
            if (it.raw == null) return null;
            const v = it.dataset.offshore ? it.raw - anchored[it.dataIndex] : it.raw;
            return `${it.dataset.label}: ${v.toFixed(1)}`;
          } } },
        overlay: { test: testIdx, news: newsMarks, cursor: null, episode: null,
          marks: marks.filter((m) => index.has(m.date)).map((m) => ({ i: index.get(m.date), label: m.label })) },
      },
      onClick(_e, _els, ch) {
        const i = Math.round(ch.scales.x.getValueForPixel(_e.x));
        if (i >= 0 && i < labels.length) onPick(labels[i]);
      },
    },
    plugins: [overlay],
  });

  const o = chart.options.plugins.overlay;
  return {
    setHorizon(h) {
      chart.data.datasets[1].data = series(h, 'pred');
      chart.data.datasets[1].label = `Model, ${h} day${h > 1 ? 's' : ''} ahead`;
      chart.data.datasets[2].data = series(h, 'baseline');
      chart.data.datasets[2].label = baseName(h);
      chart.update('none');
    },
    setRange(d0, d1) {
      chart.options.scales.x.min = index.get(d0) ?? 0;
      chart.options.scales.x.max = index.get(d1) ?? labels.length - 1;
      chart.update('none');
    },
    // day + fraction of the day (0..1), from the replay clock
    setCursor(day, frac = 0) {
      o.cursor = index.has(day) ? index.get(day) + frac - 0.5 : null;
      chart.draw();
    },
    setEpisode(ep) {
      o.episode = ep && index.has(ep.start) ? [index.get(ep.start), index.get(ep.end) ?? labels.length - 1, ep.title] : null;
      chart.update('none');
    },
  };
}

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
function fmtTick(d) {
  return d ? `${MON[+d.slice(5, 7) - 1]} ${+d.slice(8)}` : '';
}
