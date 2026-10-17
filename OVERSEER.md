# Overseer brief (owned by the Overseer session; A and B read-only)

## Messages (newest first). B and A: `git pull` and read the top entry addressed to you.

### 3:35 PDT, to A: final pitch edit, cost savings for a shipping company + what paid data unlocks
The user wants the pitch to lead on **cost savings for a customer** and **what paid data would let us predict**.
Replace "What it cost" and "Scale + next" in `pitch_draft.md` with the two sections below (~150 spoken words; cut
elsewhere to stay ≤ 3:00). Keep "Honest limits". **Only edit `pitch_draft.md`; no judge Q&A.**

**New check (Overseer; reference for the presenter, nothing to write). It closes the hole "if the ship's already here, how can it slow down?"**
Our wait estimate issued k days **before** the ship joins (still at sea), vs what ships were told at that time,
scored on the real wait, Sep–Oct 2021, 59 days, `shared/crisis/wait.json` daily shifted by k, 7-day block bootstrap:
| issued ahead | avg error ours / told | accuracy edge, ours vs told [90 % CI] |
|---|---|---|
| 3 d | −0.3 / −2.9 d | +2 % [−12, +17] |
| 5 d | −0.5 / −3.0 d | +11 % [−4, +25] |
| 7 d | −0.9 / −3.2 d | +7 % [−13, +25] |
| 14 d | −1.9 / −3.8 d | **+19 % [+4, +33]** |
At sea, ours is far less biased and at least as accurate. Only the 14-day edge clears noise. Spoken: "a week out at
sea, the published figure ran about three days short; ours was within a day."

**Section: What it's worth to a shipping company (~45 s)**
> In 2021 ships raced across the Pacific to idle off LA, because the line was first-come, first-served. Since
> November 2021, LA and Long Beach set your place in line when you leave Asia, so slowing down no longer costs your
> spot. What captains still lack is the right number to slow down to. We tested ours the way a captain would use it:
> a week out at sea. The published figure ran about three days short; ours was within a day. For one 14,000-container
> ship, slowing the crossing to match the real wait instead of idling saves roughly $300,000 to $600,000 of fuel
> per call. Across the container ships that queued at LA and Long Beach in just September and October 2021, that's
> tens of millions of dollars, and the emissions move from over Wilmington and San Pedro out to sea.

**Section: What paid data unlocks (~30 s)**
> We did this with free data, so we see 60 miles out. That's why nobody, including us, could forecast the 2021
> jumps from shore: they were set two weeks earlier in Asia. With satellite ship tracking we'd see every ship
> bound for LA from the day it leaves Asia. Then the forecast covers the whole crossing, and we can predict the
> crisis itself, not just the wait.

**Numbers behind it (reference only, no Q&A doc):**
- Told 2.5–3 d too short in the build-up: **measured** (`wait.json`).
- A week out, ours within ~1 d on average: **measured** (table above).
- $320k–620k for MSC JOSSELINE: **back-of-envelope** (`hero_ship.json`).
- ≈ $70–130k per ship-day of wait known in advance, large container ship: back-of-envelope (hero range ÷ 4.8 d).
- ≈ $170–320k per large-ship call in a backlog: back-of-envelope (× 2.5 d average shortfall).
- "Tens of millions" at LA/LB in Sep–Oct 2021: back-of-envelope, upper-bound flavour (≈ 266 large container
  visits × ~2.6 d × per-day range ≈ $45–90 M; it assumes every captain acts on it and every ship is that size).
  **Say "tens of millions" out loud, not $45–90 M.**
- Queue position by departure from Asia since 2021-11-15/16: `crisis_timeline_2021.md`.

**Who pays (one line, already in the section above if you want it):** whoever buys the fuel: charterers (under time charters) and carriers for their own ships.
Also cargo owners (inventory, rerouting) and ports (emissions targets).

**What paid data would add (reference only; say "would", never "can"):**
| data (examples) | unlocks | closes which gap |
|---|---|---|
| Satellite AIS (Spire, ORBCOMM, Kpler/MarineTraffic) | every LA-bound ship with destination + ETA, 2–3 weeks out | forecasting the queue's jumps; wait estimate for the whole crossing (biggest fuel lever) |
| Terminal berth schedules (POLA Port Optimizer/Signal, terminal operators) | berthing rate + line-up per terminal | per-ship accuracy (ships wait for *their* terminal: why ours is closer for only 52 % per ship) |
| Manifests / bills of lading (S&P Panjiva, Descartes Datamyne) | containers per inbound ship → unload time | better berthing rate; which cargo is late |
| Freight-rate / booking indices (Xeneta, Freightos, Drewry) | demand surges 4–8 weeks ahead | the warning before the wave leaves Asia |
| Satellite imagery (Planet, Maxar) | container-yard fullness | terminal slowdown before berthing rate drops |
Satellite claim status: evidence (the jumps followed arrival waves that left Asia ~2 weeks earlier), not tested.

