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

## ⚠ For the Overseer / crisis data (A, 12:10 PDT): count LOITERING ships, not only anchored ones
- Checked raw NOAA AIS for the peak day **2021-10-25** (`pipeline/check_crisis_box.py`, fig `pipeline/figs/crisis_anchor_check.png`):
  our boxes catch every status=1 ship (56 distinct anchored ships, all inside ANCHOR_BOX), and ~60 more cargo/tankers
  were drifting slowly outside the bay, ~95 % of them within 60 nm. With the pipeline's own definition (hourly mean,
  `pipeline/build_daily.py`): **48 anchored + 54 loitering = 102.5 vs the Marine Exchange's 56 at anchor + 51 in
  holding areas = 107** (gCaptain; `pipeline/notes/crisis_timeline_2021.md`). A bay-only count misses half the queue.
  (The famous "109" is a DIFFERENT count, 2022-01-09, after the Nov-16 rule: it includes ships 150+ nm out that shore
  AIS can't see. On 2022-01-12 only 11 of 104 were within 40 mi. Don't mix them.)
- So for 2021–22 the target should be **n_waiting = n_anchored + offshore_waiting**, where offshore_waiting = hourly mean
  of distinct cargo/tanker ships < 60 nm from (33.70, -118.20), outside the study bbox, SOG < 3 kn — the same definition
  as `pipeline/extract_approach.py` + `build_daily.py`. Pull box for that: lat 32.5–34.6, lon -121.0 to -117.2.
  Please add `offshore_waiting` (and `inbound_60nm`) columns to `shared/crisis/daily.parquet`; A will model n_waiting.

