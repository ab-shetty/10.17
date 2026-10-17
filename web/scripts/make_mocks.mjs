// Writes mock versions of A's not-yet-published contracts so the UI never waits on A:
//   shared/episodes.mock.json, shared/replay/YYYY-MM-DD.mock.json
// Shapes match the Contracts table in CLAUDE.md. A's real files (no ".mock") take precedence in the app.
import { mkdirSync, writeFileSync } from 'node:fs';

const SHARED = new URL('../../shared/', import.meta.url);
mkdirSync(new URL('replay/', SHARED), { recursive: true });

const episodes = [
  { start: '2024-04-20', end: '2024-04-24', title: 'MOCK: April queue spike',
    why: 'MOCK: 20 arrivals in one day outpaced berth turnover; queue peaked at ~20 ships.' },
  { start: '2024-07-25', end: '2024-08-04', title: 'MOCK: Late-July peak season',
    why: 'MOCK: Early peak-season imports ahead of tariff deadlines kept ~19 ships at anchor for a week.' },
];
writeFileSync(new URL('episodes.mock.json', SHARED), JSON.stringify(episodes, null, 1));

// Deterministic PRNG so mocks are stable across runs.
let seed = 42;
const rand = () => ((seed = (seed * 1664525 + 1013904223) % 2 ** 32) / 2 ** 32);
const lerp = (a, b, t) => a + (b - a) * t;

// Boxes from CLAUDE.md (approximate).
const ANCH = { lat: [33.60, 33.72], lon: [-118.30, -118.00] };
const BERTH = { lat: [33.72, 33.77], lon: [-118.27, -118.17] };
const SEA = { lat: 33.56, lon: [-118.30, -118.00] }; // southern entry edge
const pt = (box) => [lerp(...box.lat, rand()), lerp(...box.lon, rand())];

function replayDay(date, nShips) {
  const rows = [];
  const t0 = Date.parse(date + 'T00:00:00Z');
  for (let i = 0; i < nShips; i++) {
    const mmsi = 366000000 + Math.floor(rand() * 999999);
    const name = `MOCK VESSEL ${i + 1}`;
    const anchor = pt(ANCH), berth = pt(BERTH), sea = [SEA.lat, lerp(...SEA.lon, rand())];
    // Phases in 10-min steps (144/day): [arrive?] -> anchored -> [to berth -> moored]
    const arrives = rand() < 0.3, berths = rand() < 0.35;
    const tArr = arrives ? Math.floor(rand() * 60) : -1;      // step reaching anchor
    const tLeave = berths ? 70 + Math.floor(rand() * 60) : 999; // step leaving anchor
    for (let s = 0; s < 144; s++) {
      let lat, lon, status, sog;
      if (arrives && s < tArr) {
        if (s < tArr - 12) continue; // not in bbox yet
        const f = 1 - (tArr - s) / 12;
        [lat, lon] = [lerp(sea[0], anchor[0], f), lerp(sea[1], anchor[1], f)];
        status = 0; sog = 11 + rand();
      } else if (s < tLeave) {
        [lat, lon] = [anchor[0] + (rand() - 0.5) * 0.002, anchor[1] + (rand() - 0.5) * 0.002];
        status = 1; sog = +(rand() * 0.3).toFixed(2);
      } else if (s < tLeave + 9) {
        const f = (s - tLeave) / 9;
        [lat, lon] = [lerp(anchor[0], berth[0], f), lerp(anchor[1], berth[1], f)];
        status = 0; sog = 6 + rand();
      } else {
        [lat, lon] = berth; status = 5; sog = 0;
      }
      rows.push({ mmsi, name, t: new Date(t0 + s * 600_000).toISOString().slice(0, 19) + 'Z',
        lat: +lat.toFixed(5), lon: +lon.toFixed(5), status, sog });
    }
  }
  return rows;
}

for (const [date, n] of [['2024-04-22', 26], ['2024-07-30', 24]]) {
  writeFileSync(new URL(`replay/${date}.mock.json`, SHARED), JSON.stringify(replayDay(date, n)));
}
console.log('mocks written to shared/');
