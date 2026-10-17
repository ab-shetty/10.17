"""Extract San Pedro Bay AIS from NOAA's 2021-2023 daily zipped CSVs (the GeoParquet series is 2024 only).

Usage: python pipeline/extract_csv2021.py 2021-06-01 2022-03-31
Per day: download AIS_YYYY_MM_DD.zip (~330 MB), unzip to a temp CSV, write
  data/ais_crisis/ais_lalb_YYYY-MM-DD.parquet       study bbox, full cadence, same schema as data/ais/
  data/approach_crisis/appr_YYYY-MM-DD.parquet      approach zone outside the bbox, 10-min, same as extract_approach.py
then delete the zip + CSV. Skips days already done; writes via .tmp + rename. Workers claim a day with an atomic
lock file (data/tmp_csv/DATE.lock), so several can run over the same range. Delete stale locks after a crash.
"""
import os, sys, time, subprocess, datetime as dt
from pathlib import Path
import duckdb

URL = "https://coast.noaa.gov/htdata/CMSP/AISDataHandler/{y}/AIS_{y}_{m:02d}_{d:02d}.zip"
LAT, LON = (33.55, 33.80), (-118.35, -117.95)
A_LAT, A_LON = (32.5, 34.6), (-121.0, -117.2)
import os  # noqa: E402
# AIS_OUT / APPR_OUT override the output folders (e.g. a 2023 calm-period pull that must not mix with the crisis set)
OUT = Path(os.environ.get("AIS_OUT", "data/ais_crisis"))
AOUT = Path(os.environ.get("APPR_OUT", "data/approach_crisis"))
TMP = Path("data/tmp_csv")


def one_day(c, d0, out, aout, lock):
    t = time.time()
    z = TMP / f"{d0}.zip"
    subprocess.run(["curl", "-s", "--fail", "--retry", "5", "--retry-all-errors", "--max-time", "900", "-o", str(z),
                    URL.format(y=d0.year, m=d0.month, d=d0.day)], check=True)
    csv = subprocess.run(["unzip", "-Z1", str(z)], capture_output=True, text=True, check=True).stdout.split()[0]
    subprocess.run(["unzip", "-o", "-q", str(z), "-d", str(TMP / str(d0))], check=True)
    f = TMP / str(d0) / csv
    c.execute(f"""CREATE OR REPLACE TEMP TABLE r AS
      SELECT MMSI AS mmsi, BaseDateTime::TIMESTAMP AS ts, LAT AS lat, LON AS lon, SOG::FLOAT AS sog,
             COG::FLOAT AS cog, Heading::INT AS heading, VesselName AS vessel_name, IMO AS imo,
             VesselType::INT AS vessel_type, Status::INT AS status, Length::FLOAT AS length,
             Width::INT AS width, Draft::FLOAT AS draft
      FROM read_csv_auto('{f}', ignore_errors=true)
      WHERE VesselType BETWEEN 70 AND 89 AND LAT BETWEEN {A_LAT[0]} AND {A_LAT[1]}
        AND LON BETWEEN {A_LON[0]} AND {A_LON[1]}""")
    inb = f"lat BETWEEN {LAT[0]} AND {LAT[1]} AND lon BETWEEN {LON[0]} AND {LON[1]}"
    c.execute(f"COPY (SELECT * FROM r WHERE {inb}) TO '{out.with_suffix('.tmp')}' (FORMAT parquet)")
    c.execute(f"""COPY (
      SELECT mmsi, time_bucket(INTERVAL 10 MINUTE, ts) AS t10, arg_max(lat, ts) AS lat, arg_max(lon, ts) AS lon,
             arg_max(sog, ts) AS sog, arg_max(cog, ts) AS cog, arg_max(status, ts) AS status,
             arg_max(draft, ts) AS draft
      FROM r WHERE NOT ({inb}) GROUP BY 1, 2) TO '{aout.with_suffix('.tmp')}' (FORMAT parquet)""")
    out.with_suffix(".tmp").rename(out)
    aout.with_suffix(".tmp").rename(aout)
    subprocess.run(["rm", "-rf", str(z), str(TMP / str(d0)), str(lock)], check=True)
    n = c.execute(f"SELECT count(DISTINCT mmsi) FROM '{out}'").fetchone()[0]
    print(f"{d0}: {n} vessels in bbox, {time.time() - t:.0f}s", flush=True)


def main(start, end=None):
    for p in (OUT, AOUT, TMP):
        p.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    c.execute("SET memory_limit='2GB'; SET threads=2;")
    d0, d1 = dt.date.fromisoformat(start), dt.date.fromisoformat(end or start)
    while d0 <= d1:
        out, aout = OUT / f"ais_lalb_{d0}.parquet", AOUT / f"appr_{d0}.parquet"
        lock = TMP / f"{d0}.lock"
        if not (out.exists() and aout.exists()):
            try:  # atomic claim: several workers can share one date range without clobbering each other
                os.close(os.open(lock, os.O_CREAT | os.O_EXCL))
            except FileExistsError:
                d0 += dt.timedelta(days=1)
                continue
            for attempt in range(4):  # NOAA resets connections; one bad day must not kill the worker
                try:
                    one_day(c, d0, out, aout, lock)
                    break
                except Exception as e:
                    print(f"{d0}: attempt {attempt + 1} failed: {e.__class__.__name__}: {str(e)[:120]}", flush=True)
                    subprocess.run(["rm", "-rf", str(TMP / f"{d0}.zip"), str(TMP / str(d0)),
                                    str(out.with_suffix(".tmp")), str(aout.with_suffix(".tmp"))])
                    time.sleep(10 * (attempt + 1))
            else:
                print(f"{d0}: GAVE UP after 4 attempts", flush=True)
            lock.unlink(missing_ok=True)
        d0 += dt.timedelta(days=1)


if __name__ == "__main__":
    main(*sys.argv[1:3])
