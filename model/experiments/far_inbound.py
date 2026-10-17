import sys, duckdb, pandas as pd, numpy as np
appr, daily = sys.argv[1], sys.argv[2]
c = duckdb.connect(); c.execute("SET memory_limit='3GB'")
q = f"""
WITH p AS (
  SELECT mmsi, t10, lat, lon, sog, cog, status,
    sqrt(power((lat-33.70)*60,2)+power((lon+118.20)*60*cos(radians(33.7)),2)) AS d,
    (degrees(atan2((-118.20-lon)*cos(radians(33.7)), 33.70-lat))+360)%360 AS brg
  FROM read_parquet('{appr}/*.parquet') WHERE hour(t10)=23 AND sog>=6 AND coalesce(status,0)<>5),
l AS (SELECT mmsi, CAST(t10 AS DATE) AS day, arg_max(d,t10) d, arg_max(sog,t10) sog, arg_max(cog,t10) cog, arg_max(brg,t10) brg
      FROM p GROUP BY 1,2)
SELECT day,
  count(*) FILTER (WHERE d<60) AS in_lt60,
  count(*) FILTER (WHERE d>=60 AND d<140) AS in_60_140,
  count(*) FILTER (WHERE d/sog BETWEEN 0 AND 24) AS eta24,
  count(*) FILTER (WHERE d>=60 AND d/sog BETWEEN 0 AND 30) AS far_eta30
FROM l WHERE least(abs(cog-brg), 360-abs(cog-brg)) < 30 GROUP BY 1 ORDER BY 1"""
f = c.sql(q).df(); f["day"] = pd.to_datetime(f.day)
d = pd.read_parquet(daily); d["date"] = pd.to_datetime(d.date); d = d.set_index("date")
f = f.set_index("day").reindex(d.index)
arr_next = d.n_arrivals_24h.shift(-1)
tgt = "n_waiting" if "n_waiting" in d else "n_anchored"
dq = d[tgt].shift(-1) - d[tgt]
res_arr = arr_next - d.n_arrivals_24h.rolling(7).mean()
for col in f.columns:
    x = f[col]
    print(f"{col:10s} mean={x.mean():5.1f}  r(arrivals t+1)={x.corr(arr_next):+.2f}  r(arr t+1 - ma7)={x.corr(res_arr):+.2f}  r(d{tgt} t+1)={x.corr(dq):+.2f}")
print("today's arrivals r(arr t+1)=", round(d.n_arrivals_24h.corr(arr_next),2))
