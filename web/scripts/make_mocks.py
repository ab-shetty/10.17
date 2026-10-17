"""Write mock versions of A's not-yet-published shared/ files so the UI never waits on A.

Writes shared/episodes.mock.json and shared/replay/<day>.mock.json, with exactly the shapes in CLAUDE.md.
The web app loads the real file first and falls back to *.mock.json (shown with a MOCK badge).
Usage: python web/scripts/make_mocks.py   (from the repo root)
"""
import json
import math
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

SHARED = Path("shared")
EPISODES = [
    dict(start="2024-02-26", end="2024-03-04", title="Early-March pile-up (MOCK)",
         why="Mock text. Queue climbed to ~25 ships at anchor, the 2024 peak, while berths stayed full."),
    dict(start="2024-04-19", end="2024-04-25", title="Late-April spike (MOCK)",
         why="Mock text. A burst of arrivals over three days outran departures."),
    dict(start="2024-07-24", end="2024-08-05", title="Early peak season (MOCK)",
         why="Mock text. POLA's best July in 116 years; the queue held above 20 for a week."),
]
REPLAY_DAYS = ["2024-03-01", "2024-04-22", "2024-07-30"]

# Rough anchorage and terminal spots (lat, lon) inside the CLAUDE.md boxes.
ANCHOR_SPOTS = [(33.66, -118.03), (33.64, -118.06), (33.68, -118.08), (33.70, -118.12),
                (33.62, -118.10), (33.73, -118.17), (33.72, -118.22), (33.67, -118.15)]
BERTHS = [(33.755, -118.215), (33.748, -118.235), (33.760, -118.255), (33.745, -118.27),
          (33.765, -118.20), (33.752, -118.19), (33.737, -118.26), (33.770, -118.24)]
GATE = (33.70, -118.25)        # Angels Gate / Queens Gate approach
SEA = [(33.56, -118.05), (33.56, -118.33), (33.60, -117.96)]
NAMES = ["EVER LIVEN", "CMA CGM ARGENTINA", "MSC TINA", "OOCL HONG KONG", "COSCO PRIDE", "ONE APUS",
         "MAERSK EDMONTON", "HYUNDAI SATURN", "PACIFIC VOYAGER", "OVERSEAS ANACORTES", "ALASKA FRONTIER",
         "STENA IMPERO", "TORM HELENE", "NAVIG8 ARIA", "SEAWAYS RAINIER", "CHEMBULK OCEAN", "GULF CORAL",
         "YM WELLNESS", "APL MIAMI", "HMM ALGECIRAS", "ZIM SAMMY", "WAN HAI 512", "SEASPAN BELIEF",
         "KOTA PEMIMPIN", "MOL TRIUMPH", "NORDIC AURORA", "BRITISH CAPTAIN", "AFRAMAX STAR"]


def lerp(a, b, f):
    return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)


def plan(rng):
    """Each vessel gets a list of (start_step, end_step, kind, from, to)."""
    kind = rng.choice(["anchored", "anchored", "anchored", "moored", "moored", "transit"])
    anchor = rng.choice(ANCHOR_SPOTS)
    anchor = (anchor[0] + rng.uniform(-0.012, 0.012), anchor[1] + rng.uniform(-0.015, 0.015))
    berth = rng.choice(BERTHS)
    sea = rng.choice(SEA)
    if kind == "anchored":         # waits at anchor, some go to berth in the afternoon
        leave = rng.choice([None, None, rng.randint(60, 120)])
        if leave is None:
            return [(0, 144, "anchored", anchor, anchor)]
        return [(0, leave, "anchored", anchor, anchor), (leave, leave + 12, "underway", anchor, berth),
                (leave + 12, 144, "moored", berth, berth)]
    if kind == "moored":           # at berth, some depart to sea
        leave = rng.choice([None, rng.randint(30, 110)])
        if leave is None:
            return [(0, 144, "moored", berth, berth)]
        return [(0, leave, "moored", berth, berth), (leave, leave + 18, "underway", berth, sea),
                (leave + 18, 144, "gone", sea, sea)]
    arrive = rng.randint(0, 100)  # arrives from sea and anchors
    return [(0, arrive, "gone", sea, sea), (arrive, arrive + 16, "underway", sea, anchor),
            (arrive + 16, 144, "anchored", anchor, anchor)]


def replay(day, seed):
    rng = random.Random(seed)
    t0 = datetime.fromisoformat(day).replace(tzinfo=timezone.utc)
    rows = []
    for i, name in enumerate(rng.sample(NAMES, 24)):
        mmsi = 538000000 + seed * 1000 + i
        for s0, s1, kind, a, b in plan(rng):
            for step in range(s0, min(s1, 144)):
                if kind == "gone":
                    continue
                f = (step - s0) / max(1, s1 - s0)
                if kind == "underway":
                    # route through the gate when entering or leaving the harbor
                    p = lerp(a, GATE, f * 2) if f < 0.5 else lerp(GATE, b, f * 2 - 1)
                else:
                    p = a
                jitter = 0.0004 * math.sin(step / 9 + i) if kind == "anchored" else 0
                status = {"anchored": 1, "moored": 5, "underway": 0}[kind]
                sog = round(rng.uniform(0.0, 0.3), 1) if kind != "underway" else round(rng.uniform(6, 12), 1)
                rows.append(dict(mmsi=mmsi, name=name, t=(t0 + timedelta(minutes=10 * step)).strftime("%Y-%m-%dT%H:%M:00Z"),
                                 lat=round(p[0] + jitter, 5), lon=round(p[1] + jitter, 5), status=status, sog=sog, state=kind))
    rows.sort(key=lambda r: (r["t"], r["mmsi"]))
    return rows


def main():
    (SHARED / "episodes.mock.json").write_text(json.dumps(EPISODES, indent=1))
    (SHARED / "replay").mkdir(exist_ok=True)
    for k, day in enumerate(REPLAY_DAYS):
        f = SHARED / "replay" / f"{day}.mock.json"
        rows = replay(day, k + 1)
        f.write_text(json.dumps(rows))
        print(f, len(rows), "rows")


if __name__ == "__main__":
    main()
