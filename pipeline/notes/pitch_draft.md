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

## 30-second version
Off Los Angeles in 2021 the published wait for a berth told captains two to three days less than they really
waited, every week of the build-up, because it averages ships that already berthed. From free ship-tracking data
we rebuilt the queue, matching the Marine Exchange count, and estimated the wait as ships ahead divided by berths
freed per day: right on average, and the published figure is fine in calm 2024. Told the real number a week out,
a large ship saves up to $300,000 of fuel. The same free inputs exist for every major port.

---

## Sources and assumptions
- Hero ship: `shared/crisis/hero_ship.json`. Back-of-envelope: 5,200–6,300 nm crossing, 16–18 kn, 90–150 t/day
  main-engine burn, fuel per mile ∝ v², VLSFO $580–650/t → $320k–620k. Across all 122 container-size ships that joined
  in Oct 2021, our estimate was closer than the published figure for 52 %; the published figure was short for 60 %.
- Peak day 2021-10-25: 48 anchored + 54 loitering within 60 nm = 102.5 (hourly mean) vs Marine Exchange 56 + 51 = 107.
- Wait: `shared/crisis/wait.json`, container-size ships joining Sep–Oct 2021. Published-style 7-day average: bias
  −2.5 d, below the real wait in all 9 weeks. Ships ahead ÷ berths per day: bias +0.1 d, day-to-day error slightly
  higher (4.3 vs 3.8 d). 2024 control `shared/wait.json`: bias 0.0 d in steady weeks.
- A week out at sea: estimate issued 7 days before the ship joins, bias −0.8 d (ours) vs −3.1 d (published), Sep–Oct 2021.
  Per ship: slow the last 7 days from 17 to ~12.5 kn to absorb ~2.5 d, 60–150 t/day, $615/t ≈ $120–300k.
  Fleet: ~266 large container visits × that range; assumes every ship acts on it.
- Queue rule from 2021-11-15/16 (position set by departure from last port): `pipeline/notes/crisis_timeline_2021.md`.
- Forecast skill vs the best simple rule, rolling-origin, 90 % block-bootstrap CI: 2021–22 crisis, day+1 +0.5 %
  [−6.4, +4.8] (`shared/crisis/metrics.json`); 2024 Oct–Dec, day+1 +10.7 % [+3.3, +17.5] (`shared/metrics.json`).
- Satellite: wait known on leaving Asia → cross 5,700 nm at 12 kn instead of 17 (~14 → ~20 d), ~50 % less crossing
  fuel, 60–150 t/day, $615/t ≈ $260–650k per large ship × ~266 visits ≈ $70–170 M. Back-of-envelope, not tested.
- Model: `model/train.py`, mean of LightGBM + CatBoost + ridge predicting the change from the best simple rule; day-ahead
  HRRR gust forecast; monthly rolling-origin refit. 677 variants: `pipeline/notes/grid_results.md`. The wait estimate is
  queueing theory (Little's law: ships ahead ÷ berths freed per day).
- Fuel burned at anchor over the whole 2021–22 crisis (304 days): 71,216 t ≈ $55 M, 2,162 t NOx (`shared/crisis/emissions.json`).
