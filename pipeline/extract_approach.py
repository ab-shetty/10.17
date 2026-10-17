"""Extract cargo/tanker AIS in the APPROACH zone around San Pedro Bay (outside the study bbox), 10-min downsample.

These are tomorrow's arrivals: ships inbound in the shipping lanes, or loitering/slow-steaming offshore.
Usage: python pipeline/extract_approach.py 2024-01-01 [2024-12-31]
Writes data/approach/appr_YYYY-MM-DD.parquet (mmsi, t10, lat, lon, sog, cog, status, draft).
"""
import sys, time, datetime as dt
from pathlib import Path
import duckdb

URL = "https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/ais{y}/ais-{d}.parquet"
LAT, LON = (32.5, 34.6), (-121.0, -117.2)  # ~120 nm around the bay; US receivers reach ~40-60 nm offshore
INNER_LAT, INNER_LON = (33.55, 33.80), (-118.35, -117.95)  # study bbox, already in data/ais
OUT = Path("data/approach")


def main(start, end=None):
    OUT.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    c.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET memory_limit='1GB'; SET threads=2;")
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end or start)
    while d0 <= d1:
        out = OUT / f"appr_{d0}.parquet"
        if not out.exists():
            t, tmp = time.time(), out.with_suffix(".tmp")
            c.execute(f"""
                COPY (
                  WITH p AS (
                    SELECT mmsi, base_date_time AS ts, ST_Y(geometry) AS lat, ST_X(geometry) AS lon,
                           sog, cog, status, draft
                    FROM read_parquet('{URL.format(y=d0.year, d=d0)}')
                    WHERE vessel_type BETWEEN 70 AND 89
                      AND ST_Y(geometry) BETWEEN {LAT[0]} AND {LAT[1]}
                      AND ST_X(geometry) BETWEEN {LON[0]} AND {LON[1]})
                  SELECT mmsi, time_bucket(INTERVAL 10 MINUTE, ts) AS t10,
                         arg_max(lat, ts) AS lat, arg_max(lon, ts) AS lon, arg_max(sog, ts) AS sog,
                         arg_max(cog, ts) AS cog, arg_max(status, ts) AS status, arg_max(draft, ts) AS draft
                  FROM p
                  WHERE NOT (lat BETWEEN {INNER_LAT[0]} AND {INNER_LAT[1]} AND lon BETWEEN {INNER_LON[0]} AND {INNER_LON[1]})
                  GROUP BY 1, 2
                ) TO '{tmp}' (FORMAT parquet)""")
            tmp.rename(out)
            n = c.execute(f"SELECT count(*), count(DISTINCT mmsi) FROM '{out}'").fetchone()
            print(f"{d0}: {n[0]} rows, {n[1]} vessels, {out.stat().st_size/1e6:.2f} MB, {time.time()-t:.1f}s", flush=True)
        d0 += dt.timedelta(days=1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
