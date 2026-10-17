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
- "At anchor" = `status = 1 AND sog < 0.5 AND inside an ANCHORAGE box`. Status alone is noisy:
  some ships leave status=1 on at berth, which the box filter catches.
- Arrival = first ping of an mmsi in the bbox after ≥ 24 h absent. Wait = first anchored ping → first moored ping.

## Geography (approximate, check them against the 2024 anchored-ping heatmap and adjust)
- Study bbox: lat 33.55–33.80, lon -118.35 to **-118.05**. Ships at anchor appear right at lon -118.05/-118.06,
  so the eastern outer anchorages may be clipped. Consider widening to -117.95 and re-pulling (only ~30 min).
- ANCHORAGE (outside breakwater, LA+LB anchorages): lat 33.60–33.72, lon -118.30 to -118.05
- BERTHS (inside the breakwater / terminals): lat 33.72–33.78, lon -118.29 to -118.15
- Plot `status=1` pings first, then fix these boxes. Don't trust the numbers above blindly.

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

## Two-person workflow (one `main` branch, two machines, two Claude Code sessions)
Rules for both Claude sessions:
- Work directly on `main`. Only edit files in your own folders. `shared/` files: one owner each (below).
- Commit small and often. Always `git pull --rebase origin main` right before `git push origin main`.
- `CLAUDE.md` is edited only by **A**. B proposes changes in chat or in `NOTES-B.md`.
- Never commit `data/`, `.env`, or API keys. Use `ANTHROPIC_API_KEY` from env.
- When you change a `shared/` schema, update the **Contracts** table here (A) or tell A (B) in the same push.

### Contracts in `shared/`
| file | owner | shape | needed by |
|---|---|---|---|
| `shared/daily.json` | A | `[{date, n_anchored, n_moored, arrivals_24h, departures_24h, avg_wait_h, wind_max_kts, vis_min_m}]` | B chart, by 11:45 |
| `shared/preds.json` | A | `[{date, h, actual, pred, baseline, top_features:[{name, value, shap}]}]` (h = 1,2,3) | B chart + explanation, by 1:15 |
| `shared/metrics.json` | A | `{h: {mae_model, mae_baseline, n_test}}` | B header tiles |
| `shared/replay/YYYY-MM-DD.json` | A | `[{mmsi, name, t, lat, lon, status, sog}]`, 10-min downsample, only the story days | B map, by 12:30 |
| `shared/episodes.json` | A | `[{start, end, title, why}]` 2–3 spike stories | B story mode, by 2:00 |
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
