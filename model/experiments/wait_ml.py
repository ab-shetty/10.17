"""Experiment: can ML predict each ship's wait better than the published figure and queue / berthing rate?

Rolling origin by join month. A ship's wait is only known once it berths, so a model used on the 1st of month M is
trained only on visits with t_berth < M (no peeking). Features = what is known the day before the ship joins.
Scores: per-ship MAE and bias, and skill vs each simple figure with a 90 % CI that resamples JOIN DAYS
(ships joining the same day share an outcome).
"""
import json, sys
import numpy as np, pandas as pd, lightgbm as lgb
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

S = sys.argv[1]
POOL_2024 = "--pool2024" in sys.argv

pw = pd.DataFrame(json.load(open(f"{S}/portwatch/lalb.json")))
pw["date"] = pd.to_datetime(pw.date)
pw = pw.set_index("date").asfreq("D")
pw_c7 = pw.portcalls_container.rolling(7, min_periods=4).mean()
pw_all7 = pw.portcalls.rolling(7, min_periods=4).mean()


def prep(visits, daily, tag):
    v = visits.copy()
    d = pd.DataFrame(daily); d["date"] = pd.to_datetime(d.date); d = d.set_index("date").asfreq("D")
    t = v.join_day - pd.Timedelta(days=1)  # issue day: the evening before the ship joins
    g = lambda s: s.reindex(t).values
    v["Q_big"] = g(d.ships_waiting_eod)
    v["Q_big_chg7"] = g(d.ships_waiting_eod - d.ships_waiting_eod.shift(7))
    v["mu_big"] = g(d.berths_per_day_7d)
    v["rep_trend7"] = g(d.reported_wait_7d - d.reported_wait_7d.shift(7))
    v["lit_trend7"] = g(d.little_wait_d - d.little_wait_d.shift(7))
    v["pw_container_7d"] = pw_c7.reindex(t).values
    v["pw_calls_7d"] = pw_all7.reindex(t).values
    v["pw_trend"] = (pw_c7 - pw_c7.shift(14)).reindex(t).values
    v["gap"] = v.little - v.reported
    v["tanker"] = v.vt.between(80, 89).astype(int)
    v["dow"] = v.join_day.dt.dayofweek
    v["dataset"] = tag
    v["is2024"] = int(tag == "2024")
    return v


FEATS = ["is2024", "little", "reported", "gap", "q_trend", "Q_big", "Q_big_chg7", "mu_big", "rep_trend7", "lit_trend7",
         "pw_container_7d", "pw_calls_7d", "pw_trend", "big_cargo", "len", "tanker", "dow"]

vc = prep(pd.read_parquet(f"{S}/visits_crisis.parquet"), json.load(open(f"{S}/wait_crisis_wide.json"))["daily"], "2021")
v24 = prep(pd.read_parquet("data/cache/wait_visits_ais.parquet"), json.load(open("shared/wait.json"))["daily"], "2024")
LAG = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--lag=")), 30))
vc["big_cargo"] = vc.big_cargo.astype(int); v24["big_cargo"] = v24.big_cargo.astype(int)


def models(tr, X):
    tr = tr[(tr.little > 0.5) & (tr.reported > 0.5)]
    # relative target: log(real / anchor). Scale-free, so it carries over when waits grow; anchor = ours (little) or
    # the geometric mean of ours and published.
    out = {}
    lg_args = dict(objective="l1", n_estimators=300, learning_rate=0.03, num_leaves=7, min_child_samples=20,
                   subsample=0.8, subsample_freq=1, colsample_bytree=0.8, verbose=-1, seed=0)
    feats = [f for f in FEATS if f not in ("little", "reported", "Q_big", "mu_big", "pw_container_7d", "pw_calls_7d")]
    feats += ["log_gap"]
    for nm, anc_tr, anc_x in (("L", tr.little, X.little.clip(lower=0.5)),
                              ("G", np.sqrt(tr.little * tr.reported), np.sqrt(X.little.clip(lower=0.5) * X.reported.clip(lower=0.5)))):
        y = np.log(tr.wait_d / anc_tr)
        Xt = tr.assign(log_gap=np.log(tr.little / tr.reported))[feats]
        Xx = X.assign(log_gap=np.log(X.little.clip(lower=0.5) / X.reported.clip(lower=0.5)))[feats]
        lg = lgb.LGBMRegressor(**lg_args).fit(Xt, y)
        rg = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=30)).fit(Xt, y)
        out[f"lgbm_{nm}"] = anc_x * np.exp(lg.predict(Xx))
        out[f"ridge_{nm}"] = anc_x * np.exp(rg.predict(Xx))
        out[f"anchor_{nm}"] = anc_x
    grid = np.linspace(0, 1.5, 31)
    w = min(grid, key=lambda w: np.mean(np.abs(tr.wait_d - (tr.reported + w * tr.gap))))
    out["blend"] = X.reported + w * X.gap
    return out, w


