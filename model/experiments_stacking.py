"""Stacking experiments on top of model/train.py (nothing in train.py is changed or re-run for its outputs).

Same protocol as `train.py --rolling`: every test month is forecast by models fit on rows whose TARGET date is before
that month; the naive anchor is chosen on target dates < test_start; skill is vs the best of persistence / ma7 / blend
on the test set; 90 % CI = 7-day block bootstrap (train.block_bootstrap_skill).

Variants (all predict y[t+h]; 'avg' is the current train.py model and is re-computed here as a reproduction check):
  avg          current: mean of LightGBM / CatBoost / ridge on y[t+h] - anchor
  pool_h       (a) ONE model for h = 1,2,3 with h as a feature (rows of the 3 horizons stacked)
  b0_rel       crisis only: crisis rows only, relative target y[t+h]/anchor - 1   (control for (b))
  b1_pool24    (b) crisis only: crisis + ALL of 2024 rows, dataset flag, relative target
  b2_pool24n   (b) as b1 but count features divided by the anchor level (scale-free features)
  c_nnls       (c) non-negative least squares (weights normalised to sum 1) on out-of-fold [anchor+lgbm, anchor+cat,
               anchor+ridge, persistence, ma7, blend]; OOF = inner rolling origin, 2-week folds over the last 12 weeks
  c_ridge      (c) ridge (alpha 10, no intercept) on the same OOF, in change-from-anchor space
  holt         (d) damped-trend Holt forecast alone (alpha/beta/phi grid chosen on training target dates < test_start)
  avg_holtanc  (d) 'avg' but the anchor is chosen among persistence/ma7/blend/holt on training data only

Run:  python model/experiments_stacking.py            (both datasets)
      python model/experiments_stacking.py 2024       (or: crisis)
"""
import itertools
import sys
from functools import partial
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.optimize import nnls
from sklearn.linear_model import Ridge

sys.path.insert(0, str(Path(__file__).parent))
import train as T  # noqa: E402

# the machine is busy: cap threads inside train.fit_all without touching train.py
T.PARAMS["n_jobs"] = 2
T.CatBoostRegressor = partial(T.CatBoostRegressor, thread_count=2)

BASE3 = T.BASELINES
COMPS = ("lgbm", "cat", "ridge")
COUNT_COLS = {"anchored_today", "anchored_chg_1d", "anchored_chg_2d", "anchored_chg_3d", "anchored_chg_7d",
              "anchored_vs_7d_mean", "anchored_max_today", "moored_today", "arrivals_24h", "arrivals_48h",
              "departures_yday", "net_inflow_3d", "offshore_waiting", "inbound_60nm"}
INNER_STEP, INNER_N = 14, 6  # inner OOF folds: 6 x 14 days before each outer month


# ---------------------------------------------------------------- data prep (mirrors train.main)
class H:  # per-horizon bundle
    pass


def prep(daily, weather, test_start, test_end, target):
    T.TARGET = target
    d = pd.read_parquet(daily)
    if target == "n_waiting" and "n_waiting" not in d:
        d["n_waiting"] = d.n_anchored + d.offshore_waiting
    d["date"] = pd.to_datetime(d.date)
    d = d.set_index("date").sort_index().asfreq("D")
    for wf in weather or []:
        w = pd.read_parquet(wf)
        w.index = pd.to_datetime(w.date)
        d = d.drop(columns=[c for c in w.columns if c in d.columns and c != "date"]).join(w.drop(columns="date"))
    ts = pd.Timestamp(test_start)
    te_end = pd.Timestamp(test_end) if test_end else d.index.max()
    X = T.features(d)
    base_all = T.baselines(d[target])
    hs = {}
    for h in T.HORIZONS:
        o = H()
        o.h, o.ts, o.te_end = h, ts, te_end
        o.X = X.copy()
        o.X["target_dow"] = (d.index + pd.Timedelta(days=h)).dayofweek
        if f"fc{h}_gust_max_kts" in d and d[f"fc{h}_gust_max_kts"].notna().mean() > 0.5:
            o.X["fc_gust_target"] = d[f"fc{h}_gust_max_kts"].shift(-h)
            o.X["fc_gust_tomorrow"] = d["fc1_gust_max_kts"].shift(-1)
        o.y = d[target].shift(-h)
        o.tgt = d.index + pd.Timedelta(days=h)
        o.ok = o.y.notna() & base_all["blend"].notna()
        o.tr = o.ok & (o.tgt < ts)
        o.te = o.ok & (o.tgt >= ts) & (o.tgt <= te_end)
        o.base = base_all
        o.anchor_name = min(BASE3, key=lambda k: T.mae(base_all[k][o.tr], o.y[o.tr]))
        o.anchor = base_all[o.anchor_name]
        hs[h] = o
    return d, hs


