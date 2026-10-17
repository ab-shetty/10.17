# Judge Q&A prep: the 15 hardest questions (port ops manager, ML researcher, air-quality scientist)

Every number below is from a repo file; the source is in [brackets]. "Derived" = simple arithmetic on two repo numbers, flagged so nobody quotes it as a source figure. Where a 90 % CI includes 0 the answer says "roughly ties". Read the **Weak spot** lines out loud before the demo: each one is a place a judge can hurt us.

Framing to say first, every time: **this is a 2024 replay, not a live system** [CLAUDE.md].

---

## A. Model and evidence (ML researcher)

### 1. "How do I know there is no leakage?"
**Answer.** Test is Oct–Dec 2024 (92 days) [shared/metrics.json]. The headline is rolling-origin: the model is refit before each test month on data whose *target date* is before that month, and the model type is fixed in advance as the plain average of LightGBM, CatBoost and ridge, so no test month chooses the model [model/train.py `main`, `rolling` branch]. Features are built from data known on the issue day: departures are shifted one day because a departure is only known 24 h later, and weather forecasts are the ones issued on the issue day [model/train.py `features`, `fc_gust_target`].
**Weak spot.** Some choices were made looking at all of 2024: the berth-cell mask is built from every 2024 ping when `--berth-in` is not given, and ANCHOR_BOX was fixed from a heatmap of the year [pipeline/build_daily.py; CLAUDE.md Geography]. These are static geometry, not the target, but a strict reviewer will call them mild look-ahead. Feature and hyperparameter choices (fog, waves, inbound ships, ridge alpha) were also iterated by hand and the repo does not record whether that was done before or after seeing test scores. Do not claim "never touched the test set".

### 2. "Is +10 % even meaningful? That's a tiny forecast improvement."
**Answer.** At h=1 the model's MAE is 1.746 ships vs 1.944 for the best naive baseline (a 50/50 blend of persistence and 7-day mean), skill +10.2 %, 90 % CI [+2.9, +16.3] [shared/metrics.json]. Against persistence alone it is 2.104 → 1.746, +17.0 % [shared/metrics.json]. The baseline is picked as the *best of three on the test set*, which is deliberately the toughest comparison and works against us [model/train.py docstring].
**Weak spot.** The absolute gain at h=1 is 0.198 ships (1.944 − 1.746, derived) on a queue that averages 15.3 ships [CLAUDE.md]; the model's own error is about 11 % of the mean (derived). At h=2 and h=3 the gain is about 0.08 ships each (2.327 − 2.244; 2.381 − 2.301, derived). "+17 % vs persistence" sounds better than "+10 % vs the best baseline"; lead with the second.

### 3. "92 test days, one quarter, three horizons. Why believe any of it?"
**Answer.** Only h=1 beats the best baseline with a CI that excludes 0 (+10.2 %, [+2.9, +16.3]). At h=2 (+3.6 %, [−10.0, +15.0]) and h=3 (+3.4 %, [−9.8, +13.0]) the model **roughly ties** the 7-day mean [shared/metrics.json]. The CI is a 7-day block bootstrap because daily errors are autocorrelated [model/train.py `block_bootstrap_skill`].
**Weak spot.** 92 days is about 13 independent 7-day blocks (derived), so even the h=1 interval is fragile, and it is a 90 % interval, not 95 %. Three horizons were reported with no multiple-comparison correction. The test window also contains the 2024-12-25/26 AIS outage (11–13 h of coverage) [CLAUDE.md]; arrivals and departures are nulled there but the effect on `n_anchored` itself is not quantified in the repo.

### 4. "You reported both a single split and rolling-origin. Which did you pick, and when?"
**Answer.** CLAUDE.md reports both: rolling h=1 +10.2 % / h=2 +3.6 % / h=3 +3.4 %, and single split (train Jan–Sep once, CV-chosen model) +8.0 % [+0.9, +14.5] / −3.7 % / −1.2 % [CLAUDE.md]. Rolling is the headline because it is what a deployed system would do and what the crisis run uses [CLAUDE.md].
**Weak spot.** The sign flips at h=2 and h=3 between the two protocols. That is consistent with "no real edge beyond h=1", and the repo does not show which protocol was chosen first. Say plainly: *only h=1 is a real result; h=2 and h=3 are ties.* Also, the older OVERSEER.md numbers (8 / 5 / 5 % overall, +22–26 % on "big moves", direction right 74–82 %) are stale; "big move" selected days by the outcome and was dropped [OVERSEER.md, CLAUDE.md]. Make sure none of those reach a slide.

