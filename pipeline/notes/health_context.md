# Harbor-community health context for the closing slide

Compiled 2026-10-17 from web lookups. Status tags: **VERIFIED** = number read from a primary data service or a document this session; **SECONDARY** = reported by a search snippet or a news or advocacy page, not checked against the primary document; **UNVERIFIED** = could not confirm, do not put on a slide.

**Bottom line:** We found no study or agency statement that quantifies *health outcomes* (deaths, asthma cases) from the 2021 anchored-ship emissions over Wilmington, San Pedro or West Long Beach. What exists is (1) tract-level vulnerability (CalEnviroScreen), (2) CARB and peer-reviewed emission and air-quality findings for 2021, and (3) general health effects of diesel PM, NOx and PM2.5. Say "exposure and vulnerability", not "caused N cases".

---

## (a) CalEnviroScreen 4.0 percentiles by tract

**Source (VERIFIED, queried live 2026-10-17):** the State Water Board's hosted copy of the OEHHA CalEnviroScreen 4.0 tract layer.
`https://gispublic.waterboards.ca.gov/portalserver/rest/services/Hosted/CES4_final/FeatureServer/0`
Fields used: `ciscorep` (overall score percentile), `diesel_pm_pctl`, `asthma_pctl`, `pollution_pctl`.
Query used: `where=zip IN ('90744','90731','90732','90806','90810','90813',...)`.
Official CES 4.0 report: `https://oehha.ca.gov/calenviroscreen/report/calenviroscreen-40`.
Re-check a few tracts in OEHHA's own map or spreadsheet before the demo. This is a mirror, not OEHHA itself.

**How the communities were picked.** I grouped tracts by the ZIP code the dataset assigns. Its `approxloc` column says "Los Angeles" for all of Wilmington and San Pedro, so ZIP is the only handle.
- Wilmington = 90744.
- San Pedro = 90731. ZIP 90732 (upper San Pedro / Rancho Palos Verdes side) is left out: it scores low (overall 21–64).
- West Long Beach = 90810, with 90813 shown as adjacent. 90806 and 90802 were pulled too but are not shown. The ZIP-to-neighborhood mapping is approximate; check against a map.

Percentile = rank among all California tracts (100 = worst). Tracts with population under about 700 or null scores are dropped.

### Wilmington (ZIP 90744), 14 tracts with scores
| metric | range | median | note |
|---|---|---|---|
| Overall CES 4.0 | 76.3 – 99.3 | ~91 | all 14 tracts are at or above the 76th percentile; 9 of 14 at or above the 90th |
| Diesel PM | 37.3 – 99.8 | ~84 | 6 of 14 tracts at or above the 97th percentile |
| Asthma (ED visits) | 74.8 – 83.0 | 83.0 | 11 of 14 tracts share the value 83.0 |
| Pollution burden | 72.6 – 98.0 | ~87 | |

Tracts to quote by ID:

| tract | overall | diesel PM | asthma | pollution |
|---|---|---|---|---|
| 6037294701 | 99.3 | 99.4 | 83.0 | 98.0 |
| 6037294830 | 97.7 | 99.7 | 83.0 | 91.5 |
| 6037294900 | 96.5 | 99.8 | 81.2 | 92.4 |
| 6037294820 | 95.0 | 99.3 | 83.0 | 80.6 |
| 6037294302 | 91.1 | 97.7 | 82.2 | 87.2 |

### San Pedro (ZIP 90731), 13 tracts with scores (excluding the 671-person tract)
| metric | range | note |
|---|---|---|
| Overall | 40.8 – 99.2 | wide spread; 5 tracts at or above the 87th percentile (6037297110: 96.7, 6037296500: 94.7, 6037296210: 99.2, 6037296220: 91.7, 6037297120: 88.3) |
| Diesel PM | 16.6 – 98.9 | high in the same tracts: 6037297110: 98.9, 6037296210: 98.6, 6037297120: 97.3, 6037296220: 97.0 |
| Asthma | 56.2 – 93.6 | 93.6 in most tracts (the value is shared) |

### West Long Beach (ZIP 90810), 10 tracts; adjacent 90813, 13 tracts
| ZIP | overall | diesel PM | asthma |
|---|---|---|---|
| 90810 | 82.6 – 99.0 (median ~92) | 59.6 – 99.2 | 81.9 – 84.8 |
| 90813 | 73.7 – 99.0 | 50.3 – 99.0 | 93.8 – 97.0 |

