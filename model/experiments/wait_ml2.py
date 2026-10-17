"""Fair rolling test of carrier-aware wait estimates + ML correction (container-size ships, 2021).
Train for month M only on ships that berthed before M and joined >= LAG days before M (labels known, little censoring).
"""
import sys
import numpy as np, pandas as pd, lightgbm as lgb

S = sys.argv[1]
LAG = 30
v = pd.read_parquet(f"{S}/visits_carrier.parquet").dropna(subset=["little", "reported"])
v = v[v.reported > 0.5].copy()
v["reported_g"] = v.reported_g.fillna(v.reported)          # carrier with no recent berthings: port-wide figure
v["anchor_c"] = v.reported_g + (v.little - v.reported)
v["dow"] = v.join_day.dt.dayofweek
for g in v.grp.unique():
    v[f"g_{g}"] = (v.grp == g).astype(int)
GCOLS = [c for c in v.columns if c.startswith("g_")]
FEATS = ["little", "reported", "reported_g", "little28", "Qb_chg7", "Qb_chg14", "q_trend", "len", "dow"] + GCOLS
v["gap_rg"] = v.reported_g - v.reported
FEATS += ["gap_rg"]


def boot(ea, eb, days, n=2000, seed=0):
    rng = np.random.default_rng(seed); u = np.unique(days); idx = {d: np.where(days == d)[0] for d in u}
    r = [100 * (1 - ea[p].mean() / eb[p].mean()) for p in
         (np.concatenate([idx[d] for d in rng.choice(u, len(u))]) for _ in range(n))]
    return [round(float(np.percentile(r, 5)), 1), round(float(np.percentile(r, 95)), 1)]


rows = []
for m0 in pd.to_datetime(["2021-08-01", "2021-09-01", "2021-10-01", "2021-11-01"]):
    m1 = min(m0 + pd.offsets.MonthBegin(1), pd.Timestamp("2021-11-16"))
    tr = v[(v.t_berth < m0) & (v.join_day < m0 - pd.Timedelta(days=LAG))]
    te = v[(v.join_day >= m0) & (v.join_day < m1)].copy()
    out = {}
    for base in ("reported", "little", "anchor_c"):
        out[base] = te[base]
        out[f"{base}+med"] = te[base] + np.median(tr.wait_d - tr[base])   # 1-parameter calibration
    y = tr.wait_d - tr.anchor_c
    lg = lgb.LGBMRegressor(objective="l1", n_estimators=200, learning_rate=0.03, num_leaves=5, min_child_samples=25,
                           subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, seed=0).fit(tr[FEATS], y)
    out["anchor_c+lgbm"] = te.anchor_c + lg.predict(te[FEATS])
    out["anchor_c+0.5lgbm"] = te.anchor_c + 0.5 * lg.predict(te[FEATS])
    # lambda chosen on TRAINING data only: fit on older training ships, validate on the newest 30 join-days of the
    # training set (labels known by m0), pick lambda in {0, .25, .5, .75, 1}
    cut = m0 - pd.Timedelta(days=LAG + 30)
    itr, iva = tr[tr.join_day < cut], tr[tr.join_day >= cut]
    lam = 0.5
    if len(itr) >= 40 and len(iva) >= 20:
        ilg = lgb.LGBMRegressor(objective="l1", n_estimators=200, learning_rate=0.03, num_leaves=5, min_child_samples=25,
                                subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, seed=0
                                ).fit(itr[FEATS], itr.wait_d - itr.anchor_c)
        ic = ilg.predict(iva[FEATS])
        lam = min((0, .25, .5, .75, 1), key=lambda l: np.mean(np.abs(iva.wait_d - (iva.anchor_c + l * ic))))
    out["anchor_c+lam*lgbm"] = te.anchor_c + lam * lg.predict(te[FEATS])
    print(f"   lambda (training-only) = {lam}")
    p = te[["join_day", "wait_d"]].assign(**{k: np.asarray(s) for k, s in out.items()})
    rows.append(p)
    print(f"{m0:%Y-%m}: train {len(tr)}, test {len(te)}, med offset anchor_c {np.median(tr.wait_d - tr.anchor_c):+.2f}")
p = pd.concat(rows); days = p.join_day.values
print(f"\n{len(p)} container-size ships, {p.join_day.nunique()} join days, mean real wait {p.wait_d.mean():.2f} d")
eb = (p.reported - p.wait_d).abs().values
el = (p.little - p.wait_d).abs().values
for k in [c for c in p.columns if c not in ("join_day", "wait_d")]:
    e = p[k] - p.wait_d
    print(f"{k:18s} MAE {e.abs().mean():5.2f}  bias {e.mean():+5.2f}  vs published {100 * (1 - e.abs().mean() / eb.mean()):+5.1f}% "
          f"{boot(e.abs().values, eb, days)} | vs ours-now {100 * (1 - e.abs().mean() / el.mean()):+5.1f}% {boot(e.abs().values, el, days)}")
