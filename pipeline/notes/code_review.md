# Code review: pipeline/*.py, model/*.py, model/run_crisis.sh

Read-only review. Only read-only queries on `data/` were run. The ablations below re-ran `model/train.py`'s `main()` in
memory with file writes monkey-patched out. Nothing in the repo was changed.
External facts are cited by the local PDF they were checked in (the CARB and POLA PDFs in `data/ext/`). I did not
re-fetch any web page; where a claim rests on a web page I did not open, it is marked UNVERIFIED.

## Bottom line

- **No target leakage found.** Every feature at issue date `t` uses data up to the end of UTC day `t`. The
  forecast-gust shifts are right, the fold boundaries are right, and the departures shift is right.
- **The `departures_yday` shift is not what produces the skill.** Dropping `departures_yday` and `net_inflow_3d` gives
  h=1 +11.9 % [5.1, 18.0], slightly *better* than the published +10.2 %.
- **The h=1 headline depends on one input.** Remove the forecast-gust features and h=1 skill is **+1.6 % [-6.4, +7.0]**,
  which is a tie with the baseline (finding 1). That feature's data also looks odd (finding 2).
- **Several judge-visible text claims are wrong or contradict the model** (findings 3, 4, 7, 8).

Verified OK, so nobody re-checks it:
- Shift directions:
  - `train.py:186-187` `fc{h}_gust.shift(-h)` is the forecast for `t+h` issued on day `t`.
  - `train.py:105` `n_departures_24h.shift(1)` is knowable by the end of day `t` (24 h of silence after a ping on `t-1`).
- Training and CV cut-offs: every training row has its target before the validation or test start, in `tr`, the CV
  folds and the rolling folds. `asfreq("D")` keeps `shift(-h)` calendar-correct.
- Baselines and skill:
  - Baselines are causal.
  - Skill is computed against the best of three baselines picked on test, which is conservative.
  - `pred`, `act` and `base` share the issue-date index.
- Emissions arithmetic: kW·h × g/kWh ÷ 1e6 gives metric t. I recomputed 2024 independently: 724.76 t NOx on 5,594.5
  ship-days, matching `shared/emissions.json` (724.8 t, 5,594).
- Short→metric: `ST = 0.907185` is right, and `/ST` (metric→short) is applied in the right direction in `vs_carb_monthly`.
- CARB figures: tanker BAU 1.5 tpd, container BAU 0.2 tpd, and the excess table 17.9 / 7.0 / 4.3 / 3.5 / 2.6 tpd all
  match `data/ext/carb/SPBP_Freight_Congestion_Emissions_Feb2023_ADA.txt` lines 67-80 and 151-155.
- Nov-2021 CARB sheet: 20 tpd NOx, 0.5 tpd PM and 5.8 million cars match `SPBP_Congestion_Anchorage_Emissions_Final.txt` lines 53-61.
- POLA CY2023 anchorage hotelling matches `data/ext/pola_ei/ei2023.txt` lines 801-804: aux engine NOx 103.7 + boiler
  14.4 = **118 tons**, CO2e **12,981 t**. POLA's tables are in tons per year (short tons).

## Findings

### 1. [HIGH, credibility] The h=1 win comes almost entirely from the previous-runs gust forecast
- **Where:** `model/train.py:184-187`, `pipeline/weather.py:20-21`.
- **Ablation:** I re-ran the rolling-origin 2024 test (reproduces the published numbers exactly) with all `fc*` columns
  removed from the daily table:

| h | published (with `fc_gust_*`) | without `fc*` features | with `fc*` but no departures |
|---|---|---|---|
| 1 | +10.2 % [2.9, 16.3] | **+1.6 % [-6.4, 7.0]** (vs persistence 9.1 %) | +11.9 % [5.1, 18.0] |
| 2 | +3.6 % | +0.3 % [-13.2, 11.9] | +3.1 % |
| 3 | +3.4 % | +0.6 % [-13.3, 10.9] | not run |

- **Scenario:**
  - A judge asks "what beats the 7-day mean?". The honest answer is "a one-day-ahead gust forecast". The claim
    "the model learned the AIS dynamics" is not supported.
  - CLAUDE.md and `episodes.py` also say the model has no forecast input (finding 4), so the deck contradicts itself.
