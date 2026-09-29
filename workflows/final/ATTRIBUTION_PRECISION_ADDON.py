# ZERO-REFIT ATTRIBUTION PRECISION ADD-ON
# Adds IC/combined-vs-MA01 paired intervals, frozen-threshold paired coverage,
# and explicitly retrospective matched-control-budget retrieval comparisons.
import json,hashlib,shutil
from pathlib import Path
import numpy as np,pandas as pd
from sklearn.metrics import roc_auc_score
OUT=Path('/kaggle/working/attribution_precision_addon');OUT.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
    if p.is_file():p.unlink()
BOOT=500;FARS=[.01,.05]
BRANCHES=[
 {'condition':'paired frozen-threshold combined-minus-IC delayed coverage interval excludes zero','claim':'at the observed frozen operating points, joint state-and-dynamics identifies additional delayed ejectors','not_claimed':'equal-FAR delayed-endpoint superiority unless false-alert counts are equal'},
 {'condition':'paired frozen-threshold interval includes zero','claim':'no detectable delayed-coverage increment beyond IC at frozen thresholds','not_claimed':'marginal improvement'},
 {'condition':'retrospective equal-control-budget combined-minus-IC interval excludes zero','claim':'the joint model changes the head-of-ranking composition at equal empirical control budget','not_claimed':'prospective calibration, because the budget cut is selected on delayed-endpoint controls'},
 {'condition':'retrospective equal-budget interval includes zero','claim':'no detectable head-of-ranking increment beyond IC','not_claimed':'marginal improvement'}]
def find(name):
    hits=[]
    for root in [Path('/kaggle/input'),Path('/kaggle/working')]:
        if root.exists():hits.extend(root.rglob(name))
    if not hits:raise FileNotFoundError(name)
    return sorted(hits,key=lambda p:(0 if str(p).startswith('/kaggle/working') else 1,len(p.parts),str(p)))[0]
def dump(n,x):
    with open(OUT/n,'w') as f:json.dump(x,f,indent=1,allow_nan=True)
def threshold(table,f,model,far):
    key=min(table,key=lambda k:abs(float(k)-float(f)))
    return float(next(x['threshold'] for x in table[key][model] if abs(float(x['target_far'])-far)<1e-12))
with np.load(find('triples_untouched_test_scores.npz'),allow_pickle=False) as z:tri={k:z[k] for k in z.files}
with open(find('triples_thresholds.json')) as f:thr=json.load(f)
tail=pd.read_csv(find('matched_tail_outcomes.csv')).set_index('system_id');test_ids=tri['test_ids'].astype(int);fracs=tri['fractions'].astype(float)
matched=[]
for i,sid in enumerate(test_ids):
    if sid not in tail.index:continue
    r=tail.loc[sid]
    if int(r.stable_at_300)!=1:continue
    if int(r.delayed_ejection)==1:y=1
    elif str(r.tail_status_3000)=='stable':y=0
    else:continue
    matched.append((i,int(sid),y,float(r.tail_event_time_outer) if pd.notna(r.tail_event_time_outer) else np.nan))
pos=np.array([x[0] for x in matched]);ids=np.array([x[1] for x in matched]);y=np.array([x[2] for x in matched]);event=np.array([x[3] for x in matched])
models=['IC_only','window','combined','MA01_margin'];P={m:tri['score_'+m][pos].astype(float) for m in models}
rng=np.random.default_rng(98001)
# Paired per-horizon AUC differences.
auc_rows=[]
for j,f in enumerate(fracs):
    valid=np.ones(len(y),bool)
    for m in models:valid&=np.isfinite(P[m][:,j])
    yy=y[valid];S={m:P[m][valid,j] for m in models};boot={k:[] for k in ['IC_minus_MA01','combined_minus_MA01']}
    for _ in range(BOOT):
        ii=rng.integers(0,len(yy),len(yy))
        if len(np.unique(yy[ii]))<2:continue
        boot['IC_minus_MA01'].append(roc_auc_score(yy[ii],S['IC_only'][ii])-roc_auc_score(yy[ii],S['MA01_margin'][ii]))
        boot['combined_minus_MA01'].append(roc_auc_score(yy[ii],S['combined'][ii])-roc_auc_score(yy[ii],S['MA01_margin'][ii]))
    row={'f':float(f),'t_observation_outer':float(300*f)}
    for k,v in boot.items():row[k]={'point':float(np.mean(v)),'lo':float(np.percentile(v,2.5)),'hi':float(np.percentile(v,97.5)),'n_boot':len(v)}
    auc_rows.append(row)
