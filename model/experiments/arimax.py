"""ARIMA / ARIMAX for the daily queue, same protocol as train.py --rolling.
usage: arimax.py DAILY TARGET TEST_START TEST_END [WEATHER...]
Each test month: choose the order by AIC on data before the month, fit, then issue forecasts each day t of the month
from data through t only (the fitted parameters are applied to the longer history; no refit inside the month).
Exog at day s = values known at the end of day s-1 (end-of-day queue, ships due within 24 h, loitering offshore,
gust forecast for day s issued on s-1). For h = 2, 3 the exog is held at its last known value.
"""
import sys, warnings
import numpy as np, pandas as pd
from statsmodels.tsa.statespace.sarimax import SARIMAX
sys.path.insert(0, "model")
import train as T  # noqa: E402
warnings.filterwarnings("ignore")

daily, target, t0, t1 = sys.argv[1:5]
d = pd.read_parquet(daily); d["date"] = pd.to_datetime(d.date); d = d.set_index("date").sort_index().asfreq("D")
for wf in sys.argv[5:]:
    w = pd.read_parquet(wf); w.index = pd.to_datetime(w.date)
    d = d.drop(columns=[c for c in w.columns if c in d.columns and c != "date"]).join(w.drop(columns="date"))
y = d[target].astype(float)
ex = pd.DataFrame(index=d.index)
for c in (f"{target}_eod", "inbound_eta24", "offshore_waiting"):
    if c in d and c != target:
        ex[c] = d[c].shift(1)
if "fc1_gust_max_kts" in d and d.fc1_gust_max_kts.notna().mean() > 0.5:
    ex["fc_gust_today"] = d.fc1_gust_max_kts  # forecast for day s, issued on day s-1
ex = ex.ffill().bfill()
ORDERS = [(1, 0, 0), (2, 0, 0), (1, 0, 1), (2, 0, 1), (1, 1, 1), (0, 1, 1)]
b = T.baselines(y, d.get(f"{target}_eod"))

out = {m: {h: {} for h in (1, 2, 3)} for m in ("arima", "arimax")}
for m0 in pd.date_range(t0, t1, freq="MS"):
    m1 = m0 + pd.offsets.MonthBegin(1)
    hist = y.index < m0
    for name, X in (("arima", None), ("arimax", ex)):
        fits = []
        for o in ORDERS:
            try:
                r = SARIMAX(y[hist], exog=None if X is None else X[hist], order=o, trend="c" if o[1] == 0 else "n").fit(disp=False)
                fits.append((r.aic, o, r))
            except Exception:
                pass
        _, order, res = min(fits, key=lambda z: z[0])
        for t in pd.date_range(m0 - pd.Timedelta(days=3), min(m1, pd.Timestamp(t1)) - pd.Timedelta(days=1)):
            upto = y.index <= t
            r = res.apply(y[upto], exog=None if X is None else X[upto])
            fx = None if X is None else pd.concat([X[upto].iloc[[-1]]] * 3).set_axis(
                pd.date_range(t + pd.Timedelta(days=1), periods=3))
            if X is not None and "fc_gust_today" in X:   # the gust forecast for t+1 is known on t
                fx.iloc[0, X.columns.get_loc("fc_gust_today")] = X.fc_gust_today.get(t + pd.Timedelta(days=1), np.nan)
            f = r.forecast(3, exog=fx)
            for h in (1, 2, 3):
                td = t + pd.Timedelta(days=h)
                if m0 <= td < m1 and td <= pd.Timestamp(t1):
                    out[name][h][td] = float(f.iloc[h - 1])
        print(f"{m0:%Y-%m} {name}: order {order}")

for h in (1, 2, 3):
    for name in ("arima", "arimax"):
        p = pd.Series(out[name][h]).sort_index()
        act = y.reindex(p.index)
        ok = act.notna() & pd.concat([b[k].shift(h).reindex(p.index) for k in b], axis=1).notna().all(axis=1)
        base = {k: T.mae(b[k].shift(h).reindex(p.index)[ok], act[ok]) for k in b}
        best = min(base, key=base.get)
        em = np.abs(p[ok] - act[ok]).values
        eb = np.abs(b[best].shift(h).reindex(p.index)[ok] - act[ok]).values
        print(f"h={h} {name:6s} n={ok.sum()} MAE {em.mean():.3f} vs best naive {best} {base[best]:.3f}: "
              f"skill {100 * (1 - em.mean() / base[best]):+.1f}% CI {T.block_bootstrap_skill(em, eb)} "
              f"| vs persistence {100 * (1 - em.mean() / base['persistence']):+.1f}% "
              f"{T.block_bootstrap_skill(em, np.abs(b['persistence'].shift(h).reindex(p.index)[ok] - act[ok]).values)}")
        pd.Series(out[name][h]).to_frame("pred").to_parquet(f"{sys.argv[1].replace('/', '_')}_{name}_h{h}.parquet".replace("data_", "/tmp/claude-1000/-workspaces-10-17/f760d318-02a0-407c-bf1c-a992cd63edde/scratchpad/ts_"))
