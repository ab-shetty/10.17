"""Extract San Pedro Bay (LA/Long Beach) cargo+tanker AIS points from NOAA daily GeoParquet.

Usage: python pipeline/extract_ais.py 2024-01-01 [2024-01-31]
Writes data/ais/ais_lalb_YYYY-MM-DD.parquet per day (skips days already done).
"""
import sys, time, datetime as dt
from pathlib import Path
import duckdb

URL = "https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/ais{y}/ais-{d}.parquet"
LAT, LON = (33.55, 33.80), (-118.35, -117.95)
OUT = Path("data/ais")


def main(start, end=None):
    OUT.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    c.execute("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial; SET memory_limit='1GB'; SET threads=2;")
    d0 = dt.date.fromisoformat(start)
    d1 = dt.date.fromisoformat(end or start)
    while d0 <= d1:
        out = OUT / f"ais_lalb_{d0}.parquet"
        if not out.exists():
            t = time.time()
            c.execute(f"""
                COPY (
                  SELECT mmsi, base_date_time AS ts, ST_Y(geometry) AS lat, ST_X(geometry) AS lon,
                         sog, cog, heading, vessel_name, imo, vessel_type, status, length, width, draft
                  FROM read_parquet('{URL.format(y=d0.year, d=d0)}')
                  WHERE vessel_type BETWEEN 70 AND 89
                    AND ST_Y(geometry) BETWEEN {LAT[0]} AND {LAT[1]}
                    AND ST_X(geometry) BETWEEN {LON[0]} AND {LON[1]}
                ) TO '{out}' (FORMAT parquet)""")
            n = c.execute(f"SELECT count(*), count(DISTINCT mmsi) FROM '{out}'").fetchone()
            print(f"{d0}: {n[0]} rows, {n[1]} vessels, {out.stat().st_size/1e6:.2f} MB, {time.time()-t:.1f}s", flush=True)
        d0 += dt.timedelta(days=1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
