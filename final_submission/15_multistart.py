import os,json,time,numpy as np,collections
BASE=os.environ.get('BASE','rl2b.py'); TAG=os.environ.get('TAG','2019')
SPEC=os.environ.get('SPEC','LEN,PC1,PC2,PC3,z_E,z_F,UTURN').split(',')
GROUPS=os.environ.get('GROUPS','0')=='1'
SEED=os.environ.get('SEEDFILE','')
NSTART=int(os.environ.get('NSTART','16')); BUDGET=float(os.environ.get('BUDGET','150'))
exec(open(BASE).read())
seed=np.array(json.load(open(SEED))['beta']) if SEED else None
fn="ms_%s.json"%TAG
res=json.load(open(fn)) if os.path.exists(fn) else []
rng=np.random.default_rng(100+len(res))
t0=time.time()
while len(res)<NSTART and time.time()-t0<BUDGET:
    i=len(res)
    if i==0 and seed is not None: b0=seed.copy()
    elif i<5:
        b0=np.array([{-1:0}.get(0,0.0) for _ in SPEC],dtype=float)
        for j,s in enumerate(SPEC):
            b0[j]= (-2.0-i*0.8) if s=='LEN' else ((-2.0-i*0.4) if s=='UTURN' else 0.0)
    else:
        base=seed if seed is not None else np.array(res[0]['beta'])
        b0=base.copy()
        for j,s in enumerate(SPEC):
            if s=='LEN': b0[j]*=rng.uniform(0.7,1.4)
            elif s=='UTURN': b0[j]*=rng.uniform(0.7,1.4)
            else: b0[j]=b0[j]+rng.normal(0,0.25)
    r=fit(SPEC,groups=GROUPS,b0=np.array(b0),name="s%d"%i,maxfev=800,hess=False)
    res.append({'LL':r['LL'],'beta':r['beta']}); json.dump(res,open(fn,'w'))
ok=[r for r in res if r['LL']>-1e9]
LLs=[r['LL'] for r in ok]
if LLs:
    best=max(range(len(ok)),key=lambda i:LLs[i])
    print("\n[%s] 試行 %d回 (収束 %d回)  最良LL=%.2f"%(TAG,len(res),len(ok),max(LLs)))
    print("  LL分布:",collections.Counter(round(x,1) for x in LLs).most_common(6))
    print("  最良解の再現率: %.0f%%"%(100*sum(1 for x in LLs if x>max(LLs)-0.5)/len(LLs)))
    print("  最良解:",dict(zip(SPEC,[round(x,4) for x in ok[best]['beta']])))
