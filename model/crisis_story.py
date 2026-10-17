"""Crisis money shot: chart series + the days the forecast turned up before the queue did.

Usage: python model/crisis_story.py [--daily data/crisis/daily_a.parquet] [--preds shared/crisis/preds.json]
Writes shared/crisis/chart.json and shared/crisis/episodes.json, and exports the episode days as map replays
(shared/crisis/replay/) when the raw crisis AIS is on this machine.

A "lead day" = a 1-day-ahead forecast that rose above BOTH naive baselines (tomorrow = today, 7-day mean) on a day
the queue really did rise. Score = min(forecast - best naive, actual - best naive): large only when the model was
both early and right. 2021 has no archived weather forecasts, so the crisis model sees arrivals and offshore
loitering coming, not storms: ships loitering within 60 nm today are tomorrow's anchorage queue.
"""
import argparse
import json
from pathlib import Path
import pandas as pd

WINDOW = ("2021-09-01", "2021-10-31")


def main(daily, preds_path, n=3, min_gap_days=5, window=WINDOW, out_dir=None):
    d = pd.read_parquet(daily)
    d["date"] = pd.to_datetime(d.date)
    d = d.set_index("date").sort_index()
    p = pd.DataFrame(json.loads(Path(preds_path).read_text()))
    target = json.loads(Path(preds_path).with_name("metrics.json").read_text())["1"].get("target", "n_anchored")
    p["date"] = pd.to_datetime(p.date)
    y = d[target]
    ma7 = y.rolling(7, min_periods=4).mean()
    h1 = p[p.h == 1].set_index("date")
    h2 = p[p.h == 2].set_index("date")
    chart = pd.DataFrame({
        "actual": y, "forecast_1d": h1.pred, "forecast_2d": h2.pred,
        "tomorrow_equals_today": y.shift(1), "seven_day_mean": ma7.shift(1),
        "n_anchored": d.n_anchored, "offshore_waiting": d.get("offshore_waiting"), "inbound_60nm": d.get("inbound_60nm"),
        "arrivals_24h": d.get("n_arrivals_24h"), "avg_wait_h": d.get("avg_wait_hours"),
    }).loc[window[0]:window[1]]
    out = Path(out_dir or Path(preds_path).parent)
    out.mkdir(parents=True, exist_ok=True)
    rec = json.loads(chart.reset_index().assign(date=lambda x: x.date.dt.strftime("%Y-%m-%d")).round(2)
                     .to_json(orient="records"))
    (out / "chart.json").write_text(json.dumps(dict(target=target, window=list(window),
        note="forecast_Nd = forecast for that date issued N days earlier; baselines are what each naive rule "
             "would have said for that date", series=rec)))

    c = chart.dropna(subset=["forecast_1d", "tomorrow_equals_today", "seven_day_mean"])
    naive = c[["tomorrow_equals_today", "seven_day_mean"]].max(axis=1)
    score = pd.concat([c.forecast_1d - naive, c.actual - naive], axis=1).min(axis=1)
    picks = []
    for day, sc in score.sort_values(ascending=False).items():
        if sc <= 0 or len(picks) >= n:
            break
        if all(abs((day - q).days) >= min_gap_days for q, _ in picks):
            picks.append((day, sc))
    eps = []
    for day, sc in sorted(picks):
        issued = day - pd.Timedelta(days=1)
        r = c.loc[day]
        prev = d.loc[issued]
        week = d.loc[issued - pd.Timedelta(days=7)] if issued - pd.Timedelta(days=7) in d.index else prev
        top = h1.loc[day, "top_features"]
        up = [f for f in top if f["shap"] > 0]  # only the drivers that pushed the forecast UP
        lo, lo_wk = prev.get("offshore_waiting", float("nan")), week.get("offshore_waiting", float("nan"))
        eps.append(dict(
            start=(issued - pd.Timedelta(days=1)).strftime("%Y-%m-%d"), end=day.strftime("%Y-%m-%d"),
            replay_days=[issued.strftime("%Y-%m-%d"), day.strftime("%Y-%m-%d")],
            title=f"{day:%b %-d, %Y}: the forecast turned up before the queue did",
            why=(f"On {issued:%b %-d} {lo:.0f} ships were loitering within 60 nm (vs {lo_wk:.0f} a week earlier) and "
                 f"{prev.get('inbound_60nm', float('nan')):.0f} were inbound."
                 + (" Ships loitering offshore today are tomorrow's anchorage queue." if lo > lo_wk else "")),
            model_note=(f"Forecast for {day:%b %-d}: {r.forecast_1d:.0f} ships waiting. Tomorrow-equals-today said "
                        f"{r.tomorrow_equals_today:.0f}, the 7-day mean {r.seven_day_mean:.0f}. Actual: {r.actual:.0f}. "
                        + (f"Why it went up: " + "; ".join(f["phrase"].split(";")[0] for f in up[:2]) + "." if up else "")),
            lead_score=round(float(sc), 2)))
    (out / "episodes.json").write_text(json.dumps(eps, indent=1))
    print(json.dumps(eps, indent=1))
    return [x for e in eps for x in e["replay_days"]]


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--daily", default="data/crisis/daily_a.parquet")
    a.add_argument("--preds", default="shared/crisis/preds.json")
    a.add_argument("--no-replay", action="store_true")
    a.add_argument("--window", nargs=2, default=list(WINDOW))
    a.add_argument("--out-dir")
    x = a.parse_args()
    days = main(x.daily, x.preds, window=x.window, out_dir=x.out_dir)
    if not x.no_replay and Path("data/ais_crisis").exists():
        import subprocess
        subprocess.run(["python3", "pipeline/export_replay.py", *days, "--ais-dir", "data/ais_crisis",
                        "--approach-dir", "data/approach_crisis", "--out-dir", "shared/crisis/replay"], check=True)