### 5. "The storm-day result: how many days, and is it forecast-based?"
**Answer.** Storm days = forecast gust ≥ 25 kn known on the issue day. At h=1 that is n = 10 days, MAE 2.166 vs 3.202, skill +32.4 %; at h=2 n = 11, +18.3 %; at h=3 n = 11, +1.4 % [shared/metrics.json]. The weather input is the archived Open-Meteo previous-runs forecast, available only from 2024-01-19 [CLAUDE.md; model/train.py].
**Weak spot.** Ten days is a very small sample and no CI is reported for the storm subset. There is also an internal contradiction: one CLAUDE.md bullet says the model "does NOT foresee the gale itself (no weather-forecast input)", while `train.py` feeds `fc_gust_target` / `fc_gust_tomorrow` and the metrics report a storm skill [CLAUDE.md; model/train.py]. A judge who reads both will notice. A (Person A) should fix that bullet. Also the forecast features only cover about 8 months of training (Jan 19 → Sep, derived), so few storm examples exist to learn from.

### 6. "Does the explanation panel show causes?"
**Answer.** The reasons come from SHAP (trees) and coefficient × standardized value (ridge), averaged across the three models; the current queue level is hidden because "18 tomorrow because 18 today" explains nothing [model/train.py `contributions`, `HIDDEN`]. Phrases say what "pushes the forecast up/down".
**Weak spot.** These are model attributions, not causal effects. Phrases like "ships that left anchor tend to return" and "storm: ships leave anchor" are the team's interpretation, based on AIS showing part of the fleet riding out gales under way and re-anchoring [model/train.py `phrase`; CLAUDE.md "Episodes = weather"]. Present them as "what the model leaned on", not "what caused the change".

---

## B. What "at anchor" means (port operations manager)

### 7. "Define 'at anchor'. Whose status field is that?"
**Answer.** At anchor = AIS `status = 1` AND `sog < 0.5` AND inside ANCHOR_BOX (lat 33.58–33.77, lon −118.30 to −117.97) AND not in a data-derived berth cell; the count is the mean over 24 hourly snapshots of distinct ships, per UTC day [CLAUDE.md; pipeline/build_daily.py]. Check against the ports: our count of ≥ 250 m cargo ships at anchor correlates r = 0.49 with POLA's own container ships at anchor, and our moored count r = 0.62 with POLA at berth [CLAUDE.md].
**Weak spot.** `status` is typed in by the crew, and r = 0.49 means about a quarter of the variance (derived, r² ≈ 0.24). It is a *moderate* validation, not agreement. The ≥ 250 m cargo class is also only a proxy for container ships [pipeline/build_daily.py]. The berth mask is a heuristic (0.002° cells, ≥ 30 moored pings, dilated one cell) because inside-breakwater anchorages sit right next to terminals [CLAUDE.md]. Days are UTC, so a "day" ends at 5 pm PDT, not midnight.

### 8. "You say 'queue' and 'congestion', but is a 2024 anchored ship actually waiting for a berth?"
**Answer.** Not mostly. The 2024 anchored fleet is about 74 % tankers (11.3 of 15.3 on average) [CLAUDE.md], and in the emissions fallback mix only about 4 % are large (≥ 250 m) cargo ships [pipeline/emissions.py]. POLA's October 2024 release says record volume moved "without a single ship backed up at sea" [pipeline/notes/port_events_2024.md; CLAUDE.md]. So the honest wording is "ships waiting at anchor", not "container queue" [CLAUDE.md].
**Weak spot.** This is the biggest framing risk for the port-ops judge. A tanker at anchor can be waiting on a refinery or crude terminal slot, orders, or bunkers, not on container-port congestion. The 2024 target therefore measures anchorage use, and "congestion" is only a fair word for the 2021–22 backlog. Never say 2024 had a queue problem; the project's own sources say it did not.

