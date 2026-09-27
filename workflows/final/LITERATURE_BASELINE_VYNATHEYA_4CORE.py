# SAME-DATA MODERN LITERATURE BASELINE — Vynatheya et al. 2022/2023
# No fitting. Applies published algebraic criterion and public pretrained MLPs
# to the exact final triple cohorts/splits/horizons.
import os,sys,json,hashlib,urllib.request,warnings,shutil
from pathlib import Path
import numpy as np
import sklearn
from sklearn.metrics import roc_auc_score,average_precision_score,accuracy_score,precision_score,recall_score,f1_score,confusion_matrix
ROOT_T=Path('/kaggle/input/datasets/klienm/mergedtriples');ROOT_A=Path('/kaggle/input/datasets/klienm/final-audit-expanded')
OUT=Path('/kaggle/working/literature_baseline_vynatheya');OUT.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
    if p.is_file():p.unlink()
COMMIT='c6d4a293bc8bfb888d4a6a905e29c2aff81a31c7';BASE=f'https://raw.githubusercontent.com/pavanvyn/triple-stability/{COMMIT}/'
MODELS={'V22_MLP_semimajor':'mlp_model_trip_v1.2.2.pkl','V23_MLP_ghost':'mlp_model_trip_ghost_v1.2.2.pkl'}
FRACS=np.array([.05,.15,.30,.50,.75],float);FARS=[.001,.01,.05];BOOT=500

def find(root,name):
 h=sorted(root.rglob(name),key=lambda p:(len(p.parts),str(p)))
 if not h:raise FileNotFoundError(name)
 return h[0]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def fixed_metrics(y,s,threshold):
 pred=s>=threshold;tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
 return dict(n=len(y),prevalence=float(y.mean()),roc_auc=float(roc_auc_score(y,s)),pr_auc=float(average_precision_score(y,s)),accuracy=float(accuracy_score(y,pred)),precision=float(precision_score(y,pred,zero_division=0)),recall=float(recall_score(y,pred,zero_division=0)),f1=float(f1_score(y,pred,zero_division=0)),tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp))
def far_rows(yc,sc,yt,st):
 neg=sc[yc==0];out=[]
 for far in FARS:
  th=float(np.quantile(neg,1-far,method='higher'));pred=st>=th;n=yt==0;p=yt==1
  out.append(dict(target_far=far,threshold=th,achieved_far=float(pred[n].mean()),recall=float(pred[p].mean()),precision=float(yt[pred].mean()) if pred.any() else np.nan,n_alerts=int(pred.sum())))
 return out
# Load exact production data and final split ledger.
with np.load(find(ROOT_T,'merged_triples.npz'),allow_pickle=False) as z:
    d={k:z[k] for k in ['ids','statuses','t_event','t_max','ic']}
with np.load(find(ROOT_A,'triples_split_ids.npz'),allow_pickle=False) as z:cal_ids=z['calibration_ids'].astype(int);test_ids=z['test_ids'].astype(int)
with np.load(find(ROOT_A,'triples_untouched_test_scores.npz'),allow_pickle=False) as z:audit={k:z[k] for k in z.files}
ids=d['ids'].astype(int);order=np.argsort(ids);sid=ids[order]
def rows_for(q):return order[np.searchsorted(sid,q)]
cal=rows_for(cal_ids);test=rows_for(test_ids);status=d['statuses'];y=np.full(len(ids),-1,int);y[status=='stable']=0;y[status=='ejected']=1
ic=d['ic'];m0,m1,m2=ic[:,0],ic[:,1],ic[:,2];qin=np.minimum(m0,m1)/np.maximum(m0,m1);qout=m2/(m0+m1);alpha=ic[:,3]/ic[:,9];ein=ic[:,4];eout=ic[:,10];imut=ic[:,11]
# Published updated formula (Eq. 4), vectorized.
lk=1-(5/3)*np.cos(imut)**2;etilde=np.where(lk>=0,np.maximum(ein,.5*lk),ein);fac=.125*(1-.2*etilde+eout)*(np.cos(imut)-1)+1
Y=(1-eout)/((1+etilde)*alpha);Ycrit=2.4*(1+qout)**.4*(1+etilde)**(-.4)*(1-eout)**(-.2)*fac
formula_risk=np.log(np.maximum(Ycrit,1e-30)/np.maximum(Y,1e-30))
# MA01 continuous margin risk for reference.
ma_risk=-ic[:,16]
# Download pinned public pretrained models and evaluate probabilities.
import pickle
scores={'MA01_margin':ma_risk,'V22_formula':formula_risk};sources={}
for label,name in MODELS.items():
 path=OUT/name;urllib.request.urlretrieve(BASE+name,path);sources[label]={'url':BASE+name,'sha256':sha(path)}
 with open(path,'rb') as f:model=pickle.load(f)
 X=np.c_[qin,qout,alpha,ein,eout,imut/np.pi]
 scores[label]=model.predict_proba(X)[:,1]
