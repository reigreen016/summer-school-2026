"""14b: 論文に載せた全RLモデルを推定する実行スクリプト。
14_rl_core.py を exec で読み込み、fit(spec, groups, b0, name) を呼ぶ。
環境変数: YEARS(既定 2018,2019,2020,2021), GMODE(none|covid|gender|child|year), ATTRONLY(0|1)
使用例:
  GMODE=none  YEARS=2019           python3 14b_rl_run.py base      # 2019単年 M1/M2
  GMODE=covid YEARS=2018,2019,2020,2021 python3 14b_rl_run.py covid # P2/P3
  GMODE=child YEARS=2021           python3 14b_rl_run.py child     # M2/M5
  GMODE=gender YEARS=2018,2021 ATTRONLY=1 python3 14b_rl_run.py gender
※ 対数尤度関数は多峰性をもつため、必ず交互作用モデルの解を初期値に
   基準モデルを再推定すること(局所解対策)。15_multistart.py も併用。
"""
import os, sys, json, math, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
exec(open(os.path.join(HERE, '14_rl_core.py')).read())
MODE = sys.argv[1] if len(sys.argv) > 1 else 'base'
SPEC0 = ['LEN','UTURN']
SPEC1 = ['LEN','PC1','PC2','PC3','z_E','z_F','UTURN']
SPEC2 = ['LEN','PC1','PC2','PC3','z_E','z_F','P*PC1','P*PC2','P*z_E','UTURN']
TR0 = build(False); ll0 = 0.0
for (d,g),(ks,as_,ps,last) in TR0.items():
    for k in ks:  ll0 += -math.log(max(len(head[DN[k]]),1))
    for k in last: ll0 += -math.log(max(len(head[DN[k]]),1)+1)
print("LL(0) = %.1f" % ll0)
R = [fit(SPEC0, name='M1 基本(長さ+Uターン)'),
     fit(SPEC1, name='M2 +景観主成分')]
if MODE != 'base':
    b0 = np.array(R[1]['beta'][:6] + [0.0,0.0,0.0] + [R[1]['beta'][6]])
    m = fit(SPEC2, groups=True, b0=b0, name='M3 +交互作用(%s)' % MODE, maxfev=1200)
    # 交互作用モデルの解を初期値に基準モデルを再推定(局所解対策)
    b1 = np.array([m['beta'][m['spec'].index(s)] for s in SPEC1])
    R[1] = fit(SPEC1, b0=b1, name='M2 +景観主成分(再推定)', maxfev=900)
    R.append(m)
for r in R: r['LL0'] = ll0
json.dump(R, open(os.environ.get('WORK', os.environ['HOME']+'/tmpwork')+f"/rl_{MODE}.json","w"), ensure_ascii=False)
print("\n%-28s %10s %8s %4s" % ("モデル","対数尤度","ρ²","k"))
for r in R: print("%-28s %10.1f %8.3f %4d" % (r['name'], r['LL'], 1-r['LL']/ll0, len(r['beta'])))
if len(R) == 3:
    print("尤度比検定 LR = %.1f (%d df)" % (2*(R[2]['LL']-R[1]['LL']), len(R[2]['beta'])-len(R[1]['beta'])))
