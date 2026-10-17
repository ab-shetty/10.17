"""Experiment grid for the rolling-origin forecaster (orders: model/GPU_ORDERS.md). Imports from train, copies no logic.

  python model/grid.py design   # random + one-at-a-time grid on the design window (2024-04..09), checkpointed
  python model/grid.py final    # top 3 (by design mean skill) + default: seeds, test window, crisis (run once)

Protocol: rolling-origin as in train.main(rolling=True); configs are chosen ONLY on the design window.
"""
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from itertools import product
from pathlib import Path

os.environ.setdefault("OMP_NUM_THREADS", "1")
sys.path.insert(0, str(Path(__file__).parent))
import numpy as np
import pandas as pd
import lightgbm as lgb
from catboost import CatBoostRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
import train

ROOT = Path(__file__).resolve().parents[1]
IN = ROOT / "model" / "inputs"
OUT = ROOT / "data" / "grid"
HZ = (1, 2, 3)
WIN = dict(design=("2024-04-01", "2024-09-30"), test=("2024-10-01", "2024-12-31"),
           crisis=("2021-09-01", None), crisis_pre=("2021-09-01", "2021-11-15"))
GROUPS = {
    "fc": ["fc_gust_target", "fc_gust_tomorrow"],
    "obs_weather": ["wind_max_kts", "gust_max_kts", "visibility_min_m", "wind_max_3d"],
    "wave_fog": ["klgb_vis_min_mi", "klgb_fog_hours", "wave_hs_max_m", "wave_period_max_s"],
    "approach": ["offshore_waiting", "inbound_60nm", "inbound_eta24", "inbound_60_140"],
    "lags": ["anchored_chg_1d", "anchored_chg_2d", "anchored_chg_3d", "anchored_chg_7d", "anchored_vs_7d_mean"],
    "arr_dep": ["arrivals_24h", "arrivals_48h", "departures_yday", "net_inflow_3d"],
}
DEFAULT = dict(data="v2", shrink=0, lgb=dict(num_leaves=7, n_estimators=300, learning_rate=0.03, min_child_samples=15),
               cat=dict(depth=4, iterations=500, l2_leaf_reg=5), ridge=30.0, ens="lgbm+cat+ridge", drop=None,
               window="all", seed=0)
CFG = DEFAULT  # set per worker call; read by the patched fit_all / predict


def fit_all(X, y):
    c, m = CFG, {}
    mem = c["ens"].split("+") if c["ens"] != "median3" else ["lgbm", "cat", "ridge"]
    if "lgbm" in mem:
        m["lgbm"] = lgb.LGBMRegressor(**{**train.PARAMS, **c["lgb"], "seed": c["seed"], "n_jobs": 1}).fit(X, y)
    if "cat" in mem:
        m["cat"] = CatBoostRegressor(loss_function="MAE", learning_rate=0.03, random_seed=c["seed"], verbose=0,
                                     thread_count=1, **c["cat"]).fit(X, y)
    if "ridge" in mem:
        m["ridge"] = make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=c["ridge"])).fit(X, y)
    return m


def predict(models, name, X):
    p = np.array([m.predict(X) for m in models.values()])
    return np.median(p, axis=0) if CFG["ens"] == "median3" else p.mean(axis=0)


def load(data, target):
    """Mirror train.main's loading + joins."""
    if target == "n_waiting":
        d, w = pd.read_parquet(IN / "crisis" / "daily_a.parquet"), ["crisis/weather_daily", "crisis/ext_daily"]
    else:
        d, w = pd.read_parquet(IN / ("daily_v2.parquet" if data == "v2" else "daily.parquet")), ["weather_daily", "ext_daily"]
    if target == "n_waiting" and "n_waiting" not in d:
        d["n_waiting"] = d.n_anchored + d.offshore_waiting
    d["date"] = pd.to_datetime(d.date)
    d = d.set_index("date").sort_index().asfreq("D")
    for wf in w:
        x = pd.read_parquet(IN / f"{wf}.parquet")
        x.index = pd.to_datetime(x.date)
        d = d.drop(columns=[c for c in x.columns if c in d.columns and c != "date"]).join(x.drop(columns="date"))
    return d


