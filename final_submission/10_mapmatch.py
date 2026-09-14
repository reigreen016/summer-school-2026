import json,math,os,heapq,collections,time,sys
H=os.environ['HOME']; OUT=H+"/mnt/network/toyosu"
KX=math.cos(math.radians(35.65))*111320; KY=110570
wd=json.load(open(OUT+"/toyosu_walk_link_WD.geojson"))['features']
L=[]  # directed links
for f in wd:
    p=f['properties']; (x1,y1),(x2,y2)=f['geometry']['coordinates']
    a=(x1*KX,y1*KY); b=(x2*KX,y2*KY)
    L.append({'id':p['LinkID'],'o':p['ONodeID'],'d':p['DNodeID'],'a':a,'b':b,
              'len':math.hypot(b[0]-a[0],b[1]-a[1])})
NODE={}
for l in L: NODE[l['o']]=l['a']; NODE[l['d']]=l['b']
adj=collections.defaultdict(list)
for i,l in enumerate(L): adj[l['o']].append((l['d'],l['len'],i))
def dij(s):
    dist={s:0.0}; pq=[(0.0,s)]
    while pq:
        d,u=heapq.heappop(pq)
        if d>dist.get(u,1e18)+1e-9: continue
        for v,w,_ in adj[u]:
            nd=d+w
            if nd<dist.get(v,1e18): dist[v]=nd; heapq.heappush(pq,(nd,v))
    return dist
SP={n:dij(n) for n in NODE}
def path_nodes(s,t):
    if s==t: return [s]
    dist={s:0.0}; prev={}; pq=[(0.0,s)]
    while pq:
        d,u=heapq.heappop(pq)
        if u==t: break
        if d>dist.get(u,1e18)+1e-9: continue
        for v,w,i in adj[u]:
            nd=d+w
            if nd<dist.get(v,1e18): dist[v]=nd; prev[v]=(u,i); heapq.heappush(pq,(nd,v))
    if t not in dist: return None
    seq=[]; cur=t
    while cur!=s: u,i=prev[cur]; seq.append(i); cur=u
    return seq[::-1]
G=collections.defaultdict(list); C=50.
for i,l in enumerate(L):
    if i%2: continue
    a,b=l['a'],l['b']
    for gx in range(int(min(a[0],b[0])//C)-1,int(max(a[0],b[0])//C)+2):
        for gy in range(int(min(a[1],b[1])//C)-1,int(max(a[1],b[1])//C)+2): G[(gx,gy)].append(i)
UND=collections.defaultdict(list)
for i,l in enumerate(L): UND[tuple(sorted((l['o'],l['d'])))].append(i)
REV=[None]*len(L)
for k,v in UND.items():
    if len(v)==2: REV[v[0]]=v[1]; REV[v[1]]=v[0]
def proj(p,l):
    a,b=l['a'],l['b']; dx,dy=b[0]-a[0],b[1]-a[1]; s=dx*dx+dy*dy
    t=0.0 if s==0 else max(0.0,min(1.0,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/s))
    q=(a[0]+dx*t,a[1]+dy*t)
    return math.hypot(p[0]-q[0],p[1]-q[1]), t*l['len']
def cands(p,R=25,K=5):
    gx,gy=int(p[0]//C),int(p[1]//C); seen=set(); out=[]
    for ddx in(-1,0,1):
        for ddy in(-1,0,1):
            for i in G.get((gx+ddx,gy+ddy),[]):
                for j in UND[tuple(sorted((L[i]['o'],L[i]['d'])))]:
                    if j in seen: continue
                    seen.add(j); d,off=proj(p,L[j])
                    if d<=R: out.append((d,j,off))
    out.sort(); return out[:K]
SIG=10.0; BETA=4.0
def match(P):
    raw=[(lo*KX,la*KY) for _,la,lo in P]
    sm=[]
    for i in range(len(raw)):
        w=raw[max(0,i-1):i+2]
        sm.append((sum(p[0] for p in w)/len(w),sum(p[1] for p in w)/len(w)))
    pts=[sm[0]]
    for p in sm[1:]:
        if math.dist(p,pts[-1])>=20: pts.append(p)
    if len(pts)<3: pts=sm
    cs=[cands(p) for p in pts]
    idx=[i for i,c in enumerate(cs) if c]
    if len(idx)<2: return None
    prevcol=None; back=[]
    for k,i in enumerate(idx):
        col={}
        for d,j,off in cs[i]:
            em=-(d*d)/(2*SIG*SIG)
            if prevcol is None: col[j]=(em,None,off)
            else:
                gd=math.dist(pts[idx[k-1]],pts[i]); best=(-1e18,None)
                for pj,(sc,_,poff) in prevcol.items():
                    if pj==j: rd=abs(off-poff)
                    else:
                        s=SP.get(L[pj]['d'],{}).get(L[j]['o'])
                        rd=None if s is None else (L[pj]['len']-poff)+s+off
                    if rd is None or rd>gd*3+80: continue
                    v=sc-abs(rd-gd)/BETA
                    if v>best[0]: best=(v,pj)
                if best[1] is None: col[j]=(em-50,None,off)
                else: col[j]=(best[0]+em,best[1],off)
        if not col: return None
        back.append(col); prevcol=col
    j=max(prevcol,key=lambda k:prevcol[k][0]); seq=[j]
    for k in range(len(back)-1,0,-1):
        j=back[k][j][1]
        if j is None: j=max(back[k-1],key=lambda z:back[k-1][z][0])
        seq.append(j)
    seq.reverse()
    out=[]
    for j in seq:
        if not out or out[-1]!=j: out.append(j)
    full=[]
    for k,j in enumerate(out):
        if k==0: full.append(j); continue
        pj=full[-1]
        if L[pj]['d']==L[j]['o']: full.append(j); continue
        pth=path_nodes(L[pj]['d'],L[j]['o'])
        if pth is None or len(pth)>10: full.append(j)
        else: full.extend(pth+[j])
    ded=[]
    for j in full:
        if not ded or ded[-1]!=j: ded.append(j)
    ch=True
    while ch:
        ch=False; o2=[]; i=0
        while i<len(ded):
            if i+2<len(ded) and REV[ded[i]]==ded[i+1] and ded[i+2]==ded[i]:
                o2.append(ded[i]); i+=3; ch=True
            else: o2.append(ded[i]); i+=1
        ded=o2
    md=[cs[i][0][0] for i in idx]
    return ded,sum(md)/len(md),len(idx)
seq=json.load(open(H+"/tmpwork/gps_seq_2019.json"))
done=set()
fn=H+"/tmpwork/matched_A_2019.jsonl"
if os.path.exists(fn):
    for line in open(fn): done.add(json.loads(line)['trip'])
f=open(fn,"a"); t0=time.time(); n=0
for k,P in seq.items():
    if k in done: continue
    if time.time()-t0>140: break
    r=match(P)
    if r is None:
        f.write(json.dumps({'trip':k,'ok':0})+"\n"); n+=1; continue
    ded,md,npt=r
    f.write(json.dumps({'trip':k,'ok':1,'links':[L[j]['id'] for j in ded],
        'len_m':round(sum(L[j]['len'] for j in ded),1),'mean_dist_m':round(md,1),'n_pts':npt})+"\n"); n+=1
f.close()
print("処理",n,"／累計",len(done)+n,"／全",len(seq))
