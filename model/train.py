"""Forecast ships at anchor (n_anchored) 1..3 days ahead and compare with naive baselines.

Usage:
  python model/train.py                                   # 2024: test Oct-Dec, writes shared/preds.json ...
  python model/train.py --daily shared/crisis/daily.parquet \
                        --weather data/crisis/weather_daily.parquet data/crisis/ext_daily.parquet \
                        --test-start 2021-12-01 --out-prefix shared/crisis

Baselines: persistence (y_t), 7-day mean, and their 50/50 blend. skill_pct is against the BEST of the three on the
test set (the toughest honest comparison). The models predict y[t+h] - blend[t] (blend + learned correction).
Candidates LightGBM / CatBoost / ridge / plain average; per-horizon choice by rolling-origin CV on the 3 months
before the test start. "Storm days" = days where the forecast (known on the issue day) shows gusts >= 25 kn.
Archived weather forecasts (Open-Meteo previous-runs) only exist from 2024-01-19, so 2021-22 runs without them.
"""
import argparse
import json
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
import shap
from catboost import CatBoostRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

TARGET = "n_anchored"
HORIZONS = (1, 2, 3)
STORM_KTS = 25
PARAMS = dict(objective="l1", learning_rate=0.03, n_estimators=300, num_leaves=7, min_child_samples=15,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1, seed=0)
CANDIDATES = ("lgbm", "cat", "ridge", "avg")
BASELINES = ("persistence", "ma7", "blend")

HIDDEN = {"anchored_today"}  # "18 tomorrow because 18 today" explains nothing
LABELS = {
    "anchored_chg_1d": "change in queue since yesterday", "anchored_chg_2d": "change in queue over 2 days",
    "anchored_chg_3d": "change in queue over 3 days", "anchored_chg_7d": "change in queue over a week",
    "anchored_vs_7d_mean": "queue vs. its weekly normal", "anchored_max_today": "peak queue today",
    "moored_today": "ships at berth", "arrivals_24h": "arrivals today", "arrivals_48h": "arrivals over 2 days",
    "departures_yday": "departures yesterday", "net_inflow_3d": "arrivals minus departures, last 3 days",
    "avg_wait_h": "average wait for a berth (h)", "wind_max_kts": "max wind (kn)", "gust_max_kts": "max gust today (kn)",
    "visibility_min_m": "min visibility (model, m)", "wind_max_3d": "max wind over 3 days (kn)",
    "is_holiday": "public holiday", "klgb_vis_min_mi": "min visibility at Long Beach airport (mi)",
    "klgb_fog_hours": "hours of fog at Long Beach airport", "wave_hs_max_m": "max wave height at harbor entrance (m)",
    "wave_period_max_s": "longest swell period (s)", "target_dow": "day of week", "news_score": "news disruption score",
    "offshore_waiting": "ships waiting offshore (<60 nm, <3 kn)", "inbound_60nm": "ships inbound within 60 nm",
    "fc_gust_target": "forecast max gust on the target day (kn)", "fc_gust_tomorrow": "forecast max gust tomorrow (kn)",
}


