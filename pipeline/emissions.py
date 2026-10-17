"""Emissions from ships idling at anchor in San Pedro Bay, per day, from AIS ship-hours at anchor.

Usage: python pipeline/emissions.py --daily data/daily.parquet --out shared/emissions.json
       python pipeline/emissions.py --daily shared/crisis/daily.parquet --out shared/crisis/emissions.json

Method = the ports' own inventory method (Port of Los Angeles Inventory of Air Emissions 2023, Starcrest, Aug 2024):
  energy (kWh) = ship-hours at anchor x anchorage hotelling load (aux engines + aux boilers), by ship class
  emissions    = energy x emission factor (g/kWh), 0.1 % S marine gas oil (CARB fuel rule).
Ship classes from AIS (type code + length): tankers / cargo < 250 m (bulk, general, car carriers) /
cargo >= 250 m (large container ships). Loads are averages of the inventory's per-class defaults (below).
Aux engines use the Tier II medium-speed factors (most of the fleet); a Tier I fleet would be ~16 % higher NOx.
Cross-checks (POLA alone, short tons -> metric below): 2023 at-anchorage hotelling 118 tons NOx, 12,981 t CO2e;
2021 (the backlog) 2,848 tons NOx = 48 % of all POLA ship NOx that year.
"""
import argparse
import json
from pathlib import Path
import pandas as pd

# anchorage hotelling loads, kW. Table 3.2 (aux engines) and Table 3.5 (aux boilers), POLA EI 2023.
LOAD_KW = {
    # Tanker - Chemical / Handysize / Panamax: aux 409 / 560 / 401, boiler 208 / 321 / 512
    "tanker": dict(aux=(409 + 560 + 401) / 3, boiler=(208 + 321 + 512) / 3),
    # Bulk / General Cargo / Auto Carrier: aux 250 / 180 / 494, boiler 184 / 227 / 259
    "cargo_small": dict(aux=(250 + 180 + 494) / 3, boiler=(184 + 227 + 259) / 3),
    # Container 8000..14000 TEU: aux 1052,1174,1181,1134,1212,1319,1155; boiler 588,722,656,452,374,558,532
    "cargo_big": dict(aux=(1052 + 1174 + 1181 + 1134 + 1212 + 1319 + 1155) / 7,
                      boiler=(588 + 722 + 656 + 452 + 374 + 558 + 532) / 7),
}
# g/kWh, 0.1 % S MGO. Table 3.13 (aux, medium speed, Tier II) and Table 3.12 (steam/aux boilers).
EF = {"aux": dict(nox=10.5, pm25=0.17, co2=696), "boiler": dict(nox=1.97, pm25=0.186, co2=962)}
FUEL_G_PER_KWH = {k: v["co2"] / 3.206 for k, v in EF.items()}  # MGO: 3.206 t CO2 per t fuel

# Cross-check against POLA's own 2023 inventory. Table 3.7 (anchorage hours = avg hours x vessel count per class)
# sums to ~11,300 ship-hours behind the 118 t NOx at-anchorage total => ~250 kg NOx per ship-day. POLA counts only
# ships that then call POLA, and its tanker classes stop at Panamax: crude tankers anchored for Long Beach's crude
# terminals / refineries, and ships waiting on orders or bunkers, are outside it. We count every anchored cargo ship
# and tanker in the bay (what the harbor neighborhoods breathe), at a deliberately conservative per-ship rate.
# POLA inventories report criteria pollutants in SHORT tons (tpy) and GHG in metric tonnes; converted to metric here.
ST = 0.907185
POLA_2023 = dict(anchorage_ship_hours=11312, nox_t=round(118.0 * ST, 1), co2e_t=12981,
                 nox_kg_per_ship_day=round(118.0 * ST * 1e3 / (11312 / 24), 1),
                 source="POLA Inventory of Air Emissions CY2023, Tables 3.7 and 3.16 (hotelling at-anchorage)")
