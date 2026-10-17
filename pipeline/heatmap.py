"""Heatmap of status=1 (at anchor), sog<0.5 pings vs status=5 (moored) to place ANCHORAGE/BERTHS boxes."""
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from glob import glob
import pyarrow.parquet as pq


def valid(f):
    try:
        pq.ParquetFile(f); return True
    except Exception:
        return False


files = [f for f in sorted(glob("data/ais/*.parquet")) if valid(f)]

q = f"""SELECT lat, lon, status FROM read_parquet({files})
       WHERE (status = 1 AND sog < 0.5) OR status = 5 USING SAMPLE 400000"""
d = duckdb.sql(q).df()
fig, ax = plt.subplots(1, 2, figsize=(16, 7), sharey=True)
for a, s, name in [(ax[0], 1, "status=1 at anchor, sog<0.5"), (ax[1], 5, "status=5 moored")]:
    x = d[d.status == s]
    a.hist2d(x.lon, x.lat, bins=[300, 200], range=[[-118.35, -117.95], [33.55, 33.80]], cmap="magma", norm="log")
    a.set_title(f"{name} (n={len(x)})")
    a.set_xticks(np.arange(-118.35, -117.94, 0.05)); a.set_yticks(np.arange(33.55, 33.81, 0.025)); a.grid(alpha=.3)
    for (la0, la1, lo0, lo1), c in [((33.60, 33.72, -118.30, -118.05), "cyan"), ((33.72, 33.78, -118.29, -118.15), "lime")]:
        a.add_patch(plt.Rectangle((lo0, la0), lo1 - lo0, la1 - la0, fill=False, ec=c, lw=1.5))
plt.tight_layout(); plt.savefig("pipeline/figs/heatmap_status.png", dpi=90)
