import json,csv,os,math,heapq,collections,numpy as np
from scipy.optimize import minimize
H=os.environ['HOME']; OUT=H+"/mnt/network/toyosu"
wd=json.load(open(OUT+"/toyosu_walk_link_WD.geojson"))['features']
L={f['properties']['LinkID']:f['properties'] for f in wd}
adj=collections.defaultdict(list)
for f in wd:
    p=f['properties']; adj[p['ONodeID']].append((p['DNodeID'],p['length_m'],p['LinkID']))
V={r['LinkID']:r for r in json.load(open(H+"/tmpwork/pca_und.json"))['rows']}
key=lambda lid:tuple(sorted((L[lid]['ONodeID'],L[lid]['DNodeID'])))
byk={}
for lid,r in V.items(): byk[key(lid)]=r
KEYS=['PC1','PC2','PC3','z_E','z_F']
FT={lid:(byk.get(key(lid)) or {k:0.0 for k in KEYS}) for lid in L}
mu=None
def sp(s,t,ban=frozenset()):
    dist={s:0.0}; prev={}; pq=[(0.0,s)]
    while pq:
        d,u=heapq.heappop(pq)
        if u==t: break
        if d>dist.get(u,1e18)+1e-9: continue
        for v,w,i in adj[u]:
            if i in ban: continue
            nd=d+w
            if nd<dist.get(v,1e18): dist[v]=nd; prev[v]=(u,i); heapq.heappush(pq,(nd,v))
    if t not in dist: return None
    out=[]; cur=t
    while cur!=s: u,i=prev[cur]; out.append(i); cur=u
    return tuple(out[::-1])
def attrs(path):
    tot=sum(L[i]['length_m'] for i in path)
    a=[tot/100.0]
    for k in KEYS: a.append(sum(float(FT[i][k])*L[i]['length_m'] for i in path)/max(tot,1))
    return a,tot
def psize(paths):
    out=[]
    cnt=collections.Counter()
    for p in paths: cnt.update(set(p))
    for p in paths:
        tot=sum(L[i]['length_m'] for i in p)
        out.append(sum((L[i]['length_m']/max(tot,1))/cnt[i] for i in set(p)))
    return out
def estimate(obs,name,ps=True):
    # obs: list of (chosen_path, [alternatives])
    Xs=[];ys=[];PS=[]
    for ch,alts in obs:
        A=[ch]+[a for a in alts if a!=ch]
        if len(A)<2: continue
        x=[attrs(p)[0] for p in A]; s=psize(A)
        Xs.append(np.array(x)); ys.append(0); PS.append(np.log(np.array(s)))
    n=len(Xs); nv=Xs[0].shape[1]
    print("\n=== %s ===  観測 %d / 平均選択肢数 %.1f"%(name,n,np.mean([x.shape[0] for x in Xs])))
    def nll(b):
        ll=0.0
        for x,y,lp in zip(Xs,ys,PS):
            v=x@b[:nv]+(b[nv]*lp if ps else 0)
            v=v-v.max(); e=np.exp(v); ll+=v[y]-np.log(e.sum())
        return -ll
    k=nv+(1 if ps else 0)
    b0=np.zeros(k); b0[0]=-1.0
    r=minimize(nll,b0,method='BFGS',options={'maxiter':400})
    b=r.x; LL=-r.fun
    Hm=np.zeros((k,k)); h=1e-4
    for i in range(k):
        for j in range(i,k):
            e1=np.zeros(k);e1[i]=h;e2=np.zeros(k);e2[j]=h
            Hm[i,j]=Hm[j,i]=(nll(b+e1+e2)-nll(b+e1-e2)-nll(b-e1+e2)+nll(b-e1-e2))/(4*h*h)
    try: se=np.sqrt(np.abs(np.diag(np.linalg.inv(Hm))))
    except Exception: se=np.full(k,np.nan)
    LL0=-sum(math.log(x.shape[0]) for x in Xs)
    names=['経路長(100m)']+KEYS+(['ln(PathSize)'] if ps else [])
    print("LL=%.1f  LL(0)=%.1f  ρ²=%.3f"%(LL,LL0,1-LL/LL0))
    print("%-14s %10s %9s %8s"%("変数","係数","標準誤差","t値"))
    for nm,x,e in zip(names,b,se): print("%-14s %10.4f %9.4f %8.2f"%(nm,x,e,x/e if e>0 else np.nan))
    return {'name':name,'vars':names,'beta':b.tolist(),'se':se.tolist(),'LL':LL,'LL0':LL0,'n':n}
