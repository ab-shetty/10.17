# Pitch script (3 min, ~400 spoken words). Final numbers, 3:40 PDT

Every number has its source in [brackets]. Spoken text is in plain paragraphs; stage directions are in *italics*.
Demo = a **replay** of 2021 and 2024 AIS, not live. Say so.

---

*[Screen: crisis map replay, Oct 19 2021, dots piling up offshore]*

**Hook (≈ 50 words).**
On October 11th, 2021, the MSC Josseline, a 366-metre container ship, joined the queue off Los Angeles.
The port's published wait that day was twelve and a half days. She waited seventeen. Told the real number,
her captain could have crossed the Pacific five days slower instead of idling: roughly $300,000 to $600,000
of fuel, for one ship.
[`shared/crisis/hero_ship.json` usd_slow_steam + slow_steam_note, back-of-envelope]

*[Screen: the "queue spilled into the ocean" chart]*

**Problem + what we built (≈ 50 words).**
In the 2021 backlog over a hundred ships idled off San Pedro Bay, putting soot over the harbor neighborhoods.
From free ship-tracking data we rebuilt that queue: on the peak day we count 102, the Marine Exchange 107.
This is a replay, not live.
[CLAUDE.md, 48 + 54 = 102.5 vs MX 56 + 51]

*[Screen: weekly wait chart: real (white), published (grey dashed), ours (orange)]*

**What we found (≈ 80 words).**
The published wait averages ships that already berthed, so it looks backwards. Through the build-up it told
captains two to three days less than they waited, every week of September and October. Ships ahead divided by berths freed per day, from AIS alone, got it right on average. And on calm 2024 the
published figure is spot on: it goes wrong exactly when the queue grows.
[`shared/crisis/wait.json` bias −2.5 d vs +0.1 d; `shared/wait.json` steady weeks 0.0 d]

**What it's worth to a shipping company (≈ 110 words).**
Since November 2021 your place in line is set when you leave your last port, so slowing down no longer costs
your spot. What captains lack is the right number to slow down to. We tested ours a week out at sea: the
published figure ran three days short; ours was within a day. That's up to $300,000 of fuel per large ship, and
tens of millions across September and October 2021 alone, with the emissions moved out to sea.
[issued-ahead check: `shared/crisis/wait.json` daily, estimate issued 7 d before joining, bias ours −0.8 d vs published −3.1 d (measured);
per ship: slow the last 7 days (17 → ~12.5 kn) to absorb the ~2.5 d shortfall, 60–150 t/day at 17 kn, fuel per mile ∝ v², $615/t VLSFO ≈ $120–300k, back-of-envelope;
fleet = ~266 large container visits Sep–Oct 2021 × that, upper bound (every captain acts); rule: `pipeline/notes/crisis_timeline_2021.md`]

**Honest limits + what paid data unlocks (≈ 85 words).**
With free data we see 60 miles out, so nobody, including us, could forecast the 2021 jumps from shore: a day
ahead nothing beats "tomorrow equals today". In normal 2024 our model beats the best simple rule by 11 percent,
mostly in storms. With satellite tracking we'd see every LA-bound ship from the day it leaves Asia, and could
forecast the crisis itself. That would be worth up to $650,000 per ship, and on the order of $100 million in
two months, at one port.
[`crisis/metrics.json` h=1 +0.5 % [−6.4, +4.8]; `metrics.json` h=1 +10.7 % [+3.3, +17.5]; satellite = not tested; $ = wait known on leaving Asia → cross 5,700 nm at 12 kn instead of 17 (~14 → ~20 d), ~50 % less crossing fuel, 60–150 t/day, $615/t ≈ $260–650k per large ship × ~266 large visits Sep–Oct 2021 ≈ $70–170 M, back-of-envelope, "would"]

**Who pays + close (≈ 40 words).**
Whoever buys the fuel: charterers and carriers. The next port costs nothing to add. Two of us built this in
five hours, directing a team of Claude agents. Every captain should get the real number.

---

## Don't say
- "We can predict the crisis with satellite data" (say "would": not tested).
- "$45–90 M" out loud (say "tens of millions": it assumes every captain acts and every ship is that size).
- "We predicted the crisis" / "saw it coming in September" (crisis day+1 skill: no detectable difference).
- "Our wait estimate is more accurate" (per day it isn't: MAE 4.3 vs 3.8 d; per ship it beats the published figure for 52 %). Say "right on average".
- "Avoidable $55 M" ($55 M is everything burned at anchor; only the $5 M gap is tied to the wrong wait figure).
- "Container queue" for 2024 (74 % tankers).

## 30-second version
Off Los Angeles in 2021 the published wait for a berth told captains two to three days less than they really
waited, every week of the build-up, because it averages ships that already berthed. From free ship-tracking data
we rebuilt the queue (matching the Marine Exchange count) and estimated the wait as queue divided by berthing rate:
right on average, and the published figure is fine in calm 2024. The gap cost about $5 million in fuel and
200 tonnes of NOx in two months. Same free inputs exist for every major port.