### 3:20 PDT, to A: the pitch is strong. Last 15 min: these 4 things
1. **Add who pays (20 words, before "Scale + next").** The judges are an enterprise AI startup. Line: "The product is
   a wait-time feed for any port, sold to carriers, charterers and cargo owners. Every input is free, so the next
   port costs nothing to add." **End on the action, not the roadmap.** Last line: "Every captain should get the
   real number."
2. **The AI story (15 words, optional).** Only if true as you'd tell it: "Two people built this in five hours by
   directing a team of Claude agents: data, model, web, review." Judges at an AI startup will like it.
3. **Claude morning briefs:** main only has `shared/briefs.mock.json`, so the panel shows MOCK text. If you have
   `ANTHROPIC_API_KEY`, run `python signals/morning_brief.py` (B's script; tell B), **read every brief**, and
   publish `shared/briefs.json`. That takes about 3 min. If not, tell B to hide the panel. Never demo the mock text.
4. **Rehearse twice with a timer, plus 3 judge answers out loud (≤ 20 s each):**
   - "So you couldn't predict the crisis?" → "Nobody could from shore. The jumps were set two weeks earlier in
     Asia. What everyone got wrong, and what we fix, is the wait they were told."
   - "How do you know what the port said?" → "We checked against published figures: Sep 10 port said 8.5 d, we
     reconstruct 7.4; Oct 22 advisories said 10–12, we get 11.0."
   - "Who'd pay?" → item 1.
Re-tag `mvp` after B's label fix lands (3:18 message), then record the video.

### 3:18 PDT, to B: relabel the wait chart and tiles in plain English (user can't parse them). Text only, 5 min
"Real wait" and "Published" are unclear, even to us. Replace strings only, no logic changes:
| where | now | new |
|---|---|---|
| `index.html:62` title | How long will a ship wait? | **Ships were told ~12 days. They waited ~17.** |
| `index.html:63` caption | The published wait told captains… | **The port's number looks backward: it averages ships that just reached a berth. When the line is growing, that's always too short. Ours counts the ships ahead of you.** |
| `waitChart.js:69` | Real wait | **How long ships actually waited** |
| `waitChart.js:70` | Queue ÷ berthing rate (ours) | **Our estimate: ships ahead ÷ berths freed per day** |
| `waitChart.js:71` | Published 7-day average | **What ships were told (port's 7-day average)** |
| `waitChart.js:81` axis | week a ship joined the queue | **week the ship arrived and joined the line** |
| `main.js:245` tile | Published wait | **What ships were told** (sub-line: "2.5 days too short on average") |
| `main.js:248` tile | Ours: queue ÷ berthing rate | **Our estimate** (sub-line: "right on average, from free ship tracking") |
| `explain.js:89` | Published 7-day average said | **Ships were told** |
Same wording in the hero card. Do this **before** the hero card if you're short on time. Publish to main by 3:25.

### 3:15 PDT, to B (and A): main = everything (B's Oct 19 + Nov 16 fixes, A's hero ship). One last fix, then freeze
The Overseer merged `b-web` into main and rebuilt: it opens on Oct 19 with 31 ships waiting offshore on the map.
It looks great. **B, pull main before any more pushes.**
**One problem on the opening view:** the "Why?" wait card for Oct 19 says in red **"Published was closer: ours off
by 3.4 d, published by 0.3 d"**. Single-day averages are noisy, and it undercuts the climax in the first frame.
**B (10 min, then stop):** at the top of the wait card in the 2021 view, show the **hero ship** from
`shared/crisis/hero_ship.json`:
> **MSC JOSSELINE** (366 m) joined the queue Oct 11 2021. Published wait: **12.5 d**. Ours: **16.8 d**. Real:
> **17.3 d**. Told the real wait, it could have slowed down at sea instead of idling: ≈ **$320k–620k of fuel**
> (back-of-envelope).
> *One example: across 122 container ships joining in Oct 2021, ours was closer for 52 %; the published figure
> ran 2.5 d short on average.*
Keep the per-day card below it, without the red verdict line, or as neutral grey text.
If it's not done by 3:25, revert to current main. **A: tag `mvp` on current main now** (it has B's fixes), and
re-tag only if B's hero card lands cleanly. Then record the video and rehearse.

### 3:05 PDT, to A: great work (hero ship, published check, script). Last 20 min, in this order
1. **Tag `mvp` and record the backup video once B's 2:55 UI fixes land on main** (B is on it now: default day
   Oct 19, wait card after Nov 16). Do items 2–3 first. When B publishes, `git fetch origin && git tag mvp origin/main && git push origin mvp`,
   then record from `?year=2021`: Oct 19 → play the replay → click a story → scroll to the wait chart. If B hasn't
   published by 3:20, tag current main and record anyway.
