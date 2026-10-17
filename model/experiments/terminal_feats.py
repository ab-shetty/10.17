"""Terminal-level wait features.
usage: terminal_feats.py SCRATCH AIS_DIR VISITS_CARRIER_IN OUT D0 D1
1) berth position of every container-size visit (median of moored pings in the 3 h after berthing)
2) terminals = KMeans(12) on those positions (fit per dataset; positions only, no outcome)
3) predicted terminal of a ship ON THE DAY IT JOINS, from information known then:
   its own last terminal if it berthed here in the previous 120 days, else its carrier's most frequent terminal over the
   previous 60 days of berthings, else unknown
4) per terminal, as of the evening before the ship joins: ships waiting whose predicted terminal is T (Q_T), berthings
   at T per day (mu_T, 28-day mean), recent mean wait of ships that berthed at T (rep_T, 28 days), little_T = Q_T / mu_T
"""
import sys
from pathlib import Path
import duckdb, numpy as np, pandas as pd
from sklearn.cluster import KMeans

sys.path.insert(0, "model")
from wait_forecast import visits  # noqa: E402

S, AIS, VIN, VOUT, D0, D1 = Path(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6]
AISN = Path(AIS).name
GROUPS = {"MSC": "MSC", "MAERSK": "MAERSK", "CMA": "CMA", "APL": "CMA", "PRESIDENT": "CMA", "EVER": "EVERGREEN",
          "YM": "YANGMING", "COSCO": "COSCO", "CSCL": "COSCO", "OOCL": "COSCO", "NYK": "ONE", "MOL": "ONE", "ONE": "ONE",
          "HYUNDAI": "HMM", "HMM": "HMM", "WAN": "WANHAI", "ZIM": "ZIM", "MATSON": "MATSON", "HAPAG": "HAPAG"}

e = pd.read_parquet(f"data/cache/wait_events_{AISN}.parquet")
types = pd.read_parquet(f"data/cache/wait_events_{AISN}.types.parquet")
allv = visits(e).join(types, on="mmsi")
allv = allv[allv.vt.between(70, 79) & (allv.len >= 200)].reset_index(drop=True)
allv["vid"] = np.arange(len(allv))

c = duckdb.connect()
c.execute("SET memory_limit='4GB'")
c.register("vv", allv[["vid", "mmsi", "t_berth"]])
pos = c.sql(f"""
  SELECT vv.vid, median(a.lat) AS blat, median(a.lon) AS blon
  FROM vv JOIN read_parquet('{AIS}/*.parquet') a
    ON a.mmsi = vv.mmsi AND a.ts BETWEEN vv.t_berth AND vv.t_berth + INTERVAL 3 HOUR
  WHERE a.sog < 0.5
  GROUP BY 1""").df()
names = c.sql(f"select mmsi, any_value(vessel_name) AS vname from read_parquet('{AIS}/*.parquet') group by mmsi").df()
allv = allv.merge(pos, on="vid", how="left").dropna(subset=["blat"])
km = KMeans(12, n_init=10, random_state=0).fit(np.c_[allv.blat, allv.blon * np.cos(np.radians(33.75))])
allv["term"] = km.labels_
allv["grp"] = allv.mmsi.map(names.set_index("mmsi").vname.fillna("").str.split().str[0].map(GROUPS)).fillna("OTHER")
allv["berth_day"] = allv.t_berth.dt.normalize()
allv["join_day"] = allv.t_join.dt.normalize()
print(f"{len(allv)} container-size visits with a berth position; visits per terminal:",
      allv.term.value_counts().sort_index().to_dict())
# how predictable is the terminal? same terminal as the ship's previous visit / as its carrier's mode
allv = allv.sort_values("t_berth").reset_index(drop=True)


def predicted_terminal(mmsi, grp, day):
    """Known on `day` (berthings strictly before it)."""
    past = allv[allv.t_berth < day]
    own = past[(past.mmsi == mmsi) & (past.t_berth >= day - pd.Timedelta(days=120))]
    if len(own):
        return int(own.term.iloc[-1]), "own"
    g = past[(past.grp == grp) & (past.t_berth >= day - pd.Timedelta(days=60))]
    if grp != "OTHER" and len(g) >= 3:
        return int(g.term.mode().iloc[0]), "carrier"
    return -1, "unknown"


pt = [predicted_terminal(m, g, d) for m, g, d in zip(allv.mmsi, allv.grp, allv.join_day)]
allv["pterm"], allv["psrc"] = [p[0] for p in pt], [p[1] for p in pt]
k = allv[allv.pterm >= 0]
print("terminal prediction source:", allv.psrc.value_counts().to_dict(),
      f"| correct when known: {(k.pterm == k.term).mean():.0%} (own {(k[k.psrc=='own'].pterm == k[k.psrc=='own'].term).mean():.0%}, "
      f"carrier {(k[k.psrc=='carrier'].pterm == k[k.psrc=='carrier'].term).mean():.0%})")

# per-terminal daily series. Waiting ships' predicted terminals come from their visit rows (pterm at their join).
days = pd.date_range(D0, D1)
types_big = types[(types.vt.between(70, 79)) & (types.len >= 200)].index
last = e[(e.ev == "wait") & (e.t.dt.hour == 23) & e.mmsi.isin(types_big)].assign(day=lambda x: x.t.dt.normalize())
# map each (mmsi, day) of waiting to the visit it belongs to: the visit with t_join <= day <= t_berth
iv = allv[["mmsi", "t_join", "t_berth", "pterm"]]
lw = last.drop_duplicates(["mmsi", "day"]).merge(iv, on="mmsi")
lw = lw[(lw.day >= lw.t_join.dt.normalize()) & (lw.day <= lw.t_berth)]
ser = {}
for T in range(12):
    QT = lw[lw.pterm == T].groupby("day").mmsi.nunique().reindex(days, fill_value=0)
    b = allv[allv.term == T]
    muT = b.groupby("berth_day").size().reindex(days, fill_value=0).rolling(28).mean()
    rp = b.groupby("berth_day").wait_d.agg(["sum", "count"]).reindex(days, fill_value=0).rolling(28).sum()
    ser[T] = pd.DataFrame({"Q_T": QT, "mu_T": muT, "rep_T": rp["sum"] / rp["count"].where(rp["count"] > 0)})
    ser[T]["little_T"] = ser[T].Q_T / ser[T].mu_T.where(ser[T].mu_T > 0)

tv = pd.read_parquet(VIN)
tv = tv.merge(allv[["mmsi", "t_join", "term", "pterm", "psrc"]], on=["mmsi", "t_join"], how="left")
prev = tv.join_day - pd.Timedelta(days=1)
for col in ("Q_T", "mu_T", "rep_T", "little_T"):
    tv[col] = [ser[int(T)][col].get(d, np.nan) if pd.notna(T) and T >= 0 else np.nan for T, d in zip(tv.pterm, prev)]
tv.to_parquet(VOUT)
m = tv.dropna(subset=["little", "reported"])
m = m[m.join_day >= pd.Timestamp(D0) + pd.Timedelta(days=60)]
known = m.dropna(subset=["little_T", "rep_T"])
print(f"\ntest-able ships: {len(m)}, with a predicted terminal + terminal history: {len(known)}")
for kk in ("reported", "little", "reported_g", "rep_T", "little_T"):
    x = known.dropna(subset=[kk])
    print(f"{kk:10s} n={len(x)} MAE {(x[kk] - x.wait_d).abs().mean():5.2f} bias {(x[kk] - x.wait_d).mean():+5.2f}")
