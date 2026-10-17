"""Does the study bbox / ANCHOR_BOX capture the 2021 crisis anchorages (incl. contingency anchorages)?

Usage: python pipeline/check_crisis_box.py data/ext/noaa2021/AIS_2021_10_25.csv
Reads one raw NOAA 2021 daily CSV, keeps cargo/tanker (70-89) at anchor (status 1, sog < 0.5) in a WIDE box,
plots them with our boxes, and counts distinct ships inside vs outside. Writes pipeline/figs/crisis_anchor_check.png.
"""
import sys
import duckdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from build_daily import ANCHOR_BOX

WIDE = dict(lat0=33.0, lat1=34.2, lon0=-119.0, lon1=-117.4)
BBOX = dict(lat0=33.55, lat1=33.80, lon0=-118.35, lon1=-117.95)

f = sys.argv[1]
d = duckdb.sql(f"""
  SELECT MMSI AS mmsi, LAT AS lat, LON AS lon, VesselType AS vt, Length AS len
  FROM read_csv_auto('{f}')
  WHERE VesselType BETWEEN 70 AND 89 AND Status = 1 AND SOG < 0.5
    AND LAT BETWEEN {WIDE['lat0']} AND {WIDE['lat1']} AND LON BETWEEN {WIDE['lon0']} AND {WIDE['lon1']}""").df()
inb = d.lat.between(BBOX["lat0"], BBOX["lat1"]) & d.lon.between(BBOX["lon0"], BBOX["lon1"])
ina = d.lat.between(ANCHOR_BOX["lat0"], ANCHOR_BOX["lat1"]) & d.lon.between(ANCHOR_BOX["lon0"], ANCHOR_BOX["lon1"])
per = d.assign(inb=inb, ina=ina).groupby("mmsi").agg(inb=("inb", "max"), ina=("ina", "max"), vt=("vt", "first"))
print(f"anchored cargo/tanker ships in wide box: {len(per)}; with any ping in study bbox: {per.inb.sum()}; "
      f"in ANCHOR_BOX: {per.ina.sum()}; never inside bbox: {(~per.inb).sum()}")
print("outside-bbox by type:", per[~per.inb].vt.value_counts().to_dict())
fig, ax = plt.subplots(figsize=(11, 8))
ax.scatter(d.lon, d.lat, s=1, c=inb.map({True: "tab:blue", False: "tab:red"}))
for b, c, lab in [(BBOX, "black", "study bbox"), (ANCHOR_BOX, "green", "ANCHOR_BOX")]:
    ax.add_patch(plt.Rectangle((b["lon0"], b["lat0"]), b["lon1"] - b["lon0"], b["lat1"] - b["lat0"], fill=False, ec=c, lw=1.5, label=lab))
ax.set_title(f"{f.split('/')[-1]}: anchored cargo/tanker pings (red = outside study bbox)")
ax.legend(); ax.grid(alpha=.3); ax.set_aspect(1.2)
plt.savefig("pipeline/figs/crisis_anchor_check.png", dpi=80, bbox_inches="tight")