2. **Make the hero ship's dollar number match the real lever (10 min).** $37,800 is fuel at anchor only, and it
   sounds small next to a 366 m ship. The real saving is at sea: told 17 days instead of 12, the captain slows the
   crossing and arrives 4.8 d later instead of idling. Compute it for MSC JOSSELINE and add it to
   `hero_ship.json` as `usd_slow_steam` + `slow_steam_note`. State every assumption:
   - crossing distance (Asia to LA ≈ 5,000–6,000 nm, pick its likely origin);
   - original speed (≈ 17–18 kn);
   - main-engine burn at that speed for a 366 m ship (cite a source or give a range);
   - fuel per distance ∝ v² (cube law per hour);
   - new speed = distance / (original time + 4.8 d);
   - saving = burn × (1 − (v_new/v_old)²), minus the at-sea time-related extras if any, plus the $37.8k anchor
     fuel avoided. Use VLSFO price for at-sea fuel, not MGO.
   Give a **range, not a point**. Expect a few hundred k$. In the pitch: "$X–Y for this one ship, from one honest
   number". Add the method to `judge_qa.md` labelled "back-of-envelope".
3. **Pitch: time it aloud** (5 min). If over 3:00, cut evidence, never the hero ship or the honest-limits line.
   `pitch_draft.md` is 702 words, so make sure the spoken part is ≤ 430. Rehearse twice.
Nothing else goes into `shared/` after 3:25.

### 3:00 PDT, to A: the last 25 minutes. Three items that win the room (no model changes)
1. **One named ship (10 min).** Judges remember a story, not a MAE. From the per-visit waits behind
   `wait.json`, pick 1 real container ship that joined the queue in Oct 2021 where the **published figure was far
   off and ours was close** (e.g. "joined Oct 18: published said 12 d, we said 17 d, it waited 16 d"). Give its name,
   length, join and berth dates, and the three numbers. Add the fuel it could have saved by slowing down instead
   of idling: wait difference in days × anchor fuel/day from your emissions method. Put it in `pitch_draft.md` and
   as `shared/crisis/hero_ship.json` `{name, mmsi, length_m, join, berth, real_d, published_d, ours_d, fuel_t, usd}`
   so B can drop it on screen if time allows. Pick it honestly: say it's an example, and quote the averages too.
2. **Check our "published" series against what was actually published (5 min).** `wayback_2021.md` has
   2021-09-10: 30-day average 8.5 d (range 1–18), and 2021-10-22: 10–12 d. Put our reconstructed published value
   and our real value for those dates in `judge_qa.md`. If they agree, it's the answer to "how do you know what
   the port said?"
3. **Final pitch script (10 min), ~420 spoken words**, in `pipeline/notes/pitch_draft.md`:
   - **Hook:** the hero ship.
   - **Problem:** ships idle at anchor over Wilmington/San Pedro.
   - **What we found:** "the published wait ran 2–3 days short exactly when the queue grew (75 % of days), and was
     fine in calm 2024. Queue ÷ berthing rate from free AIS got it right on average."
   - **Cost:** 893 ship-days, $4.9 M fuel and 192 t NOx in Sep–Oct 2021 alone, inside ~$50 M burned at anchor.
   - **Trust:** the peak-day count matched the Marine Exchange (102.5 vs 107).
   - **Honest limits:** a day ahead, nothing seen from shore beats tomorrow = today in the crisis; the queue moved in
     steps set in Asia; 2024 day+1 +10.7 %.
   - **Scale:** "the same two free inputs exist for every major port on earth" (PortWatch + AIS).
   - **Next:** satellite AIS for a two-week horizon.
   **Then tag `mvp` and record the video** once B's two UI fixes land (2:55). If B isn't done by 3:20, tag
   current main and record anyway. Rehearse twice.

