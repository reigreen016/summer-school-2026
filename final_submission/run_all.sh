#!/bin/bash
# 全パイプラインの実行例（データは connected folder にある前提）
set -eux
cd "$(dirname "$0")"
python3 01_extract_boundary.py r2kb13108 "$HOME/mnt/network/toyosu"   # 要 pyshp/shapely
python3 02_build_network.py
python3 03_michiyomi_scenes.py
python3 04_link_vlm_attach.py
python3 05_text_pca.py
python3 06_pp_basic_stats.py
for Y in 2018 2019 2020 2021; do
  python3 07_prep_trips.py $Y
  bash    08_gps_extract.sh $Y
  python3 09_build_gps_seq.py $Y
  python3 10_mapmatch.py                     # gps_seq_$Y.json を読む(スクリプト内の年を指定)
  python3 11_export_paths.py $Y
done
YEAR=2019 python3 12_obs_vs_shortest.py
YEAR=2019 python3 13_od_analysis.py
GMODE=none  YEARS=2019                      python3 14b_rl_run.py base
GMODE=covid YEARS=2018,2019,2020,2021       python3 14b_rl_run.py covid
GMODE=child YEARS=2021                      python3 14b_rl_run.py child
GMODE=gender YEARS=2018,2021 ATTRONLY=1     python3 14b_rl_run.py gender
BASE=14_rl_core.py TAG=pool NSTART=16       python3 15_multistart.py
python3 16_mnl_core.py
python3 17_figures.py
