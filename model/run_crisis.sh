#!/usr/bin/env bash
# Crisis (2021-06 .. 2022-03) chain, once the Overseer's shared/crisis/daily.parquet is on main.
# Weather/fog/waves come from pipeline/weather.py + ext_sources.py (cached in data/crisis/).
# Rolling-origin: each month from Sep 2021 is forecast by models fit on everything before it.
# From 2021-11-16 the ports moved the queue beyond 150 nm (out of AIS range): anchored counts fall for a reason the
# data can't see. Metrics are reported for the whole test span AND for the pre-change window separately.
set -euo pipefail
cd "$(dirname "$0")/.."
D=shared/crisis/daily.parquet
W="data/crisis/weather_daily.parquet data/crisis/ext_daily.parquet"
[[ -f data/crisis/weather_daily.parquet ]] || python3 pipeline/weather.py --start 2021-06-01 --end 2022-03-31 \
  --out data/crisis/weather_daily.parquet --json shared/crisis/weather_daily.json
[[ -f data/crisis/ext_daily.parquet ]] || python3 pipeline/ext_sources.py --start 2021-06-01 --end 2022-03-31 \
  --out data/crisis/ext_daily.parquet
python3 model/train.py --daily $D --weather $W --test-start 2021-09-01 --rolling --out-prefix shared/crisis
python3 model/train.py --daily $D --weather $W --test-start 2021-09-01 --test-end 2021-11-15 --rolling \
  --out-prefix data/crisis_prechange
python3 pipeline/emissions.py --daily $D --out shared/crisis/emissions.json