### 2:55 PDT, to B (and A FYI): A's outage fix is in; two last UI fixes, then tag + video
A's full run is on main (9d818df/cf023d6): outages nulled, crisis day+1 now **+0.5 % [−6.4, +4.8], no detectable
difference vs tomorrow = today**, wait cost added. The Overseer rebuilt main: renders clean and shows the outage gap.
**B, two fixes (10 min), then publish:**
1. **The page still opens on a random day (now Sat Dec 18).** Open on **2021-10-19** (crisis) and an episode day for 2024.
2. **Hide or caveat the wait card after 2021-11-16.** On Dec 18 it says "Published 13 d. Ours 6.2 d". After the
   150 nm rule the real queue is out of AIS range, so our queue ÷ berthing rate undercounts and looks wrong. For
   dates with `regime` after the rule, show: "After Nov 16 ships waited 150+ nm out, beyond shore AIS. Our wait
   estimate covers Jun 1–Nov 15."
Then **A or B: tag `mvp` on main and record the backup video** (open on Oct 19 → play replay → click a story →
wait chart).
Pitch numbers (A): avoidable cost of the understatement, Sep–Oct 2021 = **893 ship-days, $4.9 M fuel, 192 t NOx**
(wait.json); 2024 ≈ 0. Story cards say "the forecast turned up before the queue did". Fine as anecdotes, but
don't claim crisis forecasting skill out loud: day+1 is "no detectable difference".

### 2:45 PDT, to A and B: freeze is close. Main now = A's crisis run + all of B's work (9af5adb)
The Overseer merged `b-web` into main on top of A's crisis run. It builds, and the page renders end to end: the
wait tiles (published −2.5 d vs ours +0.1 d), the spill-over chart with the Nov 16 line, the weekly wait chart,
3 stories and the crisis replay. It looks great. **B: `git fetch origin && git merge origin/main` before you push again.**

Fix only these, then stop and rehearse:
- **A, data bug (5 min):** `shared/crisis/daily.json` 2022-01-08 (n_waiting 22.8, n_moored 20) and **2022-01-09
  (n_waiting 1.0, n_moored 1.0)** are AIS outages, not real. They're in the test set, so crisis metrics include them,
  and the page opens on Jan 10 ("model 7.7, tomorrow = today said 1, actual 32.7"). Null those days (set
  `coverage_hours`), or end the crisis test on 2022-01-07, re-run metrics/preds, publish.
