# Fact check of CLAUDE.md "Status" sections and "⚠ For the Overseer"

Recomputed read-only from `shared/*.json`, `data/daily.parquet`, `data/ext/*`, and raw `AIS_2021_10_25.csv` (duckdb).
Web access was denied in this session, so external facts are checked only against the local copies of the primary documents
(CARB PDFs, POLA EI PDFs/txt). Anything not checkable is marked UNVERIFIABLE. Source URLs are the ones already recorded in
`pipeline/notes/*.md`; I did not re-fetch them.

Legend: OK / MISMATCH / UNVERIFIABLE. "Minor" = rounding or wording only.

## Summary of problems (read this first)
1. **MISMATCH: "52 more cargo/tankers drifting at 0.5–3 kn outside the bay", "59 of 61 within 60 nm".** I could not reproduce 52/61.
   Raw 2021-10-25, cargo+tanker (70–89), outside the study bbox, <60 nm of (33.70,-118.20), SOG 0.5–3: **63 ships**
   (59 if ships that also anchored in ANCHOR_BOX are removed; 64 with SOG<3 incl. <0.5). Within 120 nm: 65 ships, 62 within 60 nm,
   median distance ≈ 29–30 nm (so the *median* is OK). Direction of the conclusion holds (loitering ≈ as large as anchored), the numbers do not.
   Of the 63, 55 are type 70–79 and 8 are tankers, so this offshore group is container/cargo-heavy.
2. **Sum "≈110 ≈ Marine Exchange 109" is loose.** My sums: 56 + 59–63 = 115–119 distinct ships over the day; hourly mean 48.2 anchored + 54.7 offshore(<3 kn)
   = **103**. So "≈110" is within the range but the match to 109 is a coincidence of definitions, not a validation: CARB's 109 is "as many as ...
   as of October 2021" (a peak, all vessel types, Marine Exchange definition), not a 10-25 count. Say "same order of magnitude".
3. **Significance wording.** h=2 and h=3 CIs include 0 (correctly stated), but "a tie" overstates: the CIs (≈ −10 to +15 %) cannot rule out a 10 % loss or a 15 % win;
   "no detectable difference" is accurate. The h=1 claim (CI excludes 0) is fine but it is one of three horizons on 92 days, no multiplicity correction.
   Storm-day "+32 %" is n = 10 days, no CI given; for the same storm definition h=2 is +18 % (n = 11) and h=3 is +1.4 % (n = 11): quoting only h=1 is selective.