# 2021 (Table 3.16 of the CY2021 report): at-anchorage hotelling = 2,848 short tons NOx, 60.8 PM2.5, 261,649 t CO2e;
# 48 % of all POLA ocean-going-vessel NOx that year (5,956 short tons). POLA calls only; Long Beach not included.
POLA_2021 = dict(nox_t=round(2848 * ST), pm25_t=round(60.8 * ST, 1), co2e_t=261649, share_of_pola_ogv_nox=0.48,
                 source="POLA Inventory of Air Emissions CY2021, Table 3.16 (hotelling at-anchorage)")
# CARB fact sheets (SPBP = both ports), short tons/day NOx from ocean-going vessels at anchor.
# Feb 2023 update, Fig. 2 insets: business-as-usual averages; Table 1: EXCESS over BAU (containers+cruise+tankers).
CARB_BAU_TPD = dict(tanker=1.5, container=0.2, cruise=0.6)
CARB_EXCESS_TPD = {"2021-11": 17.9, "2021-12": 7.0, "2022-01": 4.3, "2022-02": 3.5, "2022-03": 2.6,
                   "2022-04": 2.0, "2022-05": 0.9, "2022-06": 0.4}
# Nov 2021 sheet: "as of October 2021 ... 20 tons per day (tpd) of NOx and 0.5 tpd of PM" above pre-pandemic,
# with up to 79 container vessels (109 total) at anchor; NOx "roughly equivalent to ... 5.8 million passenger cars".
CARB_OCT2021 = dict(excess_nox_tpd=20, excess_pm_tpd=0.5, container_ships_at_anchor=79, ships_at_anchor=109,
                    nox_equiv_passenger_cars=5.8e6, pm_equiv_class8_trucks=100000)


