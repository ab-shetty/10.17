# Pitch draft (3 min, ~420 spoken words) + 30-second version

Follows the "Pitch spine" [OVERSEER.md]. Headline = 2021-22 backlog; 2024 = "it works in normal times too".
Every number has its source in [brackets]. `{PLACEHOLDERS}` = crisis metrics not yet in the repo
(`shared/crisis/` currently holds only `weather_daily.json`; no crisis `metrics.json`, `preds.json`, `chart.json` yet).
Spoken words are the plain paragraphs; stage directions are in [brackets].

---

## 3-minute script

**1. Hook (0:00-0:25)**
[SCREEN: dark map of San Pedro Bay, crisis replay of 2021-10-25 `shared/crisis/replay/`. Dots pile up at anchor (red) and drift offshore (amber).]

This is October 25th, 2021. Every dot is a cargo ship or tanker, waiting. On this single day, 56 were at anchor and another 51 were drifting in holding areas. That is 107 ships, idling off Los Angeles and Long Beach. [crisis_timeline_2021.md; CLAUDE.md]

**2. Problem (0:25-0:55)**
[SCREEN: Wilmington / San Pedro map layer, then one big number: "+20 tons NOx per day ≈ 5.8 million cars".]

Idling ships run their engines. California's Air Resources Board put the excess at about 20 tons of nitrogen oxides a day, equal to roughly 5.8 million passenger cars. [CLAUDE.md; shared/emissions.json carb.oct_2021] The Port of LA's own 2021 inventory says ships hotelling at anchor made up 48% of its ship NOx: 2,848 short tons, versus 118 in 2023. That is Port of LA calls only; Long Beach is extra. [CLAUDE.md; shared/emissions.json cross_check.pola_2021_inventory] And it lands on Wilmington, where all 14 populated census tracts sit in California's worst quarter for pollution burden. [CLAUDE.md; health_context.md]

**3. What we built (0:55-1:25)**
[SCREEN: pipeline diagram: AIS points → bay box + approach ring → weather → forecast line.]

We took public AIS ship-tracking data and built a one-to-three-day forecast of ships waiting: anchored in the bay, plus loitering within 60 nautical miles. Inputs: ships already inbound inside 60 nautical miles, arrivals, and weather. Counting only the anchored ships would have missed half the crisis queue. [CLAUDE.md]

**4. Evidence (1:25-2:10)**
[SCREEN: Sep-Oct 2021 chart (`shared/crisis/chart.json`): actual, our forecast, "tomorrow = today", 7-day mean. Then a 3-tile validation row.]

In the crisis window, one day ahead, we beat the best naive rule by {CRISIS_SKILL_H1}, confidence interval {CRISIS_CI_H1}. {CRISIS_LEAD_SENTENCE} [shared/crisis/metrics.json, not yet in repo]

In normal times, 2024 Oct-Dec, tested forward: one day ahead we beat the best naive baseline by 10.2%, 90% interval 2.9 to 16.3. [shared/metrics.json, h=1] Two and three days ahead we roughly tie a seven-day average, since both intervals include zero. [shared/metrics.json, h=2: -10.0 to 15.0; h=3: -9.8 to 13.0] Against "tomorrow equals today" alone, the gain is 17%, 17% and 15%. [shared/metrics.json]

Is the count right? Marine Exchange reported 56 at anchor plus 51 in holding areas on the peak day; we count 56 plus 52. [crisis_timeline_2021.md; CLAUDE.md] Against the Port of LA's daily container counts our counts correlate at 0.49 at anchor and 0.62 at berth. [CLAUDE.md] Our 2024 emissions rate is 2.2 tons NOx a day against CARB's 1.7 baseline; we also count bulk and car carriers. [CLAUDE.md; shared/emissions.json]

**5. So what (2:10-2:35)**
[SCREEN: before/after sketch: ships idling at anchor vs. ships slow-steaming offshore. Then the Claude "morning brief" panel.]

Here is the action. In November 2021 the ports changed the system: ships now wait farther out, and the Port of LA says that was to improve safety and air quality. [CLAUDE.md] That moved the emissions offshore. A forecast lets ports and carriers do it routinely: slow down at sea, arrive just in time, don't idle off Wilmington.

**6. Honest limits (2:35-2:55)**
[SCREEN: one slide, four bullets.]

Limits. This is a replay of 2021 and 2024, not live. Shore receivers see about 60 nautical miles, and after November 16th, 2021 most of the queue moved beyond that. On January 12th, 2022 only 11 of 104 ships were within 40 miles. [crisis_timeline_2021.md] Archived weather forecasts start in 2024, so our 2021 model can't see storms coming. [CLAUDE.md]

**7. Next (2:55-3:00)**
Next: a live AIS feed, and Port of LA Signal data for a longer horizon. [OVERSEER.md]

---

## 30-second version

[SCREEN: crisis replay, then the forecast chart.]

On October 25th, 2021, 107 ships were idling off Los Angeles and Long Beach: 56 at anchor and 51 in holding areas. [crisis_timeline_2021.md] CARB put the excess NOx at about 20 tons a day, roughly 5.8 million cars. [shared/emissions.json] We forecast ships waiting one to three days ahead from public AIS data. In normal 2024 we beat the best naive baseline by 10.2% at one day, interval 2.9 to 16.3, and roughly tie at two and three days. [shared/metrics.json] {CRISIS_SKILL_H1} in the crisis. It's a replay, not live, and shore AIS loses the queue past about 60 nautical miles. A forecast makes just-in-time arrival routine.

---

## Placeholders to fill (from `shared/crisis/`)

| placeholder | what to fill | file to read |
|---|---|---|
| `{CRISIS_SKILL_H1}` | h=1 skill vs the best naive baseline (n_waiting target) | `shared/crisis/metrics.json` |
| `{CRISIS_CI_H1}` | its `skill_ci90`. If the CI includes 0, say "roughly ties" | `shared/crisis/metrics.json` |
| `{CRISIS_LEAD_SENTENCE}` | e.g. the lead-day episode where the forecast rose before the queue | `shared/crisis/episodes.json` (`lead_score`) |

## Fact-check notes
- POLA 2021 NOx appears as 2,848 short tons [CLAUDE.md] and 2,584 (metric) tonnes [shared/emissions.json]; same figure, different units. Script uses short tons.
- "109" (2022-01-09, container-ship queue incl. ships 150+ nm out) is a different count from CARB's Oct-2021 "109 total at anchor". Neither is in the script, to avoid mixing them. [crisis_timeline_2021.md]
- CARB Oct-2021 figures are UNVERIFIED against the PDF per `crisis_timeline_2021.md`; re-check before showing the slide.
- Story-day limits: Oct 25 2021 had a storm (bomb cyclone), so some "holding" ships were moving under power. [crisis_timeline_2021.md]
- 2024 anchored queue is ~74% tankers [CLAUDE.md]; the script says "ships waiting", never "container queue".
- Word count of the 3-minute spoken text is roughly 520 with the evidence section; trim the Wilmington sentence and the PM/POLA-correlation sentence first if over time.