### 9. "Why not just use the Marine Exchange count?"
**Answer.** The Marine Exchange count is what operators already watch, and our AIS reconstruction matches it on the one day we checked: 2021-10-25 MX = 56 at anchor + 51 in holding areas = 107; ours = 56 + 52 [CLAUDE.md; pipeline/notes/crisis_timeline_2021.md]. Our value is a *forecast* built from open data plus a replayable method, not a better count. I found no 2024 MX queue counts published in the repo's sources [pipeline/notes/port_events_2024.md].
**Weak spot.** MX has the ground truth and ships' scheduled arrivals; we have neither. After 2021-11-16 the MX headline changed to a queue by calculated time of arrival that includes ships days away in the Pacific, so there is no like-for-like series to validate against (and the 109 is a different count: 2022-01-09, ships 150+ nm out) [pipeline/notes/crisis_timeline_2021.md; CLAUDE.md]. The match is one day, not a time series.

---

## C. The 2021–22 backlog and the Nov-16 regime change

### 10. "From Nov 16, 2021 ships queue 150+ nm away. Your AIS can't see that. What does your crisis story actually show?"
**Answer.** We say so ourselves: after 2021-11-16 anchored counts fall for a reason shore AIS cannot see, so the crisis target is `n_waiting = n_anchored + offshore_waiting` (loitering < 60 nm, < 3 kn), and the story windows are before the rule change [OVERSEER.md; CLAUDE.md]. On 2021-10-25 a bay-only count would miss half the crisis queue: 56 anchored, plus 52 drifting at 0.5–3 kn outside the bay, 59 of 61 within 60 nm [CLAUDE.md].
**Weak spot.** At the time of this review `shared/crisis/` contains only `weather_daily.json`; there is no crisis `metrics.json`, `preds.json`, `chart.json` or `episodes.json` in the repo [shared/crisis/ listing]. So I cannot cite any out-of-sample crisis skill number, and "forecast turns up before the queue" [CLAUDE.md contracts] is a design goal, not a result I can verify. Also, the 2021 weather has no archived forecasts, so the crisis model "can't see storms coming" [CLAUDE.md], and the peak day coincided with a bomb cyclone that may have shifted ships between "anchored" and "loitering" [pipeline/notes/crisis_timeline_2021.md]. If the crisis model only ties the baselines, say "roughly ties".

---

## D. Emissions (air-quality scientist)

### 11. "Show me the emissions method, and which units?"
**Answer.** Ship-hours at anchor (from AIS) × POLA-inventory anchorage hotelling loads (aux engines + boilers, class averages) × 0.1 % S marine gas oil emission factors (NOx 10.5 g/kWh aux, 1.97 boiler) [pipeline/emissions.py]. 2024 result: 5,594 ship-days at anchor, 724.8 t NOx, 18.52 t PM2.5, 84,659 t CO2, 26,407 t fuel, 129.5 kg NOx per ship-day [shared/emissions.json]. Units: our files are **metric tonnes**; CARB's tons/day and POLA's NOx are **short tons** (1 short ton = 0.907185 t) [pipeline/emissions.py].
**Weak spot.** No uncertainty band is published. The loads are simple averages of POLA's per-class defaults, the fleet is assumed Tier II (a Tier I fleet is about 16 % higher in NOx) [pipeline/emissions.py], and the same load is applied for every anchored hour whatever the ship is actually doing. The fuel note itself says the tonnes-per-day burn is "±50 % uncertainty" for a large container ship [pipeline/notes/fuel_prices.md]. A slide with "725 t" and no range or unit invites a challenge. The 725 t is also the NOx *emitted at anchor*, not NOx a forecast would avoid (see Q14).

### 12. "Your rate is 'conservative' (about half POLA's), yet your total exceeds CARB's baseline. Which is it?"
**Answer.** Both, for different reasons. Our rate is 129.5 kg NOx/ship-day vs POLA's implied 227.1 [shared/emissions.json], about 57 % (derived; CLAUDE.md says "~½"). But our ship-days are higher because we count every cargo ship and tanker anchored in the bay, not only POLA calls. Result: 2.18 short tons NOx/day vs CARB's business-as-usual 1.7 for tankers + containers at anchor (1.5 + 0.2) [shared/emissions.json].
**Weak spot.** The 28 % excess over CARB (2.18 / 1.7, derived) is partly scope (we include bulk and car carriers; CARB's figure in this comparison excludes cruise ships' 0.6 and ours excludes them too, so that part is consistent), and it is not constant: November 2024 is 1.61, below CARB's 1.7 [shared/emissions.json `vs_carb_monthly`]. "Conservative" and "above CARB BAU" will sound contradictory unless explained as *rate per ship* vs *number of ships*. The comparison is a sanity check at the right order of magnitude, not an independent validation.