def main(daily, out):
    d = pd.read_parquet(daily)
    d["date"] = pd.to_datetime(d.date)
    if not {"n_anchored_tanker", "n_anchored_cargo", "n_anchored_bigcargo"} <= set(d.columns):
        # fallback for daily tables without the type split: 2024 mix (74 % tanker, 22 % small cargo, 4 % big cargo)
        print("WARNING: no per-type anchored counts; using the 2024 fleet mix for all anchored ships")
        d = d.assign(n_anchored_tanker=d.n_anchored * 0.74, n_anchored_cargo=d.n_anchored * 0.26,
                     n_anchored_bigcargo=d.n_anchored * 0.04)
    hours = pd.DataFrame({  # mean hourly count x 24 = ship-hours at anchor that day
        "tanker": d.n_anchored_tanker * 24,
        "cargo_small": (d.n_anchored_cargo - d.n_anchored_bigcargo).clip(lower=0) * 24,
        "cargo_big": d.n_anchored_bigcargo * 24,
    })
    res = pd.DataFrame({"date": d.date.dt.strftime("%Y-%m-%d"), "ship_hours": hours.sum(axis=1)})
    for pol in ("nox", "pm25", "co2"):
        res[f"{pol}_t"] = sum(hours[c] * LOAD_KW[c][src] * EF[src][pol] for c in hours for src in ("aux", "boiler")) / 1e6
    res["fuel_t"] = sum(hours[c] * LOAD_KW[c][src] * FUEL_G_PER_KWH[src] for c in hours for src in ("aux", "boiler")) / 1e6
    res["ship_days"] = res.ship_hours / 24
    if "offshore_waiting" in d:
        # ships loitering < 60 nm offshore (< 3 kn, engines mostly off): same hotelling loads; mostly container
        # ships in the 2021 backlog (45 of 52 on 2021-10-25), so the large-cargo class is used. Reported separately:
        # these emissions are 10-60 nm out, not over the harbor neighborhoods.
        oh = d.offshore_waiting.fillna(0).values * 24
        for pol in ("nox", "pm25", "co2"):
            res[f"offshore_{pol}_t"] = sum(oh * LOAD_KW["cargo_big"][src] * EF[src][pol] for src in ("aux", "boiler")) / 1e6
        res["offshore_ship_days"] = oh / 24
    tot = res[["ship_days", "nox_t", "pm25_t", "co2_t", "fuel_t"]].sum()
    summary = dict(start=res.date.iloc[0], end=res.date.iloc[-1], days=len(res),
                   ship_days_at_anchor=round(float(tot.ship_days)), nox_t=round(float(tot.nox_t), 1),
                   pm25_t=round(float(tot.pm25_t), 2), co2_t=round(float(tot.co2_t)), fuel_t=round(float(tot.fuel_t)),
                   nox_kg_per_ship_day=round(float(tot.nox_t / tot.ship_days * 1000), 1),
                   peak_day=res.loc[res.nox_t.idxmax(), "date"], peak_day_nox_kg=round(float(res.nox_t.max() * 1000)),
                   **({} if "offshore_nox_t" not in res else dict(
                       offshore_ship_days=round(float(res.offshore_ship_days.sum())),
                       offshore_nox_t=round(float(res.offshore_nox_t.sum()), 1),
                       offshore_pm25_t=round(float(res.offshore_pm25_t.sum()), 2),
                       offshore_co2_t=round(float(res.offshore_co2_t.sum())),
                       offshore_note="loitering ships < 60 nm, < 3 kn, at large-container-ship hotelling loads. Valid "
                                     "for the 2021-22 backlog (mostly queued container ships); in normal times these "
                                     "slow ships are a mixed fleet, so do not headline the offshore number for 2024")),
                   method="POLA Inventory of Air Emissions 2023: anchorage hotelling loads (Tables 3.2, 3.5) x "
                          "0.1% S MGO emission factors (Tables 3.12, 3.13); ship-hours at anchor from AIS",
                   scope="every cargo ship and tanker anchored in San Pedro Bay (both ports, plus refinery/crude "
                         "tankers and ships waiting on orders), not only POLA calls",
                   cross_check=dict(pola_2023_inventory=POLA_2023, pola_2021_inventory=POLA_2021,
                                    note="our rate per ship-day is about half POLA's implied rate (conservative); "
                                         "our ship-days are higher because POLA counts only its own calls"))
    # month-by-month vs CARB (short tons/day): ours excludes cruise ships (AIS types 70-89 only)
    mon = res.assign(m=res.date.str[:7]).groupby("m").agg(nox_t=("nox_t", "mean"), days=("nox_t", "size"))
    carb_bau = CARB_BAU_TPD["tanker"] + CARB_BAU_TPD["container"]
    summary["vs_carb_monthly"] = [dict(month=m, ours_nox_tpd_short=round(r.nox_t / ST, 2),
                                       carb_nox_tpd_short=round(carb_bau + CARB_EXCESS_TPD.get(m, 0), 1)
                                       if m in CARB_EXCESS_TPD or m >= "2022-07" or m < "2020-11" else None)
                                  for m, r in mon.iterrows()]
    summary["carb"] = dict(bau_nox_tpd_short=CARB_BAU_TPD, excess_nox_tpd_short=CARB_EXCESS_TPD, oct_2021=CARB_OCT2021,
                           ours_mean_nox_tpd_short=round(float(res.nox_t.mean() / ST), 2),
                           source="CARB, Emissions Impact of Ships Anchored at POLA/POLB (Nov 2021); Emissions "
                                  "Impacts of Vessel Congestion ... February 2023 Update (Table 1, Fig. 2)")
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(dict(summary=summary, daily=json.loads(res.round(3).to_json(orient="records"))), indent=None))
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    a = argparse.ArgumentParser()
    a.add_argument("--daily", default="data/daily.parquet")
    a.add_argument("--out", default="shared/emissions.json")
    x = a.parse_args()
    main(x.daily, x.out)
