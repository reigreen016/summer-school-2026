"""06: PPデータの基礎集計(交通手段・目的分担率、年次推移、豊洲内々の集計)。
入力: $PP/trip_toyosu_{2018..2021}.csv, $OUT/toyosu_boundary.geojson
出力: $PP/basic_stats/*.csv, $PP/basic_stats_toyosu/*.csv, 図PNG
"""
import csv, collections, json, os, statistics, datetime, math, sys
import matplotlib; matplotlib.use('Agg')
import japanize_matplotlib, matplotlib.pyplot as plt, numpy as np
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
inT = make_in_toyosu(OUT + "/toyosu_boundary.geojson")
MODE6 = {100:'鉄道系',101:'鉄道系',103:'鉄道系',200:'鉄道系',201:'バス',
         300:'自動車・二輪',301:'自動車・二輪',302:'自動車・二輪',303:'自動車・二輪',
         400:'自転車',401:'自転車',402:'その他',500:'徒歩',600:'その他',601:'その他',602:'その他',999:'その他'}
PUR6 = {300:'帰宅',400:'買物',100:'通勤・通学',200:'業務',201:'業務',401:'食事'}
PUR5 = {'通勤・通学':'義務','帰社・帰校':'義務','帰宅':'義務','業務':'義務',
        '習い事':'活動','通院':'活動','送迎':'活動','買物':'生活','食事':'生活',
        '散策':'余暇','娯楽':'余暇','待ち時間':'余暇','観光':'余暇'}
M6 = ['徒歩','自転車','鉄道系','自動車・二輪','バス','その他']
P6 = ['帰宅','買物','通勤・通学','業務','食事','その他']
P5 = ['義務','活動','生活','余暇','その他']
COL = {'徒歩':'#2a78d6','鉄道系':'#eb6834','自転車':'#1baf7a','自動車・二輪':'#eda100',
       'バス':'#e87ba4','その他':'#008300','帰宅':'#2a78d6','通勤・通学':'#1baf7a','買物':'#eda100',
       '業務':'#e87ba4','食事':'#008300','義務':'#2a78d6','活動':'#eb6834','生活':'#1baf7a','余暇':'#eda100'}
SUR='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'
rows = []
for y in (2018,2019,2020,2021):
    for r in csv.DictReader(open(f"{PP}/trip_toyosu_{y}.csv")):
        try: mc=int(r['MainTransportationCode']); pc=int(r['PurposeID'])
        except Exception: continue
        try: dt=datetime.datetime.strptime(r['DepartureTime'].strip(),"%Y/%m/%d %H:%M")
        except Exception: dt=None
        try: xo,yo,xd,yd = float(r['LonO']),float(r['LatO']),float(r['LonD']),float(r['LatD'])
        except Exception: xo=yo=xd=yd=None
        both = (xo is not None) and inT(xo,yo) and inT(xd,yd)
        rows.append({'y':y,'u':r['UserID'],'m6':MODE6.get(mc,'その他'),'mn':r['MainTransportationName'],
                     'p6':PUR6.get(pc,'その他'),'pn':r['Purpose'],'p5':PUR5.get(r['Purpose'],'その他'),
                     'dt':dt,'both':both,'tt':float(r['TripTime'] or 0)/60,'d':float(r['ODDirectDistance'] or 0)})
def share(sub,key,order):
    c=collections.Counter(x[key] for x in sub); t=len(sub)
    return [(k,c.get(k,0),100*c.get(k,0)/t) for k in order]
def pie(items,title,sub,fn):
    it=sorted([x for x in items if x[2]>=0.1],key=lambda x:-x[1])
    fig,ax=plt.subplots(figsize=(7.6,6.4),facecolor=SUR); ax.set_facecolor(SUR)
    wg,_=ax.pie([x[1] for x in it],colors=[COL[x[0]] for x in it],startangle=90,counterclock=False,
                wedgeprops=dict(edgecolor=SUR,linewidth=2))
    for we,(k,n,s) in zip(wg,it):
        an=math.radians((we.theta1+we.theta2)/2); r0=.72 if s>=8 else 1.16
        ax.text(r0*math.cos(an),r0*math.sin(an),f"{k}\n{s:.1f}%",ha='center',va='center',
                fontsize=11 if s>=8 else 9.5,color='white' if s>=8 else INK,
                fontweight='bold' if s>=8 else 'normal')
    ax.set_title(title,fontsize=14,color=INK,pad=14); ax.text(0,-1.42,sub,ha='center',fontsize=9,color=INK2)
    plt.savefig(fn,dpi=130,bbox_inches='tight',facecolor=SUR); plt.close(); print(fn)
for tag, sel, d in (("all", lambda r: True, PP+"/basic_stats"),
                    ("toyosu", lambda r: r['both'], PP+"/basic_stats_toyosu")):
    os.makedirs(d, exist_ok=True); S = [r for r in rows if sel(r)]
    for nm, key, order in (("mode",'m6',M6), ("purpose",'p6',P6), ("purpose5",'p5',P5)):
        sh = share(S,key,order)
        with open(f"{d}/{nm}_share_{tag}.csv","w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f); w.writerow(["区分","トリップ数","分担率(%)"])
            for k,n,s in sh: w.writerow([k,n,round(s,2)])
        pie(sh, f"{'交通手段' if nm=='mode' else '移動目的'}分担率（{tag}）",
            f"{len(S):,}トリップ", f"{d}/{nm}_share_{tag}.png")
    with open(f"{d}/summary_by_year_{tag}.csv","w",newline="",encoding="utf-8-sig") as f:
        w=csv.writer(f); w.writerow(["年","トリップ数","被験者","延べ人日","原単位"])
        for y in (2018,2019,2020,2021):
            R=[r for r in S if r['y']==y]; ud={(r['u'],r['dt'].date()) for r in R if r['dt']}
            w.writerow([y,len(R),len({r['u'] for r in R}),len(ud),round(len(R)/len(ud),2) if ud else ""])
    print(tag, len(S), "トリップ")