### 13. "Do your emissions cause health harm in Wilmington?"
**Answer.** We do not claim that. The health notes state: no study or agency statement was found that quantifies health outcomes (deaths, asthma cases) from the 2021 anchored-ship emissions; say "exposure and vulnerability", not "caused N cases" [pipeline/notes/health_context.md]. What is verified: all 14 populated Wilmington tracts rank in California's worst quarter on CalEnviroScreen 4.0 (76th–99th percentile), and 6 are at or above the 97th for diesel PM [pipeline/notes/health_context.md; CLAUDE.md]. CARB estimated about 20 tpd of excess NOx at the Oct 2021 peak [CLAUDE.md; shared/emissions.json].
**Weak spot.** CalEnviroScreen diesel PM is a 2016 emissions-based estimate that does not reflect the 2021 queue, and ZIP-to-neighborhood mapping is approximate [pipeline/notes/health_context.md]. We ran no dispersion model, so we cannot say how much of our anchored-ship NOx reaches Wilmington (the loitering ships are 10–60 nm out [pipeline/emissions.py]). The "5.8 million passenger cars" equivalence is CARB's, and the CARB PDF text was not re-read in the health notes (tagged SECONDARY). Several statistics (86 deaths/yr, 67 deaths/yr, 98 % higher cancer risk) are UNVERIFIED or not headline-grade; do not use them [pipeline/notes/health_context.md].

---

## E. Generalization and action (all three)

