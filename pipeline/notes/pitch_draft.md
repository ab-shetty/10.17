# Pitch script (read aloud, about 3 minutes)

*(Screen: 2021 map replay, Oct 19, ships piling up offshore)*

On October 11th, 2021, the MSC Josseline, a 366-metre container ship, joined the queue off Los Angeles.
The port's published wait that day was twelve and a half days. She waited seventeen. Told the real number,
her captain could have crossed the Pacific five days slower instead of idling: roughly $300,000 to $600,000
of fuel, for one ship.

*(Screen: "queue spilled into the ocean" chart)*

In the 2021 backlog over a hundred ships idled off San Pedro Bay, putting soot over the harbor neighborhoods.
From free ship-tracking data we rebuilt that queue: on the peak day we count 102, the Marine Exchange 107.
This is a replay, not live.

*(Screen: weekly wait chart)*

The published wait averages ships that already berthed, so it looks backwards. Through the build-up it told
captains two to three days less than they waited, every week of September and October. Ships ahead divided by
berths freed per day, from ship tracking alone, got it right on average. And in calm 2024 the published figure
is spot on: it goes wrong exactly when the queue grows.

Since November 2021 your place in line is set when you leave your last port, so slowing down no longer costs
your spot. What captains lack is the right number to slow down to. We tested ours a week out at sea: the
published figure ran three days short; ours was within a day. That's up to $300,000 of fuel per large ship, and
tens of millions across September and October 2021 alone, with the emissions moved out to sea.

With free data we see 60 miles out, so nobody, including us, could forecast the 2021 jumps from shore: a day
ahead, nothing beats "tomorrow equals today". In normal 2024 our model beats the best simple rule by 11 percent,
mostly in storms. Under the hood it's an ensemble of LightGBM, CatBoost and ridge regression that learns only the
correction to the best simple rule, reads tomorrow's weather forecast, and is refit every month on past data only.
We tested 677 variants; none beat it. With satellite tracking we'd see every LA-bound ship from the day it leaves Asia, and could
forecast the crisis itself. That would be worth up to $650,000 per ship, and on the order of $100 million in
two months, at one port.

Whoever buys the fuel pays for this: charterers and carriers. The next port costs nothing to add. Two of us
built this in five hours, directing a team of Claude agents. Every captain should get the real number.

---

## Don't say
- "We can predict the crisis with satellite data" (say "would": not tested).
- "$45–90 million" or "$70–170 million" out loud (say "tens of millions" / "on the order of $100 million").
- "We predicted the crisis" / "saw it coming in September" (a day ahead in the crisis: no detectable difference).
- "Our wait estimate is more accurate" (per day it isn't; per ship it beats the published figure for 52 %). Say "right on average".
- "Avoidable $55 million" ($55 M is everything burned at anchor).
- "Container queue" for 2024 (74 % tankers).

## 30-second version
Off Los Angeles in 2021 the published wait for a berth told captains two to three days less than they really
waited, every week of the build-up, because it averages ships that already berthed. From free ship-tracking data
we rebuilt the queue, matching the Marine Exchange count, and estimated the wait as ships ahead divided by berths
freed per day: right on average, and the published figure is fine in calm 2024. Told the real number a week out,
a large ship saves up to $300,000 of fuel. The same free inputs exist for every major port.

---

## Sources (for us, not for reading aloud)
- Hook: `shared/crisis/hero_ship.json` (`usd_slow_steam`, `slow_steam_note`). Back-of-envelope: 5,200–6,300 nm,
  16–18 kn, 90–150 t/day, fuel per mile ∝ v², VLSFO $580–650/t → $320k–620k.
- Peak day: 48 anchored + 54 loitering = 102.5 vs Marine Exchange 56 + 51 = 107 (CLAUDE.md).
- Wait: `shared/crisis/wait.json` (published bias −2.5 d, ours +0.1 d, short in all 9 weeks); 2024 control
  `shared/wait.json` (steady weeks 0.0 d).
- A week out at sea: estimate issued 7 d before joining, bias ours −0.8 d vs published −3.1 d (measured, Sep–Oct 2021).
  $: slow the last 7 days 17 → ~12.5 kn to absorb ~2.5 d, 60–150 t/day, $615/t ≈ $120–300k per large ship;
  fleet = ~266 large container visits × that (upper bound: every captain acts).
- Queue rule (Nov 15/16 2021, position by departure from last port): `pipeline/notes/crisis_timeline_2021.md`.
- Forecast skill: crisis day+1 +0.5 % [−6.4, +4.8] (`shared/crisis/metrics.json`); 2024 day+1 +10.7 % [+3.3, +17.5]
  (`shared/metrics.json`).
- Satellite $: cross 5,700 nm at 12 kn instead of 17 (~14 → ~20 d), ~50 % less crossing fuel, 60–150 t/day,
  $615/t ≈ $260–650k per large ship × ~266 visits ≈ $70–170 M. Back-of-envelope, untested ("would").
- Model: `model/train.py` (mean of LightGBM + CatBoost + ridge on y[t+h] − best naive anchor; day-ahead HRRR gust
  forecast; rolling-origin monthly refit; 7-day block-bootstrap CI). 677 variants: `pipeline/notes/grid_results.md`
  (nothing beats the default). The wait estimate itself is queueing theory (Little's law), not ML: don't call it a model.
