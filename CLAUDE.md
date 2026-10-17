# San Pedro Bay Congestion Forecast (hackathon)

Forecast the number of cargo/tanker ships **at anchor** in San Pedro Bay (LA + Long Beach) 1, 2, 3 days ahead,
and beat the "tomorrow = today" baseline. Demo is a **2024 replay**, not live. Say so plainly.

## Status (data spike, 10:55 PDT): GO
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

## Repo layout (one folder per track, avoid stepping on each other)
```
pipeline/   AIS extraction, daily feature table, weather pull (Open-Meteo, no key)
model/      LightGBM h=1,2,3 + persistence baseline, time-split backtest (train Jan–Sep, test Oct–Dec)
signals/    Claude-scored news/press releases → daily news_score (stretch: vision on satellite)
web/        map replay of ship dots + forecast-vs-actual chart + explanation panel
data/       gitignored; parquet outputs
```
Contracts between tracks are files in `data/`. Don't import across folders.

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
