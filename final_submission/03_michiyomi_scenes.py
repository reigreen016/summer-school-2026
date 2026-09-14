"""03: michiyomi(江東区)から豊洲地区のシーンを抽出し、analysis JSON を属性に展開。
入力: $MICHI/data/koto.parquet, $OUT/toyosu_boundary.geojson
出力: toyosu_michiyomi_scenes.geojson (6,539点)
"""
import pyarrow.parquet as pq, json, os
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
inT = make_in_toyosu(OUT + "/toyosu_boundary.geojson")
MU = "https://www.mapillary.com/app/?pKey=%s&focus=photo"
cols = ['id','lat','lon','capture_year','captured_at_jst','position_source','view_class','is_pano',
        'quality_score','travel_bearing','heading8','summary','analysis','abs_objects',
        'green_ratio','colorfulness','warm_ratio','sequence_id','camera_type']
d = pq.read_table(MICHI + "/data/koto.parquet", columns=cols).to_pydict()
def g(o, *ks, default=None):
    for k in ks:
        if not isinstance(o, dict): return default
        o = o.get(k)
        if o is None: return default
    return o
feats = []
for i in range(len(d['id'])):
    x, y = d['lon'][i], d['lat'][i]
    if not (BBOX[0] <= x <= BBOX[1] and BBOX[2] <= y <= BBOX[3]) or not inT(x, y): continue
    try: a = json.loads(d['analysis'][i]) if d['analysis'][i] else {}
    except Exception: a = {}
    try: objs = json.loads(d['abs_objects'][i]) if d['abs_objects'][i] else []
    except Exception: objs = []
    p = {"id":str(d['id'][i]),"capture_year":d['capture_year'][i],
         "captured_at_jst":str(d['captured_at_jst'][i]),"view_class":d['view_class'][i],
         "is_pano":int(d['is_pano'][i] or 0),"quality_score":d['quality_score'][i],
         "travel_bearing":d['travel_bearing'][i],"heading8":d['heading8'][i],
         "position_source":d['position_source'][i],"sequence_id":d['sequence_id'][i],
         "green_ratio":d['green_ratio'][i],"colorfulness":d['colorfulness'][i],
         "warm_ratio":d['warm_ratio'][i],"summary":d['summary'][i],
         "road_type":g(a,'road_structure','type'),"facility_type":g(a,'road_structure','facility_type'),
         "roadway_width_m":g(a,'geometry','roadway_width_m','value'),
         "sidewalk_left":g(a,'geometry','sidewalk','left','presence'),
         "sidewalk_right":g(a,'geometry','sidewalk','right','presence'),
         "walkable_width_m":g(a,'accessibility','clear_walkable_width_m','baseline_value'),
         "tactile_paving":g(a,'accessibility','tactile_paving','present'),
         "slope":g(a,'geometry','slope'),"intersection_type":g(a,'geometry','intersection','type'),
         "pavement":g(a,'pavement','surface'),
         "undergrounded":g(a,'infrastructure','utilities','undergrounded'),
         "poles_visible":g(a,'infrastructure','utilities','poles_visible'),
         "lights_road":g(a,'infrastructure','lighting','lights_road'),
         "parking_pressure":g(a,'mobility','parking_pressure','assessment'),
         "n_risk_cues":len(a.get('risk_cues') or []),
         "n_positive":len(a.get('positive_features') or []),"n_objects":len(objs),
         "road_context":g(a,'road_context'),"mapillary_url":MU % d['id'][i]}
    feats.append({"type":"Feature","properties":p,
                  "geometry":{"type":"Point","coordinates":[round(x,7),round(y,7)]}})
json.dump({"type":"FeatureCollection","name":"toyosu_michiyomi_scenes","features":feats},
          open(OUT+"/toyosu_michiyomi_scenes.geojson","w"), ensure_ascii=False)
print("scenes:", len(feats))
