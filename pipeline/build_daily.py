"""Build data/daily.parquet (+ shared/daily.json) from data/ais/*.parquet and data/weather_daily.parquet.

Days are UTC. "At anchor" = status=1, sog<0.5, inside ANCHOR_BOX, and NOT in a berth cell.
Berth cells are data-driven: 0.002-deg grid cells with dense status=5 (moored) pings, dilated by 1 cell.
(The heatmap showed rectangles can't work: inside-breakwater anchorages overlap the terminal area.)
Counts n_anchored / n_moored are the mean over 24 hourly snapshots of distinct vessels.
"""
import json
from glob import glob
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from pandas.tseries.holiday import USFederalHolidayCalendar

ANCHOR_BOX = dict(lat0=33.58, lat1=33.77, lon0=-118.30, lon1=-117.97)
CELL = 0.002
BERTH_MIN_PINGS = 30
GAP_H = 24  # absence that separates two visits
# Slow ships in the approach zone that are NOT waiting for San Pedro Bay: moored (status 5), at Port Hueneme, or at
# the El Segundo offshore tanker terminal (code review: these were 68 % of 2024 "waiting offshore").
OTHER_TERMINAL = ("status = 5 OR (lat BETWEEN 34.0 AND 34.3 AND lon BETWEEN -119.4 AND -119.0)"
                  " OR (lat BETWEEN 33.85 AND 33.95 AND lon BETWEEN -118.50 AND -118.40)")


def valid(f):
    try:
        pq.ParquetFile(f)
        return True
    except Exception:
        return False


