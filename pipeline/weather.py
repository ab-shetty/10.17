"""Pull hourly 2024 weather for San Pedro Bay from Open-Meteo (no key), aggregate per UTC day.

Uses the historical-forecast API because the ERA5 archive has no visibility.
Writes data/weather_daily.parquet: date, wind_max_kts, gust_max_kts, visibility_min_m.
"""
from pathlib import Path
import pandas as pd
import time
import requests

URL = ("https://historical-forecast-api.open-meteo.com/v1/forecast?latitude=33.72&longitude=-118.20"
       "&start_date=2024-01-01&end_date=2024-12-31&hourly=wind_speed_10m,wind_gusts_10m,visibility"
       "&wind_speed_unit=kn&timezone=UTC")
OUT = Path("data/weather_daily.parquet")


def main():
    for i in range(5):
        try:
            h = pd.DataFrame(requests.get(URL, timeout=120).json()["hourly"])
            break
        except requests.RequestException as e:
            print(f"retry {i}: {e.__class__.__name__}", flush=True)
            time.sleep(5)
    h["date"] = pd.to_datetime(h["time"]).dt.date
    d = h.groupby("date").agg(wind_max_kts=("wind_speed_10m", "max"),
                              gust_max_kts=("wind_gusts_10m", "max"),
                              visibility_min_m=("visibility", "min")).reset_index()
    OUT.parent.mkdir(exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(d.describe().round(1))


if __name__ == "__main__":
    main()
