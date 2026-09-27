# ZERO-REFIT ATTRIBUTION + JOINT GROWTH BOOTSTRAP V2
import json,hashlib,shutil
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score,average_precision_score

OUT=Path('/kaggle/working/attribution_growth_v2');OUT.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
    if p.is_file():p.unlink()
FARS=[.001,.01,.05];PAIR_BOOT=500;GROWTH_INITIAL=300;GROWTH_EXTENDED=1500
INTERPRETATION_BRANCHES=[
 {'outcome':'window-only transfers; IC-only does not','claim':'dynamical structure carries foresight beyond the training endpoint where initial conditions do not','not_claimed':None},
 {'outcome':'both transfer, comparable; combined approximately either','claim':'far-future risk information is largely present at t=0; the dynamical increment is endpoint-specific','not_claimed':'dynamics see the far future'},
 {'outcome':'combined clearly beats both singles','claim':'transfer needs joint state-and-dynamics information','not_claimed':'attribution to either family alone'},
 {'outcome':'MA01 margin approximately equals or beats learned rows','claim':'contribution is calibrated alarm, lead distribution, and FAR discipline','not_claimed':'foresight advantage'}]

def find(name):
    hits=[]
    for root in [Path('/kaggle/input'),Path('/kaggle/working')]:
        if root.exists():hits.extend(root.rglob(name))
    if not hits:raise FileNotFoundError(name)
    return sorted(hits,key=lambda p:(0 if str(p).startswith('/kaggle/working') else 1,len(p.parts),str(p)))[0]
def dump(name,x):
    with open(OUT/name,'w') as f:json.dump(x,f,indent=1,allow_nan=True)
def load_scores(task):
    p=find(f'{task}_untouched_test_scores.npz')
    with np.load(p,allow_pickle=False) as z:return {k:z[k] for k in z.files},str(p)
def threshold(table,f,model,far):
    key=min(table,key=lambda k:abs(float(k)-float(f)))
    return float(next(x['threshold'] for x in table[key][model] if abs(float(x['target_far'])-far)<1e-12))
def paired_ci(y,a,b,seed,nboot=PAIR_BOOT):
    rng=np.random.default_rng(seed);d=[];n=len(y)
    for _ in range(nboot):
        ii=rng.integers(0,n,n)
        if len(np.unique(y[ii]))<2:continue
        d.append(roc_auc_score(y[ii],a[ii])-roc_auc_score(y[ii],b[ii]))
    return {'point':float(roc_auc_score(y,a)-roc_auc_score(y,b)),
            'lo':float(np.percentile(d,2.5)),'hi':float(np.percentile(d,97.5)),'n_boot':len(d)}

# ---------------- frozen prospective attribution
tri,tri_path=load_scores('triples')
with open(find('triples_thresholds.json')) as f:thr=json.load(f)
tail_path=find('matched_tail_outcomes.csv');tail=pd.read_csv(tail_path).set_index('system_id')
test_ids=tri['test_ids'].astype(int);fracs=tri['fractions'].astype(float)
matched=[]
for i,sid in enumerate(test_ids):
    if sid not in tail.index:continue
    r=tail.loc[sid]
    if int(r.stable_at_300)!=1:continue
    if int(r.delayed_ejection)==1:label=1
    elif str(r.tail_status_3000)=='stable':label=0
    else:continue
    matched.append((i,int(sid),label,float(r.tail_event_time_outer) if pd.notna(r.tail_event_time_outer) else np.nan,str(r.delayed_ejection_type)))
