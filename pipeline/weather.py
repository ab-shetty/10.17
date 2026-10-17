"""Pull hourly weather for San Pedro Bay from Open-Meteo (no key), aggregate per UTC day.

Usage: python pipeline/weather.py [--start 2024-01-01 --end 2024-12-31 --out data/weather_daily.parquet [--json f]]

Two sources:
- historical-forecast API: "what happened" (wind, gusts, visibility; ERA5 archive has no visibility).
- previous-runs API: what the forecast said 1/2/3 days EARLIER for each hour (`*_previous_dayN`). This is what a
  forecaster on day t could know about day t+N, so the model can see a storm coming without peeking.
Raw responses are cached in data/cache/ (Open-Meteo rate-limits).
"""
import argparse
import hashlib
import json
import time
from pathlib import Path
import pandas as pd
import requests

LOC = "latitude=33.72&longitude=-118.20&wind_speed_unit=kn&timezone=UTC"
HIST = "https://historical-forecast-api.open-meteo.com/v1/forecast?" + LOC + \
       "&start_date={s}&end_date={e}&hourly=wind_speed_10m,wind_gusts_10m,visibility"
PREV = "https://previous-runs-api.open-meteo.com/v1/forecast?" + LOC + "&start_date={s}&end_date={e}&hourly=" + \
       ",".join(f"{v}_previous_day{n}" for v in ("wind_gusts_10m", "wind_speed_10m") for n in (1, 2, 3))
CACHE = Path("data/cache")


def get(url):
    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.md5(url.encode()).hexdigest() + ".json")
    if f.exists():
        return json.loads(f.read_text())
    for i in range(6):
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            f.write_text(r.text)
            return r.json()
        except requests.RequestException as e:
            print(f"retry {i}: {e.__class__.__name__}", flush=True)
            time.sleep(5 * (i + 1))
    raise RuntimeError(url)


def main(start, end, out, js=None):
    h = pd.DataFrame(get(HIST.format(s=start, e=end))["hourly"])
    p = pd.DataFrame(get(PREV.format(s=start, e=end))["hourly"])
    h = h.merge(p, on="time", how="left")
    h["date"] = pd.to_datetime(h["time"]).dt.normalize()
    agg = dict(wind_max_kts=("wind_speed_10m", "max"), gust_max_kts=("wind_gusts_10m", "max"),
               visibility_min_m=("visibility", "min"))
    for n in (1, 2, 3):  # forecast for this day, issued n days before
        agg[f"fc{n}_gust_max_kts"] = (f"wind_gusts_10m_previous_day{n}", "max")
        agg[f"fc{n}_wind_max_kts"] = (f"wind_speed_10m_previous_day{n}", "max")
    d = h.groupby("date").agg(**agg).reset_index()
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(out, index=False)
    if js:
        Path(js).parent.mkdir(parents=True, exist_ok=True)
        Path(js).write_text(d.assign(date=d.date.dt.strftime("%Y-%m-%d")).round(1).to_json(orient="records"))
    print(d.describe().T.round(1).to_string())
    print("corr(observed gust, 1-day-ahead forecast gust):", round(d.gust_max_kts.corr(d.fc1_gust_max_kts), 2))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--start", default="2024-01-01")
    a.add_argument("--end", default="2024-12-31")
    a.add_argument("--out", default="data/weather_daily.parquet")
    a.add_argument("--json")
    x = a.parse_args()
    main(x.start, x.end, x.out, x.json)
