"""17: 論文用の図をまとめて作成。
入力: $WORK/pca_und.json, toyosu_link_vlm_text.geojson, toyosu_chome_boundary.geojson,
      toyosu_link_usage_2019.geojson ほか
出力: vlm_01〜vlm_16, rl_12〜rl_14 の PNG
"""
import json, os, collections, numpy as np
import matplotlib; matplotlib.use('Agg')
import japanize_matplotlib, matplotlib.pyplot as plt, matplotlib.cm as cm, matplotlib.colors as mc
from matplotlib.lines import Line2D
from wordcloud import WordCloud
exec(open(os.path.join(os.path.dirname(__file__), '00_config.py')).read())
FONT = os.path.dirname(japanize_matplotlib.__file__) + "/fonts/ipaexg.ttf"
SUR='#fcfcfb'; INK='#0b0b0b'; INK2='#52514e'
CATS=['A_形状舗装','B_アクセシビリティ','C_沿道景観','D_設備維持管理','E_リスク','F_好ましい特徴']
LAB=['A 形状・舗装','B 歩行者配慮','C 沿道・景観','D 設備・維持管理','E リスク','F 好ましい特徴']
COL={c:v for c,v in zip(CATS,['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300'])}
P = json.load(open(WORK+"/pca_und.json")); rows=P['rows']; ev=P['ev']; load=P['load']; prof=P['prof']
ch = json.load(open(OUT+"/toyosu_chome_boundary.geojson"))['features']
def base(ax):
    ax.set_facecolor(SUR)
    for f in ch:
        g=f['geometry']; ps=g['coordinates'] if g['type']=='MultiPolygon' else [g['coordinates']]
        for p in ps:
            for r in p: ax.plot([c[0] for c in r],[c[1] for c in r],color='#ddd',lw=.6)
    ax.set_aspect(1/0.813); ax.grid(alpha=.12)
# 図A: カテゴリ×主成分 相関ヒートマップ
M=np.zeros((6,6))
for i,c in enumerate(CATS):
    v=np.array([r['z_'+c[0]] for r in rows])
    for j in range(6): M[i,j]=np.corrcoef(v,[r['PC%d'%(j+1)] for r in rows])[0,1]
fig,ax=plt.subplots(figsize=(8.4,5.6),facecolor=SUR)
im=ax.imshow(M,cmap='RdBu_r',vmin=-.8,vmax=.8)
ax.set_xticks(range(6)); ax.set_xticklabels(["PC%d\n(%.1f%%)"%(i+1,100*ev[i]) for i in range(6)],fontsize=9)
ax.set_yticks(range(6)); ax.set_yticklabels(LAB,fontsize=10)
for i in range(6):
    for j in range(6):
        ax.text(j,i,"%.2f"%M[i,j],ha='center',va='center',fontsize=9,color='white' if abs(M[i,j])>.45 else INK)
plt.colorbar(im,shrink=.8,label='相関係数'); ax.set_title('言語カテゴリと主成分の相関',fontsize=12,pad=12)
plt.tight_layout(); plt.savefig(OUT+"/vlm_15_category_pc_heatmap.png",dpi=130,bbox_inches='tight',facecolor=SUR)
# 図B: 主成分ローディングのヒートマップ
sel=[]
for i in range(4):
    for t,_ in sorted(load['PC%d'%(i+1)].items(),key=lambda x:-abs(x[1]))[:6]:
        if t not in sel: sel.append(t)
Lm=np.array([[load['PC%d'%(j+1)][t] for j in range(6)] for t in sel])
fig,ax=plt.subplots(figsize=(8.6,0.34*len(sel)+2),facecolor=SUR)
im=ax.imshow(Lm,cmap='RdBu_r',vmin=-np.abs(Lm).max(),vmax=np.abs(Lm).max(),aspect='auto')
ax.set_xticks(range(6)); ax.set_xticklabels(["PC%d"%(i+1) for i in range(6)],fontsize=9)
ax.set_yticks(range(len(sel))); ax.set_yticklabels(sel,fontsize=9)
plt.colorbar(im,shrink=.7,label='ローディング'); ax.set_title('主成分ベクトルのヒートマップ',fontsize=12,pad=12)
plt.tight_layout(); plt.savefig(OUT+"/vlm_16_loading_heatmap.png",dpi=130,bbox_inches='tight',facecolor=SUR)
# 図: 卓越カテゴリ地図 / 街路タイプ地図
cnt=collections.Counter(r['dom_z_cat'] for r in rows)
fig,ax=plt.subplots(figsize=(10,10),facecolor=SUR); base(ax)
for r in rows:
    c=r['geom']['coordinates'] if 'geom' in r else None
    if c is None: continue
    ax.plot([c[0][0],c[1][0]],[c[0][1],c[1][1]],color=COL[r['dom_z_cat']],
            lw=.9+1.6*min(r['dom_z_val'],2.5)/2.5,zorder=3)
ax.legend(handles=[Line2D([0],[0],color=COL[c],lw=3,label="%s（%d本）"%(l,cnt.get(c,0)))
                   for c,l in zip(CATS,LAB)],loc='lower left',frameon=False,fontsize=10)
ax.set_title('リンクごとに最も突出したカテゴリ（zスコア最大）',fontsize=13)
plt.savefig(OUT+"/vlm_08_dominant_category_map.png",dpi=115,bbox_inches='tight',facecolor=SUR)
CC=['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#4a3aa7']
cn=collections.Counter(r['cluster'] for r in rows)
fig,ax=plt.subplots(figsize=(11,10),facecolor=SUR); base(ax)
for r in rows:
    c=r['geom']['coordinates']
    ax.plot([c[0][0],c[1][0]],[c[0][1],c[1][1]],color=CC[r['cluster']-1],lw=2.0,zorder=3)
ax.legend(handles=[Line2D([0],[0],color=CC[i],lw=3,
    label="C%d（%d本）: %s"%(i+1,cn.get(i+1,0),"・".join(prof[str(i)][:4] if str(i) in prof else prof[i][:4])))
    for i in range(6)],loc='lower left',frameon=False,fontsize=9.5)
ax.set_title('街路タイプ分類（語ベクトルのk-means, k=6）',fontsize=13)
plt.savefig(OUT+"/vlm_09_street_type_map.png",dpi=115,bbox_inches='tight',facecolor=SUR)
print("figures ok")