def boot(err_a, err_b, days, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    u = np.unique(days); idx = {d: np.where(days == d)[0] for d in u}
    res = []
    for _ in range(n):
        pick = np.concatenate([idx[d] for d in rng.choice(u, len(u))])
        res.append(100 * (1 - err_a[pick].mean() / err_b[pick].mean()))
    return [round(float(np.percentile(res, 5)), 1), round(float(np.percentile(res, 95)), 1)]


def run(test_months, label):
    allv = vc.sort_values("t_join").reset_index(drop=True)
    preds, ws = [], []
    for m0 in pd.to_datetime(test_months):
        m1 = m0 + pd.offsets.MonthBegin(1)
        # labels known by m0 AND joined >= LAG days earlier (otherwise only the quick ones are known: censoring)
        tr = allv[(allv.t_berth < m0) & (allv.join_day < m0 - pd.Timedelta(days=LAG))]
        if POOL_2024:  # another year, all of it (a different regime; flagged by `dataset`)
            tr = pd.concat([tr, v24])
        te = allv[(allv.join_day >= m0) & (allv.join_day < m1)]
        if len(tr) < 80 or te.empty:
            print(label, m0.date(), "skip (train", len(tr), ")"); continue
        out, w = models(tr, te); ws.append(round(w, 2))
        p = te[["join_day", "wait_d", "reported", "little", "big_cargo"]].copy()
        for k, s in out.items():
            p[k] = s.values
        preds.append(p)
        print(f"{label} {m0:%Y-%m}: train {len(tr)} (berthed before), test {len(te)}, blend w={w:.2f}")
    p = pd.concat(preds)
    days = p.join_day.values
    print(f"\n=== {label}: {len(p)} ships, {p.join_day.nunique()} join days; mean real wait {p.wait_d.mean():.2f} d")
    for k in ("reported", "little", "blend", "anchor_G", "lgbm_L", "ridge_L", "lgbm_G", "ridge_G"):
        e = (p[k] - p.wait_d)
        line = f"{k:9s} MAE {e.abs().mean():5.2f}  bias {e.mean():+5.2f}"
        if k not in ("reported", "little"):
            for ref in ("reported", "little"):
                line += f" | vs {ref} {100 * (1 - e.abs().mean() / (p[ref] - p.wait_d).abs().mean()):+5.1f}% " \
                        f"{boot(e.abs().values, (p[ref] - p.wait_d).abs().values, days)}"
        print(line)
    # daily mean of container-size ships (what a port would publish)
    b = p[p.big_cargo == 1].groupby("join_day").mean(numeric_only=True)
    print("daily mean, container-size:", {k: round(float((b[k] - b.wait_d).abs().mean()), 2) for k in
                                         ("reported", "little", "blend", "anchor_G", "lgbm_L", "ridge_L", "lgbm_G", "ridge_G")})
    return p


if __name__ == "__main__":
    tag = ("pooled 2024" if POOL_2024 else "2021 only") + f", lag {LAG} d"
    run(["2021-08-01", "2021-09-01", "2021-10-01", "2021-11-01"], f"crisis Aug-Nov15 2021 ({tag})")
