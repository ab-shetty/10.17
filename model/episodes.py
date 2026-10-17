"""Write shared/episodes.json: out-of-sample (Oct-Dec 2024) turning points where the model beat persistence.

Picked from data/preds.parquet (h=1 big moves) + daily weather; mechanism checked by tracing the ships anchored
the day before through data/ais + data/approach. Numbers below come from data/daily.parquet and shared/preds.json.
"""
import json
from pathlib import Path

EPISODES = [
    dict(start="2024-11-05", end="2024-11-09", replay_days=["2024-11-05", "2024-11-06", "2024-11-07", "2024-11-08", "2024-11-09"],
         title="Santa Ana gale: the anchorage thins out, then refills",
         why="Gusts hit 36 kn on Nov 6-7. Part of the anchored fleet weighed anchor and rode it out under way; "
             "the queue fell from 10 to 6 ships. Once the wind dropped they came back: 12 ships on Nov 8.",
         model_note="On Nov 7 the model forecast 10.0 for Nov 8 (persistence: 6.3, actual: 12.0). Top reasons: "
                    "queue unusually low, yesterday's 36 kn gusts. It also expected the rebound a day early on Nov 7."),
    dict(start="2024-11-14", end="2024-11-18", replay_days=["2024-11-15", "2024-11-16", "2024-11-17", "2024-11-18"],
         title="Storm swell halves the queue, and it bounces back",
         why="3 m waves at the harbor-entrance buoy and 27 kn gusts on Nov 15-16. Anchored ships got under way "
             "inside the bay; the anchored count fell to 5.6. By Nov 18 it was back to 15.",
         model_note="For Nov 17 the model said 8.3 (persistence 5.6, actual 9.4), reading the low queue plus "
                    "the 27 kn gusts as a temporary dip. It under-called the size of the Nov 18 refill (10.7 vs 15.3)."),
    dict(start="2024-12-08", end="2024-12-11", replay_days=["2024-12-09", "2024-12-10", "2024-12-11"],
         title="December wind event: 18 -> 10 -> 15 ships",
         why="32 kn gusts on Dec 10. Of the 20 ships anchored on Dec 9, five were drifting 20-30 nm offshore the "
             "next day, waiting it out at sea. The queue dropped to 10, then refilled to 14.5 on Dec 11.",
         model_note="For Dec 11 the model forecast 12.0 vs persistence 10.1 (actual 14.5): it again expected the "
                    "post-gale refill. It did NOT see the Dec 10 drop coming (16.4 vs 10.1): the gale itself is not "
                    "in its inputs ahead of time. A weather forecast feed would fix that."),
]

if __name__ == "__main__":
    Path("shared/episodes.json").write_text(json.dumps(EPISODES, indent=1))
    print("wrote shared/episodes.json;", sum(len(e["replay_days"]) for e in EPISODES), "replay days")
