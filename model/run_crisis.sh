#!/usr/bin/env bash
# Crisis (2021-06 .. 2022-03) chain.
# Target = n_waiting = ships anchored in the bay + loitering < 60 nm offshore (on the peak day 2021-10-25 half the
# queue was loitering; anchored + loitering ~= the Marine Exchange's count). Needs offshore_waiting, which comes from
# A's own pull (pipeline/extract_csv2021.py -> data/ais_crisis + data/approach_crisis). Use the Overseer's
# shared/crisis/daily.parquet instead if it has offshore_waiting:  CRISIS_DAILY=shared/crisis/daily.parquet
# Rolling-origin: each month from Sep 2021 is forecast by models fit on everything before it.
# From 2021-11-16 the ports moved the queue beyond 150 nm (out of AIS range): counts fall for a reason the data can't
# see. Metrics are reported for the whole span AND for the pre-change window separately.
set -euo pipefail
cd "$(dirname "$0")/.."
W="data/crisis/weather_daily.parquet data/crisis/ext_daily.parquet"
[[ -f data/crisis/weather_daily.parquet ]] || python3 pipeline/weather.py --start 2021-06-01 --end 2022-03-31 \
  --out data/crisis/weather_daily.parquet --json shared/crisis/weather_daily.json
[[ -f data/crisis/ext_daily.parquet ]] || python3 pipeline/ext_sources.py --start 2021-06-01 --end 2022-03-31 \
  --out data/crisis/ext_daily.parquet
D=${CRISIS_DAILY:-data/crisis/daily_a.parquet}
if [[ $D == data/crisis/daily_a.parquet ]]; then
  python3 pipeline/build_daily.py --ais-dir data/ais_crisis --approach-dir data/approach_crisis \
    --weather data/crisis/weather_daily.parquet --ext data/crisis/ext_daily.parquet \
    --out $D --out-json shared/crisis/daily.json --berth-in data/berth_cells.parquet --null-outages
  cp $D shared/crisis/daily.parquet
fi
T=${TARGET:-n_waiting}
python3 model/train.py --daily $D --weather $W --test-start 2021-09-01 --rolling --target $T --out-prefix shared/crisis
python3 model/train.py --daily $D --weather $W --test-start 2021-09-01 --test-end 2021-11-15 --rolling --target $T \
  --out-prefix data/crisis_prechange
python3 pipeline/emissions.py --daily $D --out shared/crisis/emissions.json
python3 model/crisis_story.py --daily $D --preds shared/crisis/preds.json