## Status (A, 2:55 PDT): the climax is the WAIT result, not the 1-day count forecast
- **Published wait ran short through the build-up** (`shared/crisis/wait.json`, `model/wait_forecast.py`, container-size
  ships joining Sep–Oct 2021): reported 7-day wait −2.5 d bias (below the real wait in **all 9 weeks**); queue ÷ berthing
  rate (Little's law, AIS only) bias +0.1 d. Little is not more accurate day to day (MAE 4.3 vs 3.8 d); the result is the bias.
  Week of Oct 18: real 17.8 d, reported 12.8, Little 17.3.
- **Validated vs what the port said**: our reported-7d series ≈ published figures (Aug 15: ours 6.5 vs 6.8 published;
  Sep 9: ours 7.1 (≈7.3 over 30 d) vs POLA 30-day 8.5; Oct 14: ours 13.9 vs NBC4 12). Ships joining Sep 9–15 really waited 10.5 d
  (`pipeline/notes/wayback_2021.md`).
- **Issued while the ship is still at sea** (estimate made k days before it joins, `wait.json` daily shifted, Sep–Oct 2021):
  bias ours / published: 3 d −0.1 / −2.8; 7 d **−0.8 / −3.1**; 14 d −1.8 / −3.7. Accuracy edge only clears noise at 14 d
  (+19 % [+7, +32]); at 1 d ours loses (−14 %).
- **2024 control** (`shared/wait.json`): reported bias 0.00 d in steady weeks, −1.0 d when the queue grew, +1.2 d when it shrank:
  the published figure is fine in calm times and lags exactly when the queue moves.
- **Cost of the gap** (net understatement, bias × 437 visits, Sep–Oct 2021 only): **893 ship-days ≈ 6,500 t fuel ≈ $5.1 M,
  200 t NOx, 21 kt CO2** (priced at the Sep–Oct fleet mix, 7.3 t fuel/ship-day; was $4.9 M / 192 t with the whole-file average) of idling nobody planned for. 2024: −18 ship-days (≈ 0). Per-ship sums mostly reflect scatter of individual waits.
  Total burned at anchor in the crisis: `shared/crisis/emissions.json` fuel_t × $780/t (not all avoidable).
- **Post-freeze experiments (A, `pipeline/notes/wait_experiments.md`)**: 80 % ranges for each ship's wait
  (`model/wait_intervals.py`) are calibrated in both years: 85 % of real waits inside in the 2021 crisis, 84 % in 2024.
  Ranges built on the published figure fall to 69 % coverage by Nov 2021. ML per ship, carrier/terminal-level estimates and
  ARIMA did not beat the existing figures. **For the Overseer to decide:** add the range (`lo_d`, `hi_d`) to
  `shared/crisis/wait.json` for the demo, or leave the demo as is. Not in `shared/` yet.
- **Crisis count forecast, honest** (`shared/crisis/metrics.json`, full run 2021-06-01..2022-03-31, rolling from Sep 2021):
  a day ahead, nothing seen from shore beats tomorrow = today: h=1 +0.5 % [−6.4, +4.8], h=2 −1.7 %, h=3 −6.0 % (no detectable
  difference; pre-rule-change window h=1 −3.0 %). The queue moved in steps set weeks earlier in Asia.
  Fuel burned at anchor over those 304 days: 71,216 t ≈ **$55 M** at $780/t, 2,162 t NOx (total, not all avoidable).
  2024 stays the proof of skill (h=1 +10.7 %, Oct–Dec). But on Apr–Sep 2024 the same model does NOT beat the naive rules
  (h=1 ≈ −10 %): the 2024 win is winter storms + the day-ahead HRRR gust forecast.
- Lead-day stories (`crisis/episodes.json`) are weak: the forecast was only 1–2 ships above the naive rules.
- AIS receiver outages in NOAA's own data (2022-01-08/09: national file full size, 0–5 h in the bay) are nulled (`outage`).
- New, NOT in `shared/` (post-demo): end-of-day queue + ETA features (`inbound_eta24`: r = 0.48 with next-day arrivals in 2024)
  and a `tonight` naive baseline that beats every day-mean rule at h=1 by ~15 %. Grid search on a remote box: `model/GPU_ORDERS.md`.

## Status (A, 12:00 PDT)  — HEADLINE is now the 2021–22 backlog (see OVERSEER.md); 2024 = "works in normal times"
- Full 2024 pulled (366 days, bbox to -117.95), plus an **approach zone** (ships 20–120 nm out, `data/approach/`).
- Model: LightGBM + CatBoost + ridge predicting y[t+h] − blend(persistence, 7-day mean); per-horizon choice by
  rolling-origin CV on the 3 months before test. `model/train.py --daily --weather --test-start --out-prefix`.
- **2024 test (Oct–Dec, 92 days) vs the BEST naive baseline**, rolling-origin (refit before each month, model fixed
  in advance = plain average): **h=1 +10.7 % [90 % CI +3.3, +17.5]; h=2 +6.3 %, h=3 +2.8 % (CIs include 0: no detectable difference).**
  Vs persistence alone: +17 / +19 / +15 %.
  **Honest caveats (from the code review, `pipeline/notes/code_review.md`):**
  - The h=1 win is mostly the **day-ahead gust forecast**. Open-Meteo's default ("gfs_seamless") uses HRRR for day 1:
    a real forecast issued ≥ 24 h ahead (no leakage), and markedly better than global GFS. With pure global GFS instead,
    h=1 = +6.2 % [−2.1, +12.5]; without any forecast features +1.6 % [−6.4, +7.0] (no detectable difference). Say: "it wins by reading
    tomorrow's weather forecast the way a pilot would".
  - Storm-day numbers (n = 10 days) are ~3 events. Too few for a reliable percentage.
  - The Oct–Dec window was also used for design choices (features, the 25 kn cut, rolling vs split). One winter quarter.
- `offshore_waiting` now excludes moored ships, Port Hueneme and the El Segundo terminal (they were 68 % of it in 2024);
  2024 mean 8.0 → 2.4, and it became a better predictor (corr with tomorrow's change 0.13 → 0.25).
- Best new signal: **ships inbound within 60 nm** (corr 0.18 with tomorrow's queue change, more than today's arrivals).
- **The 2024 anchored queue is ~74 % tankers** (11.3 of 15.3 on average). It is not a container queue.
- Plausible agreement with POLA's own daily Container Vessel Activity 2024 **on the container slice only** (the 74 % tanker
  share has no independent daily check; total n_anchored vs POLA r = −0.01) (`pipeline/pola_summary.py`, PDF in `data/ext/pola/`,
  hand-downloaded because Cloudflare blocks scripts): our ≥250 m cargo anchored count r = 0.49 with POLA container ships
  at anchor; our moored count r = 0.62 with POLA at berth.
- **Episodes = weather, not trade news.** In gales/heavy swell part of the anchored fleet weighs anchor and rides it out
  under way (in the bay or 20–30 nm offshore), then re-anchors; the model learned to expect the rebound. It does NOT
  foresee the gale itself (no weather-forecast input). POLA's Oct release: record volume "without a single ship backed up".
- Extra features: KLGB observed fog (IEM ASOS), harbor wave buoy 46222 (NDBC) → `pipeline/ext_sources.py`.
- AIS outage 2024-12-25/26 (11–13 h coverage): arrivals/departures nulled there (`coverage_hours` column).
- Research notes: `pipeline/notes/port_events_2024.md` (events timeline), `pipeline/notes/aistrack2025.md` (2025 tracks: coarse only).
- Codespace now 16 GB. Next for A: emissions at anchor (OVERSEER bet 1), inbound ships in replay files.

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
| `shared/preds.json` | A | `[{date, issued, h, actual, pred, baseline, baseline_name, persistence, top_features:[{name, label, phrase, value, shap}]}]` (h = 1,2,3; `date` = target day, `issued` = date − h; `baseline` = the best naive baseline on the test set, named in `baseline_name`: persistence / ma7 / blend. **Show `phrase`**: plain-English, direction-aware reason; current queue level excluded as circular) | B chart + explanation, by 1:15 |
| `shared/metrics.json` | A | `{h: {mae_model, mae_baseline, baseline, n_test, skill_pct, skill_ci90:[lo,hi], skill_vs_persistence_pct, baselines_mae:{persistence, ma7, blend}, model, cv_mae, test_mae_all, n_storm?, mae_model_storm?, mae_baseline_storm?, skill_pct_storm?}}`. skill_pct = 100·(1 − mae_model/mae_baseline) vs the **best** baseline; negative = loses. skill_ci90 = 7-day block-bootstrap. Storm days = forecast gust ≥ 25 kn, known on the issue day (2024 only) | B header tiles |
| `shared/replay/YYYY-MM-DD.json` | A | `[{mmsi, name, t, lat, lon, status, sog, state}]`, 10-min downsample, only the story days. **Color by `state`**: anchored / moored / underway inside the bay (same rules as the counts), plus ships within 60 nm outside the bay: **inbound** (≥ 6 kn, heading for the bay) / **waiting_offshore** (< 3 kn) / **other_terminal** (moored, Port Hueneme, El Segundo terminal: not waiting for us; draw faint or hide) / passing — same definitions as the model features. Not raw `status` | B map, by 12:30 |
| `shared/episodes.json` | A | `[{start, end, title, why, model_note, replay_days:[...]}]` 3 out-of-sample (Oct–Dec 2024) weather-driven dips + rebounds | B story mode, by 2:00 |
| `shared/news.json` | B | `[{date, score, title, reason, url}]` | B explanation panel + chart ticks, **context only**. Tested as a model feature: ±1 % skill, inside the CI → not used (A applied this in `model/train.py`) |
| `shared/emissions.json` (+ `shared/crisis/emissions.json`) | A | `{summary:{start, end, days, ship_days_at_anchor, nox_t, pm25_t, co2_t, fuel_t, nox_kg_per_ship_day, peak_day, peak_day_nox_kg, method, scope, cross_check}, daily:[{date, ship_hours, nox_t, pm25_t, co2_t, fuel_t, ship_days}]}`. Every anchored cargo ship + tanker in the bay × POLA-inventory loads/factors. Quote `scope` with the number | B closing slide |
| `shared/crisis/daily.json`, `daily.parquet` | A (`model/run_crisis.sh`) | same columns as `shared/daily.json` / `data/daily.parquet`, 2021-06-01..2022-03-31, + `outage` (bool: local AIS receiver outage, queue counts null that day, e.g. 2022-01-08/09) and `regime` (`before_150nm_rule` / `after_150nm_rule`, switch 2021-11-16) | A model, B chart |
| `shared/crisis/weather_daily.json` | A | `[{date, wind_max_kts, gust_max_kts, visibility_min_m, fc1..3_gust_max_kts, fc1..3_wind_max_kts}]` (fc* are null before 2024-01-19: no archived forecasts) | A model |
| `shared/crisis/preds.json`, `metrics.json` | A | same shapes as `shared/preds.json` / `metrics.json` (no storm metric: no archived forecasts for 2021) | B crisis chart |
| `shared/crisis/chart.json` | A | `{target, window, note, events:[{date, label, note}], series:[{date, actual, forecast_1d, forecast_2d, tomorrow_equals_today, seven_day_mean, n_anchored, offshore_waiting, inbound_60nm, arrivals_24h, avg_wait_h}]}` Sep–Oct 2021: **the money shot** (forecast turns up before the queue; both naive rules lag). target = n_waiting = anchored + loitering < 60 nm | B crisis chart |
| `shared/crisis/episodes.json` | A | same shape as `shared/episodes.json` + `lead_score`; the 2–3 days where the 1-day forecast rose above both naive rules on a day the queue really rose. Weak: the forecast was only 1–2 ships above the naive rules | B story mode |
| `shared/crisis/hero_ship.json` | A | `{name, mmsi, length_m, join, berth, real_d, published_d, ours_d, gap_d, fuel_t, usd, nox_t, usd_slow_steam:[lo,hi], fuel_t_slow_steam:[lo,hi], slow_steam_note, note, published_d_def, ours_d_def}` (`usd` = anchor fuel only; `usd_slow_steam` = back-of-envelope saving at sea, a range): ONE example ship (MSC JOSSELINE, Oct 2021). `note`: it is mid-range, and ours beat the published figure for 52 % of October ships | B hook / pitch |
| `shared/crisis/wait.json` (Sep–Oct 2021), `shared/wait.json` (2024) | A (`model/wait_forecast.py`) | `{window, data_end, all, big_cargo, big_cargo_daily_mean, other, by_regime:{growing, steady, shrinking}, gap_cost:{reported, little, net_understatement:{ship_days, fuel_t, fuel_usd_m, nox_t, co2_t, note}, note}, daily:[{date, ships_waiting_eod, berths_per_day_7d, little_wait_d, reported_wait_7d, actual_wait_of_ships_joining_next_day}], weekly:[{week, real_d, reported_d, little_d, n}]}`. Score blocks: `{n, actual_mean_d, mae_little_d, mae_reported_d, bias_little_d, bias_reported_d, skill_pct}`. real = actual wait of container-size ships joining that week; reported = trailing 7-day mean wait of ships that berthed (what was published); little = queue ÷ berthings per day | B wait chart |
| `shared/crisis/replay/YYYY-MM-DD.json` | A (`model/run_crisis.sh`) | same shape as `shared/replay/` | B map |
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
