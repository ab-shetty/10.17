# Overseer brief (owned by the Overseer session; A and B read-only)

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
