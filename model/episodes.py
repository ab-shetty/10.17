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
             "the queue fell from 10 to 6 ships. Once the wind dropped they came back: 12 ships on Nov 8."),
    dict(start="2024-11-14", end="2024-11-18", replay_days=["2024-11-15", "2024-11-16", "2024-11-17", "2024-11-18"],
         title="Storm swell halves the queue, and it bounces back",
         why="3 m waves at the harbor-entrance buoy and 27 kn gusts on Nov 15-16. Anchored ships got under way "
             "inside the bay; the anchored count fell to 5.6. By Nov 18 it was back to 15."),
    dict(start="2024-12-08", end="2024-12-11", replay_days=["2024-12-09", "2024-12-10", "2024-12-11"],
         title="December wind event: 18 -> 10 -> 15 ships",
         why="32 kn gusts on Dec 10. Of the 20 ships anchored on Dec 9, five were drifting 20-30 nm offshore the "
             "next day, waiting it out at sea. The queue dropped to 10, then refilled to 14.5 on Dec 11. The 2024 model does get a day-ahead gust forecast "
             "(HRRR via Open-Meteo); the queue refilling after the gale is what it learned from history."),
]

KEY_DAYS = {  # turning points to quote per episode (target dates, h=1)
    "2024-11-05": ["2024-11-07", "2024-11-08"],
    "2024-11-14": ["2024-11-16", "2024-11-17", "2024-11-18"],
    "2024-12-08": ["2024-12-10", "2024-12-11"],
}


def model_note(start, preds):
    out = []
    for day in KEY_DAYS[start]:
        r = preds[(day, 1)]
        bname = {"blend": "blend of the two naive rules", "ma7": "7-day mean", "persistence": "tomorrow = today"}[r["baseline_name"]]
        better = abs(r["pred"] - r["actual"]) < abs(r["baseline"] - r["actual"])
        out.append(f"{day}: model {r['pred']:.1f}, tomorrow = today {r['persistence']:.1f}, {bname} {r['baseline']:.1f}; "
                   f"actual {r['actual']:.1f} ({'model' if better else bname} closer). "
                   f"Why: {r['top_features'][0]['phrase']}.")
    return " ".join(out)


if __name__ == "__main__":
    preds = {(r["date"], r["h"]): r for r in json.loads(Path("shared/preds.json").read_text())}
    for e in EPISODES:
        e["model_note"] = model_note(e["start"], preds)
    Path("shared/episodes.json").write_text(json.dumps(EPISODES, indent=1))
    print("wrote shared/episodes.json;", sum(len(e["replay_days"]) for e in EPISODES), "replay days")
