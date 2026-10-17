"""True holdout: train on ALL of 2024 (no weather-forecast features, since 2023 has no archived forecasts),
test on 2023 days the model has never seen. Uses train.py's own features / fit_all / predict / baselines.
usage: holdout2023.py TRAIN_DAILY TEST_DAILY TARGET
"""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, "model")
import train as T  # noqa: E402

tr_path, te_path, target = sys.argv[1], sys.argv[2], sys.argv[3]
T.TARGET = target
W = {"2024": ["data/weather_daily.parquet", "data/ext_daily.parquet"],
     "2023": ["data/y2023/weather_daily.parquet", "data/y2023/ext_daily.parquet"]}


def load(path, wfiles):
    d = pd.read_parquet(path)
    d["date"] = pd.to_datetime(d.date)
    d = d.set_index("date").sort_index().asfreq("D")
    for wf in wfiles:
        w = pd.read_parquet(wf); w.index = pd.to_datetime(w.date)
        d = d.drop(columns=[c for c in w.columns if c in d.columns and c != "date"]).join(w.drop(columns="date"))
    return d


dtr, dte = load(tr_path, W["2024"]), load(te_path, W["2023"])
res = {}
for h in (1, 2, 3):
    parts = {}
    for name, d in (("tr", dtr), ("te", dte)):
        X = T.features(d)
        X["target_dow"] = (d.index + pd.Timedelta(days=h)).dayofweek
        b = T.baselines(d[target], d.get(f"{target}_eod"))
        y = d[target].shift(-h)
        ok = y.notna() & b["blend"].notna()
        parts[name] = (X, b, y, ok)
    Xtr, btr, ytr, oktr = parts["tr"]; Xte, bte, yte, okte = parts["te"]
    cols = [c for c in Xtr.columns if c in Xte.columns]
    anchor = min(btr, key=lambda k: T.mae(btr[k][oktr], ytr[oktr]))
    m = T.fit_all(Xtr.loc[oktr, cols], (ytr - btr[anchor])[oktr])
    pred = bte[anchor][okte] + T.predict(m, "avg", Xte.loc[okte, cols])
    act = yte[okte]
    base = {k: T.mae(bte[k][okte], act) for k in bte}
    best = min(base, key=base.get)
    em, eb = np.abs(pred - act).values, np.abs(bte[best][okte] - act).values
    res[h] = dict(n=int(okte.sum()), anchor=anchor, mae_model=round(em.mean(), 3), best=best, mae_best=round(base[best], 3),
                  skill=round(100 * (1 - em.mean() / base[best]), 1), ci=T.block_bootstrap_skill(em, eb),
                  vs_persistence=round(100 * (1 - em.mean() / base["persistence"]), 1),
                  baselines={k: round(v, 3) for k, v in base.items()})
    print(f"h={h}: n={res[h]['n']} anchor(2024)={anchor} model MAE {em.mean():.3f} vs best naive {best} {base[best]:.3f}: "
          f"skill {res[h]['skill']}% CI {res[h]['ci']} | vs persistence {res[h]['vs_persistence']}% | {res[h]['baselines']}")
