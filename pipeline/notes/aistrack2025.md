# NOAA 2025 AIS monthly tracks: findings (partial, see "NOT verified")

URL pattern: https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/ais-track-2025-MM.parquet

## 1. Months that exist (HEAD, all HTTP 200)
All 12 months, 2025-01 to 2025-12. Sizes: 01 1.14 GB, 02 1.08, 03 1.34, 04 1.40, 05 1.60, 06 1.63, 07 1.78, 08 1.72, 09 1.47, 10 1.46, 11 1.43, 12 1.40 GB.

## 2. Exact schema (DuckDB `describe`, 2025-01)
mmsi INTEGER, vessel_name VARCHAR, imo VARCHAR, call_sign VARCHAR, vessel_type INTEGER, vessel_type_name VARCHAR,
status INTEGER, length FLOAT, width INTEGER, draft FLOAT, cargo INTEGER, transceiver VARCHAR,
duration_minutes INTEGER, start_time TIMESTAMP_NS, end_time TIMESTAMP_NS, geometry GEOMETRY('EPSG:4326').

Parquet metadata for 2025-01: 1,508,751 rows, only 2 row groups.
Column stats: start_time 2025-01-01 00:00:00 to 2025-01-31 23:59:53; duration_minutes 0 to 1440 (max one day per track);
status 0 to 14; vessel_type 1 to 255; length 1 to 500; draft 0.1 to 24.
The geometry column is 1,114 MB of the ~1,144 MB file (97%). All other columns together are about 30 MB.

## 3. Per-point timestamps, nav status, sog?
- Per-point timestamps: **no**. Only one `start_time` and one `end_time` per track segment. Segments are at most 1440 min (about 1 day).
  Only the segment endpoints are timed. If the line geometry carries M/Z values, per-vertex times could be recovered. I did not check this.
- Nav status: a **single `status` per segment** (an int, not a time series).
- sog: **no sog column at all.** Speed can only be derived as `ST_Length(geometry in meters) / duration_minutes`, or from vertex spacing.
- Geometry type and vertex count: **NOT verified** (see below).
- Implication: the 2024 definition "status=1 AND sog<0.5 AND inside box" cannot be applied literally.
  The per-segment equivalent is: `status=1` AND segment is nearly stationary AND its centroid/bbox lies inside the anchorage box.

## 4. Tested January 2025 extraction query: NOT verified
I could not complete a query that reads `geometry`. Results:
- Metadata-only queries (describe, parquet_file_metadata, parquet_metadata) work. Each takes about 1 s and costs almost no data.
- Any query that touches `geometry` fails.
  - With `memory_limit='1GB'` DuckDB raised OutOfMemoryException: "could not allocate block of size 719.3 MiB".
    One decoded geometry column chunk is about 720 MB because each row group holds about 750k rows.
  - With `memory_limit='1500MB'`, `threads=1` and `preserve_insertion_order=false`, the process was killed (SIGTERM) after more than 90 s.
    At the time the machine had about 2 GB available. Three `pipeline/extract_ais.py` 2024 background processes use about 3.4 GB RSS together.
    I did not stop them.
- Consequence: the vessel_type and bbox filter cannot be pushed down in a memory-light way.
  The file has no per-row bbox covering column in the stats (geometry stats are None).
  With only 2 row groups, DuckDB must decode a whole 720 MB geometry chunk and cannot skip data.
  A scan streams about 1.1 GB per month and needs roughly 2–3 GB of free RAM.
- Untested query to run once the 2024 pull finishes and RAM is free. Use `SET memory_limit='3GB'; SET threads=1;`
  ```sql
  INSTALL spatial; LOAD spatial; INSTALL httpfs; LOAD httpfs;
  COPY (
    SELECT mmsi, vessel_name, imo, vessel_type, status, length, width, draft,
           duration_minutes, start_time, end_time, geometry
    FROM read_parquet('https://ocmgeodatastor1.blob.core.windows.net/marinecadastre/aistrack/ais-track-2025-01.parquet')
    WHERE vessel_type BETWEEN 70 AND 89
      AND ST_Intersects(geometry, ST_MakeEnvelope(-118.35, 33.55, -117.95, 33.80))
  ) TO 'data/aistrack/2025-01_lalb.parquet' (FORMAT parquet);
  ```
  Notes on the query:
  - `ST_MakeEnvelope` takes (xmin, ymin, xmax, ymax), i.e. lon first.
  - Run it with only one process active.
  - Expect several minutes per month (the 2024 daily pull took 4.5 s per day).
  - Expect a result of at most a few tens of thousands of rows.
  - Row count and timing for this query are **not known**.
- The full 2025 pull is therefore about 12 x 1.1–1.8 GB (about 17 GB) of streamed transfer.
  That is the same order as the 2024 pull, but heavier on RAM.

## 5. Recommendation: daily anchored count from tracks (design only, untested)
1. Extract with the query above for each month. Keep `status`, `start_time`, `end_time`, `duration_minutes` and the geometry.
2. Per segment compute:
   - `len_m` = `ST_Length_Spheroid(geometry)`;
   - `speed_kts` = `len_m / 1852 / (duration_minutes / 60)`;
   - `ST_Centroid(geometry)` and `ST_Extent(geometry)`.
3. Count a segment as anchored if all of these hold:
   - `status = 1`;
   - `speed_kts < 0.5`, or equivalently the extent diagonal is under about 1 nm (the swing circle);
   - the centroid falls in the anchorage box lat 33.58–33.77, lon -118.30 to -117.97, **minus the breakwater and terminal polygon** (use the BERTHS box from CLAUDE.md, or tighter polygons from the 2024 heatmap);
   - `duration_minutes >= 60`.
4. `n_anchored(day)` = `COUNT(DISTINCT mmsi)` per UTC day, over segments that satisfy step 3 and overlap that day. Hours-weighted occupancy is an alternative: `SUM(overlap_minutes)/1440`.
5. Calibrate on January 2024.
   - Build the same metric from the 2024 daily points and from the tracks.
   - Compare n_anchored for Jan 2024 vs Jan 2025 and check the offset.
   - Do this before presenting 2025 as a holdout, because the definitions differ (segment status vs per-ping status).
   - 2024 has no track files.
   - Fallback: compare the track-derived count with the point-derived count over the same box on any overlapping period.
     I did not confirm that any 2024 track file exists, so I did not test this.
6. Caveats:
   - A single `status` per segment can hide transitions.
   - Segments are capped at 1 day, so an anchor stay appears as consecutive segments. Use DISTINCT mmsi per day.
   - There is no hourly resolution.
   - It is only usable for daily features.

## Bottom line
2025 monthly tracks exist for all 12 months and have the schema above. They hold segment-level status and times only, with no sog and no per-ping timestamps.
They are usable only as a coarse daily holdout, after calibration against the 2024 points.
The extraction is RAM-heavy: each month needs a full 1.1 GB geometry scan and about 2–3 GB free.
I could not run it while the 2024 pull is active.
