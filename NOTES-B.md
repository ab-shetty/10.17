# Notes from B (web + signals)

## For A
- **`shared/preds.json` contains bare `NaN`** (31 × `net_inflow_3d` values, mid-Oct, probably the AIS gap days).
  That's not valid JSON, so `JSON.parse` fails in the browser. The web loader now maps `NaN` → `null` as a stopgap,
  but please write `null` (e.g. `df.to_json` or `json.dumps(..., allow_nan=False)` after `fillna(None)`).
- Waiting on `shared/episodes.json` and `shared/replay/*.json`. Until then the UI uses
  `shared/episodes.mock.json` and `shared/replay/2024-{03-01,04-22,07-30}.mock.json` (badged MOCK in the UI).
  Real files win automatically, no code change needed. The map loads replay days that fall inside an episode's
  `[start, end]`, so export at least one replay day per episode.
- `shared/news.json` is real (15 sourced items, from `pipeline/notes/port_events_2024.md`). Optional `news_score` feature.
  Dates are publication dates (the press release date in the URL where there is one).

## Running the web app
```
cd web && npm install && npm run dev     # http://localhost:5173, serves shared/ as the static root
npm run build                            # static site in web/dist (includes shared/)
```
Basemap is CARTO dark raster tiles (needs internet). Dots, counts and the chart still work without tiles.

## Signals
`python signals/score_news.py` writes `shared/news.json` from `signals/sources.json` + the score cache
`signals/scored.json`. The current scores were made in-session by Claude without an API key (labelled in
`scorer`). With `ANTHROPIC_API_KEY` set, `--rescore` re-scores every item through the API.
