"""LightGBM forecast of n_anchored at t+1..t+3 vs persistence. Train on targets Jan-Sep 2024, test Oct-Dec.

The model predicts the change y[t+h] - y[t] (persistence + learned correction), so it can't do worse
than persistence by much when it has nothing to say. Writes data/preds.parquet, shared/preds.json,
shared/metrics.json.
"""
import json
from pathlib import Path
import lightgbm as lgb
import numpy as np
import pandas as pd
import shap

TARGET = "n_anchored"
TEST_START = pd.Timestamp("2024-10-01")
HORIZONS = (1, 2, 3)
BIG = 3  # ships
PARAMS = dict(objective="l1", learning_rate=0.03, n_estimators=300, num_leaves=7, min_child_samples=15,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1, seed=0)


HIDDEN = {"anchored_today"}
LABELS = {
    "anchored_chg_1d": "change in queue since yesterday", "anchored_chg_2d": "change in queue over 2 days",
    "anchored_chg_3d": "change in queue over 3 days", "anchored_chg_7d": "change in queue over a week",
    "anchored_vs_7d_mean": "queue vs. its weekly normal", "anchored_max_today": "peak queue today",
    "moored_today": "ships at berth", "arrivals_24h": "arrivals today", "arrivals_48h": "arrivals over 2 days",
    "departures_yday": "departures yesterday", "net_inflow_3d": "arrivals minus departures, last 3 days",
    "avg_wait_h": "average wait for a berth (h)", "wind_max_kts": "max wind (kn)", "gust_max_kts": "max gust (kn)",
    "visibility_min_m": "min visibility (model, m)", "wind_max_3d": "max wind over 3 days (kn)",
    "is_holiday": "public holiday", "klgb_vis_min_mi": "min visibility at Long Beach airport (mi)",
    "klgb_fog_hours": "hours of fog at Long Beach airport", "wave_hs_max_m": "max wave height at harbor entrance (m)",
    "wave_period_max_s": "longest swell period (s)", "offshore_waiting": "ships waiting offshore (<60 nm, <3 kn)",
    "inbound_60nm": "ships inbound within 60 nm", "target_dow": "day of week", "news_score": "news disruption score",
}


def phrase(name, value, shap_value):
    """Plain-English reason, direction from the SHAP sign (pushes the forecast up or down)."""
    up = shap_value > 0
    pushes = "pushes the forecast up" if up else "pulls the forecast down"
    v = round(value, 1)
    special = {
        "anchored_vs_7d_mean": (f"queue is {abs(v):g} ships {'above' if v > 0 else 'below'} its weekly normal, "
                                f"so it tends to {'shrink back' if v > 0 else 'refill'}"),
        "net_inflow_3d": (f"{abs(v):g} more ships {'arrived than left' if v > 0 else 'left than arrived'} "
                          f"over the last 3 days"),
        "gust_max_kts": f"gusts reached {v:g} kn" + (" (ships that left anchor tend to return)" if up and v >= 25 else ""),
        "wind_max_3d": f"wind peaked at {v:g} kn in the last 3 days",
        "wave_hs_max_m": f"waves reached {v:g} m at the harbor entrance",
        "klgb_fog_hours": f"{v:g} hours of fog at Long Beach airport",
        "departures_yday": f"{v:g} ships departed yesterday",
        "arrivals_24h": f"{v:g} ships arrived today",
        "offshore_waiting": f"{v:g} ships waiting offshore, outside the anchorage",
        "inbound_60nm": f"{v:g} ships inbound within 60 nm",
    }
    if name in special:
        return f"{special[name]}; {pushes}"
    if name.startswith("anchored_chg_"):
        days = {"1d": "a day", "2d": "2 days", "3d": "3 days", "7d": "a week"}[name.rsplit("_", 1)[1]]
        return f"queue {'grew' if v > 0 else 'shrank'} by {abs(v):g} ships over {days}; {pushes}"
    if name == "target_dow":
        return f"{['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'][int(v)]} pattern; {pushes}"
    return f"{LABELS.get(name, name)} = {v:g}; {pushes}"