def holt_series(y, h, a, b, phi):
    out = np.full(len(y), np.nan)
    lvl = trend = None
    damp = sum(phi ** i for i in range(1, h + 1))
    for i, v in enumerate(y.values):
        if np.isnan(v):
            continue
        if lvl is None:
            lvl, trend = v, 0.0
        else:
            lp = lvl
            lvl = a * v + (1 - a) * (lp + phi * trend)
            trend = b * (lvl - lp) + (1 - b) * phi * trend
        out[i] = lvl + damp * trend
    return pd.Series(out, index=y.index)


def holt_for(d, hc, target):
    """Pick (alpha, beta, phi) on training target dates only; return the h-step forecast issued each day."""
    best = None
    for a, b, phi in itertools.product((0.3, 0.5, 0.7, 0.9), (0.1, 0.2, 0.4), (0.8, 0.9, 0.98)):
        f = holt_series(d[target], hc.h, a, b, phi)
        e = T.mae(f[hc.tr], hc.y[hc.tr])
        if best is None or e < best[0]:
            best = (e, (a, b, phi), f)
    return best[2], best[1]


# ---------------------------------------------------------------- per-horizon variants (avg, c_nnls, c_ridge)
def months(hc):
    return list(pd.date_range(hc.ts, hc.te_end, freq="MS"))


def per_h_variants(hc, anchor, base):
    """avg / components / vertical stacks for one horizon, rolling-origin. Returns ({variant: Series on te}, n_fallback)."""
    X, y, tgt = hc.X, hc.y, hc.tgt
    dy = y - anchor
    idx = y[hc.te].index
    out = {k: pd.Series(np.nan, index=idx) for k in ("avg", "lgbm", "cat", "ridge", "c_nnls", "c_ridge")}
    n_fallback = 0
    for m0 in months(hc):
        fte = hc.te & (tgt >= m0) & (tgt < m0 + pd.DateOffset(months=1))
        if not fte.any():
            continue
        ti = fte[fte].index
        trm = hc.ok & (tgt < m0)
        fm = T.fit_all(X[trm], dy[trm])
        P = {k: T.predict(fm, k, X[fte]) for k in COMPS}
        # inner rolling-origin out-of-fold predictions for the meta learner
        oof_p, oof_y, oof_b, oof_a = [], [], [], []
        for j in range(INNER_N, 0, -1):
            i0 = m0 - pd.Timedelta(days=INNER_STEP * j)
            i1 = i0 + pd.Timedelta(days=INNER_STEP)
            ftr, fva = trm & (tgt < i0), trm & (tgt >= i0) & (tgt < i1)
            if ftr.sum() < 30 or not fva.any():
                continue
            im = T.fit_all(X[ftr], dy[ftr])
            oof_p.append(np.column_stack([T.predict(im, k, X[fva]) for k in COMPS]))
            oof_y.append(y[fva].values)
            oof_a.append(anchor[fva].values)
            oof_b.append(np.column_stack([base[k][fva].values for k in BASE3]))
        pm = np.column_stack([P[k] for k in COMPS])
        a_te = anchor[fte].values
        b_te = np.column_stack([base[k][fte].values for k in BASE3])
        avg = a_te + pm.mean(axis=1)
        for k in COMPS:
            out[k][ti] = a_te + P[k]
        out["avg"][ti] = avg
        if sum(len(v) for v in oof_y) < 20:
            n_fallback += 1
            out["c_nnls"][ti] = avg
            out["c_ridge"][ti] = avg
            continue
        Po, yo, ao, bo = np.vstack(oof_p), np.concatenate(oof_y), np.concatenate(oof_a), np.vstack(oof_b)
        A = np.column_stack([ao[:, None] + Po, bo])
        w, _ = nnls(A, yo)
        w = w / w.sum() if w.sum() > 0 else np.r_[np.ones(3) / 3, np.zeros(3)]
        out["c_nnls"][ti] = np.column_stack([a_te[:, None] + pm, b_te]) @ w
        Z = np.column_stack([Po, bo - ao[:, None]])
        r = Ridge(alpha=10.0, fit_intercept=False).fit(Z, yo - ao)
        out["c_ridge"][ti] = a_te + r.predict(np.column_stack([pm, b_te - a_te[:, None]]))
    return out, n_fallback