def evaluate(cfg, target, win):
    """Rolling-origin skill per horizon vs the best naive baseline (same logic as train.main, rolling=True)."""
    global CFG
    CFG = cfg
    train.TARGET = target
    train.fit_all, train.predict = fit_all, predict  # shrink_factor calls these through the module
    d = load(cfg["data"], target)
    t0 = pd.Timestamp(WIN[win][0])
    t1 = pd.Timestamp(WIN[win][1]) if WIN[win][1] else d.index.max()
    X = train.features(d)
    base_all = train.baselines(d[target], d.get(f"{target}_eod"))
    names, res = tuple(base_all), {}
    for h in HZ:
        Xh = X.copy()
        Xh["target_dow"] = (d.index + pd.Timedelta(days=h)).dayofweek
        if f"fc{h}_gust_max_kts" in d and d[f"fc{h}_gust_max_kts"].notna().mean() > 0.5:
            Xh["fc_gust_target"] = d[f"fc{h}_gust_max_kts"].shift(-h)
            Xh["fc_gust_tomorrow"] = d["fc1_gust_max_kts"].shift(-1)
        Xh = Xh.drop(columns=[c for c in train.HIDDEN if c in Xh and False])  # hidden only affects display
        if cfg["drop"]:
            Xh = Xh.drop(columns=[c for c in GROUPS[cfg["drop"]] if c in Xh])
        y_fut = d[target].shift(-h)
        tgt = d.index + pd.Timedelta(days=h)
        ok = y_fut.notna() & base_all["blend"].notna()
        tr = ok & (tgt < t0)
        anchor = base_all[min(names, key=lambda k: train.mae(base_all[k][tr], y_fut[tr]))]
        dy = y_fut - anchor
        te = ok & (tgt >= t0) & (tgt <= t1)
        act, pred = y_fut[te], pd.Series(np.nan, index=y_fut[te].index)
        for m0 in pd.date_range(t0, t1, freq="MS"):
            f = te & (tgt >= m0) & (tgt < m0 + pd.DateOffset(months=1))
            if not f.any():
                continue
            fit = ok & (tgt < m0)
            if cfg["window"] == "6m":
                fit &= tgt >= m0 - pd.DateOffset(months=6)
            lam = train.shrink_factor(Xh, dy, ok, tgt, m0, months=cfg["shrink"]) if cfg["shrink"] else 1.0
            pred[f[f].index] = anchor[f] + lam * predict(fit_all(Xh[fit], dy[fit]), "avg", Xh[f])
        tb = {k: train.mae(base_all[k][te], act) for k in names}
        best = min(names, key=tb.get)
        em, eb = np.abs(pred - act).values, np.abs(base_all[best][te] - act).values
        res[h] = dict(skill=100 * (1 - em.mean() / eb.mean()), ci=train.block_bootstrap_skill(em, eb), mae=float(em.mean()),
                      mae_base=float(eb.mean()), base=best, n=int(te.sum()),
                      skill_persist=100 * (1 - em.mean() / tb["persistence"]),
                      skill_daymean=100 * (1 - em.mean() / min(tb[k] for k in train.BASELINES)))
    return res


def run_one(args):
    cid, cfg, target, win = args
    t = time.time()
    try:
        r = evaluate(cfg, target, win)
    except Exception as e:  # keep the grid going; the error lands in the log
        return dict(cid=cid, win=win, target=target, cfg=cfg, err=repr(e))
    return dict(cid=cid, win=win, target=target, cfg=cfg, res=r, mean_skill=float(np.mean([r[h]["skill"] for h in HZ])),
                secs=time.time() - t)


def one_at_a_time():
    out = [("default", DEFAULT)]
    def var(tag, **kw):
        out.append((tag, {**DEFAULT, **kw}))
    var("data=v1", data="v1")
    var("shrink3", shrink=3)
    var("shrink6", shrink=6)
    for nl, ne, lr, mc in product((3, 7, 15), (150, 300, 600), (0.03, 0.06), (15, 30)):
        var(f"lgb_{nl}_{ne}_{lr}_{mc}", lgb=dict(num_leaves=nl, n_estimators=ne, learning_rate=lr, min_child_samples=mc))
    for a in (10, 30, 100):
        var(f"ridge{a}", ridge=float(a))
    for e in ("cat+ridge", "lgbm+ridge", "ridge", "median3", "lgbm+cat", "lgbm", "cat"):
        var(f"ens={e}", ens=e)
    for g in GROUPS:
        var(f"drop={g}", drop=g)
    var("window=6m", window="6m")
    return out


