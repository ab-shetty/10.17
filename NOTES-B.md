# Notes from B (web + signals)

## For A (2:15 PDT)
- **`shared/crisis/wait.json` is live in the UI** (2021 view): bias tiles, a weekly chart (real / published / ours)
  and a per-day "a ship joining today" block. Until `weekly` exists, the UI computes weekly means of the daily rows
  inside `window`. `weekly` in the Overseer's shape `[{week: "YYYY-MM-DD" (Monday), real_d, reported_d, little_d, n}]`
  is picked up with no code change (tested with a stand-in).
- **Oct 13 2021 looks like a data gap:** `ships_waiting_eod` = 11 (neighbours 48–59), so `little_wait_d` = 2.66 vs a
  real 18.14 d. That one day adds ~0.26 d to Little's MAE (15.5 d / 59 days). Probably missing hour-23 pings; if so,
  fall back to the latest hour with data, or mark the day null. Also visible as a spike in the queue chart.
- The 2021 view switches on when `crisis/daily.json` **or** `crisis/wait.json` exists. Without `crisis/daily.json`
  the queue line comes from `wait.daily.ships_waiting_eod` (container-size ships only). When `crisis/daily.json`,
  `preds.json` and `metrics.json` land, the queue chart, forecasts and a "Queue, day +1" tile appear automatically.
- **Crisis daily.json:** the 2021 chart stacks `n_anchored` + `offshore_waiting` under the total and marks 2021-11-16.
  It needs both columns. Missing dates show as gaps (the x-axis is continuous).
- Replay `state` handled: anchored, moored, underway, inbound, waiting_offshore, passing, other_terminal (faint,
  uncounted). Baseline labels come from `baseline_name`; tiles say "no detectable difference" when the CI spans 0.

## Running the web app
```
cd web && npm install && npm run dev     # http://localhost:5173, serves shared/ as the static root
npm run build                            # static site in web/dist (includes shared/)
```
Basemap is Esri World Dark Gray raster tiles (no key; needs internet; CARTO now requires a key). Dots, counts and the chart still work without tiles.

## Signals
`python signals/score_news.py` writes `shared/news.json` from `signals/sources.json` + the score cache
`signals/scored.json`. The current scores were made in-session by Claude without an API key (labelled in
`scorer`). With `ANTHROPIC_API_KEY` set, `--rescore` re-scores every item through the API.
