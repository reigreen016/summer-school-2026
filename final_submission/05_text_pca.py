"""05: VLM言語記述の6カテゴリ分類 → 形態素解析 → TF-IDF → PCA → クラスタリング。
入力: toyosu_michiyomi_scenes.geojson, toyosu_walk_link_WD.geojson, $MICHI/data/koto.parquet
出力: toyosu_link_vlm_text.geojson/.csv (無向487リンク × カテゴリ構成比・z得点・PC1-6)
      toyosu_link_term_matrix.csv, toyosu_vlm_category_terms.csv, toyosu_vlm_pca_loadings.csv
"""
import pyarrow.parquet as pq, json, os, csv, math, collections, statistics, numpy as np
from fugashi import Tagger
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
CAT = {'A_形状舗装':['road_structure','geometry','pavement','markings_wear'],
       'B_アクセシビリティ':['accessibility','mobility'],
       'C_沿道景観':['townscape','zone_cues','road_context','objects_permanent'],
       'D_設備維持管理':['infrastructure','infrastructure_issues'],
       'E_リスク':['risk_cues','objects_temporary','needs_close_inspection'],
       'F_好ましい特徴':['positive_features']}
# capture_meta / image_file / confidence_overall は撮影条件であり街路属性でないため除外
K2C = {k:c for c,ks in CAT.items() for k in ks}; CATS = list(CAT)
STOP = set("""不明 該当 なし 無し 有無 確認 出来る 為る 居る 有る 無い 成る 因る 見る 見える 認める 思う 言う 有り
こと もの ため 判断 推定 可能 困難 程度 部分 一部 以降 以外 以上 以下 未満 場合 状態 全体 各種 その他 他
手前 正面 左側 右側 奥側 周囲 付近 位置 方向 側面 上部 下部 前方 後方 両側 片側 一方 対象 範囲 側
画角 画像 撮影 視点 視認 観察 昼間 夜間 評価 基準 基づく 情報 記録 内容 特に 非常 やや 概ね 当該 同様
数値 単位 mm cm km 本数 個数 箇所 地点 要素 種類 一般 普通 主要 良い 多い 少ない 高い 低い 大きい 小さい
含める 除く 想定 実質 合算 差し引く 控除 最小 最大 平均 相当 実見 到達 届く 発見 気付く コウ""".split())
STOP2 = {'該当なし','画角外不明','あり','なし','設備観察','外観','安定','s以降','階以上','階超','low','mid','high',
         '目視範囲内','普通車同士可','その他','歩道橋あり','夜間実見','固定状態','内部状態','照明点灯状態','照明状態'}
tg = Tagger()
def texts(o):
    if isinstance(o,str): yield o
    elif isinstance(o,dict):
        for v in o.values(): yield from texts(v)
    elif isinstance(o,list):
        for v in o: yield from texts(v)
def toks(t):
    """名詞連続を複合語として結合し、動詞・形容詞は原形。"""
    out, buf = [], []
    for w in tg(t):
        p1 = w.feature.pos1; p2 = getattr(w.feature,'pos2','') or ''
        isn = (p1=='名詞' and p2!='数詞') or (p1=='接尾辞' and p2=='名詞的')
        if isn: buf.append(w.surface); continue
        if buf: out.append("".join(buf)); buf=[]
        if p1 in ('動詞','形容詞'):
            out.append((getattr(w.feature,'lemma',None) or w.surface).split('-')[0])
    if buf: out.append("".join(buf))
    return [x for x in out if len(x)>=2 and x not in STOP and not x.isdigit()]
ids = {f['properties']['id'] for f in json.load(open(OUT+"/toyosu_michiyomi_scenes.geojson"))['features']}
d = pq.read_table(MICHI+"/data/koto.parquet", columns=['id','analysis']).to_pydict()
sc_cat = collections.defaultdict(collections.Counter); sc_tm = collections.defaultdict(collections.Counter)
gterm = collections.defaultdict(collections.Counter)
for i in range(len(d['id'])):
    sid = str(d['id'][i])
    if sid not in ids: continue
    try: a = json.loads(d['analysis'][i])
    except Exception: continue
    for k, v in a.items():
        c = K2C.get(k)
        if not c: continue
        t = "。\n".join(x for x in texts(v) if x)     # 文字列を区切って連結(誤結合防止)
        tk = toks(t); sc_cat[sid][c] += len(tk)
        for w in tk: gterm[c][w] += 1; sc_tm[sid][(c,w)] += 1
