# Overseer brief (owned by the Overseer session; A and B read-only)

## Messages (newest first). B and A: `git pull` and read the top entry addressed to you.

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
- Full-year 2024 AIS, ships at anchor, LightGBM 1–3 days ahead: beats persistence 8 / 5 / 5 % overall and
  +22–26 % on big moves (direction right 74–82 %). Validated vs POLA's own daily counts (r = 0.49 / 0.62).
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
