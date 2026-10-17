# Orders for the remote training session (Lambda A10 box), from A

You are a helper on person A's model track. Read `CLAUDE.md` first. Work on branch **`a-gpu`** (create it from
`origin/a-data`), commit only the files named below, and push that branch after every commit (`git push origin a-gpu`).
Never push to `main` or `a-data`, never force-push, never commit keys. A reviews and merges.

## Why this box
The models train on ~300 rows. A GPU does not make one fit faster. What this box adds is **cores**: run the
experiment grid below in parallel (`joblib` / `concurrent.futures`, one process per config, `n_jobs = cores - 2`,
set `OMP_NUM_THREADS=1` and LightGBM `n_jobs=1`, CatBoost `thread_count=1` inside each worker).
CatBoost `task_type="GPU"` is NOT worth it at this size; don't.

## Setup
```
pip install lightgbm catboost shap scikit-learn pandas pyarrow duckdb scipy joblib
```
Inputs are committed in `model/inputs/` (see its README). `model/train.py` takes them via `--daily` and `--weather`.

## The protocol (do not break it: it is what makes the numbers honest)
- Everything is **rolling-origin**: each test month is forecast by models fit on rows whose TARGET date is before that
  month (`train.main(..., rolling=True)`). Copy that logic; don't invent a different split.
- **Design window = 2024-04-01 .. 2024-09-30** (2024, target `n_anchored`, `model/inputs/daily_v2.parquet`).
  Choose every config ONLY on the design window. Rank by mean skill over h = 1, 2, 3 vs the best naive baseline,
  where the naive set includes `tonight` and `tonight_blend` (train.py adds them when `n_anchored_eod` exists).
- **Test window = 2024-10-01 .. 2024-12-31**: run ONLY the top 3 design configs plus the current default, once.
  Report all four, including the ones that lose. No re-ranking on test.
- **Crisis** (`model/inputs/crisis/daily_v2.parquet` when A pushes it, else `crisis/daily_a.parquet`; `--target n_waiting`,
  test from 2021-09-01, data ends where the pull ended): run the same top 3 + default once. Also report the
  pre-rule-change window (target dates <= 2021-11-15) separately.
- CIs: `train.block_bootstrap_skill` (7-day blocks). If a CI includes 0, the write-up says "no detectable difference".

## The grid (write `model/grid.py`; import from `train` instead of copying it; monkeypatch `train.PARAMS` / `fit_all`)
1. Data: `daily.parquet` (v1) vs `daily_v2.parquet` (+ end-of-day queue, ETA features).
2. Shrinkage: `shrink=False` vs `True` (`train.shrink_factor`); also a variant with 6 inner months.
3. LightGBM: num_leaves {3, 7, 15}, n_estimators {150, 300, 600}, learning_rate {0.03, 0.06}, min_child_samples {15, 30}.
4. CatBoost: depth {3, 4, 6}, iterations {300, 500, 1000}, l2_leaf_reg {3, 5, 10}. Sample ~20 combos at random (seed 0),
   don't run the full product.
5. Ridge alpha {10, 30, 100}.
6. Ensemble members: avg of {lgbm, cat, ridge} (current) vs {cat, ridge} vs {lgbm, ridge} vs ridge alone vs median of the 3.
7. Feature groups dropped one at a time: weather forecast (fc_*), observed weather, waves/fog, approach (offshore/inbound/eta),
   queue lags (anchored_chg_*), arrivals/departures.
8. Training window: all history vs the last 6 months only (concept drift).
9. Seeds: for the final top 3, repeat with seeds 0..4 and report the spread.
Total budget: as many configs as fit in ~45 min of wall clock. Log every config to `data/grid/results.csv`
(gitignored) and checkpoint so a crash loses nothing.

## Deliverables (commit + push to `a-gpu`)
- `model/grid.py`
- `pipeline/notes/grid_results.md`: a table of the top 15 design configs (h = 1/2/3 skill + CI), then the test and
  crisis tables for the top 3 + default, then plain sentences: what helped, what didn't, and how big the gain is vs
  noise. Say plainly if nothing beats the default.
- Do NOT edit `model/train.py`, `shared/`, or `CLAUDE.md`. If you think train.py needs a change, describe it in the notes.

## Context you need
- Current 2024 result (default, v1 data): h=1 +10.7 % [+3.3, +17.5] vs the best day-mean naive rule (blend), Oct–Dec.
- On Apr–Sep the same model LOSES (h=1 about −10 %): the win is winter storms + the day-ahead HRRR gust forecast.
- The new `tonight` baseline (tomorrow = the queue at the end of today) beats every day-mean rule at h=1 by ~15 %.
  Beating it is the real bar.
- Sonnet's stacking experiments (`model/experiments_stacking.py`): pooled horizons, pooling 2024 into the crisis,
  NNLS/ridge meta-learners and Holt don't beat avg beyond noise. Don't redo them.