### 14. "What would an operator actually do with a 1-day forecast? Where is the avoided-emissions number?"
**Answer.** The pitch is just-in-time arrival: inbound ships slow down instead of idling at anchor [OVERSEER.md]. The model does see ships inbound within 60 nm, its best new signal (corr 0.18 with tomorrow's queue change) [CLAUDE.md]. The horizon is only 1–3 days from shore receivers; a longer horizon needs Port of LA Signal data [CLAUDE.md Risk 2].
**Weak spot.** `shared/emissions.json` contains emissions *at anchor*, with no avoided-tonnes or avoided-dollars estimate [shared/emissions.json summary keys]; OVERSEER.md's "X tonnes and $Y avoided" has no repo number behind it yet. Physically, a 1-day h=1 forecast with +0.198-ship accuracy gain (Q2) leaves little room for speed changes by ships crossing the Pacific; and in 2024 only about 4 % of anchored ships are big cargo ships [pipeline/emissions.py], while tanker waits depend on refinery schedules. If asked, say: "the forecast helps anchorage and pilot planning and is a base for the longer-horizon version; we have not measured avoided emissions." A fuel-cost line can be derived from repo values (26,407 t × $760/t ≈ $20 M for all 2024 anchored ship-days, derived) but that is total burn at anchor, not savings, and $760/t is an EIA diesel *proxy* [pipeline/notes/fuel_prices.md].

### 15. "Does this generalize beyond one port-year?"
**Answer.** Evidence so far: one port complex, one normal year (2024) with a Oct–Dec test, plus an in-progress 2021–22 crisis run [CLAUDE.md]. The 2025 holdout is not done: only monthly *tracks* exist (no per-ping sog or timestamps), 1.1–1.8 GB per month, a status per segment, and the extraction query was never completed because of RAM [pipeline/notes/aistrack2025.md].
**Weak spot.** Everything quantitative in this file is from Oct–Dec 2024. The 2025 tracks use a different definition of "at anchor" and need calibration before they could be called a holdout [pipeline/notes/aistrack2025.md]. No other port, no other year with the same pipeline, and no crisis result in the repo yet (Q10). The honest line is "works in normal times for 1 day ahead; crisis-period and 2025 checks are not complete".

---

## The 3 changes that would most strengthen the project in the time left

1. **Lock one "defensible numbers" sheet and purge contradictions (≈30 min, highest value per minute).** Use only: h=1 +10.2 % [+2.9, +16.3] vs the best baseline; h=2/h=3 "roughly ties"; storm days n = 10, +32.4 % labelled small-sample; 725 t NOx with unit, scope and a range. Delete or fix the stale lines: OVERSEER.md's 8/5/5 % and +22–26 % "big moves", and CLAUDE.md's "no weather-forecast input" bullet that contradicts `train.py`. Say "ships waiting at anchor (74 % tankers)", never "container queue" for 2024.
2. **Produce and honestly report the crisis out-of-sample result, or demote it.** `shared/crisis/` has no metrics, preds or chart yet, yet the 2021 story is the headline. Run the same rolling-origin evaluation (n_waiting target, same block-bootstrap CI vs the best naive baseline), publish `shared/crisis/metrics.json`, and show the number whatever it is. If the CI includes 0, the slide says "roughly ties" and the headline becomes the AIS reconstruction (56 + 52 vs MX 56 + 51) plus the emissions context.
3. **Put an uncertainty band and the right units on the emissions headline, and relabel it "emitted at anchor", not "avoidable".** Re-run `pipeline/emissions.py` with a low/high load case (for example the min and max of the POLA per-class loads it already lists, and the +16 % Tier I case) and show 725 t as a range in metric tonnes, with CARB's short-ton figures converted. Add one clearly labelled *scenario* (for example "if X % of anchored hours were avoided") only as an illustration, since no avoided-emissions result exists.

Not worth the remaining time: the 2025 holdout (RAM-heavy, definitions differ, calibration unfinished) and any new health statistic beyond the verified CalEnviroScreen line.

**Q: Your berthing rate (3.6 container ships/day in 2021) is lower than IMF PortWatch's 5.7 LA-LB container calls/day. Why?**
Definitional. Our rate (`wait.json` `berths_per_day_7d`) counts only ships that **waited** (≥ 6 h at anchor or loitering)
before berthing, because it is the service rate of the queue in Little's law. Ships that went straight to a berth, and
ships under 200 m, are not in it; PortWatch counts every call. Day to day the two move together (r = 0.42, 7-day means,
Jun–Dec 2021, 201 days; Overseer check). Same two inputs (free AIS for the queue, PortWatch for berthings) exist for
~1,600 ports.

**Q: Is the "published wait ran 2–3 days short" claim cherry-picked?**
No. Same code on 2024: the published-style 7-day average has bias 0.00 d in steady weeks, −1.0 d when the queue grew,
+1.2 d when it shrank (a lagging average does exactly that). In Sep–Oct 2021 the queue grew for months, so it was short
in all 9 weeks (−2.5 d for container-size ships). Our reconstruction matches the published figures (Aug 15: 6.5 vs 6.8 d;
Sep 9: ~7.3 d 30-day vs POLA 8.5; Oct 14: 13.9 vs NBC4 12). Little's law is unbiased but NOT more accurate per day
(MAE 4.3 vs 3.8 d): we claim bias, not accuracy.

**Q: How do you know what the port actually said?**
We rebuilt the published figure from AIS (trailing average wait of container ships that berthed) and checked it
against the dated published numbers (`pipeline/notes/wayback_2021.md`):
| date | published | our reconstruction | what ships joining that week really waited |
|---|---|---|---|
| 2021-09-10 | 8.5 d (POLA, 30-day average, range 1–18) | 7.4 d (30-day) / 7.3 d (7-day) | 9.6 d |
| 2021-10-22 | 10–12 d (Western Overseas advisory) | 11.0 d (7-day) | 17.8 d |
Agreement within ~1 day; in both weeks the real wait was longer than either.

**Q: Where does $5.1 M come from?**
Net understatement only: Σ over the 437 ships that joined the queue in Sep–Oct 2021 of (actual wait − the wait published
the day before) = 893 ship-days, × 7.3 t fuel per ship-day at anchor (Sep–Oct 2021 fleet mix; POLA inventory loads, our emissions method) ×
$780/t MGO = 6,500 t ≈ $5.1 M, 200 t NOx. Same calculation for 2024 gives −18 ship-days (≈ 0). Offshore loitering is priced at anchor rates (approximation).

**Q: "$320k–620k for one ship": how? (back-of-envelope)**
MSC JOSSELINE was told 12.5 d and waited 17.3 d. Told the real wait, she could have crossed the Pacific 4.8 d slower
instead of idling. Assumptions (all ranges): origin East Asia, 5,200–6,300 nm (Busan to Yantian); original speed
16–18 kn; main-engine burn 90–150 t/day at that speed for a ~14,000 TEU, 366 m ship (typical for the class, not her
logbook); fuel per mile ∝ v² (cube law per hour); new speed = distance ÷ (original time + 4.8 d) ≈ 12–13.5 kn;
VLSFO $580–650/t (Oct 2021). Saving = 550–950 t ≈ $320k–620k. The $38k of anchor fuel is NOT added: the generators
run at sea too, so that burn moves 100+ nm offshore instead of disappearing. It ignores engine-load limits and schedule penalties.