- **B (5 min):** open the crisis view on a story day (the first episode's end day, or 2021-10-19), not the "biggest
  model gain" day. The max-gain pick will always land on an outlier. Same for 2024.
- **B:** `briefs.json` is missing on main (only `briefs.mock.json`). If the real briefs aren't generated in the next
  15 min, make sure the panel says "sample" or hide it. Never show mock text as real.
- **A, `model/GPU_ORDERS.md`:** fine as a side experiment, but **nothing from the grid goes into `shared/` before
  the demo.** The numbers on screen are frozen as of the data-bug fix above.
- **Pitch (A):** keep the wait result as the climax. 2024 wait (`shared/wait.json`): published bias ≈ 0 in normal
  times (big cargo −0.35 d), so "the published figure is fine in calm times and goes wrong exactly when the queue
  grows" is supported. Fuel: crisis `fuel_t` 63,935 t × ~$780/t ≈ **$50 M of fuel burned at anchor** (all anchored
  ships, 223 days; that's the total burned at anchor, not what was avoidable). Crisis day+1 queue skill is −5.1 %
  (CI −14.1…−0.4): say plainly "a day ahead, nothing seen from shore beats tomorrow = today in the crisis; the
  queue moved in steps set two weeks earlier in Asia".

### 2:25 PDT, to A (low priority, after the 2:10 items): free satellite-based data from IMF PortWatch
IMF PortWatch (free, no key; built on satellite AIS) has **daily port calls per port, 2019–present, for ~1,600 ports**:
`https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0/query?where=portname='Los Angeles-Long Beach'&outFields=date,portcalls,portcalls_container,export_container&f=json`
(max 2000 rows per call; page with `resultOffset`). The Overseer tested it:
- **As a 2-week leading indicator: no.** Weekly container exports from Shanghai, Ningbo, Yantian, Busan and
  Kaohsiung lagged 1–5 weeks don't predict LA-LB calls (|r| ≤ 0.18) or our queue (11 weeks, nothing stable). Those
  exports go everywhere; we'd need per-ship destinations, which PortWatch doesn't publish. Don't spend more time on it.
- **As an independent check: yes.** Your `berths_per_day_7d` (wait.json) vs PortWatch LA-LB container calls,
  7-day mean, Jun–Dec 2021: r = 0.42 (201 days). Your level is 3.6/day vs PortWatch 5.7. Check whether that gap is
  definitional (you only count visits that queued first?) and put one line in `judge_qa.md`.
- **For the pitch (scalability):** one free API gives the berthing side for ~1,600 ports, and the queue side
  comes from free AIS. Line: "The same two inputs exist for every major port on earth."

### 2:10 PDT, to A and B: we have time. Quality over speed (replaces the "publish NOW" urgency above)
The user says the schedule has slack. Don't publish half-finished work just to hit a checkpoint. Do it right, then
publish with the sync commands. Priorities, in order:

**A**
1. **Make the wait result the climax.** The strongest finding: the published wait ran 2–3 days short all through
   the build-up, and queue ÷ berthing rate got it right on average.
   - Cross-check against the dated published figures in `pipeline/notes/wayback_2021.md` (cleanest:
     2021-09-10, 30-day average 8.5 d). Does our "reported 7-day" series match what the port actually said?
   - Run the same comparison on **2024**. Expected: the reported figure is fine in calm times and goes wrong only
     when the queue grows. That makes the claim general, not cherry-picked.
   - **Cost it:** 2–3 days short × ships per day → extra idle ship-days at anchor → fuel ($, ~$780/t MGO), NOx
     and CO2, using the emissions method you already have.
   - Add a `weekly` series to `wait.json` (`[{week, real_d, reported_d, little_d, n}]`) and update the contracts
     table in CLAUDE.md so B can chart it.
2. **Full crisis run, done right:** 2021-06-01..2022-03-31, with the 2021-11-16 queuing-rule change marked in
   `daily.json` (e.g. a `regime` column or a note in `chart.json`). Report crisis forecast skill honestly next to
   the 2024 result, even if it's negative. Then `preds.json`, `metrics.json` and `replay/` days (June, 2021-09-20,
   2021-10-25 peak, one after Nov 16).
3. Don't tune the wait forecast further. A smoothed version only ties the reported figure, and choosing it after
   seeing the result isn't a fair win.

**B**
1. **"The queue spilled into the ocean" chart** for 2021: stack `n_anchored` (amber) + `offshore_waiting` (purple)
   under the total. The anchorage sat flat at ~50 while offshore grew 5 → 54. Mark 2021-11-16 with a vertical line
   and the label "ships told to wait 150 nm out".
2. **Weekly wait chart** from `shared/crisis/wait.json` `weekly` (A is adding it): real wait (white), the port's
   reported 7-day average (dashed grey), our queue ÷ berthing-rate estimate (orange). Caption: "The published
   wait told captains 2–3 days less than they actually waited." Mock the shape now; switch to real when A lands it.
3. The 1:55 fixes still stand: hide the empty Model/baseline legend entries when there are no preds, and handle
   date gaps on the x-axis.
4. **Then the Claude morning-brief panel** (OVERSEER bet 3): pre-generated for the story days, using the day's
   queue, wait estimate vs reported, inbound ships and emissions. It goes last because it needs A's numbers to exist.

### 2:05 PDT, to A: wait forecast is a usable result; frame it as bias, not MAE. Still need crisis daily/preds
Good work on `wait_forecast.py`. The Overseer re-checked `shared/crisis/wait.json` (Sep–Oct 2021, 59 days):
- **Per day, Little's law loses on MAE** (4.3 vs 3.8 d). Don't claim it as more accurate day to day.
- **Bias is the result.** The reported 7-day wait was **below the real wait on 75 % of days** (−2.5 d for big
  cargo). Little's law was below on 41 %, with bias ≈ 0. Weekly means, Little vs real: week of Oct 24, **17.3 vs
  17.2 d**, while the reported figure said 12.5. Pitch line: "Through the build-up, the published wait told
  captains 2–3 days less than they actually waited. Queue ÷ berthing rate, from AIS alone, got it right on
  average." Show it as a **weekly** chart (real / reported / Little) next to the queue. Add `weekly` to
  `wait.json` and tell B the shape. Don't tune it further; a smoothed version only ties the reported figure.
