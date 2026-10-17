import Chart from 'chart.js/auto';
import { baselineLabel } from './explain.js';

const C = { actual: '#e6edf3', model: '#f5a524', base: '#7d8794', grid: 'rgba(255,255,255,0.06)', tick: '#8b96a3' };

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

export function createChart(canvas, { daily, preds, news, onPick, target = 'n_anchored', yLabel = 'ships at anchor (daily mean)' }) {
  const labels = daily.map((d) => d.date);
  const index = new Map(labels.map((d, i) => [d, i]));
  const actual = daily.map((d) => d[target] ?? d.n_anchored);
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
        { label: 'Actual', data: actual, borderColor: C.actual, borderWidth: 1.6, pointRadius: 0, tension: 0.2 },
        { label: 'Model', data: series(1, 'pred'), borderColor: C.model, borderWidth: 2.2, pointRadius: 0, tension: 0.2, spanGaps: false },
        { label: baseName(1), data: series(1, 'baseline'), borderColor: C.base, borderWidth: 1.4, borderDash: [5, 4], pointRadius: 0, tension: 0 },
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
        legend: { labels: { color: '#c9d1d9', boxWidth: 18, boxHeight: 2 } },
        tooltip: { callbacks: { title: (it) => labels[it[0].dataIndex],
          label: (it) => it.raw == null ? null : `${it.dataset.label}: ${it.raw.toFixed(1)}` } },
        overlay: { test: testIdx, news: newsMarks, cursor: null, episode: null },
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