# ---------------------------------------------------------------- (a) pooled across horizons
def pooled_h(hs):
    out = {h: pd.Series(np.nan, index=hs[h].y[hs[h].te].index) for h in hs}
    for m0 in months(hs[1]):
        parts_X, parts_y = [], []
        for h, hc in hs.items():
            trm = hc.ok & (hc.tgt < m0)
            Xp = hc.X[trm].copy()
            Xp["h"] = h
            parts_X.append(Xp)
            parts_y.append((hc.y - hc.anchor)[trm])
        fm = T.fit_all(pd.concat(parts_X), pd.concat(parts_y))
        for h, hc in hs.items():
            fte = hc.te & (hc.tgt >= m0) & (hc.tgt < m0 + pd.DateOffset(months=1))
            if not fte.any():
                continue
            Xt = hc.X[fte].copy()
            Xt["h"] = h
            out[h][fte[fte].index] = hc.anchor[fte].values + T.predict(fm, "avg", Xt)
    return out


# ---------------------------------------------------------------- (b) crisis + 2024 pool, relative target
def _with_anchor(hc, name):
    o = H()
    o.__dict__.update(hc.__dict__)
    o.anchor_name, o.anchor = name, hc.base[name]
    return o


def rel_frame(hc, cols, normalise, flag):
    sc = hc.anchor.clip(lower=1.0)
    Xr = hc.X[cols].copy()
    if normalise:
        for c in cols:
            if c in COUNT_COLS:
                Xr[c] = Xr[c] / sc
    Xr["is24"] = flag
    return Xr, sc


def pooled_2024(hs_c, hs_24, normalise, use_24=True):
    cols = [c for c in hs_c[1].X.columns if c in hs_24[1].X.columns]  # drops fc_* (no archived forecasts in 2021)
    out = {}
    for h in hs_c:
        hc, h24 = hs_c[h], hs_24[h]
        a24 = min(BASE3, key=lambda k: T.mae(h24.base[k][h24.ok], h24.y[h24.ok]))
        h24 = _with_anchor(h24, a24)
        Xc, sc_c = rel_frame(hc, cols, normalise, 0)
        X24, sc_24 = rel_frame(h24, cols, normalise, 1)
        rel_c, rel_24 = hc.y / sc_c - 1, h24.y / sc_24 - 1
        res = pd.Series(np.nan, index=hc.y[hc.te].index)
        for m0 in months(hc):
            fte = hc.te & (hc.tgt >= m0) & (hc.tgt < m0 + pd.DateOffset(months=1))
            if not fte.any():
                continue
            trm = hc.ok & (hc.tgt < m0)
            Xtr, ytr = Xc[trm], rel_c[trm]
            if use_24:
                Xtr, ytr = pd.concat([Xtr, X24[h24.ok]]), pd.concat([ytr, rel_24[h24.ok]])
            fm = T.fit_all(Xtr, ytr)
            res[fte[fte].index] = hc.anchor[fte].values * (1 + T.predict(fm, "avg", Xc[fte]))
        out[h] = res
    return out


