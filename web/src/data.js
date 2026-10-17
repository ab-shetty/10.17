// Loads the shared/ contracts. A's real file wins; falls back to the *.mock.json version.

// Python's json.dump writes bare NaN/Infinity, which JSON.parse rejects. Treat them as null.
const parseLoose = (text) => JSON.parse(text.replace(/\b(NaN|-?Infinity)\b/g, 'null'));

async function fetchJSON(path) {
  const res = await fetch(path);
  if (!res.ok) return null;
  return parseLoose(await res.text());
}

export const mockFiles = new Set();

// Returns the parsed contract (unwrapping a top-level {mock: true, data: [...]} if present), or null.
export async function load(name) {
  let data = await fetchJSON(`/${name}.json`);
  if (data == null) {
    data = await fetchJSON(`/${name}.mock.json`);
    if (data != null) mockFiles.add(name);
  }
  if (data && !Array.isArray(data) && data.mock) {
    mockFiles.add(name);
    data = data.data ?? data;
  }
  return data;
}

export function datesBetween(start, end) {
  const out = [];
  for (let t = Date.parse(start); t <= Date.parse(end); t += 86_400_000)
    out.push(new Date(t).toISOString().slice(0, 10));
  return out;
}
