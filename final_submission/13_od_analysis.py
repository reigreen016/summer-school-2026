"""13: OD集計(丁目/250m・100mメッシュ/ノード)と推定可能性の確認。
入力: toyosu_matched_paths_{YEAR}.csv, toyosu_walk_node_WD.geojson, toyosu_chome_boundary.geojson
出力: toyosu_od_mesh250_{YEAR}.csv/.geojson, toyosu_od_flow_mesh250_{YEAR}.geojson
"""
import json, csv, os, collections, statistics
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
YEAR = os.environ.get('YEAR','2019')
nodes = {f['properties']['NodeID']: f['geometry']['coordinates']
         for f in json.load(open(OUT+"/toyosu_walk_node_WD.geojson"))['features']}
rows = [r for r in csv.DictReader(open(OUT+f"/toyosu_matched_paths_{YEAR}.csv",encoding="utf-8-sig"))
        if r['quality_ok']=='1']
def mesh(n, sz):
    x,y = nodes[int(n)]; return (int(x*KX//sz), int(y*KY//sz))
for lab, f in (("ノードOD", lambda r:(r['O_node'],r['D_node'])),
               ("100mメッシュ", lambda r:(mesh(r['O_node'],100),mesh(r['D_node'],100))),
               ("250mメッシュ", lambda r:(mesh(r['O_node'],250),mesh(r['D_node'],250)))):
    c = collections.Counter(f(r) for r in rows); dest = collections.Counter(f(r)[1] for r in rows)
    print("%-12s OD対 %4d / 目的地 %4d / 1件のみ %4d / 最大 %3d / 中央値 %.1f" %
          (lab, len(c), len(dest), sum(1 for v in c.values() if v==1), max(c.values()), statistics.median(c.values())))
od = collections.Counter((mesh(r['O_node'],250), mesh(r['D_node'],250)) for r in rows)
cells = collections.Counter()
for r in rows: cells[mesh(r['O_node'],250)] += 1; cells[mesh(r['D_node'],250)] += 1
feats=[]
for (gx,gy),n in cells.items():
    x0,x1 = gx*250/KX,(gx+1)*250/KX; y0,y1 = gy*250/KY,(gy+1)*250/KY
    feats.append({"type":"Feature","properties":{"mesh":f"{gx}_{gy}","n_endpoints":n},
        "geometry":{"type":"Polygon","coordinates":[[[x0,y0],[x1,y0],[x1,y1],[x0,y1],[x0,y0]]]}})
json.dump({"type":"FeatureCollection","features":feats},
          open(OUT+f"/toyosu_od_mesh250_{YEAR}.geojson","w"), ensure_ascii=False)
cc = lambda g: [(g[0]+.5)*250/KX,(g[1]+.5)*250/KY]
json.dump({"type":"FeatureCollection","features":[
    {"type":"Feature","properties":{"o":f"{o[0]}_{o[1]}","d":f"{d[0]}_{d[1]}","n_trips":n},
     "geometry":{"type":"LineString","coordinates":[cc(o),cc(d)]}} for (o,d),n in od.items() if o!=d]},
    open(OUT+f"/toyosu_od_flow_mesh250_{YEAR}.geojson","w"), ensure_ascii=False)
with open(OUT+f"/toyosu_od_mesh250_{YEAR}.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(["O_mesh","D_mesh","trips","same_mesh"])
    for (o,d),n in od.most_common(): w.writerow([f"{o[0]}_{o[1]}",f"{d[0]}_{d[1]}",n,int(o==d)])
print("出力完了")
