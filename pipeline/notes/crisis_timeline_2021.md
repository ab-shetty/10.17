# San Pedro Bay container-ship backlog, June 2021 – March 2022: dated timeline

Compiled 2026-10-17 from web sources (fetched/searched today). Everything is tagged with a source URL; anything I could not
confirm on the page itself is marked **UNVERIFIED**. "MX" = Marine Exchange of Southern California.

## Read this first: the MX numbers are NOT one series

1. **Before Nov 15/16 2021** the MX headline was ships "at anchor + in holding/drift areas" within ~40 mi of the ports.
   Oct 25 2021: 56 at anchor + 51 in holding areas (gCaptain, below). Our repo found 56 status=1 ships on 2021-10-25, which matches the
   MX "at anchor" figure exactly; the MX "holding areas" ones are the loitering ships we found offshore.
2. **After the new queue (effective Nov 15 4 pm PST per Supply Chain Dive; Nov 16 per most others)** the headline became
   "container ships in the queue": `within 40 mi (anchored or loitering)` + `slow-steaming / loitering outside the 150 nm
   Safety and Air Quality Area (SAQA)`. Per FreightWaves, a ship is "in the queue" if its Calculated Time of Arrival (CTA, assigned when it
   leaves its previous port) is before the time of the count. So the later totals include ships that are still days away in
   the Pacific, far beyond ~60 nm. **Only the "within 40 mi" part is visible to shore AIS.**
3. **The famous "109" is a container-ship queue count on 2022-01-09 under definition 2** (MX centennial piece, Seapower; FreightWaves;
   LB Business Journal). Our CLAUDE.md quotes CARB (Nov 2021) saying "109 total vessels, up to 79 container ships at anchor"
   for Oct 2021, which is a different number that happens to be equal (all vessel types, definition 1). Do not mix them.
   (I could not re-read the CARB PDF text today, the fetch tool returned nothing for it; the CARB figure is from the search
   snippet and from CLAUDE.md. **UNVERIFIED here.**)
4. The "60 ships at anchor, Jan 28" record in Maritime Executive is **2021-01-28, not 2022** (the article is dated 2021-01-29; some
   search snippets mislabelled it).
5. Counts are container ships only after Nov 2021; before, "vessels" mixes types. Our AIS filter is all cargo + tankers (types 70–89).

## Timeline

