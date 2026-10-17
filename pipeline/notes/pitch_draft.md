# Pitch script (3 min, ~420 spoken words). Final numbers, 3:05 PDT

Every number has its source in [brackets]. Spoken text is in plain paragraphs; stage directions are in *italics*.
Demo = a **replay** of 2021 and 2024 AIS, not live. Say so.

---

*[Screen: crisis map replay, Oct 19 2021, dots piling up offshore]*

**Hook (≈ 50 words).**
On October 11th, 2021, the MSC Josseline, a 366-metre container ship, joined the queue off Los Angeles.
The port's published wait that day was twelve and a half days. She waited seventeen. Told the real number,
her captain could have crossed the Pacific five days slower instead of idling over Wilmington and San Pedro:
roughly $300,000 to $600,000 of fuel, for one ship, from one honest number.
[`shared/crisis/hero_ship.json` usd_slow_steam, back-of-envelope; judge_qa.md]

**Problem (≈ 50 words).**
In the 2021 backlog, more than a hundred ships waited off San Pedro Bay. Every day at anchor burns fuel and
puts NOx and soot over the harbor neighborhoods. Captains could slow down at sea instead, but only if they
know how long the wait really is.

*[Screen: the "queue spilled into the ocean" chart]*

**What we built (≈ 60 words).**
From free NOAA ship-tracking data we rebuilt the whole queue: ships at anchor plus ships loitering offshore.
On the peak day we count 102 waiting; the Marine Exchange counted 107. The anchorage sat flat at about fifty
while the overflow drifted out to sea. This is a replay of 2021, not a live feed.
[CLAUDE.md, 48 + 54 = 102.5 vs MX 56 + 51]

*[Screen: weekly wait chart: real (white), published (grey dashed), ours (orange)]*

**What we found (≈ 80 words).**
The published wait is an average of ships that already berthed, so it looks backwards. All through the
build-up it told captains two to three days less than they actually waited: in every one of nine weeks in
September and October. Queue divided by berthing rate, from AIS alone, got it right on average.
And it's not cherry-picked: on calm 2024 the published figure is spot on. It goes wrong exactly when the queue grows.
[`shared/crisis/wait.json` bias −2.5 d vs +0.1 d; `shared/wait.json` steady weeks 0.0 d]

**What it cost (≈ 45 words).**
That gap alone is 893 ship-days of idling nobody planned for in two months: about $5 million of fuel and
200 tonnes of NOx. It sits inside roughly $55 million of fuel burned at anchor over the backlog.
[`wait.json` gap_cost.net_understatement; `crisis/emissions.json` 71,216 t × $780/t]

**Honest limits (≈ 60 words).**
Forecasting the count a day ahead in the crisis: nothing seen from shore beats "tomorrow equals today".
The queue moved in steps set weeks earlier in Asia. In normal 2024 our model does beat the best naive rule
a day ahead, by 11 percent, mostly by reading the weather forecast in stormy weather.
And after November 16th ships were told to wait 150 miles out, beyond shore receivers.
[`crisis/metrics.json` h=1 +0.5 % [−6.4, +4.8]; `metrics.json` h=1 +10.7 % [+3.3, +17.5]]

**Scale + next (≈ 45 words).**
Both inputs are free and exist for every major port on earth: ship positions from AIS, berthing rates from
the IMF's PortWatch. Next: satellite AIS to see ships two weeks out, and give every captain the real wait.

---

## Don't say
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