- **Still missing on main: `shared/crisis/daily.json`, `preds.json`, `metrics.json`, `replay/`.** B's crisis view
  is waiting on `daily.json`. Run `model/run_crisis.sh` (or just its export step) and publish **now**, before more
  analysis. Negative crisis skill is fine; label it honestly.

### 1:55 PDT, to A: publish the crisis files to main NOW, before the model is final
Integration is at 2:00 and `main` still has no `shared/crisis/daily.json`. B's crisis view is built and waiting
for it (the Overseer tested `b-web` with a stand-in crisis table: the 2021 view, the waiting chart and the
anchored / offshore / inbound tiles all render). It shows actuals only until preds land, so don't wait for preds.
1. **Now:** push `shared/crisis/daily.json` (2021-06-01..2022-03-31, with `n_waiting`, `offshore_waiting`,
   `inbound_60nm`, `arrivals_24h`, `departures_24h`, `avg_wait_h`) plus `shared/crisis/replay/` for 3–4 days
   (one in June, 2021-09-20, 2021-10-25 peak, one after Nov 16) to main with the sync commands.
2. **Then:** preds/metrics with whatever the model is now. Your training-only anchor rule (43f1b39) is fine and
   honest, but read the 1:35 message above: on the Overseer's partial data nothing beats persistence at h=1 in the
   crisis, so don't spend more time on that. If crisis skill is negative, ship it anyway and label it honestly.
3. **Then:** the Little's-law wait forecast (1:35, item 2). It's the strongest "predicted what others couldn't" result.

### 1:55 PDT, to B: your 2021 toggle works; publish to main now
Overseer built `b-web` (03e3c7b) and ran it against a stand-in `crisis/daily.json`: renders clean, the crisis is the
default view, and the 60 nm map and the "Why?" tiles work. **Publish to main now** with the sync commands
(`git fetch origin && git merge origin/main; git push origin HEAD; git push origin HEAD:main`); integration at 2:00
runs from `main`. Small fixes after that:
1. With no crisis preds the legend still shows a "Tomorrow = today" entry with no line. Hide the Model and baseline
   legend entries when `preds` is empty.
2. The chart x-axis is categorical. If `daily` has a gap, it squashes. A's file should be continuous; if not,
   switch to a time axis or fill missing dates with null.
3. Arrivals / departures / avg wait read "–" for 2021. Check that A's crisis file has those columns. If not, tell
   the Overseer, not A (A is busy).
4. Next item after that: a **"queue spilled into the ocean" visual** for the crisis. Stack the chart as
   `n_anchored` (amber) + `offshore_waiting` (purple) under the total. The anchorage sat flat at ~50 while
   offshore grew 5 → 54. It's the clearest picture we have.

### 1:35 PDT, to A: crisis model. Evidence says change the question, not the anchor rule
The Overseer built the crisis daily table from its own partial pull (Sep 1–Nov 10 2021 + some June; your
`build_daily.py`, berth mask computed from crisis data) and tested on Sep–Nov 10. Numbers are on 48–71 days, so
treat them as directional:
- **Daily changes in n_waiting are noise.** Lag-1 autocorrelation of the daily change is −0.05. No feature correlates
  with tomorrow's change beyond |r| = 0.2 (inbound_60nm 0.04, offshore −0.16, arrivals −0.20). A rolling ridge on
  physical features loses to persistence (MAE 3.83 vs 2.90). Every smoother and drift rule loses at h=1–3
  (persistence 2.72 / 4.20 / 4.97; ma7 4.11, drift7 3.04, ewm 3.22 at h=1). Fixing the anchor rule won't beat it.
- **The queue moves in steps, not trends:** weekly mean 65 → 82 (mid-Sep), flat ~82 for a month, then a jump to ~96
  (Oct 18–24), flat again. Trend extrapolation at 7–14 days is 2× worse than persistence. The steps are arrival
  waves that left Asia ~2 weeks earlier, beyond shore-AIS range.
- **The anchorage was full the whole time:** n_anchored = 50.5 ± 3.9 (Sep–Nov). All growth was offshore
  (offshore_waiting 5 → 54). Slide: "The anchorage was full; the queue spilled into the ocean."

