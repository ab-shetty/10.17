# San Pedro Bay Congestion Forecast (hackathon)

Forecast the number of cargo/tanker ships **at anchor** in San Pedro Bay (LA + Long Beach) 1, 2, 3 days ahead,
and beat the "tomorrow = today" baseline. Demo is a **2024 replay**, not live. Say so plainly.

## Status (data spike, 10:45 PDT): GO
- Source: NOAA MarineCadastre daily **GeoParquet broadcast points, 2024 only**:
  `https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/ais2024/ais-2024-MM-DD.parquet` (~227 MB/day, national).
- `pipeline/extract_ais.py` streams one day through DuckDB httpfs in **~4.5 s** → ~0.4 MB filtered. Full year ≈ 30 min.
  Full-year pull is running in background: `data/extract_2024.log`, output `data/ais/ais_lalb_YYYY-MM-DD.parquet`.
- **2025 is NOT available as daily points.** Only monthly *tracks* (lines) exist:
  `.../marinecadastre/aistrack/ais-track-2025-MM.parquet` (~1 GB/month). Possible holdout set; unverified.
- The old `coast.noaa.gov/.../AISDataHandler` zip links 404. Don't use them.
- Sanity check 2024-01-01: 41 vessels in box, 19 reporting status=1 (at anchor), sog ≈ 0.07.

## Status (A, 11:55 PDT)
- Full 2024 pulled (366 days, bbox to -117.95). `data/daily.parquet` + `shared/daily.json` built. Model trained on full year:
  **beats persistence at h=1/2/3 by only 2.4/1.9/1.6 % MAE** (92 test days, Oct–Dec) after fixing a leak (departures
  were known a day early; the earlier 8/5/5 % was inflated). Near-tie overall. `shared/preds.json`, `shared/metrics.json` real.
- **The 2024 anchored queue is ~74 % tankers** (11.3 of 15.3 on average). Frame it as "ships waiting at anchor", not "container queue".
- Validated against POLA's own daily Container Vessel Activity 2024 (`pipeline/pola_summary.py`, PDF in `data/ext/pola/`,
  hand-downloaded because Cloudflare blocks scripts): our ≥250 m cargo anchored count r = 0.49 with POLA container ships
  at anchor; our moored count r = 0.62 with POLA at berth.
- Extra features: KLGB observed fog (IEM ASOS), harbor wave buoy 46222 (NDBC) → `pipeline/ext_sources.py`.
- AIS outage 2024-12-25/26 (11–13 h coverage): arrivals/departures nulled there (`coverage_hours` column).
- **Big-move days** (queue moves ≥ 3 ships): model beats persistence by **18/23/24 %** MAE at h=1/2/3, direction right 67–82 %.
  That's the pitch number; the 5–8 % headline is diluted by quiet days where persistence is near-perfect.
- **Episodes = weather, not trade news.** In gales/heavy swell part of the anchored fleet weighs anchor and rides it out
  under way (in the bay or 20–30 nm offshore), then re-anchors; the model learned to expect the rebound. It does NOT
  foresee the gale itself (no weather-forecast input). POLA's Oct release: record volume "without a single ship backed up".