def cat_samples(n=20):
    allc = [dict(depth=a, iterations=b, l2_leaf_reg=c) for a, b, c in product((3, 4, 6), (300, 500, 1000), (3, 5, 10))]
    idx = np.random.default_rng(0).choice(len(allc), n, replace=False)
    return [allc[i] for i in idx]


def random_combos(n, seed=1):
    rng = np.random.default_rng(seed)
    cats = cat_samples()
    out = []
    for i in range(n):
        out.append((f"rand{i}", dict(
            data=str(rng.choice(["v1", "v2"])), shrink=int(rng.choice([0, 0, 3, 6])),
            lgb=dict(num_leaves=int(rng.choice([3, 7, 15])), n_estimators=int(rng.choice([150, 300, 600])),
                     learning_rate=float(rng.choice([0.03, 0.06])), min_child_samples=int(rng.choice([15, 30]))),
            cat=cats[int(rng.integers(len(cats)))], ridge=float(rng.choice([10, 30, 100])),
            ens=str(rng.choice(["lgbm+cat+ridge", "lgbm+cat+ridge", "cat+ridge", "lgbm+ridge", "ridge", "median3"])),
            drop=None if rng.random() < 0.7 else str(rng.choice(list(GROUPS))),
            window=str(rng.choice(["all", "all", "6m"])), seed=0)))
    return out


def run_pool(jobs, log):
    done = set()
    if log.exists():
        done = {(json.loads(l)["cid"], json.loads(l)["win"], json.loads(l)["target"]) for l in log.open()}
    jobs = [j for j in jobs if (j[0], j[3], j[2]) not in done]
    print(f"{len(jobs)} jobs ({len(done)} already done)", flush=True)
    t0 = time.time()
    with ProcessPoolExecutor(max(1, (os.cpu_count() or 4) - 2)) as ex, log.open("a") as f:
        futs = [ex.submit(run_one, j) for j in jobs]
        for i, fu in enumerate(as_completed(futs)):
            f.write(json.dumps(fu.result(), default=float) + "\n")
            f.flush()
            if i % 20 == 0:
                print(f"{i + 1}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)


def read(log):
    rows = [json.loads(l) for l in log.open()]
    errs = [r for r in rows if "err" in r]
    if errs:
        print(f"{len(errs)} errors, e.g. {errs[0]['cid']}: {errs[0]['err']}")
    return [r for r in rows if "res" in r]


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    mode = sys.argv[1]
    log = OUT / "results.csv"  # JSON lines (one config per line), despite the name the orders gave it
    if mode == "design":
        n_rand = int(sys.argv[2]) if len(sys.argv) > 2 else 250
        jobs = [(c, cfg, "n_anchored", "design") for c, cfg in one_at_a_time() + random_combos(n_rand)]
        jobs += [(f"cat_{i}", {**DEFAULT, "cat": c}, "n_anchored", "design") for i, c in enumerate(cat_samples())]
        run_pool(jobs, log)
    elif mode == "final":
        des = sorted([r for r in read(log) if r["win"] == "design"], key=lambda r: -r["mean_skill"])
        top = [r for r in des if r["cid"] != "default"][:3]
        cfgs = [("default", DEFAULT)] + [(r["cid"], r["cfg"]) for r in top]
        jobs = []
        for cid, cfg in cfgs:
            for s in range(5):  # seed spread on the design window
                jobs.append((f"{cid}|seed{s}", {**cfg, "seed": s}, "n_anchored", "design"))
            jobs.append((f"{cid}|final", cfg, "n_anchored", "test"))
            jobs.append((f"{cid}|final", cfg, "n_waiting", "crisis"))
            jobs.append((f"{cid}|final", cfg, "n_waiting", "crisis_pre"))
        run_pool(jobs, OUT / "final.csv")