def phrase(name, value, contrib):
    """Plain-English reason; direction from the contribution sign (pushes the forecast up or down)."""
    up = contrib > 0
    pushes = "pushes the forecast up" if up else "pulls the forecast down"
    v = round(value, 1)
    special = {
        "anchored_vs_7d_mean": (f"queue is {abs(v):g} ships {'above' if v > 0 else 'below'} its weekly normal, "
                                f"so it tends to {'shrink back' if v > 0 else 'refill'}"),
        "net_inflow_3d": (f"{abs(v):g} more ships {'arrived than left' if v > 0 else 'left than arrived'} "
                          f"over the last 3 days"),
        "gust_max_kts": f"gusts reached {v:g} kn today" + (" (ships that left anchor tend to return)" if up and v >= 25 else ""),
        "fc_gust_target": f"forecast gusts of {v:g} kn on the target day" + (" (storm: ships leave anchor)" if not up and v >= 25 else ""),
        "fc_gust_tomorrow": f"forecast gusts of {v:g} kn tomorrow",
        "wind_max_3d": f"wind peaked at {v:g} kn in the last 3 days",
        "wave_hs_max_m": f"waves reached {v:g} m at the harbor entrance",
        "klgb_fog_hours": f"{v:g} hours of fog at Long Beach airport",
        "departures_yday": f"{v:g} ships departed yesterday",
        "arrivals_24h": f"{v:g} ships arrived today",
        "offshore_waiting": f"{v:g} ships waiting offshore, outside the anchorage",
        "inbound_60nm": f"{v:g} ships inbound within 60 nm",
        "avg_wait_h": f"ships are waiting {v:g} h on average for a berth",
    }
    if name in special:
        return f"{special[name]}; {pushes}"
    if name.startswith("anchored_chg_"):
        days = {"1d": "a day", "2d": "2 days", "3d": "3 days", "7d": "a week"}[name.rsplit("_", 1)[1]]
        return f"queue {'grew' if v > 0 else 'shrank'} by {abs(v):g} ships over {days}; {pushes}"
    if name == "target_dow":
        return f"{['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][int(v)]} pattern; {pushes}"
    return f"{LABELS.get(name, name)} = {v:g}; {pushes}"


def baselines(y):
    ma7 = y.rolling(7, min_periods=4).mean()
    return dict(persistence=y, ma7=ma7, blend=0.5 * y + 0.5 * ma7)


def features(d):
    f = pd.DataFrame(index=d.index)
    y = d[TARGET]
    f["anchored_today"] = y
    for k in (1, 2, 3, 7):
        f[f"anchored_chg_{k}d"] = y - y.shift(k)
    f["anchored_vs_7d_mean"] = y - y.rolling(7, min_periods=4).mean()
    opt = {"anchored_max_today": "n_anchored_max", "moored_today": "n_moored", "arrivals_24h": "n_arrivals_24h",
           "arrivals_48h": "n_arrivals_48h", "wind_max_kts": "wind_max_kts", "gust_max_kts": "gust_max_kts",
           "visibility_min_m": "visibility_min_m", "is_holiday": "is_holiday"}
    for k, c in opt.items():
        if c in d:
            f[k] = d[c]
    if "n_departures_24h" in d:
        # a departure = last ping before >= 24 h of silence, so day t's departures are only known on day t+1
        dep_known = d.n_departures_24h.shift(1)
        f["departures_yday"] = dep_known
        if "n_arrivals_24h" in d:
            f["net_inflow_3d"] = d.n_arrivals_24h.rolling(3).sum() - dep_known.rolling(3).sum()
    if "avg_wait_hours" in d:
        f["avg_wait_h"] = d.avg_wait_hours.ffill()
    if "wind_max_kts" in d:
        f["wind_max_3d"] = d.wind_max_kts.rolling(3).max()
    for c in ("klgb_vis_min_mi", "klgb_fog_hours", "wave_hs_max_m", "wave_period_max_s", "offshore_waiting", "inbound_60nm"):
        if c in d:
            f[c] = d[c]
    if "news_score" in d and d.news_score.notna().any():
        f["news_score"] = d.news_score.fillna(0)
    return f


def fit_all(X, y):
    return dict(lgbm=lgb.LGBMRegressor(**PARAMS).fit(X, y),
                cat=CatBoostRegressor(loss_function="MAE", depth=4, iterations=500, learning_rate=0.03,
                                      l2_leaf_reg=5, random_seed=0, verbose=0).fit(X, y),
                ridge=make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), Ridge(alpha=30.0)).fit(X, y))


def predict(models, name, X):
    if name == "avg":  # plain average: no learned weights, so no extra overfitting on a few hundred rows
        return np.mean([models[k].predict(X) for k in ("lgbm", "cat", "ridge")], axis=0)
    return models[name].predict(X)


