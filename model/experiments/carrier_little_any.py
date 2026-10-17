"""Per-carrier queue estimate: ships of your carrier group waiting / your group's berthings per day.
Carriers use specific terminals, so this is closer to a ship's own line than the port-wide figure.
Writes visits_carrier.parquet (the 2021 test visits + carrier features) for wait_ml.py.
"""
import sys
from pathlib import Path
import duckdb, numpy as np, pandas as pd

sys.path.insert(0, "model")
from wait_forecast import visits  # noqa: E402

S = Path(sys.argv[1])
AIS, VIN, VOUT, D0, D1, M0, M1 = sys.argv[2], Path(sys.argv[3]), Path(sys.argv[4]), sys.argv[5], sys.argv[6], sys.argv[7], sys.argv[8]
AISN = Path(AIS).name
GROUPS = {"MSC": "MSC", "MAERSK": "MAERSK", "CMA": "CMA", "APL": "CMA", "PRESIDENT": "CMA", "EVER": "EVERGREEN",
          "YM": "YANGMING", "COSCO": "COSCO", "CSCL": "COSCO", "OOCL": "COSCO", "NYK": "ONE", "MOL": "ONE", "ONE": "ONE",
          "HYUNDAI": "HMM", "HMM": "HMM", "WAN": "WANHAI", "ZIM": "ZIM", "MATSON": "MATSON", "HAPAG": "HAPAG"}

names = duckdb.sql(f"""select mmsi, any_value(vessel_name) AS vname from '{AIS}/*.parquet' group by mmsi""").df()
names["grp"] = names.vname.fillna("").str.split().str[0].map(GROUPS).fillna("OTHER")
grp = names.set_index("mmsi").grp

e = pd.read_parquet(f"data/cache/wait_events_{AISN}.parquet")
types = pd.read_parquet(f"data/cache/wait_events_{AISN}.types.parquet")
allv = visits(e).join(types, on="mmsi")
allv["big"] = allv.vt.between(70, 79) & (allv.len >= 200)
allv = allv[allv.big]
allv["grp"] = allv.mmsi.map(grp).fillna("OTHER")
allv["berth_day"] = allv.t_berth.dt.normalize()
allv["join_day"] = allv.t_join.dt.normalize()
days = pd.date_range(D0, D1)

e = e.join(types, on="mmsi")
e = e[e.vt.between(70, 79) & (e.len >= 200)]
last = e[(e.ev == "wait") & (e.t.dt.hour == 23)].assign(day=lambda x: x.t.dt.normalize(), grp=lambda x: x.mmsi.map(grp).fillna("OTHER"))

feat = {}
for g in sorted(allv.grp.unique()):
    Q = last[last.grp == g].groupby("day").mmsi.nunique().reindex(days, fill_value=0)
    vb = allv[allv.grp == g]
    mu14 = vb.groupby("berth_day").size().reindex(days, fill_value=0).rolling(14).mean()
    rp = vb.groupby("berth_day").wait_d.agg(["sum", "count"]).reindex(days, fill_value=0).rolling(14).sum()
    feat[g] = pd.DataFrame({"Q_g": Q, "mu_g": mu14, "little_g": Q / mu14.where(mu14 > 0),
                            "reported_g": rp["sum"] / rp["count"].where(rp["count"] > 0)})
print("berthings per group, Jun-Nov 2021:", allv[allv.berth_day < M1].grp.value_counts().to_dict())

tv = pd.read_parquet(VIN)
tv = tv[tv.big_cargo].copy()
tv["grp"] = tv.mmsi.map(grp).fillna("OTHER")
prev = tv.join_day - pd.Timedelta(days=1)
for c in ("Q_g", "mu_g", "little_g", "reported_g"):
    tv[c] = [feat[g][c].get(d, np.nan) for g, d in zip(tv.grp, prev)]
tv.to_parquet(VOUT)

m = tv[(tv.join_day >= M0) & (tv.join_day <= M1)].dropna(subset=["little", "reported"])
print(f"\ncontainer-size ships joining Aug 1 - Nov 15 2021: {len(m)}")
for k in ("reported", "little", "reported_g", "little_g"):
    x = m.dropna(subset=[k])
    print(f"{k:11s} n={len(x):4d}  MAE {(x[k] - x.wait_d).abs().mean():5.2f}  bias {(x[k] - x.wait_d).mean():+5.2f}"
          f"   (same ships: reported {(x.reported - x.wait_d).abs().mean():5.2f}, little {(x.little - x.wait_d).abs().mean():5.2f})")
both = m.dropna(subset=["little_g"])
print("\nby group (MAE little vs little_g):")
print(both.groupby("grp").apply(lambda x: pd.Series(dict(n=len(x), little=(x.little - x.wait_d).abs().mean(),
      little_g=(x.little_g - x.wait_d).abs().mean(), reported=(x.reported - x.wait_d).abs().mean()))).round(2).to_string())

# port-wide container-size queue with a 14-day berthing rate (less noisy than 7)
Qb = last.groupby("day").mmsi.nunique().reindex(days, fill_value=0)
mu14b = allv.groupby("berth_day").size().reindex(days, fill_value=0).rolling(14).mean()
mu28b = allv.groupby("berth_day").size().reindex(days, fill_value=0).rolling(28).mean()
tv["little14"] = (Qb / mu14b).reindex(prev).values
tv["little28"] = (Qb / mu28b).reindex(prev).values
tv["Qb_chg7"] = (Qb - Qb.shift(7)).reindex(prev).values
tv["Qb_chg14"] = (Qb - Qb.shift(14)).reindex(prev).values
tv["anchor_c"] = tv.reported_g + (tv.little - tv.reported)
tv.to_parquet(VOUT)
for k in ("little14", "little28"):
    x = m.assign(**{k: tv.loc[m.index, k]}).dropna(subset=[k])
    print(f"{k:11s} MAE {(x[k] - x.wait_d).abs().mean():5.2f}  bias {(x[k] - x.wait_d).mean():+5.2f}")