# ---------------------------------------------------------------- evaluation
def paired_delta(err_v, err_ref, err_b, block=7, n=2000, seed=0):
    """90% CI of (skill_variant - skill_ref) in percentage points, same resampled blocks for both."""
    rng, k = np.random.default_rng(seed), len(err_v)
    starts = np.arange(k - block + 1)
    out = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s0, s0 + block) for s0 in rng.choice(starts, k // block + 1)])[:k]
        out.append(100 * (err_ref[idx].mean() - err_v[idx].mean()) / err_b[idx].mean())
    return [round(float(np.percentile(out, 5)), 1), round(float(np.percentile(out, 95)), 1)]


def table(title, hs, preds, mask_fn=None):
    """preds: {variant: {h: Series}}. Skill vs the best naive of the 3 (chosen on the test set, as train.py)."""
    lines = [f"### {title}", "", "| variant | h | n | MAE | skill vs best naive | 90% CI | Δ vs avg (pp) | Δ 90% CI |",
             "|---|---|---|---|---|---|---|---|"]
    for h in T.HORIZONS:
        hc = hs[h]
        te = hc.te if mask_fn is None else hc.te & mask_fn(hc)
        act = hc.y[te]
        tb = {k: T.mae(hc.base[k][te], act) for k in BASE3}
        best = min(tb, key=tb.get)
        eb = (hc.base[best][te] - act).abs().values
        er = (preds["avg"][h].reindex(act.index) - act).abs().values
        for v, ph in preds.items():
            p = ph[h].reindex(act.index)
            if p.isna().any():
                continue
            ev = (p - act).abs().values
            sk = 100 * (1 - ev.mean() / eb.mean())
            ci = T.block_bootstrap_skill(ev, eb)
            dl = "" if v == "avg" else f"{sk - 100 * (1 - er.mean() / eb.mean()):+.1f}"
            dc = "" if v == "avg" else str(paired_delta(ev, er, eb))
            lines.append(f"| {v} | {h} | {len(act)} | {ev.mean():.3f} | {sk:+.1f}% | [{ci[0]:+.1f}, {ci[1]:+.1f}] | {dl} | {dc} |")
        pers = 100 * (1 - er.mean() / tb["persistence"])
        lines.append(f"| *naive MAE: {', '.join(f'{k} {v:.3f}' for k, v in tb.items())}; best = {best}; avg vs persistence {pers:+.1f}%* | {h} | | | | | | |")
    return "\n".join(lines) + "\n"


def run(name, daily, weather, test_start, target, hs24=None, test_end=None):
    d, hs = prep(daily, weather, test_start, test_end, target)
    preds = {}
    for h, hc in hs.items():
        v, nfb = per_h_variants(hc, hc.anchor, hc.base)
        for k in ("avg", "c_nnls", "c_ridge"):
            preds.setdefault(k, {})[h] = v[k]
        hf, par = holt_for(d, hc, target)
        preds.setdefault("holt", {})[h] = hf[hc.te]
        # (d) anchor chosen among 4 candidates on training data only
        base4 = dict(hc.base, holt=hf)
        an4 = min(base4, key=lambda k: T.mae(base4[k][hc.tr], hc.y[hc.tr]))
        if an4 == hc.anchor_name:
            preds.setdefault("avg_holtanc", {})[h] = v["avg"]
        else:
            hc4 = _with_anchor(hc, an4)
            hc4.base, hc4.anchor, hc4.ok = base4, base4[an4], hc.ok & hf.notna()
            preds.setdefault("avg_holtanc", {})[h] = per_h_variants(hc4, hc4.anchor, base4)[0]["avg"]
        print(f"[{name}] h={h} anchor={hc.anchor_name} holt(alpha,beta,phi)={par} 4-way-anchor={an4} "
              f"meta-fallback-months={nfb}", flush=True)
    preds["pool_h"] = pooled_h(hs)
    if hs24 is not None:
        preds["b0_rel"] = pooled_2024(hs, hs24, False, use_24=False)
        preds["b1_pool24"] = pooled_2024(hs, hs24, False)
        preds["b2_pool24n"] = pooled_2024(hs, hs24, True)
    order = ["avg", "pool_h", "b0_rel", "b1_pool24", "b2_pool24n", "c_nnls", "c_ridge", "holt", "avg_holtanc"]
    return hs, {k: preds[k] for k in order if k in preds}


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "both"
    ext24 = ["data/weather_daily.parquet", "data/ext_daily.parquet"]
    md = []
    if which in ("both", "2024"):
        hs, preds = run("2024", "data/daily.parquet", ext24, "2024-10-01", "n_anchored")
        md.append(table("2024, target n_anchored, test Oct-Dec 2024 (rolling-origin)", hs, preds))
    if which in ("both", "crisis"):
        _, hs24 = prep("data/daily.parquet", ext24, "2024-10-01", None, "n_waiting")
        cw = ["data/crisis/weather_daily.parquet", "data/crisis/ext_daily.parquet"]
        hs, preds = run("crisis", "data/crisis/daily_a.parquet", cw, "2021-09-01", "n_waiting", hs24)
        md.append(table("Crisis, target n_waiting, test from 2021-09-01 (rolling-origin)", hs, preds))
        cut = pd.Timestamp("2021-11-15")
        md.append(table("Crisis, pre-rule-change window only (target date <= 2021-11-15)", hs, preds,
                        mask_fn=lambda hc: pd.Series(hc.tgt <= cut, index=hc.y.index)))
    print("\n".join(md))