# Frozen warning indicators and paired coverage differences.
def frozen_indicator(model,far,index=None):
    idx=np.arange(len(y)) if index is None else np.asarray(index);out=np.zeros(len(idx),bool);first=np.full(len(idx),-1,int)
    th=np.array([threshold(thr,f,model,far) for f in fracs])
    for q,i in enumerate(idx):
        hit=np.where(np.isfinite(P[model][i])&(P[model][i]>=th))[0]
        if len(hit):out[q]=True;first[q]=int(hit[0])
    return out,first
frozen=[]
for far in FARS:
    inds={m:frozen_indicator(m,far)[0] for m in models};rows={}
    for m,a in inds.items():rows[m]={'delayed_warned':int(np.sum(a&(y==1))),'control_alerts':int(np.sum(a&(y==0))),'coverage':float(a[y==1].mean())}
    dif=[]
    posidx=np.where(y==1)[0]
    for _ in range(BOOT):
        ii=rng.choice(posidx,len(posidx),replace=True);dif.append(float(inds['combined'][ii].mean()-inds['IC_only'][ii].mean()))
    frozen.append({'target_original_far':far,'arms':rows,'combined_minus_IC_coverage':{'point':float(rows['combined']['coverage']-rows['IC_only']['coverage']),'lo':float(np.percentile(dif,2.5)),'hi':float(np.percentile(dif,97.5)),'n_boot':len(dif)}})
# Retrospective equal-control-budget comparison. This is descriptive, not prospective.
def risk(model,index):return np.nanmax(P[model][index],axis=1)
def equal_budget_once(index,budget_fraction):
    yy=y[index];controls=np.where(yy==0)[0];positives=np.where(yy==1)[0];out={};warn={}
    for m in models:
        r=risk(m,index);th=float(np.quantile(r[controls],1-budget_fraction,method='higher'));a=r>=th;warn[m]=a
        leads=[]
        for local in positives[a[positives]]:
            global_i=index[local];hit=np.where(np.isfinite(P[m][global_i])&(P[m][global_i]>=th))[0]
            if len(hit):leads.append(event[global_i]-300*fracs[int(hit[0])])
        out[m]={'threshold':th,'control_alerts':int(a[controls].sum()),'delayed_warned':int(a[positives].sum()),'coverage':float(a[positives].mean()),'precision':float(yy[a].mean()),'median_lead':float(np.median(leads)) if leads else np.nan}
    return out,warn
equal=[]
# Match the smallest observed learned-arm control count in each original FAR block.
learned=['IC_only','window','combined']
budgets=[]
for block in frozen:
    k=min(block['arms'][m]['control_alerts'] for m in learned)
    budgets.append((f"matched_budget_from_original_far_{block['target_original_far']}",k,block['target_original_far']))
for label,K,source_far in budgets:
    frac=K/int((y==0).sum());base,_=equal_budget_once(np.arange(len(y)),frac);diff=[]
    for _ in range(300):
        ii=rng.integers(0,len(y),len(y));o,_=equal_budget_once(ii,frac);diff.append(o['combined']['coverage']-o['IC_only']['coverage'])
    equal.append({'budget_name':label,'source_original_far_block':source_far,'target_control_alert_count':int(K),'target_control_fraction':frac,'arms':base,'combined_minus_IC_coverage':{'point':base['combined']['coverage']-base['IC_only']['coverage'],'lo':float(np.percentile(diff,2.5)),'hi':float(np.percentile(diff,97.5)),'n_boot':len(diff)},'warning':'threshold selected on delayed-endpoint controls; retrospective ranking diagnostic, not prospective operating point'})
result={'protocol':{'no_refit':True,'frozen_rows_use_original_calibration_thresholds':True,'equal_budget_rows_are_retrospective':True,'horizon_notation':'t_observation = f * 300 T_out'},'interpretation_branches':BRANCHES,'cohort':{'n':len(y),'n_delayed':int(y.sum()),'n_controls':int((y==0).sum())},'paired_auc_differences':auc_rows,'frozen_threshold_paired_coverage':frozen,'retrospective_equal_control_budget':equal}
dump('attribution_precision_addon.json',result)
manifest={'status':'complete','interpretation_branches':BRANCHES,'files':{}}
for p in OUT.iterdir():
    if p.is_file():manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
dump('OUTPUT_MANIFEST.json',manifest)
zip_path=shutil.make_archive('/kaggle/working/attribution_precision_addon','zip',root_dir=str(OUT));print(json.dumps(result,indent=2));print('DOWNLOAD',zip_path)
