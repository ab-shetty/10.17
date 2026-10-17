import maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';

export const STATE_COLORS = { anchored: '#f5a524', moored: '#38bdf8', underway: '#9aa4b2' };
const ANCHOR_BOX = [[-118.30, 33.58], [-117.97, 33.58], [-117.97, 33.77], [-118.30, 33.77], [-118.30, 33.58]];

const STYLE = {
  version: 8,
  sources: {
    // Esri dark gray canvas: no API key. (CARTO tiles now return an "API KEY REQUIRED" watermark.)
    basemap: {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      maxzoom: 16,
      attribution: 'Esri, HERE, Garmin, © OpenStreetMap contributors',
    },
  },
  layers: [
    { id: 'bg', type: 'background', paint: { 'background-color': '#0b1622' } },
    { id: 'basemap', type: 'raster', source: 'basemap' },
  ],
};

export function createMap(el) {
  const map = new maplibregl.Map({
    container: el,
    style: STYLE,
    bounds: [[-118.33, 33.56], [-117.94, 33.79]], // study bbox, anchorage box fully in view
    fitBoundsOptions: { padding: 12 },
    attributionControl: { compact: true },
  });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), 'top-right');

  // 'style.load', not 'load': 'load' waits for basemap tiles, and the dots must draw even offline.
  const ready = new Promise((resolve) => map.once('style.load', () => {
    map.addSource('box', { type: 'geojson', data: { type: 'Feature', geometry: { type: 'LineString', coordinates: ANCHOR_BOX } } });
    map.addLayer({ id: 'box', type: 'line', source: 'box',
      paint: { 'line-color': '#f5a524', 'line-opacity': 0.45, 'line-width': 1.2, 'line-dasharray': [3, 3] } });
    map.addSource('ships', { type: 'geojson', data: { type: 'FeatureCollection', features: [] } });
    map.addLayer({ id: 'ships', type: 'circle', source: 'ships', paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 9, 3, 13, 7],
      'circle-color': ['match', ['get', 'state'],
        'anchored', STATE_COLORS.anchored, 'moored', STATE_COLORS.moored, STATE_COLORS.underway],
      'circle-stroke-color': '#0b1622', 'circle-stroke-width': 1,
    } });
    resolve();
  }));

  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 8 });
  map.on('mousemove', 'ships', (e) => {
    const p = e.features[0].properties;
    map.getCanvas().style.cursor = 'pointer';
    popup.setLngLat(e.lngLat)
      .setHTML(`<b>${escapeHtml(p.name || String(p.mmsi))}</b><br>${p.state} · ${p.sog} kn`)
      .addTo(map);
  });
  map.on('mouseleave', 'ships', () => { map.getCanvas().style.cursor = ''; popup.remove(); });

  return { map, ready };
}

// Group replay rows into 10-minute frames of GeoJSON. A vessel missing from a bucket keeps its last
// position for up to an hour (HOLD frames) so dots don't blink between sparse AIS pings.
const HOLD = 6;

export function buildFrames(rows) {
  const byT = new Map();
  for (const r of rows) {
    if (!byT.has(r.t)) byT.set(r.t, []);
    byT.get(r.t).push(r);
  }
  const last = new Map(); // mmsi -> { r, i }
  return [...byT.keys()].sort().map((t, i) => {
    for (const r of byT.get(t)) last.set(r.mmsi, { r, i });
    const features = [];
    const counts = { anchored: 0, moored: 0, underway: 0 };
    for (const [mmsi, v] of last) {
      if (i - v.i > HOLD) { last.delete(mmsi); continue; }
      const r = v.r;
      const state = r.state in counts ? r.state : 'underway';
      counts[state]++;
      features.push({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [r.lon, r.lat] },
        properties: { mmsi: r.mmsi, name: r.name, state, sog: r.sog },
      });
    }
    return { t, fc: { type: 'FeatureCollection', features }, counts };
  });
}

export function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
