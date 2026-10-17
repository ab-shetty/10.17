// Loads the shared/ contracts. Real file first, then <name>.mock.json; reports which one it got.
const BASE = import.meta.env.BASE_URL;

async function getJSON(path) {
  try {
    const r = await fetch(BASE + path);
    if (!r.ok) return null;
    // Python's json.dumps writes bare NaN, which JSON.parse rejects; read those as null.
    return JSON.parse((await r.text()).replace(/\bNaN\b/g, 'null'));
  } catch {
    return null;
  }
}

// Mocks are either *.mock.json or carry "mock": true at the top level (then rows sit under data/rows).
function unwrap(j) {
  if (Array.isArray(j) || !j || !j.mock) return j;
  return j.data ?? j.rows ?? j.items ?? j;
}

export async function load(name) {
  const real = await getJSON(`${name}.json`);
  if (real) return { data: unwrap(real), mock: !!(real && real.mock) };
  const mock = await getJSON(`${name}.mock.json`);
  if (mock) return { data: unwrap(mock), mock: true };
  return null;
}

async function exists(path) {
  try {
    const r = await fetch(BASE + path, { method: 'HEAD' });
    return r.ok;
  } catch {
    return false;
  }
}

// Which replay days are on disk for these dates (real wins over mock).
export async function findReplays(days) {
  const found = await Promise.all(days.map(async (d) => {
    if (await exists(`replay/${d}.json`)) return { day: d, mock: false };
    if (await exists(`replay/${d}.mock.json`)) return { day: d, mock: true };
    return null;
  }));
  return found.filter(Boolean);
}

export function daysBetween(start, end) {
  const out = [];
  for (let t = Date.parse(start + 'T00:00:00Z'); t <= Date.parse(end + 'T00:00:00Z'); t += 864e5) {
    out.push(new Date(t).toISOString().slice(0, 10));
  }
  return out;
}

export function addDays(day, n) {
  return new Date(Date.parse(day + 'T00:00:00Z') + n * 864e5).toISOString().slice(0, 10);
}
