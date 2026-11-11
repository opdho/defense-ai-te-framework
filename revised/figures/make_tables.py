# Rebuilds tables.json (all numbers in the revised paper's tables and figures) from the per-scenario CSVs.
# Run from the repository root:  python revised/figures/make_tables.py
# Key names: A' = paper A (model_A_rep), B' = paper B (model_B_rep), C = paper C (model_C_clean), D = paper D (model_D);
#            A, B = the submitted models re-evaluated on the same images (eval/2x2_submitted_set).
import csv,json,statistics as st,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
R=str(ROOT/'revised'/'results')+'/'
def load(p):
    return {r['scenario_id']:r for r in csv.DictReader(open(p,encoding='utf-8-sig'))}
def met(rows,floor=0.2):
    v={k:float(r['map50']) for k,r in rows.items()}
    b={k:r['bucket'] for k,r in rows.items()}
    clean=st.mean(v[k] for k in v if b[k]=='clean_reference')
    mpc=st.mean(v[k] for k in v if b[k]!='clean_reference')
    adv=st.mean(v[k] for k in v if b[k] in('adverse','critical'))
    crit=sum(1 for k in v if b[k]=='critical' and v[k]<floor)
    f=[g for g,x,t in (('G1',clean,.7),('G2',adv,.5),('G3',mpc/clean,.65)) if x<t]
    if crit: f.append('G4')
    return dict(clean=clean,mpc=mpc,rpc=mpc/clean,adv=adv,crit=crit,s11=v['SCN_011'],worst=min(v.values()),verdict='PASS' if not f else 'FAIL ('+', '.join(f)+')')
P={'A':R+'eval/2x2_submitted_set/eval_results_model_A.csv','B':R+'eval/2x2_submitted_set/eval_results_model_B.csv',
 "A'":R+'eval/2x2_retrain/eval_results_model_A_rep.csv',"B'":R+'eval/2x2_retrain/eval_results_model_B_rep.csv',
 'C':R+'eval/2x2_retrain/eval_results_model_C_clean.csv','D':R+'eval/2x2_submitted_set/eval_results_model_D.csv'}
rows={k:load(p) for k,p in P.items()}
out={'scn':{k:{s:float(r['map50']) for s,r in v.items()} for k,v in rows.items()},'met':{k:met(v) for k,v in rows.items()}}
out['bucket']={s:r['bucket'] for s,r in rows['A'].items()}
out['fam']={s:r.get('corruption_family','') for s,r in rows['A'].items()}
M=out['met']
eff={}
for k in('clean','mpc','rpc','adv','s11'):
    eff[k]=dict(arch=((M['D'][k]-M["A'"][k])+(M["B'"][k]-M['C'][k]))/2, recipe=((M['C'][k]-M["A'"][k])+(M["B'"][k]-M['D'][k]))/2,
      arch_base=M['D'][k]-M["A'"][k], arch_rob=M["B'"][k]-M['C'][k], rec_n=M['C'][k]-M["A'"][k], rec_s=M["B'"][k]-M['D'][k])
out['eff']=eff
# seeds
mp={'A':'A','B':'B',"A'":'A_rep',"B'":'B_rep','C':'C_clean','D':'D'}
seeds={}
for k,m in mp.items():
    per=[met(load(R+f'eval/preset_seed{s}/eval_results_model_{m}.csv')) for s in range(5)]
    seeds[k]={x:[st.mean(p[x] for p in per),st.stdev(p[x] for p in per)] for x in('clean','mpc','rpc','adv','s11')}
    seeds[k]['verdicts']=[p['verdict'] for p in per]
    fl={}
    for f in (0.05,0.10,0.15,0.20,0.25,0.30):
        fl[f'{f:.2f}']=sum(1 for s in range(5) if met(load(R+f'eval/preset_seed{s}/eval_results_model_{m}.csv'),f)['verdict']=='PASS')
    seeds[k]['floor_pass']=fl
out['seeds']=seeds
sub={}
for k,v in rows.items():
    sub[k]={f'{f:.2f}':(met(v,f)['crit'],met(v,f)['verdict']) for f in (0.05,0.10,0.15,0.20,0.25,0.30)}
out['floor_sub']=sub
g=R+'eval/llm_gemma4_12b_seed0/'
out['e2']={k:met(load(g+f'eval_results_model_{k}.csv')) for k in 'ABCD'}
out['e2scn']={k:{s:float(r['map50']) for s,r in load(g+f'eval_results_model_{k}.csv').items()} for k in 'ABCD'}
json.dump(out,open(Path(__file__).with_name('tables.json'),'w'),indent=1,ensure_ascii=False)
for k,v in M.items(): print(k,{a:(round(b,4) if isinstance(b,float) else b) for a,b in v.items()})
for k,v in eff.items(): print(k,{a:round(b,4) for a,b in v.items()})
for k,v in seeds.items(): print(k,v['floor_pass'],set(v['verdicts']))
print(out['fam'])

# ---- E7 / E9 ----
E=R+'eval/'
g=R+'eval/llm_gemma4_12b_seed0/'
e7src={'A':g+'eval_results_model_A.csv','B':g+'eval_results_model_B.csv','D':g+'eval_results_model_D.csv',
 "A'":E+'e7_gemma_seed0_retrain/eval_results_model_A_rep.csv',"B'":E+'e7_gemma_seed0_retrain/eval_results_model_B_rep.csv','C':E+'e7_gemma_seed0_retrain/eval_results_model_C_clean.csv'}
e9src={'A':'A','B':'B','D':'D',"A'":'A_rep',"B'":'B_rep','C':'C_clean'}
out['e7']={k:met(load(p)) for k,p in e7src.items()}
out['e7scn']={k:{s:float(r['map50']) for s,r in load(p).items()} for k,p in e7src.items()}
out['e9']={k:met(load(E+f'e9_hybrid_seed0/eval_results_model_{m}.csv')) for k,m in e9src.items()}
out['e9scn']={k:{s:float(r['map50']) for s,r in load(E+f'e9_hybrid_seed0/eval_results_model_{m}.csv').items()} for k,m in e9src.items()}
json.dump(out,open(Path(__file__).with_name('tables.json'),'w'),indent=1,ensure_ascii=False)
for nm in ('e7','e9'):
    print(nm)
    for k,v in out[nm].items(): print(' ',k,{a:(round(b,4) if isinstance(b,float) else b) for a,b in v.items()})