- **Related:**
  - Storm-day skill (`n_storm = 10`, +32 %) is about 3 independent weather events. The 10 days are clustered in
    ~3 events (Nov 6-7, Nov 15-16, Dec 10). `train.py:245-247` gives no CI.
  - The three `episodes.json` episodes are the same events and were picked after the fact ("where the model beat
    persistence", `episodes.py` docstring).
  - Training sees `fc` features only from 2024-01-19 to Sep, which is a handful of storms.
- **Fix:**
  - Say plainly in the deck: "h=1 +10 % is a storm-forecast effect; without the forecast the model ties the 7-day mean".
  - Add a block-bootstrap CI for the storm subset (or report event-level: 3 events).
  - Add an own-history-only benchmark (the same pipeline with only lag features) next to the naive baselines.

### 2. [HIGH if real, UNVERIFIED cause] `fc1_gust` is anomalously close to "observed" gust; `fc2`/`fc3` are not
- **Where:** `pipeline/weather.py:20-21, 49-52` (the `_previous_dayN` columns).
- **Data**, 2024, `data/daily.parquet`:

| forecast | r vs observed gust | MAE (kn) | bias (kn) |
|---|---|---|---|
| fc1 | 0.79 | 2.46 | +1.0 |
| fc2 | 0.71 | 5.52 | **-5.0** |
| fc3 | 0.65 | 5.60 | -5.3 |

- **Why it matters:**
  - A genuine forecast degrades smoothly with lead time. Here fc1→fc2 loses 3 kn of MAE, while fc2→fc3 loses 0.1 kn.
  - The -5 kn bias at fc2 and fc3 against +1 at fc1 suggests that `previous_day1` is drawn from a different or fresher
    model or run than `previous_day2`/`previous_day3`, or is partly an analysis-like field.
  - The observed series (`gust_max_kts`) comes from the *historical-forecast* API, which is itself model output.
  - If fc1 contains post-issue information, h=1 skill is optimistic and the +32 % storm skill is too.
  - The pattern (h=1 skill is real, h=2/h=3 skill is about 0) is consistent with a privileged fc1.
  - How Open-Meteo builds `*_previous_dayN` (which model run, which lead hours) is UNVERIFIED.
    Docs to check: https://open-meteo.com/en/docs/previous-runs-api (not opened in this review).
- **Fix:**
  - Pin one model (`&models=gfs_seamless` or ecmwf) for both the previous-runs request and the "observed" request.
  - Confirm the `previous_day1` lead time for one sample hour against that model's archived run.
  - Re-run h=1. If the gain survives, say so with that evidence.

### 3. [MED] `offshore_waiting` is mostly ships moored at other ports (2024), and the replay map shows them as "waiting"
- **Where:** `pipeline/build_daily.py:131` (`nm < 60 AND sog < 3`, no berth exclusion); the same rule in
  `pipeline/export_replay.py:49-52`; `n_waiting` at `build_daily.py:159` and `train.py:168`.
- **Data**, `data/approach/*.parquet`, 2024, mean hourly count of ships with `nm<60, sog<3`:

| part | mean ships |
|---|---|
| all | 8.03 |
| Port Hueneme (34.15, -119.21; 57 nm, lat 34.0-34.3 / lon -119.4 to -119.0) | **4.26** |
| El Segundo offshore terminal (~33.90, -118.45; 18 nm) | 1.35 |
| everything else (real offshore waiters, drifters) | **2.4** |

- In the shipped `shared/replay/2024-1*.json`, **68 %** of `waiting_offshore` rows (12,552 of 18,474) are in those two boxes.
- **Scenario:**
  - On the map, "ships waiting offshore" shows tankers and car carriers sitting at Port Hueneme's pier. A local
    judge will spot that.
  - In 2024 the feature is a near-constant offset, so the model is only mildly hurt.
- **Crisis impact is small on the peak day.** On the raw 2021-10-25 file: 64 ships at `nm<60, sog<3`, only 2 at Hueneme
  and 0 at El Segundo. The 2021 target is OK on that day.
- **Emissions impact:** the 2021 `offshore_*_t` totals (finding 6) would include them on other days.
- **Fix:** exclude cells whose `status=5` pings dominate (reuse the berth-cell idea for the approach zone), or
  hard-exclude polygons around Hueneme and El Segundo, and require `status != 5`. Do the same in the replay export.

### 4. [MED] `episodes.py` mislabels the baseline as "persistence"; 2 of 7 "model closer" verdicts flip
- **Where:** `model/episodes.py:33-37`. `r["baseline"]` is the *best* baseline, which is `blend` for h=1
  (`baseline_name='blend'` in all 92 rows). Persistence is `r["persistence"]`.
- **Data**, h=1 key days:

| day | model | blend | true persistence | actual | text says | truth vs persistence |
|---|---|---|---|---|---|---|
| 2024-11-07 | 8.74 | 7.99 | 6.25 | 6.29 | "persistence 8.0, persistence closer" | persistence closer by far |
| 2024-11-16 | 8.30 | 9.07 | 7.12 | 5.58 | "persistence 9.1, model closer" | **persistence is closer** |

- The other five days hold up; the numbers shown are still the blend, not persistence.
- **Scenario:** the story panel prints "vs persistence 9.1" when persistence was 7.1. A judge checks the chart and sees a
  different number.
- **Fix:** `episodes.py:34` use `r["persistence"]`, or print `r["baseline_name"]`, and re-run `episodes.py`.

### 5. [MED] Text says the model has "no weather-forecast input"; it does
- **Where:** `model/episodes.py:24` (in `shared/episodes.json`, shown to users), and CLAUDE.md "It does NOT foresee the
  gale itself (no weather-forecast input)". But `train.py:184-187` adds `fc_gust_target` / `fc_gust_tomorrow`, which
  are the #3 feature in `top_features` (109 of 828 slots), and the same file's `model_note` quotes "forecast gusts of
  28.6 kn on the target day".
- **Scenario:** the same panel says both. The statement is also false for the 2024 model.
- **Fix:** reword to "the 2021-22 crisis model has no forecasts; the 2024 model does" (finding 1).

### 6. [MED] Offshore emissions treat drifting ships as if their auxiliaries and boilers ran at full hotelling load
- **Where:** `pipeline/emissions.py:77-84`.
- **Issues:**
  - CLAUDE.md itself says the loitering ships are "engines off".
  - The POLA CY2021 report defines loitering as "main engine is turned off". Its own estimate for loitering plus
    additional anchorage is a separate small row: NOx 53 tons, CO2e 3,821 t (`data/ext/pola_ei/ei2021.txt:3640`).
    The code instead assigns the full **container** hotelling load (aux 1,175 kW + boiler 553 kW) to every ship.
  - It also counts tankers and anything at Hueneme or El Segundo (finding 3) as container ships.
  - This probably overstates `offshore_*_t` several-fold. UNVERIFIED how much.
- **Fix:** do not publish `offshore_*_t` as an emissions number. Either drop it, or label it a "hotelling-load upper bound,
  not inventory" and do not add it to `nox_t`.

### 7. [MED] "Validated against POLA" covers about 4 % of the target
- **Where:** CLAUDE.md "Validated against POLA's own daily Container Vessel Activity 2024";
  `pipeline/pola_summary.py`; `data/ext/pola_daily.parquet`.
- **Data**, 249 matched days:

| comparison | value |
|---|---|
| POLA container-ships-at-anchor | mean 0.54, median 0, max 8 |
| our `n_anchored_bigcargo` (≥250 m cargo; mean 0.65) vs POLA | Pearson 0.49 (Spearman 0.59) |
| total `n_anchored` vs POLA `pola_anchor` | **-0.01** |

- **Scenario:** a judge asks "so is the 15-ship queue validated?" The honest answer is that the 74 % tanker share has no
  independent check, and the count validated is mostly 0-1 ships.
- **Fix:** call it "plausible agreement on the container slice", and state r for the full count too.

### 8. [MED] Explanation phrases can contradict their own direction
- **Where:** `model/train.py:58-62` (and `:79`). The "so it tends to shrink back / refill" text is fixed by the sign of
  the *feature*, then `; pushes the forecast up/down` is appended from the SHAP *contribution*.
- **Data:** 5 rows in `shared/preds.json` read e.g. "queue is 0.6 ships below its weekly normal, so it tends to refill;
  **pulls**/pushes ..." with a direction that disagrees with the clause. Small, but visible if the judge reads it.
- **Fix:** drop the fixed causal clause, or choose the clause from the contribution sign.

### 9. [MED] Crisis `run_crisis.sh` will crash at the first CV fold
- **Where:** `model/train.py:177, 199-200`. With `--test-start 2021-09-01`, `cv_months = [Jun 1, Jul 1, Aug 1]`. For
  `m0 = 2021-06-01`, `ftr = tr & (tgt_date < 2021-06-01)` is empty if the crisis table starts on 2021-06-01.
- `fit_all()` on 0 rows raises (LightGBM refuses empty data).
- CV is not used in `--rolling` mode (`chosen` is overwritten at `:212`), so it is dead weight there.
- **Fix:** skip empty folds (`if not ftr.any(): continue`), or skip the CV block when `rolling`.
- **Related data gap:** only 40 of 304 crisis days are on disk now (`data/ais_crisis`). `emissions.py` also does not
  reindex to the full date range, so totals only cover days present while `days=len(res)` reads as full coverage.

### 10. [MED] Researcher degrees of freedom around "model fixed in advance"
- **Where:** `model/train.py:209-213`, `:31-33`.
- **Issues:**
  - `avg` is the best candidate at h=1 and h=2 on test (1.746 vs 1.776 / 1.807 / 1.795), but not at h=3 (cat 2.273 < avg 2.301).
  - The hyperparameters, the 25 kn storm cut, the choice of rolling vs single split and the fc features were all
    explored on the same Oct-Dec window. Whether `avg` was chosen before seeing test is UNVERIFIED.
  - `metrics.json` carries a `cv_mae` field that looks like a selection but is unused in rolling mode.
- **Fix:** state that the Oct-Dec window was also used for design choices. Ideally hold out Nov-Dec 2023 or Jan-Mar 2025
  (not available as points) as a true holdout.

### 11. [MED] CI is not a full uncertainty statement
- **Where:** `model/train.py:148-156`.
- **Issues:**
  - Non-circular 7-day blocks over 92 days give about 13 blocks.
  - The CI ignores the choice of best-of-three baseline, the model choice, and the three-horizon multiplicity.
  - The skill is a ratio of MAEs and the CI is 90 %, so an interval that excludes 0 (h=1) holds only at that level.
- **Fix:** use a stationary or circular block bootstrap, report 95 %, and say "one winter quarter".

### 12. [LOW-MED] Wait time and arrivals have undocumented censoring and definition quirks
- `pipeline/build_daily.py:99-100, 116`:
  - `avg_wait_hours` is assigned to the day of the first moored ping (`t_berth`).
  - Visits still at anchor on the last day (and, in the crisis, ships anchored outside the bbox) have no wait.
  - So during a growing queue the average understates (right-censored).
  - It is also left-censored for ships already anchored at the start of data.
  - Only `ffill` is applied, not flagged.
- `:82-85, 97`:
  - Arrivals are "first ping in bbox after 24 h absent". They include ships that merely enter and leave
    (bunkering, pilot station trips) and exclude ships that drift out for less than 24 h and come back.
  - The name `arrivals_24h` suggests port calls. State the definition on the slide.
- `:110-111`: the outage nulling only covers the outage day and the next day. A departure on the day *before* a gap day
  cannot be a false positive (the ship's last ping is real), so this is OK. A multi-day gap where coverage is ≥20 h but
  <24 is not handled (hypothetical).

### 13. [LOW] Smaller code issues
- `train.py:186-187`: at h=1, `fc_gust_target` and `fc_gust_tomorrow` are identical columns, so SHAP splits credit
  between them and may print the same fact twice in `top_features`. Drop the duplicate at h=1.
- `train.py:217`: `pd.date_range(test_start, test_end, freq="MS")` skips a first partial month if `--test-start` is not
  the 1st; those rows would stay NaN in `pred` and poison MAE. Use a month-start floor of `test_start`.
- `train.py:138-139`: the `lin()` contribution for ridge assumes `SimpleImputer` keeps all columns. A column that is
  entirely NaN in a training fold is dropped by the imputer, which gives a shape mismatch.
- `build_daily.py:42-54`: running without `--berth-in` overwrites `data/berth_cells.parquet`, which `export_replay.py`
  reads. Running it on a partial pull silently changes the replay mask.
- `build_daily.py:74` `a_big` is "cargo ≥ 250 m" and includes large bulkers. In `emissions.py:27-28` that class gets
  container 8,000-14,000 TEU loads, an overestimate for bulkers. Only 4 % of ships.
- `emissions.py:35-36` comment says POLA's implied rate is "~250 kg NOx per ship-day". The code (`:41-42`) correctly
  gives **227**: 118 short tons × 907 kg ÷ (11,312 h / 24). 250 is what you get by treating short tons as metric.
  Fix the comment. Our 129.5 kg is 57 % of 227, so "about half" is fair.
- `emissions.py:41-43` cites "Table 3.16" for POLA 2023. In the 2023 report Table 3.16 is the methanol emission factors;
  the by-mode table is **Table 3.18** (`ei2023.txt:4790`). The 2021 report's Table 3.16 is correct for 2021.
- CLAUDE.md figures not re-verified: POLA CY2021 anchorage hotelling "2,848 short tons NOx = 48 % of 5,956". The 5,956
  total is confirmed (`ei2021.txt:3641`), and 2,848/5,956 = 47.8 %. The mode table does not extract from the PDF text
  here, so the 2,848 itself is UNVERIFIED. Note POLA 2021 also reports loitering in a separate row.
- Nov-2021 CARB sheet says container BAU at anchor is 0.09 tpd; the Feb-2023 sheet says 0.2 tpd. `emissions.py` uses
  0.2 (the later one). State which vintage is quoted.
- Time conventions: all UTC days. Issue time is the end of UTC day `t` (5 pm PDT), and "h=1" is a 24 h mean starting at
  that moment. Say so, because "tomorrow" on the slide reads as local.

## Suggested order of fixes (if time is short)
1. Findings 4 and 5: text only, 5 minutes, and they are wrong on the screen now.
2. Finding 3: exclude Hueneme/El Segundo from replay `waiting_offshore` (map is judge-visible).
3. Findings 1 and 2: reword the h=1 claim; pin one Open-Meteo model and re-run.
4. Finding 9: one-line guard before running the crisis chain.
5. Findings 6 and 7: relabel in the deck.
