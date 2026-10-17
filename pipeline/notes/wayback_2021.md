# Dated queue / wait-time ground truth, San Pedro Bay, Aug–Dec 2021

CSV: `pipeline/notes/wayback_2021.csv` (33 rows incl. 4 context rows outside the window). Every row has a source URL; `archived` is **no** for all rows.

## What I could not do
- **No Wayback snapshots.** `web.archive.org` is blocked from the fetch tool here, and the availability API returned no snapshot for `mxsocal.org` near 2021-10-25. So there are no `web.archive.org/web/2021…` URLs. The CSV cites the live news pages instead. I did not open mxsocal.org, signal.portoptimizer.com or the Port of Long Beach pages directly.
- Several Seatrade, S&P and gCaptain pages returned 403. Those rows say `search-snippet only` and are less reliable. The rest were fetched and read.
- The NBC4 page had no body text, so its 12-day figure is unverified.
- I did not extract the Seroka testimony PDF text. Its 20-day figure comes from a search snippet.

## Coverage
- **Average wait (days), container ships**
  - 2021-08-17: 6.8
  - Aug monthly: 8.5 (POLA)
  - 2021-09-10: 8.5 (30-day avg, range 1–18)
  - 2021-09-17: 11–15
  - 2021-10-14: 12 (unverified)
  - 2021-10-22: 10–12
  - Nothing found for Nov or Dec 2021.
  - There is no clean daily series. Only 2021-09-10 states its averaging window.
- **Counts**
  - Dated Marine Exchange counts exist for Aug 13–16, Sep 10, Sep 17, Oct 18–22, Nov 9–10 and Dec 1.
  - Of these, only Sep 10 and Oct 19 give a clean container-ship or all-vessel split.
  - Nothing found for Dec 2021 beyond Dec 1.

## Caveats
- **Definitions changed on 2021-11-16** (voluntary queuing rule: ships wait 150+ nm out until about 72 h before their berthing slot). Counts before are "anchor + drift area"; after, "at anchor" is small and the queue is mostly ships loitering outside the safety zone. The Dec 1 row (46 anchored, ~50 loitering) is not comparable to Oct's "79 queued".
- **Scope varies:** container-only, all cargo vessels, or all types (including tankers and bulkers). The `vessel_scope` column records it, and the `note` column often says more.
- **Averages differ in meaning:** POLA's monthly or 30-day figure, an advisory's range, and Seroka's "20 days" (which includes loiter time for a specific vessel group) are different quantities. Use 2021-09-10 as the cleanest check. Do not use the 20-day figure as a validation point.
- **Trap:** a "4.6 days in December, 7.3 in January" figure circulates, but it is December 2020 / January 2021. I left it out.
- **Dates:** the 2021-10-25 (84) and 2021-11-10 (92) rows are approximate, from relative phrasing in the articles. The 2019-01-01 baseline (17 at anchor) has a nominal date.
- The CSV `note` column ends with "fetched" or "search-snippet only" for each row.

## Sources
Each row's URL is in the CSV. Main pages: Maritime Executive (Aug 17 and Sep 10 2021), Western Overseas advisories (Sep 17 and Oct 22), Supply Chain Dive (Nov 12), Stars and Stripes/AP (Dec 3), Seatrade Maritime (Oct 21, Nov 9), FreightWaves (May 13), Seroka testimony (congress.gov, Jan 19 2022).
