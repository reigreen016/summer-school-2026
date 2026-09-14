"""02: 首都圏徒歩ネットワークから豊洲地区のリンク・ノードを切り出す。
注意: walk_node.csv / walk_link.csv は列名 Lat/Lon の中身が入れ替わっている
      (Lat列に経度, Lon列に緯度)。ここで正しい順序に直す。
入力: $NET/walk_node.csv, walk_link.csv, $OUT/toyosu_boundary.geojson
出力: toyosu_walk_link_official.geojson  (両端が豊洲内, 1336有向リンク)
      toyosu_walk_link_official_incl_boundary.geojson (境界跨ぎ68本を含む)
      toyosu_walk_node_official.geojson
      toyosu_walk_link_WD.geojson / toyosu_walk_node_WD.geojson (種別WDのみ=解析対象)
"""
import csv, json, os, sys
sys.path.insert(0, os.path.dirname(__file__)); from importlib import import_module
C = import_module('00_config') if False else None
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
inT = make_in_toyosu(OUT + "/toyosu_boundary.geojson")
import math
nodes, flag = {}, {}
for r in csv.DictReader(open(NET + "/walk_node.csv")):
    x, y = float(r['Lat']), float(r['Lon'])            # ← 入替済み
    if BBOX[0] <= x <= BBOX[1] and BBOX[2] <= y <= BBOX[3]:
        nodes[r['NodeID']] = (x, y); flag[r['NodeID']] = inT(x, y)
def dist(a, b): return math.hypot((b[0]-a[0])*KX, (b[1]-a[1])*KY)
seen, ft = set(), []
for r in csv.DictReader(open(NET + "/walk_link.csv")):
    o, d = r['ONodeID'], r['DNodeID']
    if o not in nodes or d not in nodes: continue
    fo, fd = flag[o], flag[d]
    if not (fo or fd): continue
    k = (min(o, d), max(o, d)); dup = 1 if k in seen else 0; seen.add(k)
    mx, my = (nodes[o][0]+nodes[d][0])/2, (nodes[o][1]+nodes[d][1])/2
    ft.append({"type":"Feature","properties":{
        "LinkID":int(r['LinkID']),"ONodeID":int(o),"DNodeID":int(d),
        "length_m":round(dist(nodes[o],nodes[d]),1),"speed_kmh":float(r['speed'] or 0),
        "link_type":r['link type'],"both_ends_in":1 if (fo and fd) else 0,
        "mid_in":1 if inT(mx,my) else 0,"reverse_dup":dup},
        "geometry":{"type":"LineString","coordinates":[
            [round(nodes[o][0],7),round(nodes[o][1],7)],[round(nodes[d][0],7),round(nodes[d][1],7)]]}})
def dump(fn, feats):
    json.dump({"type":"FeatureCollection","name":fn[:-8],"features":feats},
              open(OUT+"/"+fn,"w"), ensure_ascii=False); print(fn, len(feats))
full = [f for f in ft if f['properties']['both_ends_in']]
dump("toyosu_walk_link_official_incl_boundary.geojson", ft)
dump("toyosu_walk_link_official.geojson", full)
wd = [f for f in full if f['properties']['link_type'] == 'WD']   # 豊洲歩道リンク(code=10)
dump("toyosu_walk_link_WD.geojson", wd)
for src, fn in ((full,"toyosu_walk_node_official.geojson"), (wd,"toyosu_walk_node_WD.geojson")):
    nd = {}
    for f in src:
        nd[f['properties']['ONodeID']] = f['geometry']['coordinates'][0]
        nd[f['properties']['DNodeID']] = f['geometry']['coordinates'][1]
    dump(fn, [{"type":"Feature","properties":{"NodeID":n},"geometry":{"type":"Point","coordinates":c}}
              for n, c in sorted(nd.items())])
