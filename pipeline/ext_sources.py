"""Extra observed daily features (UTC days), written to data/ext_daily.parquet and joined by build_daily.py.

- KLGB (Long Beach airport) ASOS via Iowa Environmental Mesonet: observed visibility + fog codes.
  Better than Open-Meteo's modelled visibility; fog is the classic reason the pilot station slows boardings.
- NDBC/CDIP buoy 46222 (San Pedro, at the harbor entrance): significant wave height + dominant period.
"""
import argparse
import io
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ASOS = ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=LGB&data=vsby&data=wxcodes"
        "&year1={s.year}&month1={s.month}&day1={s.day}&year2={e.year}&month2={e.month}&day2={e.day}&tz=Etc/UTC"
        "&format=onlycomma&latlon=no&missing=M&trace=T&report_type=3")
BUOY = "https://www.ndbc.noaa.gov/view_text_file.php?filename=46222h{y}.txt.gz&dir=data/historical/stdmet/"


def get(url):
    for _ in range(4):
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print("retry", e.__class__.__name__)
    raise RuntimeError(url)


def asos(start, end):
    a = pd.read_csv(io.StringIO(get(ASOS.format(s=start, e=end + pd.Timedelta(days=1)))), na_values="M")
    a["date"] = pd.to_datetime(a.valid).dt.normalize()
    a["fog"] = a.wxcodes.fillna("").str.contains("FG") | (a.vsby < 1)
    a["hour"] = pd.to_datetime(a.valid).dt.floor("h")
    return a.groupby("date").agg(klgb_vis_min_mi=("vsby", "min"),
                                 klgb_fog_hours=("hour", lambda h: h[a.loc[h.index, "fog"]].nunique()))


def buoy(start, end):
    b = pd.concat([pd.read_csv(io.StringIO(get(BUOY.format(y=y))), sep=r"\s+", skiprows=[1])
                   for y in range(start.year, end.year + 1)])
    b.columns = [c.lstrip("#") for c in b.columns]
    b["date"] = pd.to_datetime(dict(year=b.YY, month=b.MM, day=b.DD))
    b["WVHT"] = b.WVHT.replace(99.0, np.nan)
    b["DPD"] = b.DPD.replace(99.0, np.nan)
    return b.groupby("date").agg(wave_hs_max_m=("WVHT", "max"), wave_hs_mean_m=("WVHT", "mean"),
                                 wave_period_max_s=("DPD", "max"))


def main(start, end, out):
    start, end = pd.Timestamp(start), pd.Timestamp(end)
    d = asos(start, end).join(buoy(start, end), how="outer").loc[start:end]
    d.reset_index().to_parquet(out, index=False)
    print(d.describe().T.round(2).to_string())


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--start", default="2024-01-01")
    a.add_argument("--end", default="2024-12-31")
    a.add_argument("--out", default="data/ext_daily.parquet")
    x = a.parse_args()
    main(x.start, x.end, x.out)
