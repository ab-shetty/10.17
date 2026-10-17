# Fuel prices for the at-anchor cost / emissions numbers (MGO, 0.1 % S, Los Angeles / Long Beach)

Searched 2026-10-17. **Bottom line: no sourced LA/LB MGO monthly or quarterly bunker series was reachable.**
Ship & Bunker's LA/LB history is behind a sign-in, Bunkerworld is paywalled, and the EIA has no bunker series.
What we can source is the **EIA Los Angeles ultra-low-sulfur CARB diesel spot price** (via FRED). It is the
nearest public, free proxy for LA MGO. $/t below is **our conversion**, not a quoted bunker price.

## 1. Sourced inputs

| Item | Value | Source |
|---|---|---|
| LA ULSD CARB diesel spot, monthly, $/gal (EIA via FRED series MDFUELLA) | Jun-21 2.077, Jul 2.124, Aug 2.155, Sep 2.251, Oct 2.512, Nov 2.509, Dec 2.291, Jan-22 2.674, Feb 2.851, Mar 3.631 | https://fred.stlouisfed.org/data/MDFUELLA |
| Same, 2024 monthly, $/gal | Jan 2.573, Feb 2.794, Mar 2.676, Apr 2.706, May 2.418, Jun 2.491, Jul 2.435, Aug 2.265, Sep 2.183, Oct 2.283, Nov 2.255, Dec 2.204 | https://fred.stlouisfed.org/data/MDFUELLA |
| Same, annual, $/gal | 2021 2.104; 2022 3.532; 2024 2.445 | https://fred.stlouisfed.org/series/ADFUELLA |
| Global 20-port average MGO, 2024 annual (not LA) | $812/t (2023: $897/t) | https://shipandbunker.com/news/world/424013-annual-average-bunker-price-at-key-hubs-mostly-flat-in-2024 |
| MABUX global MGO index, mid-Oct 2021 (not LA) | 761.06 $/t on 14 Oct 2021; 774.62 on 20 Oct 2021 | https://www.hellenicshippingnews.com/?p=891801 and https://www.hellenicshippingnews.com/?p=892686 (figures as relayed by a search summary; UNVERIFIED, pages not opened) |
| Argus Marine Fuels sample, 18 Oct 2021, Los Angeles ex-wharf | three numbers 637.50 / 759.00 / 524.50 $/t; **column labels not read** (PDF text could not be extracted). Order is likely VLSFO / MGO / IFO380, which would make LA MGO ≈ $759/t. Do not quote until checked. | https://view.argusmedia.com/rs/584-BUW-606/images/PRO-Sample-Report-Argus-Marine-Fuels-%282021-10-18%29.pdf (**UNVERIFIED**) |
| Ship & Bunker LA/LB page | Live daily quotes only (Oct 2026 MGO ≈ $1,600–1,700/t); history gated | https://shipandbunker.com/prices/am/us/lax-la-long-beach |

## 2. Conversion to $/tonne (our arithmetic)

$/t = $/gal × 310.8 gal/t, assuming MGO density 0.85 t/m³ (1 t = 1,176 L = 310.8 US gal). The density is an
assumption (typical 0.84–0.89), so ±3 %. EIA spot is ex-tax and ex-delivery, and a real MGO bunker quote
usually carries a barge/delivery premium over spot, so proxy values are probably a bit **low** (premium UNVERIFIED).

| Period | Mean $/gal | Proxy $/t |
|---|---|---|
| Jun-21 / Jul / Aug / Sep | 2.077 / 2.124 / 2.155 / 2.251 | 646 / 660 / 670 / 700 |
| Oct-21 / Nov / Dec | 2.512 / 2.509 / 2.291 | 781 / 780 / 712 |
| Jan-22 / Feb / Mar | 2.674 / 2.851 / 3.631 | 831 / 886 / 1,129 |
| **Jun-21 – Mar-22 (10 mo)** | 2.508 | **≈ 779** |
| Jun – Dec 2021 | 2.283 | ≈ 710 |
| Oct – Dec 2021 (queue peak) | 2.437 | ≈ 757 |
| **2024 (12 mo)** | 2.440 (EIA annual 2.445) | **≈ 758** |

