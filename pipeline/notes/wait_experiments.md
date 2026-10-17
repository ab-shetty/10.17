# Wait-time and queue experiments after the demo freeze (A)

All tests use the same rule as the published results: a method used on the 1st of a month only sees data known then.
For waits that means a ship's wait counts as training data only once it has berthed, and only for ships that joined
30+ days earlier (otherwise the known waits are biased toward the quick ones). Container-size = cargo ≥ 200 m.
90 % intervals resample join days (ships joining the same day share an outcome) or 7-day blocks.
Nothing here changes `shared/`.

## Result kept: 80 % ranges for a ship's wait (`model/wait_intervals.py`)
Range = estimate × [10th, 90th percentile] of (real wait ÷ estimate) among ships whose wait was already known.

| ships | range built on | real wait inside the 80 % range | by month | median width |
|---|---|---|---|---|
| 2021 crisis, joined Aug 1 – Nov 15 (457) | ours (ships ahead ÷ berths per day) | **85 %** | 88, 89, 79, 83 % | 25.9 d |
| | published 7-day average | 79 % | 81, 83, 76, **69 %** | 18.2 d |
| 2024, joined Apr – Dec 10 (152) | ours | **84 %** | 69–100 % | 10.9 d |
| | published 7-day average | 88 % | 78–100 % | 8.7 d |

- Ranges built on our estimate stay calibrated in both years, including through the 2021 build-up.
- Ranges built on the published figure lose coverage as the 2021 queue grows (69 % in November), with the misses
  mostly ships that waited longer than the range: the same lag as the bias result in `shared/crisis/wait.json`.
- Width is the real per-ship uncertainty with free data (≈ 26 d in the crisis). Narrowing it needs berth schedules.
- Not in `shared/` yet. Adding `{lo_d, hi_d}` to `wait.json` daily is a small change if wanted.

## Tried and not adopted

**ML for each ship's wait** (LightGBM / ridge, inputs known the day before joining: our estimate, the published figure,
queue trend, berthing rate, IMF PortWatch port calls, ship size and type, day of week). 754 ships, Aug – Nov 15 2021.
- Trained directly: biased 3.5–5 d short, worse than the published figure on per-ship error (−4 to −12 %). Waits rose
  all through 2021; a model trained on past waits predicts past waits.
- As a relative correction to our estimate: still biased short (late, skewed labels).
- Pooling 2024 ships in: no change.

**Carrier-aware estimate.** Carriers are identifiable from ship names (MSC, CMA CGM/APL, ONE = NYK + MOL + ONE,
COSCO/CSCL/OOCL, Evergreen, Yang Ming, HMM, Maersk, Wan Hai, ZIM, Matson).
- Per-carrier queue ÷ per-carrier berthing rate: too noisy (1–2 berthings a day per carrier); MAE 8.3 vs 6.8 d.
- A carrier's own recent average wait predicted individual ships better than the port-wide published figure in the
  crisis (MAE 5.95 vs 6.34 d, same ships).
- Carrier's recent wait + (ours − published), with a LightGBM correction whose weight is chosen on training data only:

  | test | per-ship MAE: this / published / ours | vs published [90 % CI] | vs ours [90 % CI] |
  |---|---|---|---|
  | 2021 crisis (471 ships) | 6.42 / 6.47 / 6.80 d (bias −0.6 / −2.4 / +0.2) | +0.8 % [−4.9, +5.8] | **+5.6 % [+2.5, +8.6]** |
  | 2024, frozen method (188 ships) | 3.02 / 2.86 / 3.16 d | −5.6 % [−22, +9] | +4.5 % [−8, +16] |

  Daily mean of container-size ships: no difference distinguishable from noise in either year.
  Not adopted: the carrier idea came from looking at the 2021 data, and the gain does not hold on 2024.

**Terminal-level estimate.** Terminals from k-means (12) on observed berth positions; a ship's terminal predicted on
the day it joins from its own previous call (correct 79 %) or its carrier's usual terminal (46 %). Terminal recent wait:
MAE 6.43 vs port-wide 6.34 d; terminal queue ÷ berthing rate: 7.76 d. Not better than carrier-level.

**ARIMA / ARIMAX for the daily queue** (statsmodels SARIMAX, order by AIC on training data each month; exogenous:
end-of-day queue, ships due within 24 h, loitering offshore, day-ahead gust forecast).
- 2024 Oct–Dec, `n_anchored`, 1 day ahead: MAE 2.13 (ARIMA) / 2.20 (ARIMAX) vs best simple rule 1.67 and the
  LightGBM + CatBoost + ridge ensemble 1.51 on the same data. Clearly worse; behaves like tomorrow = today.
- 2021-09 – 2022-03, `n_waiting`, vs tomorrow = today: h=1 −0.9 % [−4.4, +2.1], h=2 +0.6 % [−2.0, +2.6],
  h=3 +1.3 % [−2.3, +4.5]. No detectable difference (the ensemble: +0.5 / −1.7 / −6.0 %).

## Summary
With free data, per-ship accuracy plateaus at about the published figure; our estimate's advantage is that it is
unbiased and its uncertainty ranges stay honest while the queue grows. The remaining per-ship error comes from berth
slots and carrier contracts, which AIS does not show.
