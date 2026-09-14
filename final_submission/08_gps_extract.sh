#!/bin/bash
# 08_gps_extract.sh : locData から豊洲bbox内・対象ユーザのGPS点を抽出
# 使い方: bash 08_gps_extract.sh 2019
# 入力 : $PP/locData_toyosu_$Y.csv, $WORK/users$Y.txt (07で作成)
# 出力 : $WORK/loc${Y}_toyosu.csv, $WORK/loc${Y}_tgt.csv
set -eu
Y=$1
PP="${PP:-$HOME/mnt/PP/Toyosu2018-2021}"
WORK="${WORK:-$HOME/tmpwork}"
# 列: ID,UserID,Time,Lat(WGS),Lon(WGS),mesh_code  → $2,$3,$4,$5 を出力
awk -F, 'NR>1 && $4>35.636 && $4<35.667 && $5>139.773 && $5<139.808 {print $2","$3","$4","$5}' \
    "$PP/locData_toyosu_$Y.csv" > "$WORK/loc${Y}_toyosu.csv"
awk -F, 'NR==FNR{u[$1];next} ($1 in u)' "$WORK/users$Y.txt" "$WORK/loc${Y}_toyosu.csv" \
    > "$WORK/loc${Y}_tgt.csv"
echo "$Y: bbox内 $(wc -l < "$WORK/loc${Y}_toyosu.csv") 点 / 対象ユーザ $(wc -l < "$WORK/loc${Y}_tgt.csv") 点"
