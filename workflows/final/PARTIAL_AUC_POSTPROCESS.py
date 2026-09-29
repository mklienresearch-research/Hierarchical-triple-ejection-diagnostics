#!/usr/bin/env python3
"""Paired standardized partial-AUC analysis on the frozen prospective cohort."""
import argparse,json
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score

ap=argparse.ArgumentParser()
ap.add_argument('--scores',required=True)
ap.add_argument('--tail',required=True)
ap.add_argument('--out',default='partial_auc_results')
ap.add_argument('--boot',type=int,default=1000)
args=ap.parse_args();out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
with np.load(args.scores,allow_pickle=False) as z:data={k:z[k] for k in z.files}
tail=pd.read_csv(args.tail).set_index('system_id');test_ids=data['test_ids'].astype(int);fracs=data['fractions'].astype(float)
matched=[]
for i,sid in enumerate(test_ids):
    if sid not in tail.index:continue
    r=tail.loc[sid]
    if int(r.stable_at_300)!=1:continue
    if int(r.delayed_ejection)==1:y=1
    elif str(r.tail_status_3000)=='stable':y=0
    else:continue
    matched.append((i,int(sid),y))
pos=np.array([x[0] for x in matched]);ids=np.array([x[1] for x in matched]);y=np.array([x[2] for x in matched])
models=['IC_only','window','combined','MA01_margin'];scores={m:data['score_'+m][pos].astype(float) for m in models}
max_fprs=[.001,.01];B=args.boot;rng=np.random.default_rng(20260925);rows=[];boot_store={}
for j,f in enumerate(fracs):
    valid=np.ones(len(y),bool)
    for m in models:valid &= np.isfinite(scores[m][:,j])
    yy=y[valid];S={m:scores[m][valid,j] for m in models};point_full={m:float(roc_auc_score(yy,v)) for m,v in S.items()}
    for alpha in max_fprs:
        point={m:float(roc_auc_score(yy,v,max_fpr=alpha)) for m,v in S.items()}
        best='window' if point['window']>=point['IC_only'] else 'IC_only'
        diff_names={'window_minus_IC':('window','IC_only'),'combined_minus_IC':('combined','IC_only'),
                    'combined_minus_best_single':('combined',best),'IC_minus_MA01':('IC_only','MA01_margin'),
                    'combined_minus_MA01':('combined','MA01_margin')}
        vals={k:[] for k in models};diffs={k:[] for k in diff_names}
        for _ in range(B):
            ii=rng.integers(0,len(yy),len(yy))
            if len(np.unique(yy[ii]))<2:continue
            current={m:roc_auc_score(yy[ii],S[m][ii],max_fpr=alpha) for m in models}
            for m in models:vals[m].append(current[m])
            for name,(a,b) in diff_names.items():diffs[name].append(current[a]-current[b])
        ci_models={m:{'point':point[m],'lo':float(np.percentile(vals[m],2.5)),'hi':float(np.percentile(vals[m],97.5))} for m in models}
        ci_diffs={k:{'point':float(point[a]-point[b]),'lo':float(np.percentile(diffs[k],2.5)),'hi':float(np.percentile(diffs[k],97.5)),'n_boot':len(diffs[k])} for k,(a,b) in diff_names.items()}
        row={'f':float(f),'t_observation_outer':float(300*f),'n':len(yy),'n_delayed':int(yy.sum()),
             'max_fpr':alpha,'definition':'sklearn standardized partial ROC-AUC; random ranking=0.5',
             'full_auc':point_full,'partial_auc':ci_models,'best_single_by_partial_auc':best,'paired_differences':ci_diffs}
        rows.append(row)
        key=f'f{j}_a{alpha}';boot_store[key+'_y']=yy
        for m in models:boot_store[key+'_'+m]=np.asarray(vals[m],np.float32)
result={'protocol':{'refit':False,'recalibration':False,'paired_ID_bootstrap':True,'bootstrap_replicates':B,
                    'horizon_notation':'t_observation=f*300 T_out'},
        'cohort':{'n':len(y),'n_delayed':int(y.sum()),'n_controls':int((y==0).sum()),'prevalence':float(y.mean())},
        'rows':rows}
with open(out/'partial_auc_results.json','w') as f:json.dump(result,f,indent=1)
np.savez_compressed(out/'partial_auc_bootstrap.npz',**boot_store)
print(json.dumps(result,indent=1))