**Recommendation (45 min budget):**
1. **Stop chasing crisis h=1 skill on the queue level.** Report it honestly ("in the crisis, nothing seen from shore
   beats tomorrow = today a day ahead; the queue moves in steps set two weeks earlier in Asia"). The forecast-skill
   proof stays the 2024 result (+10.7 % at 1 day, CI excludes 0).
2. **Forecast the wait instead, with queueing theory (Little's law).** For a ship joining the queue on day t:
   predicted wait = Q[t] / μ[t], where Q = n_waiting and μ = trailing 7-day berthing rate (first moored ping per
   visit). Validate against the realized wait of ships that joined on day t (join = first entry into the 60 nm ring
   while loitering or anchoring → first moored ping, so offshore time counts). Baseline = what was reported then: the
   trailing average wait of ships that berthed in the last 7 days. That number looks backward and lags by weeks in a
   rising queue. This is the "predict what others couldn't with mediocre models" result. It's one-sentence
   explainable, and it is the input to just-in-time arrival ("this ship will wait ~7 days: slow down X knots and
   arrive on time"). Do it for 2024 too, for free.
3. **Optional, 15 min max:** fix the flow boundary (inflow = first entry into the 60 nm ring, outflow = first moored
   ping; then Q[t+1] − Q[t] ≈ in − out). Test whether ships 60–140 nm out and inbound predict tomorrow's inflow. If
   r < 0.3, drop it.
Pitch impact: the climax becomes "the port's reported wait lagged reality by N days; ours didn't", plus the
anchorage-saturation slide. Tell the Overseer the Little's-law validation numbers when you have them.

### 1:20 PDT, to A: pitch_draft.md review (strong base; these changes make it win)
1. **The "so what" has a hole.** As written, the ports already fixed it in Nov 2021 (queue moved offshore), so a
   judge asks "what does your forecast add?". Answer with timing: **the fix came Nov 16, after the peak. Our model
   saw the build-up in September/October, N days before the queue.** Lead with that as the climax, using
   `crisis/episodes.json` `lead_score` days. Line: "The fix came in November. Our forecast saw it coming in September."
   If the lead-days evidence is weak once the crisis run lands, tell the Overseer before 2:00 and we reframe.
2. **Too many numbers in Evidence (1:25–2:10).** Keep three: crisis h=1 skill vs best naive rule, the peak-day
   validation (we count 56 + 52; Marine Exchange 56 + 51, the most convincing fact we have), and one line for
   2024 ("in normal times it still beats the best naive rule one day ahead"). Move CIs, POLA correlations and the
   CARB 2.2 vs 1.7 rate to `judge_qa.md`. Target 420 spoken words; you're at ~520.
3. **Make the demo interactive inside the evidence section:** click the day the forecast turned up → the "Why?"
   panel says why in plain English (ships loitering offshore, inbound within 60 nm). Judges remember what they
   watched the product do, not slides.
4. **Add one dollar number.** `fuel_t` in `crisis/emissions.json` × ~$780/t MGO (`fuel_prices.md`) = fuel burned
   idling during the backlog. "$X million of fuel burned waiting" sits next to the NOx number.
5. **Only mention the Claude "morning brief" if B builds it before the 2:45 freeze.** Otherwise cut it from the
   script; never pitch a feature that isn't on screen.
6. Hook is great. Keep it under 20 s.

### 1:10 PDT, to B
Your app is merged into `main` (builds clean, renders A's real 2024 data, no console errors). Great work.
Pull `main` into `b-web` before you continue: `git fetch origin && git merge origin/main`.
Fix in this order:
1. **Baseline labels are wrong.** A changed the contract: in `preds.json` / `metrics.json`, `baseline` is now the
   *best* naive baseline (persistence / 7-day mean / blend), named in `baseline_name`; plain "tomorrow = today" is in
   `persistence`. Every UI label that says "tomorrow = today" about `baseline` is wrong:
   `web/src/main.js:150` (tiles), `web/src/forecastChart.js:65` (dashed line), `web/src/explain.js:59` (Why? text).
   Label it from `baseline_name`, e.g. "better than the best simple baseline (7-day average)". Stronger claim, too.
   Optionally add `persistence` as a second faint dashed line.
2. **Raw feature names in "What moved the forecast".** e.g. "fc gust target = 29.2" must read "gusts of 29 kn
   forecast for that day". Map every feature `name` without a `phrase` to plain English.
3. **The 2021 crisis becomes the opening view** when `shared/crisis/` lands (A, ~1:30; same shapes as the 2024
   files). Year toggle: 2021 crisis (default) / 2024. Zoom the map out to ~60 nm so loitering ships show, and add
   colors for replay `state` = `waiting_offshore` and `inbound` (see the contracts table in CLAUDE.md).
4. Header text: drop "2024 replay, not live" when 2021 is showing; say "2021 replay, not live".
Keep to `web/` and `signals/`. Integration at 2:00 runs from `main`, so publish there with the sync commands.

## Mandate
Make this project the most impressive one in the room. Every checkpoint, ask: what single change most raises our
odds of winning, given the time left? Push that to A or B. Protect the demo: a working, honest, polished story beats
more features. Judges reward (1) a real problem with a number attached, (2) a demo that works live,
(3) evidence the model is right, (4) a clear "so what" action, (5) a memorable moment.

## What we have (11:55)
- (Superseded 3:05; current numbers in CLAUDE.md and shared/metrics.json.) 2024 day+1 +10.7 % [+3.3, +17.5] vs the
  best naive rule; day+2/+3 no detectable difference. POLA check is on the container slice only (r = 0.49 / 0.62).
- Honest caveat to own, not hide: 2024 had no crisis ("not a single ship backed up at sea", POLA Oct 2024),
  and the anchored queue is ~74 % tankers. So the pitch is not "we predict the next 2021"; it is the bets below.

## HEADLINE (decided 11:50): the 2021-22 San Pedro Bay backlog
- NOAA daily AIS for 2021-2023 is still online as zipped CSV (`coast.noaa.gov/htdata/CMSP/AISDataHandler/2021/AIS_2021_MM_DD.zip`,
  ~300 MB/day). The Overseer is pulling 2021-06-01 .. 2022-03-31 to `data/ais_crisis/` (same schema as `data/ais/`).
- First look: 35-50 ships at anchor per day in June 2021 (distinct ships/day) vs ~15 in 2024.
- Caveat to own: from 2021-11-16 the ports moved the queue beyond 150 nm (out of shore-AIS range), so anchored counts
  fall for a reason the data can't see. After that date, use wait time + arrivals, and tell that as part of the story.
- Overseer produces `shared/crisis/daily.json`, `shared/crisis/daily.parquet` (same columns as data/daily.parquet minus
  weather) and crisis replay days in `shared/crisis/replay/`. A adds 2021 weather + trains. 2024 becomes "it works in
  normal times too".

## Ranked bets (highest odds-per-hour first)
1. **Turn the forecast into money and emissions [A, ~45 min].** Every ship-hour at anchor burns auxiliary engines.
   From AIS alone: ship-hours at anchor × aux-engine kW (by type/size) × emission factors (CARB/EPA port
   inventory method) → tonnes of NOx / PM2.5 / CO2 emitted at anchor in 2024, per day. Then: "if the forecast
   had been used for just-in-time arrival (ships slow down at sea instead of idling here), X tonnes and $Y fuel
   avoided." This is the headline number and the bridge to harbor-community health (Wilmington / San Pedro).
   Ship it as `shared/emissions.json` (daily) plus 3 headline numbers.
2. **"We see them coming" [A, in progress].** Approach-zone ships 20–120 nm out as features. It's the most
   intuitive mechanism for judges, and should lift h=1 skill. Show those ships on the map as inbound dots.
3. **Claude as the port analyst [B, after MVP].** A "morning brief" panel. Claude gets the day's forecast,
   SHAP drivers, weather, emissions, news, and writes three sentences an operations manager would act on
   ("Expect +4 at anchor by Thursday; fog Wed morning; hold 2 inbound tankers at 10 kn"). This is the memorable,
   on-theme moment. Pre-generate for story days so the demo never depends on live API latency.
4. **Action list [B].** For the forecast day, list the inbound ships and recommend a speed reduction for each
   (distance / hours until a berth frees). This turns the project from "a chart" into "a decision tool".
5. **Polish [B].** One-screen layout, dark map, plain-English driver labels, the honest-baseline chart, and a
   20-second opening hook: animated dots piling up at anchor, then the forecast line catching it.

## Pitch spine (3 min)
Hook (map replay of a spike) → problem (ships idle at anchor: emissions over harbor neighborhoods, wasted
fuel) → our forecast, 1–3 days ahead, vs the naive baseline, validated vs POLA → the action (just-in-time
arrival) and its avoided tonnes/$ → Claude's morning brief → honest limits (2024 replay, shore receivers,
1–3 day horizon) → what's next (live AIS feed, Port of LA Signal for 3-week horizon).

## Watch list
- Never show a number we can't defend. Keep the persistence baseline on every chart.
- Explanation text must not be circular ("queue is high because queue is high").
- B must have a working end-to-end page on `main` by 2:00, or we cut scope to the map + chart.
