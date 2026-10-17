# Stacking experiments (model/experiments_stacking.py)

Question: can pooling across horizons, pooling 2024 into the crisis, a stacked meta-learner or a damped-trend baseline
beat the current `avg` (mean of LightGBM + CatBoost + ridge on `y[t+h] − anchor`)?

**Answer: no variant is worth adopting.** Nothing beats `avg` with a CI that excludes 0, and on the crisis nothing
beats plain persistence. `train.py` stays as it is.

## Protocol (identical to `train.py --rolling`)
- Same features, `fit_all`, anchor rule (best naive on target dates < test start), monthly refit on rows whose *target
  date* is before the month, same test windows. The script imports `train.py` and only caps threads (n_jobs / thread_count = 2).
- Skill = 100·(1 − MAE_variant / MAE_best naive), where best naive = min over persistence / ma7 / blend **on the test set**
  (inherited from train.py; it is chosen after looking at test and makes the bar slightly tougher).
- CI = 7-day block bootstrap (`train.block_bootstrap_skill`). "Δ vs avg" = skill difference in percentage points, with a
  paired block-bootstrap 90 % CI (same resampled blocks for both models).
- **Reproduction check:** the recomputed `avg` equals the shipped 2024 numbers exactly (h=1 MAE 1.735, +10.7 % [3.3, 17.5]; h=2 +6.2 %; h=3 +2.8 %) and the crisis numbers in CLAUDE.md (−2.1 / −6.9 / −13.4 %). The shipped `shared/crisis/metrics.json` at the time of the run is older (h=1 −0.1 %, MAE 3.522) and does not match. Both runs use `data/crisis/daily_a.parquet`, which ends 2021-12-01, so the crisis window is Sep–Nov 2021 (n = 88/87/86).
- Crisis: the best naive is persistence at every h; `avg` loses to it everywhere.

## Variants
| id | what |
|---|---|
| `pool_h` | (a) one model for h = 1,2,3, `h` as a feature (3× the rows; per-h anchors kept) |
| `b0_rel` | crisis rows only, relative target `y[t+h]/anchor − 1` (control: isolates the effect of the relative target) |
| `b1_pool24` | (b) crisis + all 2024 rows, dataset flag `is24`, relative target; features = intersection (drops forecast-gust features) |
| `b2_pool24n` | (b) as b1, count features divided by the anchor level (scale-free, since 2024 queue ≈ 15, crisis ≈ 40–100) |
| `c_nnls` | (c) NNLS (weights normalised to 1) on inner-rolling OOF [anchor+lgbm, anchor+cat, anchor+ridge, persistence, ma7, blend] |
| `c_ridge` | (c) ridge (alpha 10, no intercept) on the same OOF, in change-from-anchor space |
| `holt` | (d) damped Holt, (alpha, beta, phi) grid-searched on training target dates only, per h |
| `avg_holtanc` | (d) `avg` with the anchor picked among persistence / ma7 / blend / holt on training data. The training pick was never Holt, so this is identical to `avg` |

Fixed in advance and not tuned: ridge alpha 10, inner folds 6 × 14 days before each month, Holt grid
(alpha 0.3–0.9, beta 0.1–0.4, phi 0.8–0.98). Inner OOF needs ≥ 20 rows; otherwise the meta learner falls back to `avg`
(this happened for the **September 2021** fold in the crisis, 1 of 3–4 months: `c_*` there are just `avg`).

## Results (copied from the script's output)

### 2024, target n_anchored, test Oct–Dec 2024 (rolling-origin)
| variant | h | n | MAE | skill vs best naive | 90% CI | Δ vs avg (pp) | Δ 90% CI |
|---|---|---|---|---|---|---|---|
| avg | 1 | 92 | 1.735 | +10.7% | [+3.3, +17.5] | | |
| pool_h | 1 | 92 | 1.780 | +8.5% | [-2.6, +16.5] | -2.3 | [-9.2, 1.9] |
| c_nnls | 1 | 92 | 1.738 | +10.6% | [+4.9, +15.2] | -0.1 | [-5.3, 4.1] |
| c_ridge | 1 | 92 | 1.791 | +7.9% | [+2.4, +12.4] | -2.9 | [-10.0, 3.4] |
| holt | 1 | 92 | 2.113 | -8.7% | [-14.4, -2.5] | -19.4 | [-28.2, -10.1] |
| avg | 2 | 92 | 2.182 | +6.2% | [-6.5, +17.5] | | |
| pool_h | 2 | 92 | 2.225 | +4.4% | [-9.6, +15.9] | -1.9 | [-5.5, 1.1] |
| c_nnls | 2 | 92 | 2.272 | +2.3% | [-11.6, +15.1] | -3.9 | [-9.1, 1.5] |
| c_ridge | 2 | 92 | 2.261 | +2.8% | [-8.5, +13.9] | -3.4 | [-9.3, 3.8] |
| holt | 2 | 92 | 2.330 | -0.1% | [-7.0, +6.6] | -6.4 | [-16.0, 6.1] |
| avg | 3 | 92 | 2.314 | +2.8% | [-11.2, +12.8] | | |
| pool_h | 3 | 92 | 2.293 | +3.7% | [-8.0, +13.0] | +0.9 | [-3.6, 7.1] |
| c_nnls | 3 | 92 | 2.375 | +0.2% | [-16.7, +11.6] | -2.6 | [-9.2, 2.9] |
| c_ridge | 3 | 92 | 2.315 | +2.8% | [-9.2, +10.9] | -0.0 | [-6.4, 6.3] |
| holt | 3 | 92 | 2.384 | -0.1% | [-7.4, +7.7] | -2.9 | [-13.1, 12.1] |