| date | event | numbers (anchor / loitering / total) | effect on shore AIS within ~60 nm | source |
|---|---|---|---|---|
| 2021-01-28 | (background) first drift-box/holding-area use in ~17 yrs; record 60 at anchor | 60 at anchor, 3 in drift boxes, 110 ships in port, 38 of 60 awaiting berth were container ships | Pre-window context. Drift boxes are inside the 40 mi circle, so AIS sees them | https://maritime-executive.com/index.php/article/record-vessel-backlog-at-southern-california-ports |
| 2021-06 | Backlog low point of the year | 9 container ships waiting (June 2021) | Start of our window; everything visible | https://gcaptain.com/checking-in-on-southern-californias-containership-backup/ |
| 2021-08-29 | In-port record | 129 vessels in port (record then) | Includes ships at berth; anchored subset is smaller | https://maritime-executive.com/article/san-pedro-bay-sets-four-new-records-in-one-day-as-more-vessels-arrive |
| 2021-09-09/10 | MX "four records in a day" | 134 vessels in port; 86 containerships in port; 55 containerships waiting offshore (prev 49); 16 in drift areas (prev 12); 74 of the in-port vessels "actually waiting offshore" | Drift areas = loitering at 0.5–3 kn, inside the 40 mi circle; AIS sees them but status≠1. Our `offshore_waiting` is meant to catch these | https://maritime-executive.com/article/san-pedro-bay-sets-four-new-records-in-one-day-as-more-vessels-arrive |
| 2021-09-25 | Total-in-port record | 161 vessels in port (PolitiFact quoting MX) | Same caveat | https://www.politifact.com/factchecks/2021/oct/01/facebook-posts/no-back-cargo-ships-southern-california-coast-not- (via search snippet; page not fetched; **partly UNVERIFIED**) |
| 2021-10-13 | White House announces Port of LA moves to 24/7 operations (Long Beach had committed in Sept; Walmart/FedEx/UPS off-peak pledges) | – | Operational details "still being worked out" (Seroka). No immediate AIS signature | https://portoflosangeles.org/references/news_101321_portstatement ; https://www.cbsnews.com/amp/losangeles/news/biden-to-announce-that-port-of-la-will-operate-24-hours-a-day-in-effort-to-ease-cargo-backlog/ (statement itself only seen via search snippet) |
| 2021-10-18 (Mon) | MX noon report: new record of vessels waiting | 100 waiting (anchor + holding areas), 97 of them container ships; 157 vessels in port; pre-pandemic max 17 | Our box + offshore_waiting should show ~100 (as the ~110 we computed for Oct 25) | https://www.yahoo.com/news/theres-record-100-ships-floating-132156643.html |
| 2021-10-21 | MX count 79 containerships "at anchor or in holding areas" (record then; normal 2018/19 ≈ 17) | 79 container ships | Same | https://www.seatrade-maritime.com/ports-logistics/record-79-containerships-queued-at-la-long-beach-ports (403 on fetch; figure from search summary, **UNVERIFIED on page**) |
| 2021-10-25 | **Dwell fee announced** by both ports (see fee rows below). Same day: bomb cyclone / atmospheric river reaches the ports (Oct 25–26) | **56 at anchor + 51 in holding areas** (= 107 waiting, +57 at berth = 164 in port) | **Our peak day.** NWS small craft advisory, 15–25 kn winds, gusts 30 kn, seas 7–9 ft. Captain of the Port urged underway ships "to proceed under power"; holding-area ships told to keep engines on standby, stay >2 nm from others/shore. So some of the 51 "holding" ships were actively underway at 0.5–3 kn: wind may have moved ships between "anchored" and "loitering" | https://gcaptain.com/high-winds-expected-at-ports-of-los-angeles-and-long-beach-anchorages-and-holding-areas/ ; fee: https://gcaptain.com/los-angeles-and-long-beach-ports-continue-to-postpone-new-container-dwell-fee/ |
| 2021-10-29 | Both harbor commissions approve the temporary "container excess dwell fee": $100/container/day, rising $100 each day, for imports past the limit (8 d truck / 5 d rail per gCaptain; 9+ d / 6+ d per POLA's later release: **sources disagree**). Collected from carriers | – | None directly (landside measure) | https://gcaptain.com/los-angeles-and-long-beach-ports-continue-to-postpone-new-container-dwell-fee/ ; https://portoflosangeles.org/references/2021-news-releases/news_122721_dwellfee |
| 2021-11-09/10 | Peak of old-style count | 168 vessels of all types at anchor or loitering on Nov 9; 81 containerships on ~Nov 10 (first time >80) | Last days of the old regime: AIS box + offshore ring still sees almost all of these | https://www.seatrade-maritime.com/ports-logistics/new-record-81-containerships-waiting-outside-la-lb-ports (403 on fetch; from search summary, **UNVERIFIED on page**) |
| 2021-11-12 | Ports/MX/carriers announce voluntary queue guidelines | ~92 vessels "anchored or awaiting berth" earlier that week; goal 25–35 ships at anchor (40–60 % of anchorage capacity) | Announced, not yet in force | https://www.supplychaindive.com/news/ship-queueing-guidelines-san-pedro-bay-ports/609946/ |
| 2021-11-15 4 pm PST (most sources: Nov 16) | **New queuing process starts.** Queue position set by departure from last port (CTA), not by crossing the 20 nm line. Ships must wait outside the SAQA (150 nm for ships from the west, >50 nm from CA/Mexico coast for north/south) until ≤72 h before berth assignment. Voluntary, new arrivals only; working group covers ~90 % of anchored ships | **Record 86 container ships waiting within 40 mi on Nov 16** (MX, later quoted) | **Regime change in what AIS sees.** From here the nearshore count collapses while the queue total does not. Ships wait 60–150+ nm out, **beyond our 60 nm approach ring**. The effective-date discrepancy (Nov 15 vs 16) is a source conflict | https://www.supplychaindive.com/news/ship-queueing-guidelines-san-pedro-bay-ports/609946/ ; https://splash247.com/new-ship-queueing-process-at-la-and-long-beach-has-improved-safety-and-air-quality/ ; https://gallaghermarine.com/wp-content/uploads/2022/03/GMS-Client-Advisory-21-21-New-Queuing-Process-for-Container-Vessels-Bound-for-Ports-of-LA-LB.pdf |
| 2021-11-15 → 2022-01-03 | **Dwell fee start repeatedly postponed**: Nov 15 → 22 → 29 → Dec 6 → 13 → 20 → 27 → Jan 3 (weekly; gCaptain Dec 6: "fourth week in a row"). Ports credit a 26 % (early Nov) then 41 % (Dec 27) drop in aging cargo (POLA adds partly holiday slowdown) | – | None directly | https://portoflosangeles.org/references/2021-news-releases/news_112221_feehold ; https://portoflosangeles.org/references/2021-news-releases/news_121321_dwellfee ; https://portoflosangeles.org/references/2021-news-releases/news_122721_dwellfee ; https://www.seatrade-maritime.com/ports-logistics/ports-of-la-and-long-beach-delay-container-dwell-fee |
| 2021-11-24 | Louttit (MX): ships "loitering in SoCal waters are happily decreasing"; system doesn't speed up berthing | – | – | https://splash247.com/new-ship-queueing-process-at-la-and-long-beach-has-improved-safety-and-air-quality/ |
| 2021-12-04 | MX split count | 40 within 40 mi + 56 outside SAQA = 96 (a Facebook post cited 98) | AIS sees ≤ 40 of 96 | https://www.seatrade-maritime.com/ports-logistics/ports-of-la-lb-boxship-queue-keeps-growing-but-over-the-horizon (403; from search summary, **UNVERIFIED on page**) |
| 2021-12-08/09 | MX | **30 within 40 mi (down from record 86 on Nov 16) + 66 farther out / slow steaming = 96** at noon Dec 9 | AIS sees 31 % of the queue | https://lbbusinessjournal.com/fewer-container-ships-are-idling-directly-off-the-coast-but-the-port-backlog-persists-farther-out-at-sea/ |
| 2021-12-27 | Dwell fee "remains on hold" to Jan 3; aging cargo −41 % since Oct 25 | – | – | https://portoflosangeles.org/references/2021-news-releases/news_122721_dwellfee |
| 2022-01-09 | **Peak of the MX queue series: 109 container ships** (anchored or slow-steaming/loitering, CTA definition) | 109 total; split not found for the day. Nearest split: Jan 12 = 104 total | Mostly invisible: on Jan 12 only 11 of 104 were within 40 mi | https://seapowermagazine.org/marine-exchange-commemorates-100-years/ (MX centennial, dated 2023-07-05) ; https://www.freightwaves.com/news/zero-ships-waiting-off-southern-california-59-off-other-ports |
| 2022-01-12 | MX count | **104 total = 11 at anchor/loitering within 40 mi + 93 slow-steaming/loitering outside the SAQA** | **Best single example of the blind spot: AIS within 60 nm sees ≈ 11 of 104.** | https://latimesnow.com/2022/01/15/omicron-hits-longshore-ranks-as-absences-grow-in-ports-of-long-beach-la/ |
| 2022-01-13 | Omicron: ~800 dockworkers out (≈10 % of ~8,000 daily), ~1,200 positive tests Jan 1–10 on West Coast (80 % SoCal); ~⅓ of truckers out | – | Slower discharge keeps the queue high through mid-Jan, none of it nearshore | https://latimesnow.com/2022/01/15/omicron-hits-longshore-ranks-as-absences-grow-in-ports-of-long-beach-la/ |
| 2022-01-03 → | Dwell fee: the Dec 27 release postponed to Jan 3. I did **not** find whether it was ever charged. **UNVERIFIED** | – | – | https://portoflosangeles.org/references/2021-news-releases/news_122721_dwellfee |
| 2022-02-01 | Lunar New Year (Chinese factories close ~2 wks; fewer departures from Asia → fewer CTAs 2–3 weeks later) | – | The queue shrinks mainly offshore | calendar fact, no source needed |
| 2022-02-09 | MX queue: 78 total | **3 at anchor + 75 slow-steaming/drifting outside SAQA**; S&P headline "queue evaporates amid Lunar New Year slowdown" | AIS sees 3 of 78 | https://www.spglobal.com/commodity-insights/en/news-research/latest-news/shipping/020922-socal-container-ship-queue-evaporates-amid-lunar-new-year-slowdown (403 on fetch; numbers via search summary, **UNVERIFIED on page**) |
| 2022-03-25 | MX in-port count (all ship types) | 89 ships in the LA/LB complex, 32 container ships: 4 anchored/loitering + 28 at berth. Also "44 containerships in the arrival queue, down from 109" (undated) | Within-40-mi anchor count is back to single digits | https://www.westernoverseas.com/port-congestion-update-3-29-22/ (via search summary, **UNVERIFIED on page**) ; https://gcaptain.com/port-of-los-angeles-reports-its-third-busiest-month-ever-in-march/ |
| 2022-06-24 (Fri) | MX | 16 total = 1 at anchor + 15 outside SAQA, "2022 low"; 17 of next 18 arrivals go straight to berth. 2021 low was 9 (June 2021), 2021 Feb peak ~40 | – | https://gcaptain.com/checking-in-on-southern-californias-containership-backup/ |
| 2022-11-22 | MX declares the backlog over; first zero in 25 months; "effectively over for the prior three months" | 0 | Outside our window | https://www.freightwaves.com/news/zero-ships-waiting-off-southern-california-59-off-other-ports ; https://lbbusinessjournal.com/business/news/theres-no-longer-a-container-ship-backlog-at-san-pedro-bay-but-challenges-remain-for-the-twin-ports/ |

## Not found / gaps (do not fill from memory)

- **No MX count for the Jan–Mar 2022 "weather" days.** The only storm found in the window is the Oct 25–26 2021 bomb cyclone. My search found no
  weather-driven closure or pilot-station suspension in Nov 2021 – Mar 2022 (**UNVERIFIED either way**).
- **Labor:** the only labor event in the window is Omicron absence (Jan 2022). The ILWU contract fight (2022–23) is outside the window.
  I found no strike in June 2021 – Mar 2022.
- **MX daily noon reports** (the primary series) are not archived anywhere I could fetch; a request to the MX (mxsocal.org) is the way to get
  the daily within-40 mi / outside-SAQA split. All numbers above are as quoted in press.
- The Oct 2021 "109 total, 79 container, +20 tpd NOx" CARB numbers (from CLAUDE.md) should be re-checked against the PDF
  (`https://ww2.arb.ca.gov/sites/default/files/2021-11/SPBP_Congestion_Anchorage_Emissions_Final.pdf`) before putting on a slide.
- Dwell-fee thresholds conflict (8/5 days vs 9/6 days). Say "about a week".

## Best 3 story windows for a map replay

1. **2021-10-18 → 2021-10-27 (the peak, old regime).** Best because AIS sees the whole queue: 56 at anchor + 51 in holding areas on Oct 25,
   record 100 on Oct 18, 24/7 announced Oct 13, dwell fee announced Oct 25, and a bomb cyclone arrives Oct 25–26 (ships told to get under power
   and keep distance: you can watch anchored dots leave and re-anchor). Our offshore_waiting definition matches MX's "holding areas". Strongest numbers (~110) and matches CARB.
2. **2021-11-08 → 2021-11-24 (the regime change).** Watch the nearshore pile peak on Nov 9–16 (168 vessels all types, record 86 container ships within 40 mi on Nov 16) and then
   drain as the Nov 15/16 rule sends ships beyond the SAQA: 86 → 30 within 40 mi by Dec 8, while the MX total stays ~96. Best demo of *why a shore-based count must
   not be read as the queue* and of POLA's "improve safety and air quality" claim. Honest caveat for the pitch: the queue did not shrink, it moved.
3. **2022-01-06 → 2022-01-15 (the official peak, mostly invisible).** The 109 on Jan 9 and 104 on Jan 12, but only 11 within 40 mi. Pair with Omicron absence (800 workers out on Jan 13). Use it as the "what AIS cannot see" slide, not as a forecasting target, or as a test
   that the model's `inbound_60nm` feature rises before the discharge slowdown. Do not claim it as a queue forecast.

Optional 4th: **2022-02-01 → 2022-02-09**, Lunar New Year: 3 at anchor, 75 outside SAQA, shows the queue deflating with no visible change nearshore.
