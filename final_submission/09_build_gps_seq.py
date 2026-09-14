import csv,json,os,bisect,math,collections,sys
H=os.environ['HOME']; Y=sys.argv[1]
trips=list(csv.DictReader(open(f"target_trips_{Y}.csv")))
byu=collections.defaultdict(list)
for i,t in enumerate(trips): byu[t['UserID']].append((t['dep'],t['arr'],i))
for u in byu: byu[u].sort()
starts={u:[x[0] for x in v] for u,v in byu.items()}
KX=math.cos(math.radians(35.65))*111320; KY=110570
pts=collections.defaultdict(list); n=0
for line in open(f"loc{Y}_tgt.csv"):
    p=line.rstrip("\n").split(",")
    if len(p)<4: continue
    u,ts=p[0],p[1]; v=byu.get(u)
    if not v: continue
    j=bisect.bisect_right(starts[u],ts)-1
    for k in (j,j-1):
        if 0<=k<len(v) and v[k][0]<=ts<=v[k][1][:16]+":59.999":
            pts[v[k][2]].append((ts,float(p[2]),float(p[3]))); n+=1; break
seq={}
for i,P in pts.items():
    P.sort(); keep=[]
    for t,la,lo in P:
        if not keep: keep.append((t,la,lo)); continue
        if math.hypot((lo-keep[-1][2])*KX,(la-keep[-1][1])*KY)>=4: keep.append((t,la,lo))
    if len(keep)>=3: seq[i]=keep
print(Y,"窓内の点",n,"／3点以上のトリップ",len(seq),"/",len(trips))
json.dump({str(k):v for k,v in seq.items()},open(f"gps_seq_{Y}.json","w"))