def main(ais_dir="data/ais", approach_dir="data/approach", weather="data/weather_daily.parquet",
         ext="data/ext_daily.parquet", out_path="data/daily.parquet", out_json="shared/daily.json", berth_in=None,
         null_outages=False):
    files = [f for f in sorted(glob(f"{ais_dir}/*.parquet")) if valid(f)]
    print(f"{len(files)} valid day files")
    c = duckdb.connect()
    c.execute("SET memory_limit='2GB'")
    b = ANCHOR_BOX
    c.execute(f"""
      CREATE TABLE p AS
      SELECT mmsi, ts, lat, lon, sog, status, draft, vessel_type, length,
             floor(lat/{CELL})::INT AS cy, floor(lon/{CELL})::INT AS cx
      FROM read_parquet({files})""")
    if berth_in:  # reuse a mask built from another period (berths don't move; 2024 = normal traffic)
        c.execute(f"CREATE TABLE berth AS SELECT * FROM '{berth_in}'")
    else:
      c.execute(f"""
      CREATE TABLE berth AS
      WITH cnt AS (SELECT cy, cx, count(*) FILTER (WHERE status = 5) AS s5,
                          count(*) FILTER (WHERE status = 1) AS s1 FROM p GROUP BY 1, 2),
      dense AS (SELECT cy, cx FROM cnt WHERE s5 >= {BERTH_MIN_PINGS} AND s5 > s1),
      dil AS (SELECT DISTINCT d.cy + dy AS cy, d.cx + dx AS cx
              FROM dense d, range(-1, 2) t1(dy), range(-1, 2) t2(dx))
      -- dilation must not swallow anchorage cells (inside-breakwater anchorages sit next to terminals)
      SELECT dil.* FROM dil LEFT JOIN cnt USING (cy, cx) WHERE coalesce(cnt.s1, 0) <= coalesce(cnt.s5, 0)""")
      c.execute("COPY berth TO 'data/berth_cells.parquet' (FORMAT parquet)")  # reused by export_replay.py
    c.execute(f"""
      CREATE TABLE q AS
      SELECT p.*, (bc.cy IS NOT NULL) AS in_berth,
             (status = 1 AND sog < 0.5 AND bc.cy IS NULL
              AND lat BETWEEN {b['lat0']} AND {b['lat1']} AND lon BETWEEN {b['lon0']} AND {b['lon1']}) AS anchored,
             ((status = 5 OR sog < 0.5) AND bc.cy IS NOT NULL) AS moored
      FROM p LEFT JOIN berth bc USING (cy, cx)""")

    # hourly snapshot counts -> daily mean
    snap = c.sql("""
      WITH h AS (
        SELECT date_trunc('hour', ts) AS hr,
               count(DISTINCT mmsi) FILTER (WHERE anchored) AS a,
               count(DISTINCT mmsi) FILTER (WHERE moored) AS m,
               count(DISTINCT mmsi) FILTER (WHERE anchored AND vessel_type BETWEEN 80 AND 89) AS a_tank,
               count(DISTINCT mmsi) FILTER (WHERE anchored AND vessel_type BETWEEN 70 AND 79) AS a_cargo,
               count(DISTINCT mmsi) FILTER (WHERE anchored AND vessel_type BETWEEN 70 AND 79 AND length >= 250) AS a_big
        FROM q GROUP BY 1)
      SELECT hr::DATE AS date, avg(a) AS n_anchored, max(a) AS n_anchored_max, avg(m) AS n_moored,
             avg(a_tank) AS n_anchored_tanker, avg(a_cargo) AS n_anchored_cargo,
             avg(a_big) AS n_anchored_bigcargo,  -- >=250 m cargo, mostly container ships (cf. POLA summary)
             -- the queue at the END of the day (last 3 hourly snapshots): known at issue time and fresher than
             -- the day's mean, which lags a moving queue by ~12 h
             avg(a) FILTER (WHERE hour(hr) >= 21) AS n_anchored_eod
      FROM h GROUP BY 1""").df()

    # visits: new visit when an mmsi reappears after >= GAP_H hours (first-ever ping on day 1 is censored)
    c.execute(f"""
      CREATE TABLE v AS
      WITH g AS (
        SELECT *, CASE WHEN lag(ts) OVER w IS NULL OR ts - lag(ts) OVER w >= INTERVAL {GAP_H} HOUR
                       THEN 1 ELSE 0 END AS new_visit
        FROM q WINDOW w AS (PARTITION BY mmsi ORDER BY ts))
      SELECT *, sum(new_visit) OVER (PARTITION BY mmsi ORDER BY ts) AS visit FROM g""")
    t0, t1 = c.sql("SELECT min(ts), max(ts) FROM q").fetchone()
    visits = c.sql(f"""
      SELECT mmsi, visit, min(ts) AS t_in, max(ts) AS t_out,
             min(ts) FILTER (WHERE anchored) AS t_anchor
      FROM v GROUP BY 1, 2""").df()
    # first moored ping AFTER first anchored ping
    moor_after = c.sql("""
      WITH fa AS (SELECT mmsi, visit, min(ts) AS t_anchor FROM v WHERE anchored GROUP BY 1, 2)
      SELECT v.mmsi, v.visit, min(v.ts) AS t_berth
      FROM v JOIN fa USING (mmsi, visit) WHERE v.moored AND v.ts > fa.t_anchor GROUP BY 1, 2""").df()
    visits = visits.merge(moor_after, on=["mmsi", "visit"], how="left")
    arr = visits[visits.t_in > pd.Timestamp(t0) + pd.Timedelta(hours=GAP_H)]
    dep = visits[visits.t_out < pd.Timestamp(t1) - pd.Timedelta(hours=GAP_H)]
    waits = visits.dropna(subset=["t_berth"]).assign(
        wait_h=lambda x: (x.t_berth - x.t_anchor).dt.total_seconds() / 3600)

    d = snap.set_index("date").sort_index()
    d.index = pd.to_datetime(d.index)
    if null_outages:  # a day with no bay data at all (2021-08-01: zero pings region-wide in NOAA's file) stays as a row
        d = d.asfreq("D")
    d["n_arrivals_24h"] = arr.groupby(arr.t_in.dt.floor("D")).size()
    d["n_departures_24h"] = dep.groupby(dep.t_out.dt.floor("D")).size()
    d[["n_arrivals_24h", "n_departures_24h"]] = d[["n_arrivals_24h", "n_departures_24h"]].fillna(0)
    # AIS receiver outages (e.g. 2024-12-25/26: 11-13 h of data) make every ship look like a new arrival.
    cov = c.sql("SELECT ts::DATE AS date, count(DISTINCT date_trunc('hour', ts)) AS h FROM q GROUP BY 1").df()
    d["coverage_hours"] = cov.set_index(pd.to_datetime(cov.date)).h
    gap = (d.coverage_hours.fillna(0) < 20) | (d.coverage_hours.shift(1).fillna(0) < 20)
    d.loc[gap, ["n_arrivals_24h", "n_departures_24h"]] = float("nan")
    if null_outages:
        # local receiver outages (e.g. 2022-01-08/09: NOAA's national file is full size but the bay has 0-5 hours):
        # the hourly mean over the few hours left undercounts, so the queue counts are unknown that day. Ships at
        # berth are a steady ~38, so a moored count < 60 % of its weekly median flags a partly-down receiver too.
        moored_ok = d.n_moored >= 0.6 * d.n_moored.rolling(7, center=True, min_periods=3).median()
        d["outage"] = (d.coverage_hours < 6) | ~moored_ok
        d.loc[d.outage, [c for c in d.columns if c.startswith(("n_anchored", "n_moored"))]] = float("nan")
    # censored edges: nobody can "arrive" on day 1 (no 24 h lookback), nobody "departs" on the last day
    d.loc[d.index[0], "n_arrivals_24h"] = float("nan")
    d.loc[d.index[-1], "n_departures_24h"] = float("nan")
    d["n_arrivals_48h"] = d.n_arrivals_24h.rolling(2).sum()
    d["avg_wait_hours"] = waits.groupby(waits.t_berth.dt.floor("D")).wait_h.mean()

    w = pd.read_parquet(weather)
    w.index = pd.to_datetime(w.date)
    d = d.join(w.drop(columns="date"))
    appr = sorted(glob(f"{approach_dir}/*.parquet"))  # pipeline/extract_approach.py
    if appr:
        # hourly snapshots of ships OUTSIDE the study bbox: loitering offshore (waiting) or inbound toward the bay
        ap = c.sql(f"""
          WITH x AS (
            SELECT mmsi, date_trunc('hour', t10) AS hr, sog, cog, status, lat, lon,
                   sqrt(power((lat - 33.70) * 60, 2) + power((lon + 118.20) * 60 * cos(radians(33.7)), 2)) AS nm,
                   (degrees(atan2((-118.20 - lon) * cos(radians(33.7)), 33.70 - lat)) + 360) % 360 AS brg
            FROM read_parquet({appr})),
          xt AS (SELECT *, coalesce(({OTHER_TERMINAL}), false) AS other_terminal FROM x),
          h AS (
            SELECT hr, count(DISTINCT mmsi) FILTER (WHERE nm < 60 AND sog < 3 AND NOT other_terminal) AS waiting,
                   count(DISTINCT mmsi) FILTER (WHERE nm < 60 AND sog >= 6
                                                AND abs(((cog - brg + 540) % 360) - 180) < 30) AS inbound
            FROM xt GROUP BY 1)
          SELECT hr::DATE AS date, avg(waiting) AS offshore_waiting, avg(inbound) AS inbound_60nm,
                 avg(waiting) FILTER (WHERE hour(hr) >= 21) AS offshore_waiting_eod,
                 count(*) AS appr_hours FROM h GROUP BY 1""").df()
        ap.index = pd.to_datetime(ap.date)
        d = d.join(ap.drop(columns="date"))
        # end-of-day ETA view (last ping per ship in the day's last hour): ships heading for the bay that would reach
        # it within 24 h at their current speed, and ships 60-140 nm out heading in. Corr with next-day arrivals in
        # 2024: 0.48 (ETA < 24 h) vs -0.08 for today's arrivals.
        eta = c.sql(f"""
          WITH x AS (
            SELECT mmsi, t10::DATE AS date, arg_max(sog, t10) AS sog, arg_max(cog, t10) AS cog, arg_max(status, t10) AS status,
                   arg_max(lat, t10) AS lat, arg_max(lon, t10) AS lon
            FROM read_parquet({appr}) WHERE hour(t10) = 23 GROUP BY 1, 2),
          y AS (SELECT *, sqrt(power((lat - 33.70) * 60, 2) + power((lon + 118.20) * 60 * cos(radians(33.7)), 2)) AS nm,
                   (degrees(atan2((-118.20 - lon) * cos(radians(33.7)), 33.70 - lat)) + 360) % 360 AS brg,
                   coalesce(({OTHER_TERMINAL}), false) AS other_terminal FROM x)
          SELECT date, count(*) FILTER (WHERE nm / sog <= 24) AS inbound_eta24,
                 count(*) FILTER (WHERE nm >= 60 AND nm < 140) AS inbound_60_140
          FROM y WHERE sog >= 6 AND NOT other_terminal AND abs(((cog - brg + 540) % 360) - 180) < 30
          GROUP BY 1""").df()
        eta.index = pd.to_datetime(eta.date)
        d = d.join(eta.drop(columns="date"))
        d.loc[d.appr_hours.notna(), ["inbound_eta24", "inbound_60_140"]] = \
            d.loc[d.appr_hours.notna(), ["inbound_eta24", "inbound_60_140"]].fillna(0)
        print(f"approach features from {len(appr)} days")
    ext = Path(ext)  # KLGB fog + harbor wave buoy (pipeline/ext_sources.py)
    if ext.exists():
        e = pd.read_parquet(ext)
        e.index = pd.to_datetime(e.date)
        d = d.join(e.drop(columns="date"))
    d["dow"] = d.index.dayofweek
    hol = USFederalHolidayCalendar().holidays(d.index.min(), d.index.max())
    d["is_holiday"] = d.index.isin(hol).astype(int)
    news = Path("shared/news.json")
    d["news_score"] = float("nan")
    if news.exists():
        nj = json.loads(news.read_text())
        rows = nj["items"] if isinstance(nj, dict) else nj
        if rows and not (isinstance(nj, dict) and nj.get("mock")):
            n = pd.DataFrame(rows)
            d["news_score"] = n.groupby(pd.to_datetime(n.date))["score"].max().reindex(d.index)

    d = d.reset_index().rename(columns={"index": "date"})
    if "offshore_waiting" in d:
        d["n_waiting"] = d.n_anchored + d.offshore_waiting  # anchored in the bay + loitering < 60 nm offshore
        d["n_waiting_eod"] = d.n_anchored_eod + d.offshore_waiting_eod
    if "outage" in d:
        d.loc[d.outage, [c for c in d.columns if c.startswith(("offshore_waiting", "inbound_", "n_waiting"))]] = float("nan")
    if d.date.min() < pd.Timestamp("2021-11-16") <= d.date.max():
        # 2021-11-16: ships told to wait 150+ nm out (beyond shore AIS) until ~72 h before their berth slot
        d["regime"] = np.where(d.date >= pd.Timestamp("2021-11-16"), "after_150nm_rule", "before_150nm_rule")
    d.to_parquet(out_path, index=False)
    print(d.describe().T.round(2).to_string())

    out = d.rename(columns={"n_arrivals_24h": "arrivals_24h", "n_departures_24h": "departures_24h",
                            "avg_wait_hours": "avg_wait_h", "visibility_min_m": "vis_min_m"})
    out["date"] = out.date.dt.strftime("%Y-%m-%d")
    cols = ["date", "n_anchored", "n_moored", "arrivals_24h", "departures_24h", "avg_wait_h", "wind_max_kts", "vis_min_m"]
    cols += [c for c in ("offshore_waiting", "inbound_60nm", "inbound_eta24", "n_waiting", "outage", "regime") if c in out]
    rec = json.loads(out[cols].round(2).to_json(orient="records"))
    Path(out_json).parent.mkdir(parents=True, exist_ok=True)
    Path(out_json).write_text(json.dumps(rec))
    print(f"wrote {out_path} + {out_json} ({len(rec)} days)")


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("--ais-dir", default="data/ais")
    a.add_argument("--approach-dir", default="data/approach")
    a.add_argument("--weather", default="data/weather_daily.parquet")
    a.add_argument("--ext", default="data/ext_daily.parquet")
    a.add_argument("--out", default="data/daily.parquet")
    a.add_argument("--out-json", default="shared/daily.json")
    a.add_argument("--berth-in", help="reuse this berth mask instead of computing (and overwriting) one")
    a.add_argument("--null-outages", action="store_true",
                   help="set queue counts to null on local receiver-outage days (adds an `outage` column)")
    x = a.parse_args()
    main(x.ais_dir, x.approach_dir, x.weather, x.ext, x.out, x.out_json, x.berth_in, x.null_outages)
