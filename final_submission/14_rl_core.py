import json,csv,os,numpy as np,collections,time,itertools
from scipy.sparse import csr_matrix, identity
from scipy.sparse.linalg import spsolve
from scipy.optimize import minimize
H=os.environ['HOME']; OUT=H+"/mnt/network/toyosu"
wd=json.load(open(OUT+"/toyosu_walk_link_WD.geojson"))['features']
LID=[f['properties']['LinkID'] for f in wd]; IDX={l:i for i,l in enumerate(LID)}; A=len(LID)
ON=np.array([f['properties']['ONodeID'] for f in wd]); DN=np.array([f['properties']['DNodeID'] for f in wd])
LEN=np.array([f['properties']['length_m'] for f in wd])/100.0
V={r['LinkID']:r for r in json.load(open(H+"/tmpwork/pca_und.json"))['rows']}
key=lambda i:tuple(sorted((ON[i],DN[i])))
byk={}
for l,r in V.items(): byk[key(IDX[l])]=r
def gv(i,k):
    r=byk.get(key(i)); return float(r[k]) if r else 0.0
FE={k:np.array([gv(i,k) for i in range(A)]) for k in ['PC1','PC2','PC3','z_B','z_D','z_E','z_F']}
for k in FE: FE[k]=(FE[k]-FE[k].mean())/FE[k].std()
head=collections.defaultdict(list)
for i in range(A): head[ON[i]].append(i)
ri=[];rj=[];ut=[]
REV={}
for i in range(A):
    for j in head[DN[i]]:
        ri.append(i); rj.append(j)
        u=1.0 if (ON[i]==DN[j] and DN[i]==ON[j]) else 0.0
        ut.append(u)
        if u: REV[i]=j
ri=np.array(ri); rj=np.array(rj); UT=np.array(ut)
POS={(ri[t],rj[t]):t for t in range(len(ri))}
I=identity(A,format='csc')
OBL={'義務':{'通勤・通学','帰宅','業務','帰社・帰校'}}
GROUPMODE=os.environ.get('GMODE','none'); YEARS=os.environ.get('YEARS','2018,2019,2020,2021').split(',')
ATTR=os.environ.get('ATTRONLY','0')=='1'
trips=[]; META=[]
for Y in YEARS:
    for r in csv.DictReader(open(H+"/tmpwork/paths_%s.csv"%Y,encoding="utf-8-sig")):
        if r['selected']!='1': continue
        if ATTR and not r['Gender']: continue
        ls=[IDX[int(x)] for x in r['link_sequence'].split() if int(x) in IDX]
        if len(ls)<2: continue
        if GROUPMODE=='gender': g=1 if r['Gender']=='2' else 0
        elif GROUPMODE=='child': g=1 if r['NumChildren'] not in ('','0') else 0
        elif GROUPMODE=='covid': g=1 if Y in ('2020','2021') else 0
        elif GROUPMODE=='year': g=int(Y)-2018
        else: g=0
        trips.append((ls,(int(r['D_node']),Y),g)); META.append((Y,r['UserID'],r['Gender']))
print("年別:",collections.Counter(m[0] for m in META))
print("サンプル %d トリップ / 遷移 %d / 目的地 %d / グループ1 %d件"%(
  len(trips),sum(len(t[0])-1 for t in trips),len({t[1] for t in trips}),sum(t[2] for t in trips)))
def build(groups):
    G=collections.defaultdict(lambda:([],[],[],[]))
    for ls,d,g in trips:
        k=(d,g) if groups else (d,0)
        ks,as_,ps,last=G[k]
        for a1,a2 in zip(ls,ls[1:]):
            t=POS.get((a1,a2))
            if t is None: continue
            ks.append(a1); as_.append(a2); ps.append(t)
        last.append(ls[-1])
    return {k:(np.array(v[0]),np.array(v[1]),np.array(v[2]),np.array(v[3])) for k,v in G.items()}
def make_X(spec,g):
    cols=[]
    for s in spec:
        if s=='LEN': cols.append(LEN[rj])
        elif s=='UTURN': cols.append(UT)
        elif s.startswith('P*'): cols.append(FE[s[2:]][rj]*(1.0 if g==1 else 0.0))
        else: cols.append(FE[s][rj])
    return np.vstack(cols).T
def fit(spec,groups=False,b0=None,name="",maxfev=1500,hess=True):
    TR=build(groups)
    Xs={g:make_X(spec,g) for g in (sorted({t[2] for t in trips}) if groups else [0])}
    def nll(b):
        ll=0.0
        Ms={}
        for g,Xg in Xs.items():
            v=Xg@b
            if v.max()>15: return 1e10
            ev=np.exp(v); Ms[g]=(v,(identity(A,format='csc')-csr_matrix((ev,(ri,rj)),shape=(A,A)).tocsc()).tocsc())
        for (d,g),(ks,as_,ps,last) in TR.items():
            v,Am=Ms[g]
            bb=np.where(DN==(d[0] if isinstance(d,tuple) else d),1.0,0.0)
            try: z=spsolve(Am,bb)
            except Exception: return 1e10
            need=np.concatenate([ks,as_,last]); zz=z[need]
            if np.any(~np.isfinite(zz)) or np.any(zz<=0): return 1e10
            ll+=np.sum(v[ps]+np.log(z[as_])-np.log(z[ks]))-np.sum(np.log(z[last]))
        return -ll
    if b0 is None:
        b0=np.array([-3.0 if s=='LEN' else (-3.0 if s=='UTURN' else 0.0) for s in spec])
    t0=time.time()
    r=minimize(nll,b0,method='Nelder-Mead',options={'maxiter':maxfev,'maxfev':maxfev,'xatol':1e-3,'fatol':1e-2})
    b=r.x; LL=-r.fun
    n=len(b); Hm=np.zeros((n,n)); h=1e-3
    if not hess:
        print('%s LL=%.1f'%(name,LL),[round(x,4) for x in b]); return {'name':name,'spec':spec,'beta':b.tolist(),'se':[float('nan')]*n,'LL':LL,'groups':groups}
    for a in range(n):
        for c in range(a,n):
            e1=np.zeros(n); e1[a]=h; e2=np.zeros(n); e2[c]=h
            val=(nll(b+e1+e2)-nll(b+e1-e2)-nll(b-e1+e2)+nll(b-e1-e2))/(4*h*h)
            Hm[a,c]=Hm[c,a]=val
    try:
        cov=np.linalg.inv(Hm); se=np.sqrt(np.abs(np.diag(cov)))
    except Exception: se=np.full(n,np.nan)
    print("\n=== %s ===  LL=%.1f  (%.0fs, %d評価)"%(name,LL,time.time()-t0,r.nfev))
    print("%-14s %10s %9s %8s"%("変数","係数","標準誤差","t値"))
    for s,x,e in zip(spec,b,se): print("%-14s %10.4f %9.4f %8.2f"%(s,x,e,x/e if e>0 else np.nan))
    return {'name':name,'spec':spec,'beta':b.tolist(),'se':se.tolist(),'LL':LL,'groups':groups}
