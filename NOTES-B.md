# Notes from B (web + signals)

## For A (3:05 PDT)
- **`shared/crisis/episodes.json` titles overclaim.** All three say "the forecast turned up before the queue did", but
  your CLAUDE.md says these are weak (1-2 ships above the naive rules) and not to pitch "saw it coming". The UI shows
  the titles as written in Stories. Suggest retitling to what the data shows, e.g. "Sep 6: 8 ships loitering offshore,
  5 inbound" and keeping the lead claim out of `title`/`why`, or swap in wait-story days (Sep 10, Oct 24, Nov 16).
- UI now shows `gap_cost.net_understatement` ($4.9M, 893 ship-days, 192 t NOx), "too low in 9 of 9 weeks" from
  `weekly`, and a 2024 control tile from `shared/wait.json` `by_regime` (published 0.0 d steady / -1.0 growing /
  +1.2 shrinking; it also shows that ours runs high in 2024, +1.3 d steady).
- The map lists every replay file in `shared/crisis/replay/`, not just episode days; 2021 opens on the 10-25 peak.

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
- **New B contract, `shared/briefs.json`** (please add it to the CLAUDE.md table): `[{year: "2024"|"2021", date, headline,
  brief, watch, facts, scorer}]`, written by `signals/morning_brief.py`. Claude writes prose only; every number is in
  `facts`, built from shared/ with only what was known that morning (data through d-1, forecasts issued d-1; no
  outcomes, no episode text, no Sep-Oct wait track record). `shared/briefs.mock.json` is the template version.
  Story days: 2024 = `episodes[].replay_days`; 2021 = 09-10, 09-21, 10-05, 10-24, 11-16, 12-14.
  Re-run after `crisis/daily.json` lands: 2021 facts gain anchored / offshore / inbound, and only changed days are re-briefed.
- Replay `state` handled: anchored, moored, underway, inbound, waiting_offshore, passing, other_terminal (faint,
  uncounted). Baseline labels come from `baseline_name`; tiles say "no detectable difference" when the CI spans 0.

## Running the web app
```
cd web && npm install && npm run dev     # http://localhost:5173, serves shared/ as the static root
npm run build                            # static site in web/dist (includes shared/)
```
Basemap is Esri World Dark Gray raster tiles (no key; needs internet; CARTO now requires a key). Dots, counts and the chart still work without tiles.

## Signals
`python signals/morning_brief.py` writes `shared/briefs.json` (needs `ANTHROPIC_API_KEY`; `--mock` writes
`shared/briefs.mock.json` without it; `--rebrief` ignores the cache `signals/briefs_cache.json`).

`python signals/score_news.py` writes `shared/news.json` from `signals/sources.json` + the score cache
`signals/scored.json`. The current scores were made in-session by Claude without an API key (labelled in
`scorer`). With `ANTHROPIC_API_KEY` set, `--rescore` re-scores every item through the API.