Cross-checks: the proxy for Oct-21 (≈ 781) sits near the MABUX global MGO index (761–775) and near the likely MGO
column of the Argus LA sample (759). The 2024 proxy (≈ 758) sits below the Ship & Bunker 20-port MGO average
($812), as expected for a spot, ex-tax US West Coast number vs. a global mix.

## 3. Recommended single prices

| Period | Use | Why |
|---|---|---|
| Crisis, Jun 2021 – Mar 2022 | **$780/t** (range $650–1,130 across months) | 10-month mean of the EIA LA series converted at 0.85 t/m³. Agrees with the Oct-21 global MGO index and the probable Argus LA MGO. The Mar-22 spike (Ukraine) pulls the mean up; the queue peaked in Oct–Dec 2021 when the proxy was ≈ $757. A flat $780 is fine for a headline; if we cost day by day, use the monthly column above. |
| 2024 | **$760/t** (monthly range $680–870) | EIA 2024 annual 2.445 $/gal × 310.8 = $760. 7 % under the $812 global MGO average; the LA price is the better local choice. |

Say in the deck: "fuel priced at the EIA Los Angeles diesel spot price converted to $/tonne (assumes MGO density
0.85); actual bunker quotes carry a delivery premium, so costs are, if anything, understated". Never describe the
number as a Ship & Bunker or Bunkerworld LA quote.

## 4. Sanity check: fuel burned at anchor per ship-day

**No agency source with t/day at anchor for a container ship was found.** The CARB 2021 OGV documentation
(https://ww2.arb.ca.gov/sites/default/files/2022-03/CARB_2021_OGV_Documentation.pdf, `_ADA.pdf` variant too) has
anchorage hotelling aux power by container size bin, but the fetch returned empty so I could not read the values.
A search summary of it (UNVERIFIED) quotes berth hotelling aux kW of 683 (bin 12) to 761 (bin 19), with anchorage
listed in a separate column. To do: open the PDF by hand and read the anchorage columns. Same for CARB's at-berth
appendix: https://ww2.arb.ca.gov/sites/default/files/classic/msei/offroad/pubs/2019_ogv_inventory_writeup_ver_oct_18_2019.pdf
(says its scope excludes anchorage).

Our estimate: aux 1,200 kW × 217 g/kWh × 24 h = **6.2 t/day**; boiler 550 kW × 300 g/kWh × 24 h = **4.0 t/day**;
total **≈ 10.2 t/day** (about $7.9k/day at $780/t).

Weak outside comparisons (none is an agency source, none is a container ship at anchor):
- 19,000 DWT conventional ship, port-mode MGO 9.4 t/day (LNG-dual-fuel design 3.12 t/day), from a Springer
  *Journal of Shipping and Trade* table: https://jshippingandtrade.springeropen.com/articles/10.1186/s41072-018-0031-4/tables/5 (**UNVERIFIED**, page not opened).
- A vessel document with idle 2.0 t/day and working 4.5 t/day IFO (different ship type, source not identified; ignore).
- Generic container-ship burn at sea of 5–40 t/day (feeders) up to 200–400 t/day (ULCV) says nothing about anchor.

Read: ~10 t/day is the right order of magnitude (a 19k-DWT ship alone burns 9.4 t/day in port), but it is
unconfirmed for large container ships. The ~½-of-POLA conservative rate noted in CLAUDE.md suggests we are not
overstating. Treat 10 t/day as an estimate with ±50 % uncertainty until CARB's anchorage kW table is read.

## 5. What would close the gaps (needs a person, not a script)
1. Ship & Bunker sign-in: LA/LB quarterly MGO history for 2021–22 and 2024 (https://shipandbunker.com/prices/am/us/lax-la-long-beach).
2. Open the Argus PDF above and read the column headers of the Los Angeles row.
3. Read the anchorage-hotelling table in the CARB 2021 OGV documentation PDF.
