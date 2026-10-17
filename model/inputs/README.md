# Model inputs (small derived daily tables, copied from `data/` so a remote machine can train without the raw AIS)
Rebuilt by A with `pipeline/build_daily.py` (needs raw AIS, which stays in gitignored `data/`). Refresh = copy again.
- `daily.parquet`: 2024, the table behind the published 2024 metrics (no end-of-day / ETA columns).
- `daily_v2.parquet`: 2024 + `n_anchored_eod`, `offshore_waiting_eod`, `n_waiting_eod` (mean of the day's last 3 hourly
  snapshots), `inbound_eta24` (ships heading in that would arrive within 24 h at current speed), `inbound_60_140`.
- `weather_daily.parquet` (Open-Meteo, fc1..3 = gfs_seamless incl. HRRR), `weather_gfsglobal.parquet` (pure GFS ablation),
  `ext_daily.parquet` (KLGB fog, buoy 46222 waves).
- `crisis/daily_a.parquet`: 2021-06-01 .. (as far as the pull got), target `n_waiting`; `crisis/weather_daily.parquet`
  (no archived forecasts before 2024), `crisis/ext_daily.parquet`.