def contributions(models, name, X):
    """Per-row feature contributions (SHAP for trees, exact coef * standardized x for ridge); additive, so the
    average model's contributions are the average of the three."""
    def lin(pipe):
        imp, sc, r = pipe.named_steps.values()
        return sc.transform(imp.transform(X)) * r.coef_
    parts = dict(lgbm=lambda: shap.TreeExplainer(models["lgbm"]).shap_values(X),
                 cat=lambda: shap.TreeExplainer(models["cat"]).shap_values(X),
                 ridge=lambda: lin(models["ridge"]))
    if name == "avg":
        return np.mean([parts[k]() for k in ("lgbm", "cat", "ridge")], axis=0)
    return parts[name]()


def block_bootstrap_skill(err_m, err_b, block=7, n=2000, seed=0):
    """90% CI of skill_pct, resampling 7-day blocks (errors are autocorrelated day to day)."""
    rng, k = np.random.default_rng(seed), len(err_m)
    starts = np.arange(k - block + 1)
    out = []
    for _ in range(n):
        idx = np.concatenate([np.arange(s0, s0 + block) for s0 in rng.choice(starts, k // block + 1)])[:k]
        out.append(100 * (1 - err_m[idx].mean() / err_b[idx].mean()))
    return [round(float(np.percentile(out, 5)), 1), round(float(np.percentile(out, 95)), 1)]


def mae(a, b):
    return float(np.mean(np.abs(np.asarray(a) - np.asarray(b))))


def main(daily, weather, test_start, out_prefix, test_end=None):
    d = pd.read_parquet(daily)
    d["date"] = pd.to_datetime(d.date)
    d = d.set_index("date").sort_index().asfreq("D")
    for wf in weather or []:  # extra per-day tables (weather, fog/waves) for daily files that lack them
        w = pd.read_parquet(wf)
        w.index = pd.to_datetime(w.date)
        d = d.drop(columns=[c for c in w.columns if c in d.columns and c != "date"]).join(w.drop(columns="date"))
    test_start = pd.Timestamp(test_start)
    test_end = pd.Timestamp(test_end) if test_end else d.index.max()
    cv_months = [test_start - pd.DateOffset(months=k) for k in (3, 2, 1)]
    X = features(d)
    base_all = baselines(d[TARGET])
    rows, metrics = [], {}
    for h in HORIZONS:
        Xh = X.copy()
        Xh["target_dow"] = (d.index + pd.Timedelta(days=h)).dayofweek
        if f"fc{h}_gust_max_kts" in d and d[f"fc{h}_gust_max_kts"].notna().mean() > 0.5:
            # forecast for the target day, issued h days earlier = on the issue day: no peeking
            Xh["fc_gust_target"] = d[f"fc{h}_gust_max_kts"].shift(-h)
            Xh["fc_gust_tomorrow"] = d["fc1_gust_max_kts"].shift(-1)
        y_fut = d[TARGET].shift(-h)
        anchor = base_all["blend"]
        dy = y_fut - anchor
        tgt_date = d.index + pd.Timedelta(days=h)
        ok = y_fut.notna() & anchor.notna()
        tr = ok & (tgt_date < test_start)
        te = ok & (tgt_date >= test_start) & (tgt_date <= test_end)

        cv = {k: [] for k in CANDIDATES + BASELINES}
        for m0 in cv_months:
            m1 = m0 + pd.DateOffset(months=1)
            ftr, fva = tr & (tgt_date < m0), tr & (tgt_date >= m0) & (tgt_date < m1)
            fm = fit_all(Xh[ftr], dy[ftr])
            for k in CANDIDATES:
                cv[k].append(mae(anchor[fva] + predict(fm, k, Xh[fva]), y_fut[fva]))
            for k in BASELINES:
                cv[k].append(mae(base_all[k][fva], y_fut[fva]))
        cv = {k: round(float(np.nanmean(v)), 3) for k, v in cv.items()}
        chosen = min(CANDIDATES, key=cv.get)

        models = fit_all(Xh[tr], dy[tr])
        act = y_fut[te]
        pred = anchor[te] + predict(models, chosen, Xh[te])
        sv = contributions(models, chosen, Xh[te])
        test_models = {k: round(mae(anchor[te] + predict(models, k, Xh[te]), act), 3) for k in CANDIDATES}
        test_base = {k: round(mae(base_all[k][te], act), 3) for k in BASELINES}
        best = min(BASELINES, key=test_base.get)
        base = base_all[best][te]
        mae_m, mae_b = mae(pred, act), test_base[best]
        m = dict(mae_model=round(mae_m, 3), mae_baseline=mae_b, baseline=best, n_test=int(te.sum()),
                 skill_pct=round(100 * (1 - mae_m / mae_b), 1),
                 skill_ci90=block_bootstrap_skill(np.abs(pred - act).values, np.abs(base - act).values),
                 skill_vs_persistence_pct=round(100 * (1 - mae_m / test_base["persistence"]), 1),
                 baselines_mae=test_base, model=chosen, cv_mae=cv, test_mae_all=test_models)
        if "fc_gust_target" in Xh:
            storm = (Xh.loc[te, ["fc_gust_target", "fc_gust_tomorrow"]].max(axis=1) >= STORM_KTS).values
            if storm.sum() >= 3:
                m.update(n_storm=int(storm.sum()), mae_model_storm=round(mae(pred[storm], act[storm]), 3),
                         mae_baseline_storm=round(mae(base[storm], act[storm]), 3))
                m["skill_pct_storm"] = round(100 * (1 - m["mae_model_storm"] / m["mae_baseline_storm"]), 1)
        metrics[str(h)] = m
        print(f"h={h} [{chosen}] MAE {mae_m:.3f} vs best baseline {best} {mae_b:.3f}: skill {m['skill_pct']}% "
              f"CI {m['skill_ci90']} | vs persistence {m['skill_vs_persistence_pct']}% | baselines {test_base}"
              + (f" | storm days n={m['n_storm']}: {m['skill_pct_storm']}%" if "n_storm" in m else ""))
        print(f"   CV {cv}")

        cols = Xh.columns
        Xte = Xh[te]
        for i, (issued, td) in enumerate(zip(d.index[te], tgt_date[te])):
            top = [j for j in np.argsort(-np.abs(sv[i])) if cols[j] not in HIDDEN][:3]
            rows.append(dict(date=td.strftime("%Y-%m-%d"), issued=issued.strftime("%Y-%m-%d"), h=h,
                             actual=round(float(act.iloc[i]), 2), pred=round(float(pred.iloc[i]), 2),
                             baseline=round(float(base.iloc[i]), 2), baseline_name=best,
                             persistence=round(float(base_all["persistence"][te].iloc[i]), 2),
                             top_features=[dict(name=cols[j], label=LABELS.get(cols[j], cols[j]),
                                                phrase=phrase(cols[j], float(Xte.iloc[i, j]), float(sv[i][j])),
                                                value=round(float(Xte.iloc[i, j]), 2),
                                                shap=round(float(sv[i][j]), 3)) for j in top]))

    out = Path(out_prefix)
    out.mkdir(parents=True, exist_ok=True)
    tag = "" if out == Path("shared") else "_" + out.name
    pd.DataFrame(rows).to_parquet(f"data/preds{tag}.parquet", index=False)
    (out / "preds.json").write_text(json.dumps(rows))
    (out / "metrics.json").write_text(json.dumps(metrics, indent=1))
    print(f"wrote {out}/preds.json ({len(rows)} rows), {out}/metrics.json")


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--daily", default="data/daily.parquet")
    a.add_argument("--weather", nargs="+", help="per-day parquet(s) to join, e.g. weather + fog/waves")
    a.add_argument("--test-start", default="2024-10-01")
    a.add_argument("--test-end")
    a.add_argument("--out-prefix", default="shared")
    x = a.parse_args()
    main(x.daily, x.weather, x.test_start, x.out_prefix, x.test_end)
