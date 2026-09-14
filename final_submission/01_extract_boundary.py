"""01: e-Stat 小地域境界(江東区13108)から豊洲一〜六丁目を抽出・結合。
※ pyshp / shapely が必要。ローカルVMに入らない場合はクラウド側で実行し、
   出力2ファイルを network/toyosu/ に配置する。
入力: r2kb13108.shp/.shx/.dbf/.prj (令和2年国勢調査 小地域(基本単位区))
出力: toyosu_boundary.geojson (1〜6丁目を結合), toyosu_chome_boundary.geojson (丁目別)
"""
import shapefile, json, math, sys, os
from shapely.geometry import shape, mapping
from shapely.ops import unary_union
SHP = sys.argv[1] if len(sys.argv) > 1 else "r2kb13108"     # 拡張子なし
OUT = sys.argv[2] if len(sys.argv) > 2 else "."
K = 111320 * math.cos(math.radians(35.65)) * 110570          # deg^2 → m^2
r = shapefile.Reader(SHP, encoding='cp932')
byname = {}
for sr in r.shapeRecords():
    n = str(sr.record.as_dict().get('S_NAME'))
    if n.startswith('豊洲'):
        byname.setdefault(n, []).append(shape(sr.shape.__geo_interface__).buffer(0))
order = ['豊洲一丁目','豊洲二丁目','豊洲三丁目','豊洲四丁目','豊洲五丁目','豊洲六丁目']
feats, alls = [], []
for n in order:
    u = unary_union(byname[n]); alls.append(u)
    feats.append({"type":"Feature","properties":{"S_NAME":n,"area_ha":round(u.area*K/1e4,2),
        "source":"e-Stat 令和2年国勢調査 小地域(基本単位区) 13108"},"geometry":mapping(u)})
allu = unary_union(alls)
json.dump({"type":"FeatureCollection","features":feats},
          open(os.path.join(OUT,"toyosu_chome_boundary.geojson"),"w"), ensure_ascii=False)
json.dump({"type":"FeatureCollection","features":[{"type":"Feature","properties":{
    "name":"江東区豊洲(1-6丁目)","area_ha":round(allu.area*K/1e4,2),
    "crs_note":"JGD2000 geographic (EPSG:4612), ≈WGS84"},"geometry":mapping(allu)}]},
          open(os.path.join(OUT,"toyosu_boundary.geojson"),"w"), ensure_ascii=False)
print("豊洲 合計 %.2f ha" % (allu.area*K/1e4))
