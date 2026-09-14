"""共通設定。各スクリプトから import して使う。"""
import os, math
HOME = os.environ['HOME']
PP      = os.environ.get('PP',      HOME + "/mnt/PP/Toyosu2018-2021")
NET     = os.environ.get('NET',     HOME + "/mnt/network/tokyo-metropolitan-area")
MICHI   = os.environ.get('MICHI',   HOME + "/mnt/michiyomi-tokyo-streetscape")
OUT     = os.environ.get('OUT',     HOME + "/mnt/network/toyosu")
WORK    = os.environ.get('WORK',    HOME + "/tmpwork")     # 中間ファイル置き場
os.makedirs(WORK, exist_ok=True)
LAT0 = 35.65                                   # 豊洲の代表緯度
KX = math.cos(math.radians(LAT0)) * 111320     # 経度1度 → m
KY = 110570                                    # 緯度1度 → m
BBOX = (139.773, 139.808, 35.636, 35.667)      # 豊洲周辺(lon0,lon1,lat0,lat1)
def m(x, y):  return (x * KX, y * KY)          # 度 → メートル平面
def ins(x, y, poly):
    """点(x,y)がポリゴン(リング配列)の内側か。even-odd 判定、穴に対応。"""
    c = False
    for ring in poly:
        n = len(ring); j = n - 1
        for i in range(n):
            xi, yi = ring[i]; xj, yj = ring[j]
            if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi: c = not c
            j = i
    return c
def make_in_toyosu(boundary_geojson):
    """豊洲境界GeoJSONから内外判定関数を作る(bbox前置き+キャッシュ)。"""
    import json
    g = json.load(open(boundary_geojson))['features'][0]['geometry']
    polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    bb = [(min(c[0] for c in p[0]), max(c[0] for c in p[0]),
           min(c[1] for c in p[0]), max(c[1] for c in p[0])) for p in polys]
    cache = {}
    def inT(x, y):
        k = (round(x, 6), round(y, 6))
        if k in cache: return cache[k]
        r = any(x0 <= x <= x1 and y0 <= y <= y1 and ins(x, y, p)
                for (x0, x1, y0, y1), p in zip(bb, polys))
        cache[k] = r; return r
    return inT
def d2seg(p, a, b):
    """点pから線分abまでの距離(メートル平面)。"""
    dx, dy = b[0]-a[0], b[1]-a[1]; L = dx*dx + dy*dy
    t = 0 if L == 0 else max(0, min(1, ((p[0]-a[0])*dx + (p[1]-a[1])*dy) / L))
    return math.hypot(p[0]-(a[0]+dx*t), p[1]-(a[1]+dy*t))