Best naive: h=1 blend (MAE 1.944), h=2 and h=3 ma7 (2.327, 2.381). (`b*` variants are crisis-only; `avg_holtanc` = `avg`.)

### Crisis, target n_waiting, test from 2021-09-01 (rolling-origin)
| variant | h | n | MAE | skill vs best naive | 90% CI | Δ vs avg (pp) | Δ 90% CI |
|---|---|---|---|---|---|---|---|
| avg | 1 | 88 | 3.593 | -2.1% | [-14.5, +1.4] | | |
| pool_h | 1 | 88 | 4.222 | -20.0% | [-50.4, -11.1] | -17.9 | [-42.9, -7.8] |
| b0_rel | 1 | 88 | 3.914 | -11.2% | [-33.8, -2.3] | -9.1 | [-20.4, -2.4] |
| b1_pool24 | 1 | 88 | 4.533 | -28.9% | [-50.2, -19.7] | -26.7 | [-45.4, -13.2] |
| b2_pool24n | 1 | 88 | 4.065 | -15.6% | [-36.5, -5.7] | -13.4 | [-28.4, -0.7] |
| c_nnls | 1 | 88 | 3.501 | +0.5% | [-13.1, +5.0] | +2.6 | [-1.6, 7.0] |
| c_ridge | 1 | 88 | 3.617 | -2.8% | [-15.6, +0.6] | -0.7 | [-5.5, 3.0] |
| holt | 1 | 88 | 3.587 | -2.0% | [-4.2, +0.1] | +0.2 | [-4.5, 13.3] |
| avg | 2 | 87 | 5.695 | -6.9% | [-31.1, +1.9] | | |
| pool_h | 2 | 87 | 6.251 | -17.3% | [-48.2, -6.0] | -10.4 | [-21.0, -4.3] |
| b0_rel | 2 | 87 | 6.266 | -17.6% | [-48.8, -7.7] | -10.7 | [-19.2, -7.1] |
| b1_pool24 | 2 | 87 | 6.800 | -27.6% | [-60.5, -16.4] | -20.7 | [-41.7, -5.1] |
| b2_pool24n | 2 | 87 | 5.737 | -7.7% | [-31.3, +0.7] | -0.8 | [-8.8, 7.9] |
| c_nnls | 2 | 87 | 5.441 | -2.1% | [-18.9, +5.4] | +4.8 | [-0.3, 18.3] |
| c_ridge | 2 | 87 | 5.351 | -0.4% | [-19.1, +6.9] | +6.5 | [-1.1, 21.3] |
| holt | 2 | 87 | 5.282 | +0.9% | [-9.6, +5.0] | +7.7 | [-1.4, 26.0] |
| avg | 3 | 86 | 6.811 | -13.4% | [-36.8, -0.1] | | |
| pool_h | 3 | 86 | 6.916 | -15.1% | [-39.5, -0.1] | -1.7 | [-5.1, 2.4] |
| b0_rel | 3 | 86 | 7.600 | -26.5% | [-57.9, -11.9] | -13.1 | [-25.1, -7.4] |
| b1_pool24 | 3 | 86 | 7.673 | -27.7% | [-66.0, -8.2] | -14.3 | [-39.9, 3.0] |
| b2_pool24n | 3 | 86 | 6.681 | -11.2% | [-33.5, +0.9] | +2.2 | [-6.3, 10.1] |
| c_nnls | 3 | 86 | 6.414 | -6.8% | [-22.6, +2.8] | +6.6 | [-1.8, 22.2] |
| c_ridge | 3 | 86 | 6.377 | -6.2% | [-24.0, +7.8] | +7.2 | [-2.0, 23.8] |
| holt | 3 | 86 | 5.914 | +1.5% | [-3.6, +3.5] | +14.9 | [-0.8, 38.0] |

Best naive = persistence at all h (MAE 3.518 / 5.328 / 6.006).
The pre-rule-change window (target ≤ 2021-11-15, n = 72/71/70) gives the same picture; see the script's output (`python model/experiments_stacking.py crisis`): `avg` −2.1 / −6.4 / −7.7 %, `c_nnls` −0.7 / −4.7 / −7.6 %, `holt` −2.2 / −2.6 / −0.2 %, every pooled variant −9 % to −37 %.