# --- リンクへの割り当て(04と同じ規則、無向単位) ---
S = {f['properties']['id']: f['geometry']['coordinates']
     for f in json.load(open(OUT+"/toyosu_michiyomi_scenes.geojson"))['features']}
wd = json.load(open(OUT+"/toyosu_walk_link_WD.geojson"))['features']
M = collections.defaultdict(set)
mp = OUT+"/toyosu_link_matches.csv"
if os.path.exists(mp):
    for x in csv.DictReader(open(mp,encoding="utf-8-sig")): M[x['LinkID']].update([x['from_id'],x['to_id']])
G = collections.defaultdict(list); C = 40.
for sid, c in S.items():
    P = m(*c); G[(int(P[0]//C), int(P[1]//C))].append((sid,P))
UN = {}
for f in wd:
    p = f['properties']; key = tuple(sorted((p['ONodeID'],p['DNodeID'])))
    if key in UN: continue
    (x1,y1),(x2,y2) = f['geometry']['coordinates']; A,B = m(x1,y1), m(x2,y2)
    cand = []
    for gx in range(int(min(A[0],B[0])//C)-1, int(max(A[0],B[0])//C)+2):
        for gy in range(int(min(A[1],B[1])//C)-1, int(max(A[1],B[1])//C)+2):
            for sid,P in G.get((gx,gy),[]):
                dd = d2seg(P,A,B)
                if dd <= 30: cand.append((sid,dd))
    idset, srcs = set(), []
    for g2 in wd:
        q = g2['properties']
        if tuple(sorted((q['ONodeID'],q['DNodeID']))) == key and str(q['LinkID']) in M:
            idset |= {i for i in M[str(q['LinkID'])] if i in S}; srcs.append('match_csv')
    if not idset:
        c15 = [s for s,dd in cand if dd <= 15]
        if c15: idset, srcs = set(c15), ['nn15']
        elif cand: idset, srcs = {s for s,_ in cand}, ['nn30']
    if idset: UN[key] = (sorted(idset), 'match_csv' if 'match_csv' in srcs else srcs[0], f)
rows, LT = [], {}
for key,(sids,srcv,f) in UN.items():
    cat, tm = collections.Counter(), collections.Counter()
    for s in sids:
        for c,v in sc_cat.get(s,{}).items(): cat[c] += v
        for (c,w),v in sc_tm.get(s,{}).items():
            if w not in STOP2: tm[w] += v
    n = sum(cat.values())
    if not n: continue
    shd = {c: cat.get(c,0)/n for c in CATS}
    rows.append({'LinkID':f['properties']['LinkID'],'ONodeID':f['properties']['ONodeID'],
        'DNodeID':f['properties']['DNodeID'],'vlm_source':srcv,'n_scenes':len(sids),'n_tokens':n,
        **{'sh_'+c[0]: round(shd[c],4) for c in CATS}, **{'n_'+c[0]: cat.get(c,0) for c in CATS},
        'entropy': round(-sum(p*math.log(p) for p in shd.values() if p>0)/math.log(6),3),
        'top_terms':" ".join(w for w,_ in tm.most_common(8)),
        'geom':f['geometry'],'length_m':f['properties']['length_m']})
    LT[str(f['properties']['LinkID'])] = tm
# --- TF-IDF & PCA ---
df = collections.Counter()
for r in rows: df.update(LT[str(r['LinkID'])].keys())
N = len(rows)
terms = sorted([w for w,c in df.items() if 0.05*N <= c <= 0.85*N],
               key=lambda w: -sum(LT[str(r['LinkID'])].get(w,0) for r in rows))[:250]
X = np.array([[LT[str(r['LinkID'])].get(w,0) for w in terms] for r in rows], float)
tf = X/np.maximum(X.sum(1,keepdims=True),1); idf = np.log(N/np.maximum((X>0).sum(0),1))
Z = tf*idf; Z = (Z-Z.mean(0))/np.maximum(Z.std(0),1e-9)
U,S_,Vt = np.linalg.svd(Z, full_matrices=False); ev = S_**2/(S_**2).sum(); PC = U[:,:6]*S_[:6]
for c in CATS:
    v = np.array([r['sh_'+c[0]] for r in rows]); mu, sd = v.mean(), v.std()
    for k,r in enumerate(rows): r['z_'+c[0]] = round(float((v[k]-mu)/sd),3)
for k,r in enumerate(rows):
    for i in range(6): r['PC%d'%(i+1)] = round(float(PC[k,i]),3)
# リンク別の特徴語(log-odds) と k-means による街路タイプ
p_corpus = X.sum(0)/X.sum()
for k,r in enumerate(rows):
    rr = X[k]/max(X[k].sum(),1)
    sc = sorted((((rr[j]+1e-9)/p_corpus[j], X[k,j], terms[j]) for j in range(len(terms)) if X[k,j]>=3), reverse=True)
    r['top_distinctive'] = " ".join(t for _,_,t in sc[:6])
    zs = {c: r['z_'+c[0]] for c in CATS}
    r['dom_z_cat'] = max(zs,key=zs.get); r['dom_z_val'] = round(max(zs.values()),2)
F = U[:,:8]*S_[:8]
def km(F,k,seed):
    rng = np.random.default_rng(seed); Cc = F[rng.choice(len(F),k,replace=False)]
    for _ in range(80):
        lab = ((F[:,None,:]-Cc[None])**2).sum(2).argmin(1)
        Cn = np.array([F[lab==i].mean(0) if (lab==i).any() else Cc[i] for i in range(k)])
        if np.allclose(Cn,Cc): break
        Cc = Cn
    return lab, ((F-Cc[lab])**2).sum()
best = min((km(F,6,s) for s in range(12)), key=lambda t: t[1]); lab = best[0]
prof = {}
for i in range(6):
    sub = X[lab==i].sum(0); n2 = sub.sum()
    sc = sorted((((sub[j]/n2)/p_corpus[j], sub[j], terms[j]) for j in range(len(terms)) if sub[j]>=10), reverse=True)
    prof[i] = [t for _,_,t in sc[:8]]
for k,r in enumerate(rows):
    r['cluster'] = int(lab[k])+1; r['cluster_terms'] = " ".join(prof[lab[k]][:6])
cols = ['LinkID','ONodeID','DNodeID','vlm_source','n_scenes','n_tokens'] + ['n_'+c[0] for c in CATS] + \
       ['sh_'+c[0] for c in CATS] + ['z_'+c[0] for c in CATS] + \
       ['entropy','dom_z_cat','dom_z_val','cluster','cluster_terms','top_distinctive','top_terms'] + \
       ['PC%d'%i for i in range(1,7)] + ['length_m']
json.dump({"type":"FeatureCollection","name":"toyosu_link_vlm_text",
    "features":[{"type":"Feature","properties":{k:r[k] for k in cols},"geometry":r['geom']} for r in rows]},
    open(OUT+"/toyosu_link_vlm_text.geojson","w"), ensure_ascii=False)
with open(OUT+"/toyosu_link_vlm_text.csv","w",newline="",encoding="utf-8-sig") as fh:
    w = csv.writer(fh); w.writerow(cols+['wkt'])
    for r in rows:
        c = r['geom']['coordinates']
        w.writerow([r[k] for k in cols]+["LINESTRING(%s)"%", ".join("%s %s"%(x,y) for x,y in c)])
with open(OUT+"/toyosu_link_term_matrix.csv","w",newline="",encoding="utf-8-sig") as fh:
    w = csv.writer(fh); w.writerow(["LinkID"]+terms)
    for k,r in enumerate(rows): w.writerow([r['LinkID']]+[int(v) for v in X[k]])
with open(OUT+"/toyosu_vlm_pca_loadings.csv","w",newline="",encoding="utf-8-sig") as fh:
    w = csv.writer(fh); w.writerow(["PC","variance_ratio","term","loading"])
    for i in range(6):
        for t,v in sorted({terms[j]: float(Vt[i][j]) for j in range(len(terms))}.items(),
                          key=lambda x:-abs(x[1]))[:60]: w.writerow(["PC%d"%(i+1),round(ev[i],4),t,round(v,4)])
with open(OUT+"/toyosu_vlm_category_terms.csv","w",newline="",encoding="utf-8-sig") as fh:
    w = csv.writer(fh); w.writerow(["category","term","freq","rank"])
    for c in CATS:
        for i,(t,n2) in enumerate(sorted(gterm[c].items(),key=lambda x:-x[1])[:200]): w.writerow([c,t,n2,i+1])
json.dump({'rows':rows,'terms':terms,'ev':ev[:12].tolist(),'prof':prof,'lab':lab.tolist(),
           'X':X.tolist(),'load':{'PC%d'%(i+1):{terms[j]:round(float(Vt[i][j]),4) for j in range(len(terms))} for i in range(6)}},
          open(WORK+"/pca_und.json","w"), ensure_ascii=False)
print("リンク %d / 語彙 %d / 寄与率 %s" % (len(rows), len(terms), [round(100*x,1) for x in ev[:6]]))
