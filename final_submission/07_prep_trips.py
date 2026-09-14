import csv,json,os,datetime,sys
H=os.environ['HOME']; OUT=H+"/mnt/network/toyosu"; Y=sys.argv[1]
B=json.load(open(OUT+"/toyosu_boundary.geojson"))['features'][0]['geometry']
polys=B['coordinates'] if B['type']=='MultiPolygon' else [B['coordinates']]
bb=[(min(c[0] for c in p[0]),max(c[0] for c in p[0]),min(c[1] for c in p[0]),max(c[1] for c in p[0])) for p in polys]
def ins(x,y,poly):
    c=False
    for ring in poly:
        n=len(ring); j=n-1
        for i in range(n):
            xi,yi=ring[i]; xj,yj=ring[j]
            if (yi>y)!=(yj>y) and x<(xj-xi)*(y-yi)/(yj-yi)+xi: c=not c
            j=i
    return c
ca={}
def inT(x,y):
    k=(round(x,6),round(y,6))
    if k in ca: return ca[k]
    r=any(x0<=x<=x1 and y0<=y<=y1 and ins(x,y,p) for (x0,x1,y0,y1),p in zip(bb,polys)); ca[k]=r; return r
out=[]
for r in csv.DictReader(open(f"trip_toyosu_{Y}.csv")):
    if r['MainTransportationCode']!='500': continue
    try: xo,yo,xd,yd=float(r['LonO']),float(r['LatO']),float(r['LonD']),float(r['LatD'])
    except: continue
    if not(inT(xo,yo) and inT(xd,yd)): continue
    try:
        d=datetime.datetime.strptime(r['DepartureTime'].strip(),"%Y/%m/%d %H:%M")
        a=datetime.datetime.strptime(r['ArrivalTime'].strip(),"%Y/%m/%d %H:%M")
    except: continue
    out.append([r['TripID'],r['UserID'],d.isoformat(sep=' '),a.isoformat(sep=' '),r['Purpose'],
                r['LonO'],r['LatO'],r['LonD'],r['LatD'],r['ODDirectDistance']])
with open(f"{H}/tmpwork/target_trips_{Y}.csv","w",newline="") as f:
    w=csv.writer(f); w.writerow(["TripID","UserID","dep","arr","purpose","LonO","LatO","LonD","LatD","dist"]); w.writerows(out)
open(f"{H}/tmpwork/users{Y}.txt","w").write("\n".join(sorted({r[1] for r in out})))
print(Y,"豊洲内々の徒歩トリップ",len(out),"／ユーザ",len({r[1] for r in out}))
