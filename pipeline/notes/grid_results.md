# Grid results (model/grid.py, 677 design configs, rolling-origin)

**Bottom line: nothing beats the default. Keep `train.py` as is (v2 data, lgbm+cat+ridge average, no shrink).**
The design-window "winners" are an artifact of the baseline set, and on absolute error they are worse than the default.

## What the numbers say, in plain words
- The top 15 design configs (+3.9 to +4.5 % mean skill) are ALL `daily.parquet` (v1) with shrinkage 3 or 6 months.
  v1 has no end-of-day column, so its naive set lacks `tonight` / `tonight_blend`, the hardest rules at h=1. Skill is
  measured against a weaker opponent, so v1 looks better. On raw error v1 is **worse**: design h=1 MAE 1.720 (v1) vs
  1.567 (v2 default). Skill values are not comparable across the v1/v2 rows; MAE is.
- Test window (run once): default h=1 MAE 1.506; the three design "winners" 1.77-1.83. The default wins on absolute error
  at every horizon it was tested on. Its h=1 skill (+9.6 % [+1, +16], vs tonight_blend) is against a harder baseline than the
  winners' (+5.8 to +9.1 % vs blend, whose MAE is 1.944).
- Design-window CIs of the top configs are wide: h=1 about [-2, +11], mostly including 0. Their differences from each other
  (4.5 vs 3.9) are well inside noise; the pick of "top 3" out of 677 tries is subject to selection bias (winner's curse).
- Seeds 0-4 barely matter: sd of design mean skill 0.0-0.2 points. Seed noise is not the problem; sample size is.
- Crisis (n_waiting, no weather forecasts, 2021): the default LOSES to persistence at every horizon
  (h=1 -5.1 % [-14, -0], significant); the shrunk configs lose less (-1.6 to -2.1 %, CI includes 0 = "no detectable
  difference" from persistence). Pre-rule-change window (<= 2021-11-15): same picture (default -6.7 % [-15, -1];
  shrunk -3.7 to -4.4 %, CI includes 0; rand419 h=3 +6.3 % [-4, +14], includes 0). Shrinkage helps here because it
  falls back to the naive anchor when the model has nothing to add. That is "loses less", not "wins".
- What helped / didn't (one-at-a-time, design mean skill vs default -1.4): shrinkage +1.3 (3 mo) / +1.2 (6 mo);
  `cat+ridge` instead of the 3-model average +1.2; dropping `arr_dep` +0.2; the rest (ridge alpha, 6-month training window,
  dropping fc / waves / approach / lags) are within +-1.3 and not distinguishable from noise; lgbm alone (-5.4) or
  ridge alone (-2.3) are clearly worse. Dropping the forecast-gust features changes the design window little, because
  Apr-Sep has almost no storms.
- Features NOT supported by this grid: a tuned LightGBM/CatBoost grid (num_leaves, n_estimators, lr, min_child_samples,
  depth, iterations, l2) moved results by less than the CI width. The model has ~300 rows; hyperparameters are not the lever.

## Suggestion for train.py (not applied)
Optional only, for the crisis target: `--shrink` already exists; it reduced losses vs persistence from -5 % to about -2 %.
Nothing in this grid justifies changing the 2024 default.

## Caveats
- Design window starts 2024-04-01 with only ~90 training rows for April (the protocol, as ordered).
- Random search covers LGBM x CatBoost x ridge x ensemble x shrink x feature-drop x data x window jointly (600 draws, seed 1)
  plus one-at-a-time rows and the 20 sampled CatBoost combos (seed 0); not the full product.
- Crisis data ends 2022-01-10 (`daily_a.parquet`); crisis uses v1-style columns only (no `_eod`), so the config's `data` field
  is ignored there. Crisis tests had no archived forecasts (fc features absent).
- Raw log: `data/grid/results.csv` (JSON lines, gitignored); final stage: `data/grid/final.csv`.

## Design window (2024-04..09), top 15 of 677, skill % vs best naive [90% CI]

| # | id | mean | h=1 | h=2 | h=3 | config |
|---|---|---|---|---|---|---|
| 1 | rand530 | +4.5 | +5.3 [-2, +11] | +3.2 [-1, +7] | +4.8 [-2, +10] | v1, shr3, cat+ridge, lgb7/600/0.03/30, cat3/300/5, ridge10, drop=None, win=all |
| 2 | rand419 | +4.5 | +5.3 [-0, +10] | +4.2 [-1, +8] | +3.9 [-2, +8] | v1, shr3, ridge, lgb15/300/0.06/15, cat4/1000/5, ridge100, drop=wave_fog, win=all |
| 3 | rand66 | +4.3 | +5.0 [-2, +11] | +3.4 [-2, +7] | +4.6 [-4, +10] | v1, shr6, cat+ridge, lgb3/600/0.06/15, cat3/500/10, ridge10, drop=arr_dep, win=all |
| 4 | rand562 | +4.1 | +4.5 [-2, +10] | +3.0 [-2, +6] | +4.9 [-3, +11] | v1, shr6, cat+ridge, lgb7/600/0.03/30, cat3/500/3, ridge30, drop=None, win=all |
| 5 | rand423 | +4.1 | +5.9 [-1, +12] | +2.8 [-2, +6] | +3.7 [-4, +9] | v1, shr6, cat+ridge, lgb3/150/0.03/30, cat4/500/5, ridge10, drop=arr_dep, win=all |
| 6 | rand282 | +4.1 | +4.5 [-2, +10] | +4.0 [-2, +8] | +3.8 [-5, +9] | v1, shr6, ridge, lgb7/300/0.03/30, cat3/300/3, ridge30, drop=wave_fog, win=all |
| 7 | rand415 | +4.0 | +4.3 [-2, +10] | +2.3 [-5, +7] | +5.5 [-2, +10] | v1, shr3, ridge, lgb15/300/0.06/30, cat6/1000/3, ridge10, drop=None, win=6m |
| 8 | rand507 | +4.0 | +5.0 [-2, +11] | +2.9 [-2, +6] | +4.1 [-2, +9] | v1, shr3, cat+ridge, lgb3/600/0.06/15, cat4/300/3, ridge10, drop=None, win=all |
| 9 | rand536 | +4.0 | +5.3 [-1, +11] | +2.5 [-2, +5] | +4.3 [-1, +9] | v1, shr3, cat+ridge, lgb7/150/0.06/15, cat3/500/3, ridge100, drop=None, win=all |
| 10 | rand174 | +4.0 | +4.2 [-2, +9] | +3.1 [-1, +6] | +4.8 [-2, +10] | v1, shr3, lgbm+ridge, lgb3/150/0.03/30, cat3/300/5, ridge10, drop=None, win=all |
| 11 | rand258 | +4.0 | +5.1 [-1, +11] | +2.1 [-2, +5] | +4.6 [-1, +8] | v1, shr3, ridge, lgb15/600/0.03/15, cat4/300/5, ridge100, drop=None, win=all |
| 12 | rand315 | +3.9 | +6.0 [+0, +12] | +1.8 [-2, +4] | +4.0 [-1, +8] | v1, shr3, cat+ridge, lgb3/300/0.06/30, cat3/300/5, ridge100, drop=None, win=all |
| 13 | rand477 | +3.9 | +5.4 [-1, +11] | +3.5 [-2, +8] | +2.8 [-4, +7] | v1, shr0, ridge, lgb7/150/0.03/30, cat4/500/5, ridge100, drop=wave_fog, win=6m |
| 14 | rand69 | +3.9 | +4.1 [-2, +10] | +2.7 [-3, +7] | +4.9 [-2, +9] | v1, shr3, ridge, lgb7/150/0.06/15, cat6/500/10, ridge30, drop=None, win=all |
| 15 | rand246 | +3.9 | +4.1 [-2, +10] | +2.7 [-3, +7] | +4.9 [-2, +9] | v1, shr3, ridge, lgb3/300/0.03/15, cat3/1000/3, ridge30, drop=None, win=all |
| - | default | -1.4 | -1.0 [-13, +8] | -4.7 [-15, +2] | +1.5 [-7, +9] | v2, shr0, lgbm+cat+ridge, lgb7/300/0.03/15, cat4/500/5, ridge30, drop=None, win=all |

MAE vs baseline MAE at h=1, design window (v1 vs v2 are NOT on the same baseline set):
- default: model MAE 1.567, best naive tonight_blend 1.552
- data=v1: model MAE 1.720, best naive blend 1.784

## Test (2024-10..12, once)

| config | h=1 | h=2 | h=3 | best naive h1/h2/h3 | MAE h=1 |
|---|---|---|---|---|---|
| default | +9.6 [+1, +16] | +7.5 [-6, +18] | +5.7 [-8, +17] | tonight_blend/ma7/ma7 | 1.506 vs 1.667 |
| rand419 | +5.8 [+3, +9] | +5.6 [-4, +15] | +2.9 [-6, +11] | blend/ma7/ma7 | 1.831 vs 1.944 |
| rand530 | +7.0 [+4, +10] | +2.6 [-6, +12] | +3.0 [-7, +11] | blend/ma7/ma7 | 1.808 vs 1.944 |
| rand66 | +9.1 [+4, +14] | +4.3 [-6, +14] | +2.4 [-8, +11] | blend/ma7/ma7 | 1.767 vs 1.944 |

## Crisis n_waiting, 2021-09-01..2022-01-10

| config | h=1 | h=2 | h=3 | best naive h1/h2/h3 | MAE h=1 |
|---|---|---|---|---|---|
| default | -5.1 [-14, -0] | -2.8 [-19, +8] | -8.7 [-24, +3] | persistence/persistence/persistence | 3.757 vs 3.574 |
| rand419 | -1.6 [-5, +1] | -0.0 [-12, +9] | -1.3 [-11, +8] | persistence/persistence/persistence | 3.632 vs 3.574 |
| rand530 | -2.1 [-7, +1] | -4.8 [-21, +6] | -5.2 [-16, +5] | persistence/persistence/persistence | 3.649 vs 3.574 |
| rand66 | -1.9 [-7, +1] | -4.1 [-20, +6] | -5.2 [-16, +6] | persistence/persistence/persistence | 3.641 vs 3.574 |

## Crisis pre-rule-change, targets <= 2021-11-15

| config | h=1 | h=2 | h=3 | best naive h1/h2/h3 | MAE h=1 |
|---|---|---|---|---|---|
| default | -6.7 [-15, -1] | -3.0 [-20, +10] | -3.4 [-19, +11] | persistence/persistence/persistence | 3.139 vs 2.943 |
| rand419 | -3.7 [-9, +2] | +0.3 [-10, +9] | +6.3 [-4, +14] | persistence/persistence/persistence | 3.053 vs 2.943 |
| rand530 | -4.4 [-13, +2] | -5.3 [-26, +9] | -1.6 [-16, +11] | persistence/persistence/persistence | 3.074 vs 2.943 |
| rand66 | -4.0 [-14, +2] | -7.2 [-28, +8] | -0.9 [-16, +13] | persistence/persistence/persistence | 3.060 vs 2.943 |

## Seeds 0-4 (design mean skill)

- rand419: +4.45 .. +4.45 (sd 0.00)
- default: -1.76 .. -1.21 (sd 0.19)
- rand530: +4.40 .. +4.76 (sd 0.13)
- rand66: +4.16 .. +4.81 (sd 0.22)

## One-at-a-time (design mean skill, change vs default)

- data=v1: +1.0 (+2.4)
- shrink3: -0.1 (+1.3)
- shrink6: -0.2 (+1.2)
- ens=cat+ridge: -0.2 (+1.2)
- ridge100: -1.1 (+0.3)
- drop=arr_dep: -1.2 (+0.2)
- window=6m: -1.3 (+0.1)
- ridge30: -1.4 (+0.0)
- drop=wave_fog: -1.5 (-0.1)
- ridge10: -1.7 (-0.3)
- ens=cat: -1.8 (-0.4)
- drop=approach: -1.8 (-0.5)
- drop=fc: -2.0 (-0.6)
- drop=obs_weather: -2.0 (-0.6)
- ens=median3: -2.3 (-0.9)
- drop=lags: -2.6 (-1.2)
- ens=lgbm+ridge: -2.7 (-1.3)
- ens=lgbm+cat: -3.4 (-2.1)
- ens=ridge: -3.7 (-2.3)
- ens=lgbm: -6.8 (-5.4)
