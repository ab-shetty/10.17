# Post-freeze experiment scripts (A). Results: `pipeline/notes/wait_experiments.md`

Kept for reproducibility; none feeds `shared/`. They were run from a scratch folder (first argument `S`), which held:
`visits_crisis.parquet` (= `data/cache/wait_visits_ais_crisis.parquet` after
`python model/wait_forecast.py --refresh --start 2021-06-08 --end 2021-11-15 --out <S>/wait_crisis_wide.json`),
`wait_crisis_wide.json`, and `portwatch/lalb.json` (IMF PortWatch daily port calls for 'Los Angeles-Long Beach').
Run from the repo root.

| script | what | outcome |
|---|---|---|
| `far_inbound.py` | ships 60–140 nm out / ETA < 24 h vs next-day arrivals | ETA < 24 h: r = 0.48 (2024) |
| `wait_ml.py` | per-ship wait ML (LightGBM / ridge), absolute and relative targets | biased short; not adopted |
| `carrier_little.py`, `carrier_little_any.py` | per-carrier queue and recent-wait features | carrier recent wait informative in 2021 |
| `wait_ml2.py`, `wait_ml2_any.py` | carrier-aware anchor + LightGBM correction, rolling | +5.6 % vs ours in 2021; does not hold in 2024 |
| `terminal_feats.py` | terminals from berth positions, terminal-level estimates | not better than carrier-level |
| `arimax.py` | ARIMA / ARIMAX for the daily queue, rolling | no better than tomorrow = today |
| `holdout2023.py` | train on 2024, test on 2023 (needs a 2023 pull: `AIS_OUT=data/ais_2023 APPR_OUT=data/approach_2023 python pipeline/extract_csv2021.py 2023-01-01 2023-06-30`, then `build_daily.py` into `data/y2023/`) | not run (pull unfinished) |