pos=np.array([x[0] for x in matched]);ids=np.array([x[1] for x in matched]);y=np.array([x[2] for x in matched]);event=np.array([x[3] for x in matched]);etype=np.array([x[4] for x in matched])
models=['IC_only','window','combined','MA01_margin'];result={};score_map={}
for model in models:
    key='score_'+model
    if key not in tri:continue
    P=tri[key][pos].astype(float);score_map[model]=P;hrows=[]
    for j,f in enumerate(fracs):
        valid=np.isfinite(P[:,j]);yy=y[valid];pp=P[valid,j]
        hrows.append(dict(f=float(f),n=int(valid.sum()),n_delayed=int(yy.sum()),prevalence=float(yy.mean()),roc_auc=float(roc_auc_score(yy,pp)),pr_auc=float(average_precision_score(yy,pp))))
    leads=[]
    for far in FARS:
        th=np.array([threshold(thr,f,model,far) for f in fracs]);lead=[];types=[];false=0
        for i in range(len(y)):
            hit=np.where(np.isfinite(P[i])&(P[i]>=th))[0]
            if not len(hit):continue
            j=int(hit[0])
            if y[i]==1:lead.append(float(event[i]-300*fracs[j]));types.append(str(etype[i]))
            else:false+=1
        a=np.asarray(lead);positive=a[a>0]
        leads.append(dict(target_far=far,threshold_provenance=('analytic score cut-off derived previously on calibration negatives' if model=='MA01_margin' else 'model-specific frozen calibration threshold'),n_delayed=int(y.sum()),n_controls=int((y==0).sum()),n_delayed_warned=len(a),coverage=float(len(a)/max(y.sum(),1)),cumulative_control_false_alert=float(false/max((y==0).sum(),1)),precision=float(len(a)/max(len(a)+false,1)),positive_lead_fraction=float(len(positive)/max(len(a),1)),median_lead=float(np.median(a)) if len(a) else np.nan,p25=float(np.percentile(a,25)) if len(a) else np.nan,p75=float(np.percentile(a,75)) if len(a) else np.nan,inner_warned=int(sum(t=='inner-member' for t in types)),outer_warned=int(sum(t=='outer-member' for t in types))))
    result[model]={'horizons':hrows,'lead_by_frozen_far':leads}
# Published MA01 rule: margin <=1 means score=-margin >=-1; no calibration.
Pma=score_map['MA01_margin'];published=[]
for j,f in enumerate(fracs):
    valid=np.isfinite(Pma[:,j]);pred=Pma[valid,j]>=-1.0;yy=y[valid]
    published.append(dict(f=float(f),rule='MA01 margin <= 1; as-published, not calibrated',n=int(valid.sum()),delayed_tpr=float(pred[yy==1].mean()),control_false_alert=float(pred[yy==0].mean()),precision=float(yy[pred].mean()) if pred.any() else np.nan,n_alerts=int(pred.sum())))
# Paired prospective AUC differences, identical IDs and bootstrap resamples.
paired=[]
for j,f in enumerate(fracs):
    required=['IC_only','window','combined','MA01_margin'];valid=np.ones(len(y),bool)
    for m in required:valid &= np.isfinite(score_map[m][:,j])
    yy=y[valid];scores={m:score_map[m][valid,j] for m in required}
    point={m:roc_auc_score(yy,v) for m,v in scores.items()};best='window' if point['window']>=point['IC_only'] else 'IC_only'
    paired.append(dict(f=float(f),best_single=best,
      window_minus_IC=paired_ci(yy,scores['window'],scores['IC_only'],94000+j),
      combined_minus_best_single=paired_ci(yy,scores['combined'],scores[best],95000+j),
      window_minus_MA01=paired_ci(yy,scores['window'],scores['MA01_margin'],96000+j)))
attribution={'protocol':{'model_refit':False,'model_threshold_recalibration':False,'same_untouched_ids':True,'MA01_calibrated_cutoffs':'derived in prior audit on calibration negatives; no test information','report_null_or_positive':True},'interpretation_branches':INTERPRETATION_BRANCHES,'cohort':{'n':len(y),'n_delayed':int(y.sum()),'n_controls':int((y==0).sum()),'prevalence':float(y.mean())},'score_source':tri_path,'tail_source':str(tail_path),'models':result,'MA01_as_published':published,'paired_auc_differences':paired}
dump('prospective_model_attribution.json',attribution)

