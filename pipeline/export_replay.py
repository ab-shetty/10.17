"""Export map-replay JSON for story days: shared/replay/YYYY-MM-DD.json.

Usage: python pipeline/export_replay.py 2024-10-05 [2024-10-06 ...]
Rows: {mmsi, name, t, lat, lon, status, sog, state}, one per vessel per 10 min (last ping in the bucket).
`status` is raw AIS nav status; `state` is our derived class (anchored | moored | underway), the same
definitions build_daily.py counts, so the map and the chart agree. Run build_daily.py first (berth mask).
"""
import json
import sys
from pathlib import Path
import duckdb

from build_daily import ANCHOR_BOX, CELL

OUT = Path("shared/replay")


def export(day):
    b = ANCHOR_BOX
    rows = duckdb.sql(f"""
      WITH p AS (
        SELECT *, time_bucket(INTERVAL 10 MINUTE, ts) AS t10,
               floor(lat/{CELL})::INT AS cy, floor(lon/{CELL})::INT AS cx
        FROM 'data/ais/ais_lalb_{day}.parquet'),
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
    OUT.mkdir(parents=True, exist_ok=True)
    f = OUT / f"{day}.json"
    f.write_text(json.dumps(json.loads(rows.to_json(orient="records"))))
    print(f"{f}: {len(rows)} rows, {rows.mmsi.nunique()} vessels, {f.stat().st_size/1e3:.0f} KB")


if __name__ == "__main__":
    for day in sys.argv[1:]:
        export(day)