Example 90810 tract 6037572301: overall 99.0, diesel PM 91.7, asthma 84.8, pollution burden 98.5.

**Caveats for the slide:**
- The asthma indicator is a modeled rate of ER visits (2015–2017, from Tracking California), smoothed over larger areas. That is why many tracts share one value. Don't quote tract-level asthma as precise. Source: `https://oehha.ca.gov/calenviroscreen/indicator/asthma` (found via search; I did not read the page text).
- Diesel PM in CES 4.0 is a 2016 emissions-based exposure estimate (search snippet; SECONDARY). It does not reflect the 2021 queue.
- A few Wilmington tracts score low on diesel PM (37–59). Say "many tracts", not "all".

---

## (b) Health effects of NOx, PM2.5 and diesel PM from ships near ports

1. **Diesel PM and cancer.** OEHHA's page says long-term exposure to diesel particles carries the highest cancer risk of any toxic air contaminant OEHHA has evaluated. Diesel exhaust has 40+ toxic air contaminants; fine particles reach deep into the lungs; non-cancer effects include chronic bronchitis and airway inflammation.
   `https://oehha.ca.gov/air/health-effects-diesel-exhaust` (SECONDARY: from search snippet, page body not fetched.)
2. **Highest regional cancer risk is at the ports.** SCAQMD's MATES V summary slides: air-toxics cancer risk fell about 50% since 2012, the highest risk is in and around the ports, and diesel PM is the largest contributor.
   `https://www.aqmd.gov/docs/default-source/default-document-library/mates-v-admin-comm-presentation-060917final_jg.pdf` (SECONDARY: search snippet. That URL is dated 2017, so it is probably a *planning* deck for MATES V, not the final results. Confirm against the MATES V final report, 2021, before quoting.)
   I found no MATES V split by ocean-going vessels or a Wilmington-specific number: UNVERIFIED.
3. **Ship emissions and respiratory, cardiovascular disease and early death near ports.** A 2026 review: "The reviewed studies consistently associate these emissions with an increased risk of respiratory and cardiovascular morbidity and premature mortality among populations living near ports." NOx and fine particles remain largely unmitigated after IMO 2020 (which cut SOx).
   `https://doi.org/10.3390/su18041785` (SECONDARY: search snippet.)
