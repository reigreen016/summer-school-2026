import json,csv,math,os,statistics,datetime,collections,heapq,sys
H=os.environ['HOME']; OUT=H+"/mnt/network/toyosu"; Y=sys.argv[1]
KX=math.cos(math.radians(35.65))*111320; KY=110570
wd=json.load(open(OUT+"/toyosu_walk_link_WD.geojson"))['features']
LK={f['properties']['LinkID']:f for f in wd}; L={f['properties']['LinkID']:f['properties'] for f in wd}
adj=collections.defaultdict(list)
for f in wd:
    p=f['properties']; adj[p['ONodeID']].append((p['DNodeID'],p['length_m'],p['LinkID']))
def sp(s,t):
    dist={s:0.0}; prev={}; pq=[(0.0,s)]
    while pq:
        d,u=heapq.heappop(pq)
        if u==t: break
        if d>dist.get(u,1e18)+1e-9: continue
        for v,w,i in adj[u]:
            nd=d+w
            if nd<dist.get(v,1e18): dist[v]=nd; prev[v]=(u,i); heapq.heappush(pq,(nd,v))
    if t not in dist: return None
    o=[];cur=t
    while cur!=s: u,i=prev[cur]; o.append(i); cur=u
    return o[::-1]
# 属性
att={}
if Y=='2018':
    for x in csv.DictReader(open(H+"/mnt/Toyosu2018-2021/2018_Toyosu_PP_Survey_Individual_Attribute_Data.csv")):
        att[x['TF System ID'].strip()]={'Gender':x['Sex'],'Age':x['Age'],'NumChildren':''}
elif Y=='2021':
    mp={}
    for r in list(csv.reader(open(H+"/mnt/Toyosu2018-2021/ID_panel_survey.csv")))[2:]:
        if len(r)>2 and r[1].strip(): mp[r[1].strip()]=r[2].strip()
    for x in csv.DictReader(open(H+"/mnt/Toyosu2018-2021/2019-21_Toyosu_PP_Survey_Individual_Attribute_Data.csv")):
        if x['ID'] in mp: att[mp[x['ID']]]={'Gender':x['Gender'],'Age':x['Age'],'NumChildren':x['Number of Children']}
seq=json.load(open(f"gps_seq_{Y}.json")); tr=list(csv.DictReader(open(f"target_trips_{Y}.csv")))
R={json.loads(l)['trip']:json.loads(l) for l in open(f"matched_A_{Y}.jsonl")}
rows=[]; cache={}
for k,P in seq.items():
    r=R.get(k)
    if not r or not r['ok'] or len(r['links'])<2: continue
    t=tr[int(k)]
    g=sum(math.hypot((b[2]-a[2])*KX,(b[1]-a[1])*KY) for a,b in zip(P,P[1:]))
    dt=(datetime.datetime.fromisoformat(t['arr'])-datetime.datetime.fromisoformat(t['dep'])).total_seconds()/60
    ratio=r['len_m']/g if g>50 else None
    q=int((ratio is not None and ratio<=1.5) and r['mean_dist_m']<=15 and 2<=dt<=120)
    ls=r['links']; o=LK[ls[0]]['properties']['ONodeID']; d=LK[ls[-1]]['properties']['DNodeID']
    if (o,d) not in cache: cache[(o,d)]=sp(o,d)
    s=cache[(o,d)]; sl=sum(L[i]['length_m'] for i in s) if s else 0
    det=r['len_m']/sl if sl>0 else None
    sel=int(q==1 and sl>=300 and det is not None and det<=1.6)
    a=att.get(t['UserID'],{})
    rows.append([Y,t['TripID'],t['UserID'],t['purpose'],round(dt,1),o,d,len(ls),r['len_m'],round(g,1),
                 round(ratio,2) if ratio else "",r['mean_dist_m'],q,round(sl,1),round(det,2) if det else "",sel,
                 a.get('Gender',''),a.get('Age',''),a.get('NumChildren','')," ".join(map(str,ls))])
hdr=["year","TripID","UserID","purpose","dur_min","O_node","D_node","n_links","path_len_m","gps_len_m","len_ratio",
     "mean_dist_m","quality_ok","sp_len_m","detour","selected","Gender","Age","NumChildren","link_sequence"]
with open(f"paths_{Y}.csv","w",newline="",encoding="utf-8-sig") as f:
    w=csv.writer(f); w.writerow(hdr); w.writerows(rows)
s=[r for r in rows if r[15]==1]
print("%s: マッチ %d ／品質OK %d ／目的地指向 %d ／ユーザ %d ／目的地 %d ／遷移 %d ／属性あり %d"%(
  Y,len(rows),sum(1 for r in rows if r[12]==1),len(s),len({r[2] for r in s}),len({r[6] for r in s}),
  sum(r[7]-1 for r in s),sum(1 for r in s if r[16])))
