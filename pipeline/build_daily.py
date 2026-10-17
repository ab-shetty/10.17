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
import pandas as pd
import pyarrow.parquet as pq
from pandas.tseries.holiday import USFederalHolidayCalendar

ANCHOR_BOX = dict(lat0=33.58, lat1=33.77, lon0=-118.30, lon1=-117.97)
CELL = 0.002
BERTH_MIN_PINGS = 30
GAP_H = 24  # absence that separates two visits


def valid(f):
    try:
        pq.ParquetFile(f)
        return True
    except Exception:
        return False


def main():
    files = [f for f in sorted(glob("data/ais/*.parquet")) if valid(f)]
    print(f"{len(files)} valid day files")
    c = duckdb.connect()
    c.execute("SET memory_limit='2GB'")
    b = ANCHOR_BOX
    c.execute(f"""
      CREATE TABLE p AS
      SELECT mmsi, ts, lat, lon, sog, status, draft,
             floor(lat/{CELL})::INT AS cy, floor(lon/{CELL})::INT AS cx
      FROM read_parquet({files})""")
    c.execute(f"""
      CREATE TABLE berth AS
      WITH dense AS (SELECT cy, cx FROM p WHERE status = 5 GROUP BY 1, 2 HAVING count(*) >= {BERTH_MIN_PINGS})
      SELECT DISTINCT d.cy + dy AS cy, d.cx + dx AS cx
      FROM dense d, range(-1, 2) t1(dy), range(-1, 2) t2(dx)""")
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
               count(DISTINCT mmsi) FILTER (WHERE moored) AS m
        FROM q GROUP BY 1)
      SELECT hr::DATE AS date, avg(a) AS n_anchored, max(a) AS n_anchored_max, avg(m) AS n_moored
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
    d["n_arrivals_24h"] = arr.groupby(arr.t_in.dt.floor("D")).size()
    d["n_departures_24h"] = dep.groupby(dep.t_out.dt.floor("D")).size()
    d[["n_arrivals_24h", "n_departures_24h"]] = d[["n_arrivals_24h", "n_departures_24h"]].fillna(0).astype(int)
    d["n_arrivals_48h"] = d.n_arrivals_24h.rolling(2, min_periods=1).sum().astype(int)
    d["avg_wait_hours"] = waits.groupby(waits.t_berth.dt.floor("D")).wait_h.mean()

    w = pd.read_parquet("data/weather_daily.parquet")
    w.index = pd.to_datetime(w.date)
    d = d.join(w.drop(columns="date"))
    d["dow"] = d.index.dayofweek
    hol = USFederalHolidayCalendar().holidays("2024-01-01", "2024-12-31")
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
    d.to_parquet("data/daily.parquet", index=False)
    print(d.describe().T.round(2).to_string())

    out = d.rename(columns={"n_arrivals_24h": "arrivals_24h", "n_departures_24h": "departures_24h",
                            "avg_wait_hours": "avg_wait_h", "visibility_min_m": "vis_min_m"})
    out["date"] = out.date.dt.strftime("%Y-%m-%d")
    cols = ["date", "n_anchored", "n_moored", "arrivals_24h", "departures_24h", "avg_wait_h", "wind_max_kts", "vis_min_m"]
    rec = json.loads(out[cols].round(2).to_json(orient="records"))
    Path("shared").mkdir(exist_ok=True)
    Path("shared/daily.json").write_text(json.dumps(rec))
    print(f"wrote shared/daily.json ({len(rec)} days)")


if __name__ == "__main__":
    main()
