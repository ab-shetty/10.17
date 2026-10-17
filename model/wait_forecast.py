"""Forecast how long a ship joining the queue will wait (Little's law) vs the wait reported at the time.

Usage: python model/wait_forecast.py --ais-dir data/ais_crisis --approach-dir data/approach_crisis \
           --start 2021-09-01 --end 2021-10-31 --out shared/crisis/wait.json
       python model/wait_forecast.py --ais-dir data/ais --approach-dir data/approach --start 2024-01-15 \
           --end 2024-12-15 --out shared/wait.json

Per ship visit (cargo + tankers; container-ship-sized cargo reported separately):
  join   = first "waiting" ping: anchored in the bay (build_daily rules) or loitering < 60 nm offshore (< 3 kn, not at
           another terminal), after not having been at a berth for 24 h
  berth  = first moored ping in a berth cell after join;   actual wait = berth - join (days)
Forecasts for a ship that joins on day t (everything known by the end of day t-1, so no peeking):
  little  = Q / mu: Q = ships waiting at the end of day t-1 (distinct ships waiting in its last hour),
            mu = ships that reached a berth after waiting, per day, mean of the 7 days to t-1
  reported = mean actual wait of ships that reached a berth in the 7 days to t-1 (what the industry quoted: it is
            backward-looking, so it lags a growing queue)
Visits whose berth is unseen (data ends / ship diverted) are dropped; joins are restricted to [start, end] and the data
must extend well past `end` so long waits are observed (censoring bias otherwise, noted in the output).
"""
import argparse
import json
from glob import glob
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))
from build_daily import ANCHOR_BOX, CELL, OTHER_TERMINAL  # noqa: E402

MAX_WAIT_D = 45
FUEL_USD_T = 780  # MGO, pipeline/notes/fuel_prices.md


def events(ais_dir, approach_dir):
    b = ANCHOR_BOX
    c = duckdb.connect()
    c.execute("SET memory_limit='4GB'")
    ais = [f for f in sorted(glob(f"{ais_dir}/*.parquet"))]
    appr = [f for f in sorted(glob(f"{approach_dir}/*.parquet"))]
    bay = c.sql(f"""
      WITH p AS (
        SELECT mmsi, time_bucket(INTERVAL 10 MINUTE, ts) AS t, arg_max(lat, ts) AS lat, arg_max(lon, ts) AS lon,
               arg_max(sog, ts) AS sog, arg_max(status, ts) AS status, max(vessel_type) AS vt, max(length) AS len
        FROM read_parquet({ais}) GROUP BY 1, 2),
      q AS (SELECT p.*, bc.cy IS NOT NULL AS in_berth FROM p
            LEFT JOIN 'data/berth_cells.parquet' bc ON floor(p.lat/{CELL})::INT = bc.cy AND floor(p.lon/{CELL})::INT = bc.cx)
      SELECT mmsi, t, vt, len,
             CASE WHEN status = 1 AND sog < 0.5 AND NOT in_berth AND lat BETWEEN {b['lat0']} AND {b['lat1']}
                       AND lon BETWEEN {b['lon0']} AND {b['lon1']} THEN 'wait'
                  WHEN (status = 5 OR sog < 0.5) AND in_berth THEN 'berth' ELSE NULL END AS ev
      FROM q""").df()
    off = c.sql(f"""
      SELECT mmsi, t10 AS t, 'wait' AS ev FROM read_parquet({appr})
      WHERE sog < 3 AND NOT coalesce(({OTHER_TERMINAL}), false)
        AND sqrt(power((lat - 33.70) * 60, 2) + power((lon + 118.20) * 60 * cos(radians(33.7)), 2)) < 60""").df()
    types = bay.groupby("mmsi").agg(vt=("vt", "max"), len=("len", "max"))
    e = pd.concat([bay.dropna(subset=["ev"])[["mmsi", "t", "ev"]], off]).sort_values(["mmsi", "t"])
    return e, types


def visits(e):
    """join -> berth pairs per ship."""
    out = []
    for mmsi, g in e.groupby("mmsi", sort=False):
        last_berth, join = None, None
        for t, ev in zip(g.t.values, g.ev.values):
            if ev == "berth":
                if join is not None:
                    out.append((mmsi, join, t))
                    join = None
                last_berth = t
            elif join is None and (last_berth is None or t - last_berth > np.timedelta64(24, "h")):
                join = t
    v = pd.DataFrame(out, columns=["mmsi", "t_join", "t_berth"])
    v["wait_d"] = (v.t_berth - v.t_join) / pd.Timedelta(days=1)
    return v[(v.wait_d > 0.25) & (v.wait_d < MAX_WAIT_D)]  # < 6 h = straight to berth (not a queue)


