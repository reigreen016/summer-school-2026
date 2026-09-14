"""04: michiyomiシーンを豊洲歩道リンク(WD)に吸着させ、リンク属性を集計。
吸着の優先順位: (1)既存対応表 toyosu_link_matches.csv → (2)15m以内 → (3)30m以内 → なければ除外
入力: toyosu_walk_link_WD.geojson, toyosu_michiyomi_scenes.geojson, (任意)toyosu_link_matches.csv
出力: toyosu_walk_link_WD_vlm.geojson / .csv (974有向=487無向リンク)
"""
import csv, json, os, math, collections, statistics
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
wd = json.load(open(OUT+"/toyosu_walk_link_WD.geojson"))['features']
S = {f['properties']['id']: (f['geometry']['coordinates'], f['properties'])
     for f in json.load(open(OUT+"/toyosu_michiyomi_scenes.geojson"))['features']}
M = collections.defaultdict(set)
mp = OUT + "/toyosu_link_matches.csv"
if os.path.exists(mp):
    for x in csv.DictReader(open(mp, encoding="utf-8-sig")): M[x['LinkID']].update([x['from_id'], x['to_id']])
G = collections.defaultdict(list); C = 40.
for sid, (c, p) in S.items():
    P = m(*c); G[(int(P[0]//C), int(P[1]//C))].append((sid, P))
PPm = {'低':1,'中':2,'高':3}
num = lambda v: v if isinstance(v,(int,float)) and not isinstance(v,bool) else None
def mean(vs):
    vs=[v for v in vs if v is not None]; return round(statistics.mean(vs),3) if vs else None
out, src = [], collections.Counter()
for f in wd:
    pr = dict(f['properties']); lid = str(pr['LinkID'])
    (x1,y1),(x2,y2) = f['geometry']['coordinates']; A,B = m(x1,y1), m(x2,y2)
    lb = (math.degrees(math.atan2(B[0]-A[0], B[1]-A[1])) + 360) % 360
    cand = []
    for gx in range(int(min(A[0],B[0])//C)-1, int(max(A[0],B[0])//C)+2):
        for gy in range(int(min(A[1],B[1])//C)-1, int(max(A[1],B[1])//C)+2):
            for sid, P in G.get((gx,gy), []):
                dd = d2seg(P, A, B)
                if dd <= 30: cand.append((sid, dd))
    if lid in M:  ids = [(i, dict(cand).get(i)) for i in M[lid] if i in S]; source='match_csv'
    else:
        c15 = [c for c in cand if c[1] <= 15]
        if c15:   ids, source = c15, 'nn15'
        elif cand: ids, source = cand, 'nn30'
        else:      src['none'] += 1; continue
    src[source] += 1
    L = [S[i][1] for i,_ in ids]; ds = [d for _,d in ids if d is not None]
    ndir = sum(1 for i,_ in ids
               if (lambda tb: tb is not None and min(abs(tb-lb),360-abs(tb-lb)) <= 45)(num(S[i][1].get('travel_bearing'))))
    yrs = [p['capture_year'] for p in L]
    sw = [1 if ('あり' in str(p['sidewalk_left']) or 'あり' in str(p['sidewalk_right'])) else 0 for p in L]
    pr.update({'vlm_source':source,'n_scenes':len(L),'n_scenes_dir':ndir,
        'dist_mean_m':round(statistics.mean(ds),1) if ds else None,
        'dist_max_m':round(max(ds),1) if ds else None,'year_min':min(yrs),'year_max':max(yrs),
        'green_ratio':mean([num(p['green_ratio']) for p in L]),
        'colorfulness':mean([num(p['colorfulness']) for p in L]),
        'warm_ratio':mean([num(p['warm_ratio']) for p in L]),
        'roadway_width_m':mean([num(p['roadway_width_m']) for p in L]),
        'walkable_width_m':mean([num(p['walkable_width_m']) for p in L]),
        'sidewalk_share':round(sum(sw)/len(sw),3),
        'tactile_share':round(sum(1 for p in L if str(p['tactile_paving'])=='あり')/len(L),3),
        'undergrounded_share':round(sum(1 for p in L if str(p['undergrounded'])=='無電柱化済')/len(L),3),
        'poles_visible':mean([num(p['poles_visible']) for p in L]),
        'lights_road':mean([num(p['lights_road']) for p in L]),
        'parking_pressure':mean([PPm.get(str(p['parking_pressure'])) for p in L]),
        'n_risk_cues':mean([num(p['n_risk_cues']) for p in L]),
        'facility_type':collections.Counter(str(p['facility_type']) for p in L).most_common(1)[0][0],
        'pavement':collections.Counter(str(p['pavement']) for p in L).most_common(1)[0][0],
        'sample_scene_id':sorted(L,key=lambda p:-p['capture_year'])[0]['id'],
        'sample_summary':sorted(L,key=lambda p:-p['capture_year'])[0]['summary'][:250]})
    out.append({"type":"Feature","properties":pr,"geometry":f['geometry']})
json.dump({"type":"FeatureCollection","name":"toyosu_walk_link_WD_vlm","features":out},
          open(OUT+"/toyosu_walk_link_WD_vlm.geojson","w"), ensure_ascii=False)
print("VLM付き %d有向 / 除外 %d ／ 由来 %s" % (len(out), src['none'], src.most_common()))
