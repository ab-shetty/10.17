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
PARAMS = dict(objective="l1", learning_rate=0.03, n_estimators=300, num_leaves=7, min_child_samples=15,
              subsample=0.8, subsample_freq=1, colsample_bytree=0.8, reg_lambda=1.0, verbose=-1, seed=0)


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
    f["departures_24h"] = d.n_departures_24h
    f["net_inflow_3d"] = (d.n_arrivals_24h - d.n_departures_24h).rolling(3).sum()
    f["avg_wait_h"] = d.avg_wait_hours.ffill()
    f["wind_max_kts"] = d.wind_max_kts
    f["gust_max_kts"] = d.gust_max_kts
    f["visibility_min_m"] = d.visibility_min_m
    f["wind_max_3d"] = d.wind_max_kts.rolling(3).max()
    f["is_holiday"] = d.is_holiday
    for c in ("klgb_vis_min_mi", "klgb_fog_hours", "wave_hs_max_m", "wave_period_max_s"):
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
        metrics[str(h)] = dict(mae_model=round(mae_m, 3), mae_baseline=round(mae_b, 3), n_test=int(te.sum()),
                               skill_pct=round(100 * (1 - mae_m / mae_b), 1))
        print(f"h={h}: MAE model {mae_m:.3f}  persistence {mae_b:.3f}  n={te.sum()}  "
              f"skill {metrics[str(h)]['skill_pct']}%")
        cols = Xh.columns
        for i, (issued, td) in enumerate(zip(d.index[te], tgt_date[te])):
            top = np.argsort(-np.abs(sv[i]))[:3]
            rows.append(dict(date=td.strftime("%Y-%m-%d"), issued=issued.strftime("%Y-%m-%d"), h=h,
                             actual=round(float(act.iloc[i]), 2), pred=round(float(pred.iloc[i]), 2),
                             baseline=round(float(base.iloc[i]), 2),
                             top_features=[dict(name=cols[j], value=round(float(Xh[te].iloc[i, j]), 2),
                                                shap=round(float(sv[i][j]), 3)) for j in top]))
        imp = pd.Series(np.abs(sv).mean(0), cols).sort_values(ascending=False)
        print("   top mean|SHAP|:", ", ".join(f"{k} {v:.2f}" for k, v in imp.head(6).items()))

    pd.DataFrame(rows).to_parquet("data/preds.parquet", index=False)
    Path("shared/preds.json").write_text(json.dumps(rows))
    Path("shared/metrics.json").write_text(json.dumps(metrics, indent=1))
    print(f"wrote shared/preds.json ({len(rows)} rows), shared/metrics.json")


if __name__ == "__main__":
    main()