## Reading
- **(a) pooling across h**: no gain anywhere. 2024: −2.3 / −1.9 / +0.9 pp, all CIs include 0. Crisis h=1 and h=2: much worse (−18, −10 pp, CI excludes 0).
- **(b) pooling 2024 into the crisis**: clearly worse (−13 to −27 pp at h=1, CI excludes 0 for `b1`, `b2` at h=1). The relative-target control `b0_rel` is also worse than `avg`, so most of the damage is the relative target on a short history, not only the 2024 rows. Scale-normalised `b2` shrinks the damage (≈ ties `avg` at h=2,3) but never beats it. A caveat that applies in its favour only: it uses 2024 data to forecast 2021, which is not available in a real forecast, and it still loses.
- **(c) vertical stacking**: on 2024 it ties or loses (`c_nnls` −0.1 / −3.9 / −2.6 pp). On the crisis it moves `avg` from −2/−7/−13 % to −2…+0.5 / −2 / −7 % (up to +7 pp), but all Δ CIs include 0 and it still does not beat persistence at h=2,3. It does so mainly by putting weight on persistence, i.e. it shrinks toward the naive rule. One of the 3–4 crisis months fell back to `avg` for lack of OOF rows.
- **(d) damped Holt**: with the grid chosen on training data, it selected alpha 0.5–0.9, beta 0.1, phi 0.8 (the grid minimum for phi and beta), i.e. almost no trend: it behaves as lightly smoothed persistence. Crisis: −2.0 / +0.9 / +1.5 % vs persistence, CIs include 0 — a tie, not a win. It looks "better" than `avg` only because `avg` is below persistence. 2024: worse than the best naive at h=1 (−8.7 %, CI excludes 0). It was never chosen as the anchor. It does not capture the build-up (the data rewards "no trend" over "damped trend"); phi at the grid edge means a lower phi might fit slightly better — not explored, and I did not widen the grid after seeing test.

## What was chosen after seeing test (flag)
- Nothing in the variants was tuned on test: hyperparameters were set before the run and the grid for Holt is fit on training dates.
- The reference "best naive" is picked on the test set (inherited, makes the bar tougher). The crisis result is on 88 days that are one regime with one build-up, ~3 months; CIs are wide (±15–30 pp), so "no detectable difference" is the strongest claim for any Δ.
- The set of variants is a menu of 8 compared against `avg` on the same test windows (no multiplicity correction): even so none shows a clear win, so no selection effect to correct.
- 2024 Oct–Dec was already used for design decisions in `train.py`; this experiment adds no new tuning on it.

## Recommendation
1. **Keep `avg` and the `train.py` code unchanged.** No variant improves it with a CI excluding 0; 2024 variants all tie or lose.
2. **Crisis story: do not claim skill.** Say "the model does not beat persistence in the build-up; a Holt trend baseline and a stacked meta-learner don't either" (ties within wide CIs). If the crisis chart (`shared/crisis/chart.json`) is shown, the model line is not better than "tomorrow = today".
3. Optional (not recommended for the headline): if the team wants the toughest honest benchmark, add Holt as a fourth naive rule. On the crisis it would become the best baseline at h=2 and h=3 (MAE 5.282 vs 5.328, 5.914 vs 6.006), making `avg` look slightly worse (≈ −8 % / −15 % instead of −7 % / −13 %) and changing nothing in 2024 (Holt never wins there). The diff below is a sketch, **not applied and not tested**:

```diff
--- a/model/train.py
+++ b/model/train.py
-BASELINES = ("persistence", "ma7", "blend")
+BASELINES = ("persistence", "ma7", "blend", "holt")
...
-def baselines(y):
+def holt_series(y, h, a=0.7, b=0.1, phi=0.8):
+    """Damped-trend forecast for day t+h issued on day t (parameters fixed in advance, not tuned on test)."""
+    out, lvl, trend = np.full(len(y), np.nan), None, 0.0
+    damp = sum(phi ** i for i in range(1, h + 1))
+    for i, v in enumerate(y.values):
+        if np.isnan(v):
+            continue
+        if lvl is None:
+            lvl = v
+        else:
+            lp = lvl
+            lvl = a * v + (1 - a) * (lp + phi * trend)
+            trend = b * (lvl - lp) + (1 - b) * phi * trend
+        out[i] = lvl + damp * trend
+    return pd.Series(out, index=y.index)
+
+
+def baselines(y, h=1):
     ma7 = y.rolling(7, min_periods=4).mean()
-    return dict(persistence=y, ma7=ma7, blend=0.5 * y + 0.5 * ma7)
+    return dict(persistence=y, ma7=ma7, blend=0.5 * y + 0.5 * ma7, holt=holt_series(y, h))
...
-    base_all = baselines(d[TARGET])
     rows, metrics = [], {}
     for h in HORIZONS:
+        base_all = baselines(d[TARGET], h)
```
(`ok` also needs `base_all["holt"].notna()` only if early rows matter; `holt_series` is a copy of the tested function in
`experiments_stacking.py`, with fixed instead of grid-searched parameters. Untested inside train.py; the stored `preds.json`
fields `baseline_name` could then be "holt", which B's UI would need to label.)
