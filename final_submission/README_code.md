# 豊洲・街路景観言語化データを用いた歩行者経路選択分析 — コード一式

`network/toyosu/code/` に収録。すべて Python 3.10 / bash で動作する。

## 実行環境

```bash
pip install -r requirements.txt
```

| パッケージ | 用途 |
|---|---|
| pyarrow | michiyomi parquet の読み込み |
| numpy / scipy | 疎行列解法・最尤推定 |
| matplotlib / japanize-matplotlib | 作図（日本語フォント IPAexGothic） |
| fugashi / unidic-lite | 形態素解析 |
| wordcloud | ワードクラウド |
| pyshp / shapely | e-Stat シェープファイルの読み込み・結合（01のみ） |

パスは `00_config.py` で環境変数から設定する。既定値は連携フォルダの構成に合わせてある。

```bash
export PP=$HOME/mnt/PP/Toyosu2018-2021          # PP調査データ
export NET=$HOME/mnt/network/tokyo-metropolitan-area  # 首都圏ネットワーク
export MICHI=$HOME/mnt/michiyomi-tokyo-streetscape    # michiyomi
export OUT=$HOME/mnt/network/toyosu              # 成果物の出力先
export WORK=$HOME/tmpwork                        # 中間ファイル
```

## パイプライン

| # | スクリプト | 処理 | 主な出力 |
|---|---|---|---|
| 00 | `00_config.py` | 共通設定・座標変換・内外判定 | （import用） |
| 01 | `01_extract_boundary.py` | e-Stat小地域境界から豊洲1〜6丁目を抽出・結合 | `toyosu_boundary.geojson`, `toyosu_chome_boundary.geojson` |
| 02 | `02_build_network.py` | 首都圏徒歩NWから豊洲リンクを切り出し（Lat/Lon入替の補正を含む） | `toyosu_walk_link_WD.geojson`（499無向/998有向）ほか |
| 03 | `03_michiyomi_scenes.py` | michiyomiシーンを豊洲で抽出し `analysis` JSONを属性展開 | `toyosu_michiyomi_scenes.geojson`（6,539点） |
| 04 | `04_link_vlm_attach.py` | シーンをリンクに吸着（対応表→15m→30m） | `toyosu_walk_link_WD_vlm.geojson`（974有向） |
| 05 | `05_text_pca.py` | 6カテゴリ分類→形態素解析→TF-IDF→PCA→k-means | `toyosu_link_vlm_text.geojson`, `toyosu_link_term_matrix.csv` |
| 06 | `06_pp_basic_stats.py` | PP基礎集計（手段・目的分担率、5分類、年次推移） | `basic_stats/`, `basic_stats_toyosu/` |
| 07 | `07_prep_trips.py` | 対象トリップ抽出（豊洲内々の徒歩トリップ） | `target_trips_$Y.csv`, `users$Y.txt` |
| 08 | `08_gps_extract.sh` | locDataからbbox内・対象ユーザのGPS点を抽出（awk） | `loc${Y}_tgt.csv` |
| 09 | `09_build_gps_seq.py` | GPS点をトリップの時間窓に割り当て・4m間引き | `gps_seq_$Y.json` |
| 10 | `10_mapmatch.py` | **HMM+Viterbiによるマップマッチング** | `matched_A_$Y.jsonl` |
| 11 | `11_export_paths.py` | 経路CSV化・品質判定・最短経路との比較・属性結合 | `paths_$Y.csv`, `toyosu_matched_paths_$Y.csv` |
| 12 | `12_obs_vs_shortest.py` | 実経路と最短経路の景観特徴を対応比較 | `vlm_11_obs_vs_shortest.png` |
| 13 | `13_od_analysis.py` | OD集計（丁目/メッシュ/ノード）・推定可能性の確認 | `toyosu_od_mesh250_*.geojson` |
| 14 | `14_rl_core.py` | **RLモデルの中核**（価値関数・尤度・fit関数） | （exec用） |
| 14b | `14b_rl_run.py` | 論文掲載モデルの推定ドライバ | `rl_*.json` |
| 15 | `15_multistart.py` | 多点初期値推定（局所解の検証） | `ms_*.json` |
| 16 | `16_mnl_core.py` | 経路列挙型MNL（同一OD／代替路生成2種） | `mnl_res.json` |
| 17 | `17_figures.py` | 論文用の図の作成 | `vlm_*.png` |

`run_all.sh` に実行順の例をまとめてある。

## 主要な処理の要点

### マップマッチング（10）

1. GPS点を3点移動平均で平滑化 → 20m間隔にリサンプリング
2. 各点について25m以内の有向リンク上位5本を候補とする
3. 放出確率 `exp(-d²/2σ²)`（σ=10m）、遷移確率 `exp(-|d_route-d_gps|/β)`（β=4）のHMMをViterbi法で解く
4. 非連続部分を最短経路で補間（10リンクまで）、U字スパイクを除去

パラメータは `mm.py` 冒頭の `SIG` / `BETA` / `cands(R, K)` で調整する。品質指標（経路長比、歩行速度、GPS-リンク距離）は11で出力される。

### RLモデル（14）

状態＝有向リンク。価値関数 `z = exp(V/μ)` は線形方程式 `(I-M)z = b` を疎行列で解く（μ=1、β=1）。遷移確率は `P(a|k) = M[k,a]·z(a)/z(k)`。

**局所解に注意**。対数尤度関数は多峰性をもち、さらに `(I-M)` が正則である必要があるため、初期値の与え方で結果が大きく変わる。ランダム初期値20回のうち18回は求解不能だった。

対策として14bでは、交互作用モデルの解を初期値に基準モデルを再推定する手順を自動化してある。加えて15で多点初期値による検証を行うこと。

### 交互作用の入れ方（14）

ダミー変数はトリップ単位で付与し、`GMODE` で切り替える。

| GMODE | ダミーの定義 |
|---|---|
| `covid` | 調査年が2020または2021なら1 |
| `gender` | 属性表の `Gender` が2（女性）なら1 |
| `child` | `Number of Children` が空欄・0以外なら1 |
| `year` | 2018=0, 2019=1, 2020=2, 2021=3 |

**交互作用ダミーはグループごとに別々の価値関数を解く**点が通常の離散選択モデルと異なる（`build(groups=True)` が `(目的地, グループ)` 単位で尤度を構成する）。ダミー単独の主効果項は、全リンクで一定となり選択確率に影響しないため入れていない。

## 再現時の注意

- `walk_node.csv` / `walk_link.csv` は **列名 Lat / Lon の中身が入れ替わっている**（Lat列に経度）。02で補正済み。
- michiyomiの `analysis` を連結する際は、文字列の間に区切り（`。\n`）を入れること。区切りなしで連結すると「沿道」＋「中央」→「道中」のような誤った複合語が生成される。
- `capture_meta` は撮影条件の記述であり街路属性ではないため、テキスト分析から除外している（全文字数の20.7%を占める）。
- RLの推定サンプルは**目的地指向トリップ**（最短経路300m以上・迂回率1.6以下）に限定する。散策・回遊型トリップを含めると係数の符号が反転する。

## ライセンス

michiyomi は CC BY-SA 4.0（© Mapillary contributors を加工）。PP調査データと首都圏ネットワークデータは2026年度 行動モデル夏の学校の利用許諾範囲内。