4. **Wilmington cancer risk.** CalMatters (2022) reports cancer risk in Wilmington, mainly from diesel exhaust from trucks, ships and trains, is 98% higher than the rest of the LA basin.
   `https://calmatters.org/environment/2022/02/california-environmental-justice-by-the-numbers/` (SECONDARY: news summary of an agency figure; I did not trace the underlying data. Don't use it as a headline.)
5. **Statewide ship mortality estimates.** A search summary cited a CARB-backed InMAP analysis of about 86 premature deaths per year in California from shipping emissions, concentrated near the LA and Long Beach ports. I never saw the source: UNVERIFIED. A separate figure of 67 premature deaths and 2,000+ cases of lower respiratory harm per year from San Pedro Bay port activity came from a search summary with no link: UNVERIFIED. Do not use either.
6. **Offshore fleet and the air in port communities.** Peer-reviewed 2024 paper (IOP, Environmental Research Letters) cites a study that 2021 ship backlogs "increas[ed] NO2 and PM2.5 concentrations near the ports"; says port emissions "disproportionately impact disadvantaged communities in the South Coast Air Basin"; and notes four AB 617 communities are significantly affected by port freight.
   `https://iopscience.iop.org/article/10.1088/1748-9326/ad7747` (VERIFIED against the fetched page text, quotes are from the Introduction. The health statements there are qualitative and drawn from cited work.)

---

## (c) Studies and agency statements on the 2021 anchored-ship emissions specifically

| finding | source | status |
|---|---|---|
| Containership congestion raised South Coast NOx by about 20 tons/day and PM by 0.5 tons/day (as of Oct 2021), almost 20% of the additional 108 tpd of NOx cuts needed for the 80 ppb ozone standard by 2023 | CARB, Nov 2021: `https://ww2.arb.ca.gov/sites/default/files/2021-11/SPBP_Congestion_Anchorage_Emissions_Final.pdf` | SECONDARY (search summary; the PDF fetch returned empty). The 20 tpd figure matches the CARB fact sheets already in `data/ext/carb/` (see CLAUDE.md), so check there. |
| CARB: auxiliary-engine emissions from anchored vessels have substantial implications for portside communities, through PM and smog-forming NOx | CARB, June 2021: `https://ww2.arb.ca.gov/sites/default/files/2021-06/ogvcongestion_ada.pdf` | SECONDARY (search summary; fetch empty). Check the PDF in `data/ext/carb/` for the exact wording. |
| Excess emissions peaked October 2021 at 23 tons NOx/day; container ships at berth, anchored or loitering averaged 5.1 t/day NOx during congestion vs 0.1 t/day business-as-usual; the Nov 16, 2021 queuing system "significantly reduced vessel emissions near the coast" but moved them offshore, "not a complete mitigation strategy" | Peer-reviewed, Environmental Research Letters 2024: `https://iopscience.iop.org/article/10.1088/1748-9326/ad7747` | VERIFIED against fetched text. Note: the 23 t/d number is for the port-related total in that paper's abstract; the 5.1 vs 0.1 is containerships only. Quote them separately. |
| Ships at anchor hotelling emitted 2,848 short tons NOx in 2021 = 48% of POLA ship NOx, vs 118 tons in 2023 | POLA CY2021 and CY2023 inventories | Taken from CLAUDE.md. I did not re-fetch. POLA calls only. |
| CARB excess NOx at anchor 17.9 tpd (Nov 2021), falling to 2.6 by Mar 2022 | CARB Feb 2023: `https://ww2.arb.ca.gov/sites/default/files/2023-02/SPBP_Freight_Congestion_Emissions_Feb2023_ADA.pdf` | Taken from CLAUDE.md. I did not re-fetch. |
| Springer paper on San Pedro Bay congestion and emissions exceedances | `https://link.springer.com/article/10.1186/s41072-022-00126-5` | Title only; not read. |

Not found: any measured or modeled *health impact* (deaths, hospital visits, asthma) attributed to the 2021 anchored fleet, for any of the three communities. The 2024 ERL paper says outright that it does not quantify health outcomes. Don't claim one.

---

## (d) Slide one-liners (defensible as worded)

1. **"In Wilmington, all 14 populated census tracts rank in the worst quarter of California on CalEnviroScreen 4.0 (76th–99th percentile), and 6 sit at the 97th percentile or worse for diesel exhaust."**
   Source: OEHHA CalEnviroScreen 4.0, via `https://gispublic.waterboards.ca.gov/portalserver/rest/services/Hosted/CES4_final/FeatureServer/0`. VERIFIED. (Diesel claim: "at least the 97th" is exact: 97.7, 99.3, 99.4, 99.7, 99.7, 99.8.) Say "14 tracts with scores"; one more tract has a 9-person population.
2. **"At the Oct 2021 peak, CARB estimated the ships waiting off our ports added about 20 tons of smog-forming NOx per day to Southern California, on top of normal levels."**
   Source: CARB, Nov 2021 (URL above). SECONDARY until checked against the PDF in `data/ext/carb/`. Safe wording: "CARB estimated". Don't say "from Wilmington's air".
3. **"Diesel particles carry the highest cancer risk of any toxic air contaminant California has evaluated, and diesel PM is the largest contributor to air-toxics cancer risk around the ports."**
   Sources: OEHHA `https://oehha.ca.gov/air/health-effects-diesel-exhaust`; SCAQMD MATES V `https://www.aqmd.gov/docs/default-source/default-document-library/mates-v-admin-comm-presentation-060917final_jg.pdf`. SECONDARY for both: confirm quotes on the live pages, and use the final MATES V report rather than the 2017 deck if possible.

Optional 4th (ours, ties to the model): "Our 2024 replay counts ships anchored in the bay; in 2021 the queue was twice as large offshore" — internal, from `CLAUDE.md` / `pipeline/check_crisis_box.py`, not an external fact.

**Phrasing to avoid:** "caused", "killed", any death or asthma count for 2021, the 67/86 deaths figures, and the 98%-higher cancer-risk figure as a headline.

## Suggested next checks (10 minutes)
- Open `data/ext/carb/` PDFs and copy exact wording and page numbers for the 20 tpd and "portside communities" lines (replaces two SECONDARY tags).
- Spot-check 2–3 Wilmington tracts (e.g., 6037294701) in OEHHA's own CES 4.0 map.
- Fetch the MATES V final report for the port-area cancer-risk statement.
