import Chart from 'chart.js/auto';

const C = { actual: '#e6edf3', little: '#f5a524', reported: '#7d8794', grid: 'rgba(255,255,255,0.06)', tick: '#8b96a3' };

// Weekly wait (days) for a ship joining the queue: what it really waited, what the published 7-day average said,
// and queue ÷ berthing rate (Little's law). Uses wait.weekly from A when present; otherwise weekly means of the
// daily rows inside wait.window (only days that have all three numbers).
export function weeklyWaits(wait) {
  if (Array.isArray(wait.weekly) && wait.weekly.length) {
    return wait.weekly.map((w) => ({
      week: w.week ?? w.week_start ?? w.date,
      actual: w.actual_wait_d ?? w.actual ?? w.actual_mean_d,
      reported: w.reported_wait_d ?? w.reported ?? w.reported_wait_7d,
      little: w.little_wait_d ?? w.little,
    }));
  }
  const [w0, w1] = wait.window ?? ['0000', '9999'];
  const rows = wait.daily.filter((r) => r.date >= w0 && r.date <= w1 && r.little_wait_d != null
    && r.reported_wait_7d != null && r.actual_wait_of_ships_joining_next_day != null);
  const byWeek = new Map();
  for (const r of rows) {
    const t = new Date(r.date + 'T00:00:00Z');
    const monday = new Date(t - ((t.getUTCDay() + 6) % 7) * 864e5).toISOString().slice(0, 10);
    if (!byWeek.has(monday)) byWeek.set(monday, []);
    byWeek.get(monday).push(r);
  }
  const mean = (xs) => xs.reduce((a, b) => a + b, 0) / xs.length;
  return [...byWeek].sort(([a], [b]) => a.localeCompare(b)).map(([week, rs]) => ({
    week,
    actual: mean(rs.map((r) => r.actual_wait_of_ships_joining_next_day)),
    reported: mean(rs.map((r) => r.reported_wait_7d)),
    little: mean(rs.map((r) => r.little_wait_d)),
  }));
}

// Share of days the published figure was below the real wait, and the same for Little's law.
export function underShare(wait) {
  const [w0, w1] = wait.window ?? ['0000', '9999'];
  const rows = wait.daily.filter((r) => r.date >= w0 && r.date <= w1 && r.little_wait_d != null
    && r.reported_wait_7d != null && r.actual_wait_of_ships_joining_next_day != null);
  const share = (k) => rows.filter((r) => r[k] < r.actual_wait_of_ships_joining_next_day).length / (rows.length || 1);
  return { n: rows.length, reported: share('reported_wait_7d'), little: share('little_wait_d') };
}

const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const fmtWeek = (d) => `${MON[+d.slice(5, 7) - 1]} ${+d.slice(8)}`;

export function createWaitChart(canvas, wait) {
  const W = weeklyWaits(wait);
  return new Chart(canvas, {
    type: 'line',
    data: {
      labels: W.map((w) => fmtWeek(w.week)),
      datasets: [
        { label: 'Real wait', data: W.map((w) => w.actual), borderColor: C.actual, backgroundColor: C.actual, borderWidth: 2, pointRadius: 3 },
        { label: 'Queue ÷ berthing rate (ours)', data: W.map((w) => w.little), borderColor: C.little, backgroundColor: C.little, borderWidth: 2.4, pointRadius: 3 },
        { label: 'Published 7-day average', data: W.map((w) => w.reported), borderColor: C.reported, backgroundColor: C.reported,
          borderWidth: 1.6, borderDash: [5, 4], pointRadius: 3 },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: false,
      interaction: { mode: 'index', intersect: false },
      scales: {
        x: { title: { display: true, text: 'week a ship joined the queue', color: C.tick }, ticks: { color: C.tick }, grid: { color: C.grid } },
        y: { beginAtZero: true, title: { display: true, text: 'wait (days)', color: C.tick }, ticks: { color: C.tick }, grid: { color: C.grid } },
      },
      plugins: {
        legend: { labels: { color: '#c9d1d9', boxWidth: 18, boxHeight: 2 } },
        tooltip: { callbacks: { title: (it) => `Week of ${it[0].label}`,
          label: (it) => it.raw == null ? null : `${it.dataset.label}: ${it.raw.toFixed(1)} d` } },
      },
    },
  });
}
