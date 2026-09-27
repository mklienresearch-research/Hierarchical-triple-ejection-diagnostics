# FROZEN PROSPECTIVE 300 -> 3000 T_out SCORING
# Run only after FINAL_EXPANDED_AUDIT has completed. No model refit/calibration.
import json, csv, hashlib, shutil
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score,average_precision_score

OUT=Path('/kaggle/working/prospective_tail_scoring');OUT.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
    if p.is_file():p.unlink()
FARS=[0.001,0.01,0.05];BOOT=500

def find(name):
    hits=[]
    for root in [Path('/kaggle/working'),Path('/kaggle/input')]:
        if root.exists():hits.extend(root.rglob(name))
    if not hits:raise FileNotFoundError(name)
    return sorted(hits,key=lambda p:(0 if str(p).startswith('/kaggle/working') else 1,len(p.parts),str(p)))[0]
score_path=find('triples_untouched_test_scores.npz');threshold_path=find('triples_thresholds.json');tail_path=find('matched_tail_outcomes.csv')
print('scores:',score_path);print('thresholds:',threshold_path);print('tail:',tail_path)
with np.load(score_path,allow_pickle=False) as z:
    test_ids=z['test_ids'].astype(int);main_y=z['y'];fracs=z['fractions'].astype(float);scores=z['score_combined'].astype(float)
with open(threshold_path) as f:thresholds=json.load(f)
tail=pd.read_csv(tail_path);tail=tail.set_index('system_id')
rows=[]
for i,sid in enumerate(test_ids):
    if sid not in tail.index:continue
    r=tail.loc[sid]
    if int(r.stable_at_300)!=1:continue
    te=float(r.tail_event_time_outer) if pd.notna(r.tail_event_time_outer) else np.nan
    # Clean prospective endpoint: delayed ejection after 300 versus still stable at 3000.
    if int(r.delayed_ejection)==1:
        label=1
    elif str(r.tail_status_3000)=='stable':
        label=0
    else:
        continue # early cross-run disagreement, collision, or numerical failure
    rows.append((i,int(sid),label,te,str(r.delayed_ejection_type)))
if not rows:raise RuntimeError('No matched untouched test systems')
pos=np.array([r[0] for r in rows]);ids=np.array([r[1] for r in rows]);y=np.array([r[2] for r in rows]);event=np.array([r[3] for r in rows]);etype=np.array([r[4] for r in rows])
P=scores[pos]
print('prospective cohort',len(y),'delayed',y.sum(),'controls',(y==0).sum())

def ci_auc(y,p,seed):
    rng=np.random.default_rng(seed);a=[];ap=[];n=len(y)
    for _ in range(BOOT):
        ii=rng.integers(0,n,n)
        if len(np.unique(y[ii]))<2:continue
        a.append(roc_auc_score(y[ii],p[ii]));ap.append(average_precision_score(y[ii],p[ii]))
    return dict(auc_lo=float(np.percentile(a,2.5)),auc_hi=float(np.percentile(a,97.5)),
                pr_lo=float(np.percentile(ap,2.5)),pr_hi=float(np.percentile(ap,97.5)))

def threshold_for(f,far):
    key=min(thresholds,key=lambda k:abs(float(k)-f));entries=thresholds[key]['combined']
    return float(next(x['threshold'] for x in entries if abs(float(x['target_far'])-far)<1e-12))
horizon_rows=[]
for j,f in enumerate(fracs):
    valid=np.isfinite(P[:,j]);yy=y[valid];pp=P[valid,j]
    row=dict(f=float(f),t_warning_outer=float(300*f),n=int(valid.sum()),n_delayed=int(yy.sum()),prevalence=float(yy.mean()),
             roc_auc=float(roc_auc_score(yy,pp)),pr_auc=float(average_precision_score(yy,pp)))
    row.update(ci_auc(yy,pp,91000+j));fixed=[]
    for far in FARS:
        th=threshold_for(float(f),far);pred=pp>=th;neg=yy==0;positive=yy==1
        fixed.append(dict(target_original_far=far,threshold=th,achieved_far_delayed_endpoint=float(pred[neg].mean()),
          delayed_tpr=float(pred[positive].mean()),precision=float(yy[pred].mean()) if pred.any() else np.nan,n_alerts=int(pred.sum())))
    row['frozen_thresholds']=fixed;horizon_rows.append(row)
# Earliest frozen warning across horizons.
lead_rows=[]
for far in FARS:
    th=np.array([threshold_for(float(f),far) for f in fracs]);leads=[];types=[];warned=[];false=0
    for i in range(len(y)):
        hit=np.where(np.isfinite(P[i])&(P[i]>=th))[0]
        if not len(hit):continue
        j=int(hit[0]);warned.append(i)
        if y[i]==1:
            leads.append(float(event[i]-300*fracs[j]));types.append(str(etype[i]))
        else:false+=1
    leads=np.array(leads);positive=leads[leads>0]
    lead_rows.append(dict(target_original_far=far,n_delayed=int(y.sum()),n_controls=int((y==0).sum()),n_delayed_warned=len(leads),
      delayed_coverage=float(len(leads)/max(y.sum(),1)),cumulative_control_false_alert=float(false/max((y==0).sum(),1)),
      positive_lead_fraction=float(len(positive)/max(len(leads),1)),median_lead_outer=float(np.median(leads)) if len(leads) else np.nan,
      p25=float(np.percentile(leads,25)) if len(leads) else np.nan,p75=float(np.percentile(leads,75)) if len(leads) else np.nan,
      inner_warned=int(sum(t=='inner-member' for t in types)),outer_warned=int(sum(t=='outer-member' for t in types))))
result={'protocol':{'model_refit':False,'threshold_recalibration':False,'endpoint':'delayed ejection after 300 by 3000','report_null_or_positive':True},
        'score_source':str(score_path),'threshold_source':str(threshold_path),'tail_source':str(tail_path),
        'cohort':{'n':len(y),'n_delayed':int(y.sum()),'n_stable_controls':int((y==0).sum()),'prevalence':float(y.mean())},
        'horizons':horizon_rows,'lead_by_frozen_far':lead_rows}
with open(OUT/'prospective_tail_scoring.json','w') as f:json.dump(result,f,indent=1)
np.savez_compressed(OUT/'prospective_matched_scores.npz',system_id=ids,y_delayed=y,event_time_outer=event,event_type=etype,fractions=fracs,combined_scores=P)
manifest={'status':'complete','files':{}}
for p in OUT.iterdir():
    if p.is_file():manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
with open(OUT/'OUTPUT_MANIFEST.json','w') as f:json.dump(manifest,f,indent=2)
zip_path=shutil.make_archive('/kaggle/working/prospective_tail_scoring','zip',root_dir=str(OUT))
print(json.dumps(result['cohort'],indent=2));print(json.dumps(lead_rows,indent=2));print('DOWNLOAD',zip_path)
