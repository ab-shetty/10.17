"""Extra observed daily features (UTC days), written to data/ext_daily.parquet and joined by build_daily.py.

- KLGB (Long Beach airport) ASOS via Iowa Environmental Mesonet: observed visibility + fog codes.
  Better than Open-Meteo's modelled visibility; fog is the classic reason the pilot station slows boardings.
- NDBC/CDIP buoy 46222 (San Pedro, at the harbor entrance): significant wave height + dominant period.
"""
import io
from pathlib import Path
import numpy as np
import pandas as pd
import requests

ASOS = ("https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?station=LGB&data=vsby&data=wxcodes"
        "&year1=2024&month1=1&day1=1&year2=2025&month2=1&day2=1&tz=Etc/UTC&format=onlycomma"
        "&latlon=no&missing=M&trace=T&report_type=3")
BUOY = "https://www.ndbc.noaa.gov/view_text_file.php?filename=46222h2024.txt.gz&dir=data/historical/stdmet/"
OUT = Path("data/ext_daily.parquet")


def get(url):
    for _ in range(4):
        try:
            r = requests.get(url, timeout=180)
            r.raise_for_status()
            return r.text
        except requests.RequestException as e:
            print("retry", e.__class__.__name__)
    raise RuntimeError(url)


def asos():
    a = pd.read_csv(io.StringIO(get(ASOS)), na_values="M")
    a["date"] = pd.to_datetime(a.valid).dt.normalize()
    a["fog"] = a.wxcodes.fillna("").str.contains("FG") | (a.vsby < 1)
    a["hour"] = pd.to_datetime(a.valid).dt.floor("h")
    return a.groupby("date").agg(klgb_vis_min_mi=("vsby", "min"),
                                 klgb_fog_hours=("hour", lambda h: h[a.loc[h.index, "fog"]].nunique()))


def buoy():
    b = pd.read_csv(io.StringIO(get(BUOY)), sep=r"\s+", skiprows=[1])
    b.columns = [c.lstrip("#") for c in b.columns]
    b["date"] = pd.to_datetime(dict(year=b.YY, month=b.MM, day=b.DD))
    b["WVHT"] = b.WVHT.replace(99.0, np.nan)
    b["DPD"] = b.DPD.replace(99.0, np.nan)
    return b.groupby("date").agg(wave_hs_max_m=("WVHT", "max"), wave_hs_mean_m=("WVHT", "mean"),
                                 wave_period_max_s=("DPD", "max"))


def main():
    d = asos().join(buoy(), how="outer").loc["2024"]
    d.reset_index().to_parquet(OUT, index=False)
    print(d.describe().T.round(2).to_string())


if __name__ == "__main__":
    main()