# Domain check.
domain=((qin>=1e-2)&(qin<=1)&(qout>=1e-2)&(qout<=1e2)&(alpha>=1e-4)&(alpha<=1)&(ein>=0)&(ein<=1)&(eout>=0)&(eout<=1)&(imut>=0)&(imut<=np.pi))
# Published thresholds: risk >=0 for algebraic boundaries; MLP p>=.5.
published={'MA01_margin':-1.0,'V22_formula':0.0,'V22_MLP_semimajor':.5,'V23_MLP_ghost':.5}
valid=np.where(y>=0)[0];result={'protocol':{'target':'ejection by 300 T_out, not original literature stability label','same_final_split_ids':True,'no_refit':True,'domain_fraction':float(domain.mean()),'runtime_sklearn_version':sklearn.__version__,'model_pickle_sklearn_version':'1.2.2','warning':'Label definitions/endpoints differ; performance is transfer to this paper target, not reproduction of authors original accuracy. Pickle compatibility warnings are retained and runtime version recorded.'},'sources':sources,'overall':{},'horizons':[]}
for name,s in scores.items():result['overall'][name]=fixed_metrics(y[valid],s[valid],published[name])
# Exact in-play per-horizon parity and paired bootstrap against our combined model.
te=np.where(np.isnan(d['t_event']),np.inf,d['t_event']);rng=np.random.default_rng(20260925)
for j,f in enumerate(FRACS):
 h=f*d['t_max'];ca=cal[te[cal]>h[cal]];tt=test[te[test]>h[test]];row={'f':float(f),'t_observation_outer':float(300*f),'n_cal':len(ca),'n_test':len(tt),'models':{}}
 # audit scores are aligned with test_ids; select finite combined score at audit horizon j.
 combined_all=audit['score_combined'][:,j].astype(float);combined=combined_all[np.isfinite(combined_all)];audit_test_rows=np.where(np.isfinite(combined_all))[0]
 if not np.array_equal(test_ids[audit_test_rows],d['ids'][tt]):
  # Map robustly if order differs.
  mp={int(v):i for i,v in enumerate(test_ids)};combined=np.array([combined_all[mp[int(d['ids'][x])]] for x in tt])
 for name,s in scores.items():
  m=fixed_metrics(y[tt],s[tt],published[name]);m['fixed_far']=far_rows(y[ca],s[ca],y[tt],s[tt]);diff=[]
  for _ in range(BOOT):
   ii=rng.integers(0,len(tt),len(tt))
   if len(np.unique(y[tt][ii]))<2:continue
   diff.append(roc_auc_score(y[tt][ii],combined[ii])-roc_auc_score(y[tt][ii],s[tt][ii]))
  m['combined_minus_baseline_auc']={'point':float(roc_auc_score(y[tt],combined)-roc_auc_score(y[tt],s[tt])),'lo':float(np.percentile(diff,2.5)),'hi':float(np.percentile(diff,97.5)),'n_boot':len(diff)};row['models'][name]=m
 result['horizons'].append(row)
with open(OUT/'literature_baseline_results.json','w') as f:json.dump(result,f,indent=1)
np.savez_compressed(OUT/'literature_baseline_scores.npz',system_id=ids,y=y,domain=domain,**{k:v for k,v in scores.items()})
manifest={'status':'complete','files':{}}
for p in OUT.iterdir():
 if p.is_file():manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':sha(p)}
with open(OUT/'OUTPUT_MANIFEST.json','w') as f:json.dump(manifest,f,indent=2)
zip_path=shutil.make_archive('/kaggle/working/literature_baseline_vynatheya','zip',root_dir=str(OUT));print(json.dumps(result,indent=1));print('DOWNLOAD',zip_path)