# ---------------- joint correlated bootstrap under changing and fixed cohorts
def joint_growth(task,seed):
    z,path=load_scores(task);yy=z['y'].astype(int);f=z['fractions'].astype(float);ic=z['score_IC_only'].astype(float);co=z['score_combined'].astype(float);n=len(yy)
    def gains_for(index):
        vals=[]
        for j in range(len(f)):
            valid=np.isfinite(ic[index,j])&np.isfinite(co[index,j]);idx=index[valid]
            if len(np.unique(yy[idx]))<2:return None
            vals.append(float(roc_auc_score(yy[idx],co[idx,j])-roc_auc_score(yy[idx],ic[idx,j])))
        return np.asarray(vals)
    def run_mode(base_idx,mode,local_seed):
        point=gains_for(base_idx);rng=np.random.default_rng(local_seed)
        def generate(number,g,slopes,mono):
            for _ in range(number):
                sampled=base_idx[rng.integers(0,len(base_idx),len(base_idx))];v=gains_for(sampled)
                if v is None:continue
                g.append(v);slopes.append(float(np.polyfit(f,v,1)[0]));mono.append(bool(np.all(np.diff(v)>=0)))
        g=[];slopes=[];mono=[];generate(GROWTH_INITIAL,g,slopes,mono);p=float(np.mean(mono))
        if .85<=p<.995:generate(GROWTH_EXTENDED-len(mono),g,slopes,mono)
        g=np.asarray(g);slopes=np.asarray(slopes);p=float(np.mean(mono));mcse=float(np.sqrt(p*(1-p)/len(mono)))
        out={'mode':mode,'monotonicity_definition':'all adjacent combined-minus-IC gains non-decreasing in f (diff >= 0)','n_test':int(len(base_idx)),'fractions':f.tolist(),'point_gains':point.tolist(),'point_slope_per_fraction':float(np.polyfit(f,point,1)[0]),'bootstrap_replicates':len(mono),'slope_95':{'lo':float(np.percentile(slopes,2.5)),'hi':float(np.percentile(slopes,97.5))},'nondecreasing_fraction':p,'nondecreasing_fraction_mc_standard_error':mcse,'gain_95_by_horizon':[{'f':float(f[j]),'lo':float(np.percentile(g[:,j],2.5)),'hi':float(np.percentile(g[:,j],97.5))} for j in range(len(f))]}
        np.savez_compressed(OUT/f'{task}_{mode}_joint_bootstrap.npz',fractions=f,point_gains=point,bootstrap_gains=g,bootstrap_slopes=slopes,bootstrap_nondecreasing=np.asarray(mono))
        return out
    ordinary=run_mode(np.arange(n),'changing_inplay_risk_set',seed)
    fixed_idx=np.where(np.isfinite(ic[:,-1])&np.isfinite(co[:,-1]))[0]
    fixed=run_mode(fixed_idx,'fixed_latest_landmark_cohort',seed+1)
    out={'task':task,'score_source':path,'ordinary':ordinary,'fixed_landmark':fixed};dump(f'{task}_joint_gain_growth.json',out);return out
tri_growth=joint_growth('triples',97001);bd_growth=joint_growth('boundary',97002)
summary={'status':'complete','prospective_models':list(result),'triple_growth':tri_growth,'boundary_growth':bd_growth,'interpretation_branches':INTERPRETATION_BRANCHES}
dump('attribution_growth_summary.json',summary)
manifest={'status':'complete','interpretation_branches':INTERPRETATION_BRANCHES,'files':{}}
for p in OUT.iterdir():
    if p.is_file():manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
dump('OUTPUT_MANIFEST.json',manifest)
zip_path=shutil.make_archive('/kaggle/working/attribution_growth_v2','zip',root_dir=str(OUT))
print(json.dumps(attribution['cohort'],indent=2));print(json.dumps(paired,indent=2));print('growth',json.dumps({'triples':tri_growth,'boundary':bd_growth},indent=2));print('DOWNLOAD',zip_path)