- In progress: approach-zone AIS pull (`pipeline/extract_approach.py`, ships 20–120 nm out = tomorrow's arrivals), resumable.
- Research notes: `pipeline/notes/port_events_2024.md` (events timeline), `pipeline/notes/aistrack2025.md` (2025 tracks: coarse only).
- Codespace RAM: the full-year build gets SIGTERM'd if run alongside 2+ extract workers. Run heavy jobs one at a time on 8 GB.

## Shared schema: `data/ais/*.parquet` (one file per day)
| col | type | notes |
|---|---|---|
| mmsi | int | vessel id |
| ts | timestamp | UTC, ~1-min cadence |
| lat, lon | double | from `ST_Y/ST_X(geometry)`; raw files have **no lat/lon columns** |
| sog, cog | float | knots, degrees |
| heading | int | 511 = unavailable |
| vessel_name, imo | varchar | |
| vessel_type | int | 70–79 cargo, 80–89 tanker (already filtered) |
| status | int | 0 under way, 1 at anchor, 5 moored, 8 sailing |
| length, width, draft | float/int | draft change on departure ≈ loaded/unloaded |

Read the whole year: `duckdb -c "select * from 'data/ais/*.parquet'"`.

## Derived tables (pipeline track owns these)
- `data/daily.parquet`: one row per UTC day (or local day, but pick one and keep it consistent):
  `date, n_anchored, n_moored, n_arrivals_24h, n_arrivals_48h, n_departures_24h, avg_wait_hours,
   wind_max_kts, gust_max_kts, visibility_min_m, dow, is_holiday, news_score`
- "At anchor" = `status = 1 AND sog < 0.5 AND inside ANCHOR_BOX AND NOT in a berth cell` (see Geography).
  Counts (`n_anchored`, `n_moored`) = mean over 24 hourly snapshots of distinct vessels. Days are **UTC**.
- Arrival = first ping of an mmsi in the bbox after ≥ 24 h absent. Wait = first anchored ping → first moored ping.

## Geography (fixed from the heatmap, `pipeline/figs/heatmap_status.png`)
- Study bbox: lat 33.55–33.80, lon -118.35 to **-117.95** (widened; real anchor clusters sit at lon -118.03).
- Rectangles don't work: the inside-breakwater anchorages (lat 33.72–33.75) sit right next to the terminals.
- ANCHOR_BOX: lat 33.58–33.77, lon -118.30 to -117.97 (`pipeline/build_daily.py`).
- Berth cells (data-driven, `data/berth_cells.parquet`): 0.002° grid cells with ≥ 30 status=5 pings where moored
  pings outnumber anchored ones, dilated 1 cell, minus any cell where status=1 pings outnumber status=5.

## Repo layout and ownership
```
pipeline/   [A] AIS extraction, daily feature table, weather pull (Open-Meteo, no key)
model/      [A] LightGBM h=1,2,3 + persistence baseline, backtest (train Jan–Sep, test Oct–Dec 2024)
signals/    [B] Claude-scored news → shared/news.json (stretch: vision on satellite)
web/        [B] map replay + forecast-vs-actual chart + explanation panel
shared/     COMMITTED small JSON contracts between A and B (see below). Keep each file < 5 MB.
data/       gitignored, per-machine raw parquet. Never commit it.
```
Don't import across folders. A and B only talk through `shared/` files.

## Two-person workflow (two branches, `main` = shared source of truth)
- Person A works on branch **`a-data`**, person B on **`b-web`**. Never commit directly on `main`.
- `main` holds what the other person can rely on: `CLAUDE.md`, the `shared/` contracts, and working code.
- Only edit files in your own folders. `shared/` files: one owner each (below). Disjoint folders = no merge conflicts.
- **Sync** (do it at every schedule checkpoint, and any time you update a `shared/` file the other person needs):
  ```
  git fetch origin && git merge origin/main   # take the other person's published work
  git push origin HEAD                        # back up your branch
  git push origin HEAD:main                   # publish (fast-forward). Rejected? the other person just
                                              # published: repeat from the top.
  ```
  Never force-push, rebase shared history, or `git reset` `main`.
- `CLAUDE.md` is edited only by **A**. B proposes changes in chat or in `NOTES-B.md`.
- Never commit `data/`, `.env`, or API keys. Use `ANTHROPIC_API_KEY` from env.
- When you change a `shared/` schema, update the **Contracts** table here (A) or tell A (B) in the same push.

### Contracts in `shared/`
| file | owner | shape | needed by |
|---|---|---|---|
| `shared/daily.json` | A | `[{date, n_anchored, n_moored, arrivals_24h, departures_24h, avg_wait_h, wind_max_kts, vis_min_m}]` | B chart, by 11:45 |
| `shared/preds.json` | A | `[{date, issued, h, actual, pred, baseline, top_features:[{name, label, phrase, value, shap}]}]` (**show `phrase`**: plain-English, direction-aware reason; current queue level is excluded as circular) (h = 1,2,3; `date` = target day, `issued` = date - h) | B chart + explanation, by 1:15 |
| `shared/metrics.json` | A | `{h: {mae_model, mae_baseline, n_test, skill_pct, mae_model_bigmove, mae_baseline_bigmove, n_bigmove, skill_pct_bigmove, direction_hit_bigmove}}` (skill_pct = 100·(1 − mae_model/mae_baseline); negative = loses. *_bigmove = only days where the queue moved ≥ 3 ships over the horizon; direction_hit = share where the predicted change had the right sign) | B header tiles |
| `shared/replay/YYYY-MM-DD.json` | A | `[{mmsi, name, t, lat, lon, status, sog, state}]`, 10-min downsample, only the story days. **Color by `state`** (anchored/moored/underway, same rules as the counts), not raw `status` | B map, by 12:30 |
| `shared/episodes.json` | A | `[{start, end, title, why, model_note, replay_days:[...]}]` 3 out-of-sample (Oct–Dec) weather-driven dips + rebounds. `replay_days` = which `shared/replay/*.json` exist for it | B story mode, by 2:00 |
| `shared/news.json` | B | `[{date, score, title, reason, url}]` | A as a feature (optional) |
B starts by committing **mock** versions of A's files that have exactly these shapes, so the UI never waits on A.
A overwrites them with real data. Mocks are tagged with `"mock": true` at the top level, or the file is named `*.mock.json`.

### Schedule (PDT). Hard stop 4:00.
| time | A: data + model | B: web + signals |
|---|---|---|
| 10:50–11:45 | Re-pull 2024 with lon widened to -117.95. Heatmap of status=1 to fix ANCHORAGE/BERTHS boxes. Build `daily.parquet` + weather. Commit `shared/daily.json`. | Scaffold `web/` (Vite + MapLibre + a chart lib). Commit mocks of all A files. Map of San Pedro Bay with dots from the mock replay. |
| 11:45–1:15 | Check the series variance (Risk 1). LightGBM h=1..3 + persistence. SHAP top-3. Commit `preds.json`, `metrics.json`. | Forecast-vs-actual chart, metric tiles, explanation panel (templated sentence from top_features). Start `signals/` news scoring. |
| 1:15–2:00 | Pick 2–3 spike episodes. Export `shared/replay/*` for those days plus `episodes.json`. Add `news_score` as a feature if B has it. | Story mode: pick an episode → map replay + chart scrubbed together. Commit `news.json`. |
| 2:00–2:45 | **Integrate on B's machine.** Both people. Fix whatever breaks end to end. | same |
| 2:45 | **MVP freeze.** Tag `git tag mvp && git push origin mvp`. Record backup demo video now. | same |
| 2:45–3:30 | Stretch ladder (below), A's items | Stretch ladder, B's items |
| 3:30 | **Hard freeze.** Only fixes after this. If a stretch item isn't done, revert to `mvp`. | same |
| 3:30–4:00 | Rehearse the 3-min pitch twice. Re-record video if the stretch made it in. | same |

### Stretch ladder (take in order, only after the `mvp` tag)
1. **[A] Harbor air quality closer (Plan B):** OpenAQ PM2.5/NO2 near Wilmington joined to n_anchored → `shared/air.json`. [B] adds the final-slide chart.
2. **[B] "Ask the port" panel:** Claude answers "why is the queue growing?" using that day's features + news as context.
3. **[A] 2025 holdout:** run the model on 2025 monthly track files (`aistrack/`) to show it generalizes.
4. **[B] What-if slider:** "+10 arrivals" or "fog closes pilot station" → re-run the model (A exports a tiny ONNX or a lookup grid).
5. **[B] Claude vision on 2–3 satellite terminal images** (yard fullness).

## Risks we know about
1. **2024 queue may be small.** The 2021–22 crisis had ~100 ships waiting; 2024 is mostly 10–30.
   If the daily series is flat, forecast **arrivals / berth occupancy / avg wait** instead, or frame as "spike" detection.
   Check the series variance in the first hour of model work.
2. Horizon is 1–3 days (shore receivers only). A longer horizon needs Port of LA Signal history (stretch).
3. Always report MAE vs persistence baseline. If we don't beat it, say so.

## Per-track starter prompts
- **pipeline:** "Using data/ais/*.parquet and the ANCHORAGE/BERTHS boxes in CLAUDE.md, build data/daily.parquet
  with the columns listed. First plot a heatmap of status=1 pings to confirm the boxes. Add hourly Open-Meteo
  history (wind, gusts, visibility) for 33.72,-118.20, aggregated per day."
- **model:** "Train LightGBM to predict n_anchored at t+1,t+2,t+3 from data/daily.parquet. Time-split
  (train Jan–Sep 2024, test Oct–Dec). Report MAE vs persistence. Save predictions to data/preds.parquet with
  SHAP top-3 features per row for the explanation panel."
- **web:** "Static page (Vite or plain HTML + MapLibre/deck.gl) that replays data/ais at 1 hour per second over
  San Pedro Bay, colored by status, with a forecast-vs-actual chart from data/preds.parquet."
- **signals:** "Collect 2024 Port of LA / Long Beach press releases and port-labor news (ILWU, tariffs). Have
  Claude score each for disruption risk 0–1 with a one-line reason. Write data/news.parquet (date, score, reason)."
- **Plan B / closer:** OpenAQ or AirNow PM2.5/NO2 for Wilmington/San Pedro, joined to n_anchored.