def features(d):
    f = pd.DataFrame(index=d.index)
    y = d[TARGET]
    f["anchored_today"] = y
    for k in (1, 2, 3, 7):
        f[f"anchored_chg_{k}d"] = y - y.shift(k)
    f["anchored_vs_7d_mean"] = y - y.rolling(7).mean()
    f["anchored_max_today"] = d.n_anchored_max
    f["moored_today"] = d.n_moored
    f["arrivals_24h"] = d.n_arrivals_24h
    f["arrivals_48h"] = d.n_arrivals_48h
    # a departure = last ping before >= 24 h of silence, so day t's departures are only known on day t+1.
    # Use yesterday's count to avoid peeking ahead.
    dep_known = d.n_departures_24h.shift(1)
    f["departures_yday"] = dep_known
    f["net_inflow_3d"] = d.n_arrivals_24h.rolling(3).sum() - dep_known.rolling(3).sum()
    f["avg_wait_h"] = d.avg_wait_hours.ffill()
    f["wind_max_kts"] = d.wind_max_kts
    f["gust_max_kts"] = d.gust_max_kts
    f["visibility_min_m"] = d.visibility_min_m
    f["wind_max_3d"] = d.wind_max_kts.rolling(3).max()
    f["is_holiday"] = d.is_holiday
    for c in ("klgb_vis_min_mi", "klgb_fog_hours", "wave_hs_max_m", "wave_period_max_s", "offshore_waiting", "inbound_60nm"):
        if c in d:
            f[c] = d[c]
    if d.news_score.notna().any():
        f["news_score"] = d.news_score.fillna(0)
    return f


def main():
    d = pd.read_parquet("data/daily.parquet").set_index("date").asfreq("D")
    X = features(d)
    rows, metrics = [], {}
    for h in HORIZONS:
        Xh = X.copy()
        Xh["target_dow"] = (d.index + pd.Timedelta(days=h)).dayofweek
        y_fut = d[TARGET].shift(-h)
        tgt_date = d.index + pd.Timedelta(days=h)
        ok = y_fut.notna() & d[TARGET].notna()
        tr = ok & (tgt_date < TEST_START)
        te = ok & (tgt_date >= TEST_START)
        m = lgb.LGBMRegressor(**PARAMS).fit(Xh[tr], (y_fut - d[TARGET])[tr])
        base = d[TARGET][te]
        pred = base + m.predict(Xh[te])
        act = y_fut[te]
        sv = shap.TreeExplainer(m).shap_values(Xh[te])
        mae_m, mae_b = float(np.mean(np.abs(pred - act))), float(np.mean(np.abs(base - act)))
        # big moves: the queue changes by >= BIG ships over the horizon. Persistence is wrong by construction
        # there; this is where a forecast earns its keep.
        big = (act - base).abs() >= BIG
        mae_mb, mae_bb = float(np.mean(np.abs(pred - act)[big])), float(np.mean(np.abs(base - act)[big]))
        dir_ok = float(np.mean(np.sign(pred - base)[big] == np.sign(act - base)[big]))
        metrics[str(h)] = dict(mae_model=round(mae_m, 3), mae_baseline=round(mae_b, 3), n_test=int(te.sum()),
                               skill_pct=round(100 * (1 - mae_m / mae_b), 1),
                               mae_model_bigmove=round(mae_mb, 3), mae_baseline_bigmove=round(mae_bb, 3),
                               n_bigmove=int(big.sum()), skill_pct_bigmove=round(100 * (1 - mae_mb / mae_bb), 1),
                               direction_hit_bigmove=round(dir_ok, 2))
        print(f"   big moves (>= {BIG} ships, n={big.sum()}): MAE model {mae_mb:.2f} vs persistence {mae_bb:.2f}, "
              f"direction right {dir_ok:.0%}")
        print(f"h={h}: MAE model {mae_m:.3f}  persistence {mae_b:.3f}  n={te.sum()}  "
              f"skill {metrics[str(h)]['skill_pct']}%")
        cols = Xh.columns
        for i, (issued, td) in enumerate(zip(d.index[te], tgt_date[te])):
            # skip the current queue level: "18 tomorrow because 18 today" explains nothing
            top = [j for j in np.argsort(-np.abs(sv[i])) if cols[j] not in HIDDEN][:3]
            rows.append(dict(date=td.strftime("%Y-%m-%d"), issued=issued.strftime("%Y-%m-%d"), h=h,
                             actual=round(float(act.iloc[i]), 2), pred=round(float(pred.iloc[i]), 2),
                             baseline=round(float(base.iloc[i]), 2),
                             top_features=[dict(name=cols[j], label=LABELS.get(cols[j], cols[j]),
                                                phrase=phrase(cols[j], float(Xh[te].iloc[i, j]), float(sv[i][j])),
                                                value=round(float(Xh[te].iloc[i, j]), 2),
                                                shap=round(float(sv[i][j]), 3)) for j in top]))
        imp = pd.Series(np.abs(sv).mean(0), cols).sort_values(ascending=False)
        print("   top mean|SHAP|:", ", ".join(f"{k} {v:.2f}" for k, v in imp.head(6).items()))

    pd.DataFrame(rows).to_parquet("data/preds.parquet", index=False)
    Path("shared/preds.json").write_text(json.dumps(rows))
    Path("shared/metrics.json").write_text(json.dumps(metrics, indent=1))
    print(f"wrote shared/preds.json ({len(rows)} rows), shared/metrics.json")


if __name__ == "__main__":
    main()