4. **Single-split numbers (+8.0 [0.9,14.5] / −3.7 / −1.2) are UNVERIFIABLE** from the shipped files: all of `shared/metrics.json`, `shared/preds.json`, `data/preds.parquet` are the rolling-origin run. Re-running `model/train.py` without rolling would confirm (I did not, to avoid writing files).
5. **`shared/emissions.json` mis-cites POLA 2023:** `cross_check.pola_2023_inventory.source` says "Tables 3.7 and 3.16"; in the 2023 report the by-mode table is **Table 3.18** (Table 3.16 there is a methanol emission-factor table). The 118 t number itself is right. (The 2021 report's Table 3.16 citation is correct.)
6. **AIS outage wording incomplete.** CLAUDE.md says outage 2024-12-25/26 only. In `daily.parquet`, `n_arrivals_24h` is null on 8 days (2024-10-19, 10-20, 10-31, 11-01, 12-25, 12-26, 12-27, plus 01-01 departures/ 12-31 departures differ), and coverage <24 h on 18 days; 10-19 (18 h) and 10-31 (19 h) are real partial outages too.
7. Minor: "our rate ≈ ½ of POLA's implied" is 129.5 / 227.1 = 57 % (and the POLA figure is POLA calls only).

## Table: 2024 forecast result (Status A, 12:00)
Baselines are the best naive baseline per horizon as named in `metrics.json` (h1 blend, h2/h3 ma7). My recompute uses `shared/preds.json` (rounded to 2 dp), CI = 7-day moving-block bootstrap, 4000 draws, seed 0 (so ±0.5 pt vs the stored CI is expected).

| claim | where stated | recomputed | verdict | note |
|---|---|---|---|---|
| Test = Oct–Dec, 92 days | Status A | n_test = 92 for each h; preds.json 276 rows (92×3), dates from 2024-10-01 | OK | |
| h=1 +10.2 % [90 % CI +2.9, +16.3] | Status A | skill 10.2 %; my CI [+2.6, +16.6]; MAE model 1.745 vs blend 1.944 | OK | CI excludes 0. Single comparison of 3 horizons |
| h=2 +3.6 %, h=3 +3.4 % | Status A | metrics.json 3.6 / 3.4; from rounded preds 3.5 / 3.4 | OK (minor) | |
| "CIs include 0: a tie with the 7-day mean" | Status A | h2 [−10.0, +15.0] (mine [−10.0, +14.3]); h3 [−9.8, +13.0] (mine [−10.2, +12.6]) | OK numbers; **overstated wording** | "no detectable difference", not "a tie" |
| "Vs persistence alone: +17 / +17 / +15 %" | Status A | 17.0 / 17.0 / 15.3 (mine 17.1 / 17.0 / 15.3) | OK | |
| Storm days (gust fc ≥ 25 kn, known on issue day): h=1 +32 % | Status A | n = 10, MAE 2.166 vs 3.202 → 32.4 %; mine 32.4 % using `fc1` (target day) or tomorrow fc ≥ 25 | OK; **small n, no CI** | Definition = max(forecast gust for target day, forecast gust for issue+1) ≥ 25 kn (`model/train.py:243`). h2 +18.3 % (n=11), h3 +1.4 % (n=11) not mentioned |
| Single split: +8.0 [+0.9, +14.5] / −3.7 / −1.2 | Status A | not reproducible from shipped files | UNVERIFIABLE | see problem 4 |
| "rolling-origin, refit before each month, plain average" | Status A | metrics.json `model:"avg"`, `evaluation:"rolling-origin, monthly refit"` for all 3 h | OK | CV-best single model would differ at h2 (cat 1.942 < avg 1.998) but the plan fixed "avg" in advance |
| Best naive baseline | Status A | baselines_mae h1: persistence 2.104, ma7 2.172, blend 1.944; h2: 2.704/2.327/2.373; h3: 2.718/2.381/2.393 | OK | Baseline picked on the test set → favours the baseline, i.e. conservative for the model |
| "CV on the 3 months before test" | Status A | `cv_mae` present per h | UNVERIFIABLE (windows) | not recomputed |
| Weather forecasts (`fc1..3_*`) only from 2024-01-19 | Status A, Contracts | first non-null fc1 = 2024-01-19; 348 non-null days | OK | |
| "The 2024 anchored queue is ~74 % tankers (11.3 of 15.3)" | Status A | mean n_anchored 15.29, mean tanker 11.31; ratio of sums 73.99 % | OK | `n_anchored` is a daily mean of hourly distinct counts; range 5.2–25.6, sd 3.46 |
| Best new signal: inbound within 60 nm, corr 0.18 with tomorrow's queue change, more than today's arrivals | Status A | corr(inbound_60nm, n_anchored[t+1]−n_anchored[t]) = 0.175; arrivals_24h 0.123; offshore_waiting 0.127 | OK | r² ≈ 3 %; "best" = best of the listed ones only |
| Validated vs POLA daily: ≥250 m cargo anchored r = 0.49 with POLA container ships at anchor | Status A | r = 0.494 (n = 249 days, 2024-01-02..12-31) | OK | POLA series has mean 0.54 ships at anchor/day; the total `n_anchored` correlates −0.005 with it, small cargo 0.17. The 0.49 is the one favourable slice. Date alignment (UTC vs POLA local day) not checked |
| Our moored count r = 0.62 with POLA at berth | Status A | r = 0.616 (n = 249) | OK | |
| AIS outage 2024-12-25/26 (11–13 h coverage) | Status A | coverage_hours 13 and 11 on those two days; arrivals/departures null | OK, **incomplete** | see problem 6 |
| Full 2024 pulled, 366 days | Status A | 366 files in `data/ais/`, 366 rows in daily.parquet, 366 approach files | OK | |
| Approach zone ships 20–120 nm out | Status A | `data/approach/appr_*.parquet` exist | UNVERIFIED (bounds not rechecked) | |

## Table: emissions (Status A)
| claim | where stated | recomputed | verdict | note |
|---|---|---|---|---|
| 2024 anchored: 725 t NOx, 18.5 t PM2.5, 84.7 kt CO2 | Status A | sum of daily: 724.75 t, 18.51 t, 84,659 t | OK | metric tonnes (emissions.json `nox_t`); CLAUDE.md does not say metric |
| 5,594 ship-days | Status A | 5,594.5 | OK | |
| "conservative per-ship rate, ≈ ½ of POLA's implied rate" | Status A | 129.5 kg/ship-day vs POLA 2023 implied 227.1 → 57 % | OK (minor) | "about 0.57" |
| POLA CY2021 Table 3.16: hotelling at anchor 2,848 short tons NOx | Status A | `ei2021.txt` Table 3.16 (garbled text, parsed): total hotelling at-anchorage NOx = 2,848 (aux engines 2,619 + boilers 228) | OK | POLA "tons" = short tons (US inventory) |
| = 48 % of all POLA ship NOx | Status A | 2,848 / 5,956 (sum of modes 1,544 + 290 + 1,222 + 2,848 + 53 loitering = 5,957; the extracted text shows "3,956.3", an OCR/extraction error) = 47.8 % | OK | Denominator = POLA OGV NOx in the POLA inventory domain, "POLA calls only" is stated |
| 24× the 2023 figure (118 tons) | Status A | 2023 Table **3.18**: total hotelling at-anchorage NOx 118 tons; 2,848/118 = 24.1 | OK | emissions.json cites wrong table number (problem 5) |
| `emissions.json` pola_2021 nox_t 2,584, pm25 55.2 | emissions.json | 2,848 × 0.9072 = 2,584; PM2.5 60.8 short × 0.9072 = 55.2 | OK | metric tonnes |
| "POLA's 2021 report says the Nov-2021 queuing process was adopted 'to increase safety and improve air quality'" | Status A | `ei2021.txt` l.365–368: "a new container vessel queuing process was implemented mid-November 2021 to increase safety and improve air quality near the ports" | OK | Report also says results "may not be reflected in this report", worth quoting with it |
| Our 2024 rate 2.2 short tons NOx/day vs CARB BAU 1.7 tpd for tankers + containers | Status A | emissions.json mean 2.18 tpd short (724.75/366/0.9072 = 2.18); CARB Feb 2023 figure labels: tanker 1.5 + containership 0.2 = 1.7 (cruise 0.6 excluded) | OK | CARB PDFs do not state the ton unit explicitly (UNVERIFIED that CARB tpd are short tons); CLAUDE.md notes we also count bulk/car carriers |
| CARB Nov 2021: as of Oct 2021 up to 79 container ships (109 total) at anchor | Status A | `SPBP_Congestion_Anchorage_Emissions_Final.txt` l.19–21: "as many as 79 container vessels (total of 109 vessels) at anchor near the SPBP", attributed to Marine Exchange | OK | "as many as" = peak, not a daily count |
| +20 tpd NOx ≈ 5.8 million passenger cars | Status A | same file l.53–61: 20 tpd NOx and 0.5 tpd PM "relative to pre-pandemic baseline"; "roughly equivalent to 5.8 million passenger cars in South Coast" | OK | It is containership-only, vs a baseline |
| +0.5 tpd PM ≈ 100,000 Class 8 trucks | Status A | l.61–62: "increased diesel PM emissions is comparable to almost 100,000 Class 8 diesel trucks" | OK (minor) | CARB says diesel PM / "almost" 100,000 |
| CARB Feb 2023 Table 1: 17.9 (Nov 21) → 7.0 → 4.3 → 3.5 → 2.6 (Mar 22) | Status A | Table 1 col "Containers, Cruise, and Tanker Vessels at Anchor": Nov 17.9, Dec 7.0, Jan 4.3, Feb 3.5, Mar 2.6 (also Apr 2.0, May 0.9, Jun 0.4) | OK | |
| POLA Oct 2024 release: record volume "without a single ship backed up" | Status A | quoted in `port_events_2024.md`; page not re-fetched (WebFetch denied) | UNVERIFIABLE here | URL: https://portoflosangeles.org/references/2024-news-releases/news_112024_oct_cargo ; note the quote in CLAUDE.md drops "at sea" |

## Table: data spike (Status 10:45)
| claim | recomputed | verdict | note |
|---|---|---|---|
| Sanity check 2024-01-01: 41 vessels in box, 19 status=1, sog ≈ 0.07 | study bbox on `ais_lalb_2024-01-01.parquet`: 41 distinct, 19 status=1, mean SOG of status=1 pings 0.069 (median 0) | OK | |
| ~0.4 MB filtered per day | 388 KB for 2024-01-01 | OK | |
| ~227 MB/day, ~4.5 s/day, full year ≈ 30 min | not testable offline | UNVERIFIABLE | |
| 2025 not available as daily points; monthly tracks ~1 GB | not testable offline | UNVERIFIABLE | see `pipeline/notes/aistrack2025.md` |
| Old coast.noaa.gov AISDataHandler links 404 | not testable offline | UNVERIFIABLE | |

## Table: ⚠ For the Overseer (raw 2021-10-25)
Definitions: cargo/tanker = VesselType 70–89; study bbox lat 33.55–33.80, lon −118.35..−117.95; ANCHOR_BOX lat 33.58–33.77, lon −118.30..−117.97; distance from (33.70,−118.20) by haversine in nm; pull box lat 32.5–34.6, lon −121..−117.2. 130,141 pings, 178 ships in the pull box.

| claim | recomputed | verdict | note |
|---|---|---|---|
| 56 anchored (status 1, SOG<0.5), all inside ANCHOR_BOX | 56 distinct; 56 in ANCHOR_BOX; 56 in bbox | OK | |
| "our boxes catch every status=1 ship" | same 56 (inside the pull box). Wide box 33.0–34.2 / −119..−117.4 checked by the script | OK | |
| 52 more cargo/tankers drifting at 0.5–3 kn outside the bay | 63 (0.5≤SOG<3, outside bbox, <60 nm); 59 excluding ships that anchored in ANCHOR_BOX; 66 at any distance in the pull box; 60 with SOG<3, status≠1 | **MISMATCH** | Could not find a filter giving 52. Hourly mean of the same group is 46.7 (0.5–3 kn) or 54.7 (SOG<3). Pipeline definition (hourly mean) gives 54.7 |
| 59 of 61 within 60 nm | 62 of 65 within 60 nm (≤120 nm group) | **MISMATCH** (minor) | same conclusion: ≈ 95 % within 60 nm |
| median 29 nm | 29.4–30.0 nm | OK | |
| anchored + loitering ≈ 110 | 56 + 59..63 = 115–119 (distinct, whole day); hourly mean 48.2 + 54.7 = 102.9 | MISMATCH / loose | see problem 2 |
| ≈ Marine Exchange's "109 vessels at anchor" (CARB Oct 2021) | CARB text: "as many as ... total of 109 vessels at anchor", MX data, all vessel types, October peak | OK as a quote, **not a like-for-like validation** | `crisis_timeline_2021.md` l.37 gives MX 10-25 as 56 at anchor + 51 in holding areas = 107, which is the better comparison (secondary source, UNVERIFIED) |
| "half the queue was loitering offshore" (commit message / lead sentence) | 59–63 loitering vs 56 anchored → 51–53 % | OK | |
| offshore_waiting def: hourly mean distinct cargo/tankers <60 nm, outside bbox, SOG<3; add `offshore_waiting`, `inbound_60nm` to `shared/crisis/daily.parquet` | `data/daily.parquet` has `offshore_waiting` (mean 8.0 in 2024) and `inbound_60nm` (2.9); `shared/crisis/` currently holds only `weather_daily.json` | NOT YET DONE for crisis file | by the Overseer; not a numeric claim |
| Figure `pipeline/figs/crisis_anchor_check.png` exists | present | OK | |

## Suggested rewordings
- Overseer section: "On 2021-10-25, 56 cargo/tankers were anchored (all inside our box) and another ~55–63 were drifting at 0.5–3 kn within 60 nm outside the bay (median ~30 nm), so a bay-only count sees about half of the waiting fleet. This is the same order as Marine Exchange's 107–109 'waiting' figure (CARB Nov 2021: 'as many as 109 vessels at anchor')."
- h=2/h=3: "no statistically detectable gain over the 7-day mean (CIs span ≈ −10 % to +15 %)".
- Storm days: "+32 % at h=1 on 10 storm-forecast days (no CI; +18 % at h=2, +1 % at h=3)".
- Fix `shared/emissions.json` cross_check source for POLA 2023 to Table 3.18 (and Table 3.7 for hours).