def main(ais_dir, approach_dir, start, end, out, refresh=False, emissions=None):
    cache = Path(f"data/cache/wait_events_{Path(ais_dir).name}.parquet")
    if cache.exists() and not refresh:
        e = pd.read_parquet(cache)
        types = pd.read_parquet(cache.with_suffix(".types.parquet"))
    else:
        e, types = events(ais_dir, approach_dir)
        cache.parent.mkdir(parents=True, exist_ok=True)
        e.to_parquet(cache)
        types.to_parquet(cache.with_suffix(".types.parquet"))
    v = visits(e).join(types, on="mmsi")
    v["big_cargo"] = v.vt.between(70, 79) & (v.len >= 200)
    v["join_day"] = v.t_join.dt.normalize()
    v["berth_day"] = v.t_berth.dt.normalize()
    data_end = e.t.max()
    days = pd.date_range(e.t.min().normalize(), data_end.normalize(), freq="D")

    # Little's law per queue: container-size cargo ships and the rest use different berths, so each class gets its own
    # Q (distinct ships of that class with a "wait" ping in the last hour of day t-1) and mu (its berthings per day).
    e = e.reset_index(drop=True).join(types, on="mmsi")
    e["big_cargo"] = e.vt.between(70, 79) & (e.len >= 200)
    lasth = e[(e.ev == "wait") & (e.t.dt.hour == 23)].assign(day=lambda x: x.t.dt.normalize())
    series = {}
    for cls in (True, False):
        Qc = lasth[lasth.big_cargo == cls].groupby("day").mmsi.nunique().reindex(days, fill_value=0)
        vc = v[v.big_cargo == cls]
        mu = vc.groupby("berth_day").size().reindex(days, fill_value=0).rolling(7).mean()
        rp = vc.groupby("berth_day").wait_d.agg(["sum", "count"]).reindex(days, fill_value=0)
        series[cls] = dict(Q=Qc, mu=mu, little=Qc / mu, reported=rp["sum"].rolling(7).sum() / rp["count"].rolling(7).sum())

    j = v[(v.join_day >= start) & (v.join_day <= end)].copy()
    prev = j.join_day - pd.Timedelta(days=1)
    for cls in (True, False):
        m = j.big_cargo == cls
        j.loc[m, "little"] = series[cls]["little"].reindex(prev[m]).values
        j.loc[m, "reported"] = series[cls]["reported"].reindex(prev[m]).values
        # queue trend known on the issue day: change in this class's queue over the 14 days to t-1
        j.loc[m, "q_trend"] = (series[cls]["Q"] - series[cls]["Q"].shift(14)).reindex(prev[m]).values
    j = j.replace([np.inf, -np.inf], np.nan).dropna(subset=["little", "reported"])
    Q = series[True]["Q"]
    mu7 = series[True]["mu"]
    reported7 = series[True]["reported"]

    def score(x):
        return dict(n=int(len(x)), actual_mean_d=round(float(x.wait_d.mean()), 2),
                    mae_little_d=round(float((x.little - x.wait_d).abs().mean()), 2),
                    mae_reported_d=round(float((x.reported - x.wait_d).abs().mean()), 2),
                    bias_little_d=round(float((x.little - x.wait_d).mean()), 2),
                    bias_reported_d=round(float((x.reported - x.wait_d).mean()), 2))
    # what an operator would publish: the mean wait of ships joining each day (container-size ships)
    jb = j[j.big_cargo].groupby("join_day").agg(wait_d=("wait_d", "mean"), little=("little", "first"),
                                                 reported=("reported", "first"))
    res = dict(window=[start, end], data_end=str(data_end), all=score(j), big_cargo=score(j[j.big_cargo]),
               big_cargo_daily_mean=score(jb), other=score(j[~j.big_cargo]),
               censoring_note=f"visits whose berth was not seen by {data_end:%Y-%m-%d} are dropped; waits > "
                              f"{MAX_WAIT_D} d dropped; joins near the window end are biased toward short waits")
    # calm vs build-up: does the reported (lagging) figure only go wrong while the queue grows?
    j["regime"] = np.where(j.q_trend >= 5, "growing", np.where(j.q_trend <= -5, "shrinking", "steady"))
    res["by_regime"] = {g: score(x) for g, x in j.groupby("regime")}
    # cost of the gap: ship-days a ship spent waiting beyond what it was told (sum of positive under-statements),
    # priced at the in-bay hotelling rates of the same period (emissions.json: fuel and NOx per ship-day at anchor)
    if emissions and Path(emissions).exists():
        es = json.loads(Path(emissions).read_text())["summary"]
        fuel_d, nox_d = es["fuel_t"] / es["ship_days_at_anchor"], es["nox_kg_per_ship_day"]
        res["gap_cost"] = {}
        for k in ("reported", "little"):
            under = (j.wait_d - j[k]).clip(lower=0).sum()
            over = (j[k] - j.wait_d).clip(lower=0).sum()
            res["gap_cost"][k] = dict(ship_days_longer_than_told=round(float(under)),
                                      ship_days_shorter_than_told=round(float(over)),
                                      fuel_t=round(float(under * fuel_d)), fuel_usd_m=round(float(under * fuel_d * FUEL_USD_T / 1e6), 1),
                                      nox_t=round(float(under * nox_d / 1000), 1))
        # the defensible number: the NET (systematic) understatement, bias x visits. The per-ship sums above are mostly
        # scatter of individual waits around any average (they are as large in calm 2024), so don't headline them.
        net = float(-(j.reported - j.wait_d).sum())
        res["gap_cost"]["net_understatement"] = dict(
            ship_days=round(net), fuel_t=round(net * fuel_d), fuel_usd_m=round(net * fuel_d * FUEL_USD_T / 1e6, 1),
            nox_t=round(net * nox_d / 1000, 1), co2_t=round(net * es["co2_t"] / es["ship_days_at_anchor"]),
            note="sum over joining ships of (actual wait - reported wait the day before); positive = the published "
                 "figure was too short on net. Headline this one, not the per-ship sums.")
        res["gap_cost"]["note"] = (f"{len(j)} visits joining in the window. 'longer than told' = sum over ships of max(0, actual wait - "
                                   f"the figure available the day before it joined): idle time nobody planned for, which slow steaming "
                                   f"could have moved to sea. Priced at {fuel_d:.1f} t fuel and {nox_d:.0f} kg NOx per ship-day at "
                                   f"anchor ({emissions}) and ${FUEL_USD_T}/t MGO; ships loitering offshore are priced the same (an "
                                   f"approximation).")
    for k in ("all", "big_cargo", "big_cargo_daily_mean", "other"):
        r = res[k]
        r["skill_pct"] = round(100 * (1 - r["mae_little_d"] / r["mae_reported_d"]), 1) if r["mae_reported_d"] else None
    # daily series for the chart: container-size ships
    daily = pd.DataFrame({"date": days.strftime("%Y-%m-%d"), "ships_waiting_eod": Q.values, "berths_per_day_7d": mu7.values,
                          "little_wait_d": (Q / mu7).values, "reported_wait_7d": reported7.values})
    jd = j[j.big_cargo].groupby("join_day").wait_d.mean()
    daily["actual_wait_of_ships_joining_next_day"] = jd.reindex(days + pd.Timedelta(days=1)).values
    res["daily"] = json.loads(daily.round(2).to_json(orient="records"))
    # weekly means for the chart (container-size ships, by the Monday of the week they joined the queue)
    wk = j[j.big_cargo].assign(week=lambda x: (x.join_day - pd.to_timedelta(x.join_day.dt.dayofweek, unit="D")))
    wk = wk.groupby("week").agg(real_d=("wait_d", "mean"), reported_d=("reported", "mean"),
                                little_d=("little", "mean"), n=("wait_d", "size")).reset_index()
    wk["week"] = wk.week.dt.strftime("%Y-%m-%d")
    res["weekly"] = json.loads(wk.round(2).to_json(orient="records"))
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(res))
    print(json.dumps({k: res[k] for k in ("window", "data_end", "all", "big_cargo", "big_cargo_daily_mean", "other", "by_regime", "gap_cost") if k in res}, indent=1))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--ais-dir", default="data/ais_crisis")
    a.add_argument("--approach-dir", default="data/approach_crisis")
    a.add_argument("--start", default="2021-09-01")
    a.add_argument("--end", default="2021-10-31")
    a.add_argument("--out", default="shared/crisis/wait.json")
    a.add_argument("--emissions", help="emissions.json of the same period, to price the gap (fuel, NOx per ship-day)")
    a.add_argument("--refresh", action="store_true", help="re-extract events (after new days were pulled)")
    x = a.parse_args()
    main(x.ais_dir, x.approach_dir, x.start, x.end, x.out, x.refresh, x.emissions)
