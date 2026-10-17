"""80 % ranges for a ship's wait, and a check that they are honest.

Usage: python model/wait_intervals.py [--visits data/cache/wait_visits_ais_crisis.parquet] [--months 2021-08-01,...]
                                      [--end 2021-11-16]
Needs the per-visit table that model/wait_forecast.py writes to data/cache/wait_visits_<ais dir>.parquet (run it with
a --start/--end that covers the months you test; the crisis numbers below used --start 2021-06-08 --end 2021-11-15).

Method (container-size ships, i.e. cargo >= 200 m): for a ship joining in month M, take the ships whose wait was
already known on the 1st of M (berthed before M, joined >= 30 days before M, so long waits are not missing) and the
spread of real wait / estimate among them. Range = today's estimate x [10th, 90th percentile] of that ratio.
Checked on the ships joining in M: about 80 % of real waits should land inside.
"""
import argparse
import numpy as np
import pandas as pd

LAG_D = 30


def ranges(v, months, end):
    v = v[v.big_cargo.astype(bool)].dropna(subset=["little", "reported"])
    v = v[(v.little > 0.5) & (v.reported > 0.5)]
    out = []
    for m0 in months:
        m1 = min(m0 + pd.offsets.MonthBegin(1), end)
        known = v[(v.t_berth < m0) & (v.join_day < m0 - pd.Timedelta(days=LAG_D))]
        te = v[(v.join_day >= m0) & (v.join_day < m1)].copy()
        if len(known) < 30 or te.empty:
            continue
        for est in ("little", "reported"):
            lo, md, hi = np.quantile(known.wait_d / known[est], [0.1, 0.5, 0.9])
            te[f"{est}_lo"], te[f"{est}_md"], te[f"{est}_hi"] = te[est] * lo, te[est] * md, te[est] * hi
        out.append(te)
    return pd.concat(out)


def report(p):
    print(f"{len(p)} container-size ships, {p.join_day.nunique()} join days")
    names = {"little": "ours (ships ahead / berths per day)", "reported": "published (7-day average)"}
    for est in ("little", "reported"):
        inside = (p.wait_d >= p[f"{est}_lo"]) & (p.wait_d <= p[f"{est}_hi"])
        by = inside.groupby(p.join_day.dt.to_period("M")).mean().round(2)
        print(f"{names[est]:38s} 80 % range holds the real wait for {inside.mean():.0%} "
              f"(below {(p.wait_d < p[f'{est}_lo']).mean():.0%}, above {(p.wait_d > p[f'{est}_hi']).mean():.0%}); "
              f"median width {(p[f'{est}_hi'] - p[f'{est}_lo']).median():.1f} d")
        print(f"{'':38s} by month: " + ", ".join(f"{k} {v:.0%}" for k, v in by.items()))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--visits", default="data/cache/wait_visits_ais_crisis.parquet")
    a.add_argument("--months", default="2021-08-01,2021-09-01,2021-10-01,2021-11-01")
    a.add_argument("--end", default="2021-11-16", help="exclusive; the crisis stops at the 2021-11-16 queuing rule")
    x = a.parse_args()
    report(ranges(pd.read_parquet(x.visits), pd.to_datetime(x.months.split(",")), pd.Timestamp(x.end)))
