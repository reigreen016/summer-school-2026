"""12: 実経路と最短経路の景観特徴の比較(対応のあるt検定) + 図。
入力: toyosu_matched_paths_2019.csv, toyosu_walk_link_WD.geojson, $WORK/pca_und.json
出力: $WORK/obs_vs_sp.json, vlm_11_obs_vs_shortest.png
"""
import json, csv, os, math, heapq, collections, statistics, numpy as np
import matplotlib; matplotlib.use('Agg'); import japanize_matplotlib, matplotlib.pyplot as plt
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
YEAR = os.environ.get('YEAR','2019')
wd = json.load(open(OUT+"/toyosu_walk_link_WD.geojson"))['features']
L = {f['properties']['LinkID']: f['properties'] for f in wd}
adj = collections.defaultdict(list)
for f in wd:
    p=f['properties']; adj[p['ONodeID']].append((p['DNodeID'],p['length_m'],p['LinkID']))
V = {r['LinkID']: r for r in json.load(open(WORK+"/pca_und.json"))['rows']}
key = lambda lid: tuple(sorted((L[lid]['ONodeID'], L[lid]['DNodeID'])))
byk = {}
for lid,r in V.items(): byk[key(lid)] = r
KEYS = ['PC1','PC2','PC3','z_A','z_B','z_C','z_D','z_E','z_F']
FT = {lid: (byk.get(key(lid)) or {k:0.0 for k in KEYS}) for lid in L}
def sp(s,t):
    dist={s:0.0}; prev={}; pq=[(0.0,s)]
    while pq:
        dd,u = heapq.heappop(pq)
        if u==t: break
        if dd > dist.get(u,1e18)+1e-9: continue
        for v,w,i in adj[u]:
            nd=dd+w
            if nd < dist.get(v,1e18): dist[v]=nd; prev[v]=(u,i); heapq.heappush(pq,(nd,v))
    if t not in dist: return None
    out=[]; cur=t
    while cur!=s: u,i=prev[cur]; out.append(i); cur=u
    return out[::-1]
def agg(path):
    tot=sum(L[i]['length_m'] for i in path); o={'len':tot,'n':len(path)}
    for k in KEYS: o[k]=sum(float(FT[i][k])*L[i]['length_m'] for i in path)/max(tot,1)
    return o
res, cache = [], {}
for r in csv.DictReader(open(OUT+f"/toyosu_matched_paths_{YEAR}.csv",encoding="utf-8-sig")):
    obs=[int(x) for x in r['link_sequence'].split()]; o,d=int(r['O_node']),int(r['D_node'])
    if (o,d) not in cache: cache[(o,d)]=sp(o,d)
    s=cache[(o,d)]
    if not s: continue
    a,b = agg(obs), agg(s)
    res.append({'TripID':r['TripID'],'q':int(r['quality_ok']),'purpose':r['purpose'],
                'detour':a['len']/max(b['len'],1),
                **{'obs_'+k:a[k] for k in KEYS+['len','n']}, **{'sp_'+k:b[k] for k in KEYS+['len','n']}})
json.dump(res, open(WORK+"/obs_vs_sp.json","w"), ensure_ascii=False)
S=[x for x in res if x['q']==1 and x['sp_len']>=300 and x['detour']<=1.6]
print("目的地指向トリップ:",len(S),"／迂回率中央値 %.2f"%statistics.median([x['detour'] for x in S]))
out=[]
for k in KEYS:
    a=np.array([x['obs_'+k] for x in S]); b=np.array([x['sp_'+k] for x in S]); dd=a-b
    t=dd.mean()/(dd.std(ddof=1)/math.sqrt(len(dd)))
    out.append((k,a.mean(),b.mean(),dd.mean(),t)); print("%-4s 実 %+.3f 最短 %+.3f 差 %+.3f t=%.1f"%(k,a.mean(),b.mean(),dd.mean(),t))
SUR='#fcfcfb'
fig,ax=plt.subplots(figsize=(10,6),facecolor=SUR); ax.set_facecolor(SUR)
y=np.arange(len(out)); h=.36
ax.barh(y+h/2,[r[1] for r in out],height=h,color='#2a78d6',label='実経路')
ax.barh(y-h/2,[r[2] for r in out],height=h,color='#eda100',label='最短経路')
ax.set_yticks(y); ax.set_yticklabels([r[0] for r in out]); ax.invert_yaxis()
ax.axvline(0,color='#999',lw=.8); ax.legend(frameon=False)
ax.set_title('実経路 vs 最短経路（n=%d）'%len(S))
plt.tight_layout(); plt.savefig(OUT+"/vlm_11_obs_vs_shortest.png",dpi=120,bbox_inches='tight',facecolor=SUR)
