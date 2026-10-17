"""Export map-replay JSON for story days: shared/replay/YYYY-MM-DD.json.

Usage: python pipeline/export_replay.py 2024-10-05 [2024-10-06 ...]
Rows: {mmsi, name, t, lat, lon, status, sog, state}, one per vessel per 10 min (last ping in the bucket).
`status` is raw AIS nav status; `state` is our derived class (anchored | moored | underway), the same
definitions build_daily.py counts, so the map and the chart agree. Run build_daily.py first (berth mask).
If data/approach/ has the day, ships within 60 nm OUTSIDE the study bbox are added with state
inbound (>= 6 kn, course within 30 deg of the bay) | waiting_offshore (< 3 kn) | passing (the rest): the same
definitions as the model's inbound_60nm / offshore_waiting features. "We see them coming."
"""
import json
import sys
from pathlib import Path
import duckdb
import pandas as pd

from build_daily import ANCHOR_BOX, CELL

OUT = Path("shared/replay")


def export(day, ais_dir="data/ais", approach_dir="data/approach", out_dir=OUT):
    b = ANCHOR_BOX
    rows = duckdb.sql(f"""
      WITH p AS (
        SELECT *, time_bucket(INTERVAL 10 MINUTE, ts) AS t10,
               floor(lat/{CELL})::INT AS cy, floor(lon/{CELL})::INT AS cx
        FROM '{ais_dir}/ais_lalb_{day}.parquet'),
      s AS (
        SELECT p.*, CASE
          WHEN status = 1 AND sog < 0.5 AND bc.cy IS NULL AND lat BETWEEN {b['lat0']} AND {b['lat1']}
               AND lon BETWEEN {b['lon0']} AND {b['lon1']} THEN 'anchored'
          WHEN (status = 5 OR sog < 0.5) AND bc.cy IS NOT NULL THEN 'moored'
          ELSE 'underway' END AS state
        FROM p LEFT JOIN 'data/berth_cells.parquet' bc USING (cy, cx))
      SELECT mmsi, any_value(vessel_name) AS name, strftime(t10, '%Y-%m-%dT%H:%M:00Z') AS t,
             round(arg_max(lat, ts), 5) AS lat, round(arg_max(lon, ts), 5) AS lon,
             arg_max(status, ts) AS status, round(arg_max(sog, ts)::DOUBLE, 1) AS sog, arg_max(state, ts) AS state
      FROM s GROUP BY mmsi, t10 ORDER BY t10, mmsi""").df()
    appr = Path(f"{approach_dir}/appr_{day}.parquet")
    if appr.exists():
        ap = duckdb.sql(f"""
          WITH x AS (
            SELECT *, sqrt(power((lat - 33.70) * 60, 2) + power((lon + 118.20) * 60 * cos(radians(33.7)), 2)) AS nm,
                   (degrees(atan2((-118.20 - lon) * cos(radians(33.7)), 33.70 - lat)) + 360) % 360 AS brg
            FROM '{appr}'),
          names AS (SELECT mmsi, any_value(vessel_name) AS name FROM '{ais_dir}/*.parquet' GROUP BY 1)
          SELECT x.mmsi, names.name, strftime(t10, '%Y-%m-%dT%H:%M:00Z') AS t, round(lat, 5) AS lat, round(lon, 5) AS lon,
                 status, round(sog::DOUBLE, 1) AS sog,
                 CASE WHEN sog >= 6 AND abs(((cog - brg + 540) % 360) - 180) < 30 THEN 'inbound'
                      WHEN sog < 3 THEN 'waiting_offshore' ELSE 'passing' END AS state
          FROM x LEFT JOIN names USING (mmsi) WHERE nm < 60""").df()
        rows = pd.concat([rows, ap]).sort_values(["t", "mmsi"])
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    f = out_dir / f"{day}.json"
    f.write_text(json.dumps(json.loads(rows.to_json(orient="records"))))
    print(f"{f}: {len(rows)} rows, {rows.mmsi.nunique()} vessels, {f.stat().st_size/1e3:.0f} KB")


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("days", nargs="+")
    a.add_argument("--ais-dir", default="data/ais")
    a.add_argument("--approach-dir", default="data/approach")
    a.add_argument("--out-dir", default=str(OUT))
    x = a.parse_args()
    for day in x.days:
        export(day, x.ais_dir, x.approach_dir, x.out_dir)
