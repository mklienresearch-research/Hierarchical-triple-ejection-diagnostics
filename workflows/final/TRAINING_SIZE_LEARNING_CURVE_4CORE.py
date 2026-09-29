# TRAINING-SIZE LEARNING CURVE — combined causal model, no new simulations
import json,shutil,hashlib
from pathlib import Path
import numpy as np
from xgboost import XGBClassifier
from sklearn.metrics import roc_auc_score,average_precision_score

ROOT_T=Path('/kaggle/input/datasets/klienm/mergedtriples');ROOT_A=Path('/kaggle/input/datasets/klienm/final-audit-expanded')
OUT=Path('/kaggle/working/training_size_curve');OUT.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
    if p.is_file():p.unlink()
SIZES=[10000,25000,50000,100000,200000];SEEDS=[0,1,2];FRACS=np.array([.05,.15,.30,.50,.75]);SAFE=np.array([i for i in range(79) if i not in (72,73)])
def find(root,name):
 h=sorted(root.rglob(name),key=lambda p:(len(p.parts),str(p)))
 if not h:raise FileNotFoundError(name)
 return h[0]
def model(seed):return XGBClassifier(n_estimators=300,max_depth=3,learning_rate=.05,subsample=.8,colsample_bytree=.8,reg_lambda=2,objective='binary:logistic',eval_metric='logloss',random_state=seed,n_jobs=4,tree_method='hist')
with np.load(find(ROOT_T,'merged_triples.npz'),allow_pickle=False) as z:d={k:z[k] for k in ['ids','statuses','t_event','t_max','ic','feats']}
d['feats'][:,:,72:74]=0
with np.load(find(ROOT_A,'triples_split_ids.npz'),allow_pickle=False) as z:train_ids=z['train_ids'].astype(int);cal_ids=z['calibration_ids'].astype(int);test_ids=z['test_ids'].astype(int)
ids=d['ids'].astype(int);order=np.argsort(ids);sid=ids[order]
def rows(q):return order[np.searchsorted(sid,q)]
train0,cal0,test0=rows(train_ids),rows(cal_ids),rows(test_ids)
y=np.full(len(ids),-1,int);y[d['statuses']=='stable']=0;y[d['statuses']=='ejected']=1;te=np.where(np.isnan(d['t_event']),np.inf,d['t_event'])
ic=d['ic'];IC=np.column_stack([ic[:,0],ic[:,1],ic[:,2],ic[:,3],ic[:,4],ic[:,9],ic[:,10],ic[:,11],ic[:,12]/(ic[:,0]+ic[:,1]+1e-30),ic[:,9]/(ic[:,3]+1e-30),ic[:,9]*(1-ic[:,10])/(ic[:,3]*(1+ic[:,4])+1e-30),np.cos(ic[:,11]),np.sin(ic[:,11]),ic[:,15],ic[:,16]]).astype(np.float32)
result={'protocol':{'fixed_train_cal_test_ids':True,'equal_training_IDs_for_IC_and_combined':True,'nested_samples_within_seed':True,'seeds':SEEDS,'sizes':SIZES,'disabled_indices':[72,73],'interpretation_committed_before_results':['if combined-minus-IC persists across sizes, retain trajectory-information interpretation','if increment shrinks strongly with size, report training-size dependence and narrow claim']},'horizons':[]}
for fi,f in enumerate(FRACS):
 h=f*d['t_max'];pool=train0[te[train0]>h[train0]];cal=cal0[te[cal0]>h[cal0]];test=test0[te[test0]>h[test0]];Xw=d['feats'][:,[0,2,4,6,8][fi]][:,SAFE];Xcombined=np.hstack([IC,Xw]);entries=[]
 actual_sizes=sorted(set(min(s,len(pool)) for s in SIZES+[len(pool)]))
 for n in actual_sizes:
  nreq=n;seedrows=[]
  for seed in SEEDS:
   perm=np.random.default_rng(1000+seed+fi*10).permutation(pool);tr=perm[:n];arms={}
   for arm,X in [('IC_only',IC),('combined',Xcombined)]:
    m=model(seed);m.fit(X[tr],y[tr]);pt=m.predict_proba(X[test])[:,1];pc=m.predict_proba(X[cal])[:,1];neg=pc[y[cal]==0];th=float(np.quantile(neg,.99,method='higher'));pred=pt>=th;arms[arm]={'auc':float(roc_auc_score(y[test],pt)),'pr_auc':float(average_precision_score(y[test],pt)),'recall_at_1pct_far':float(pred[y[test]==1].mean()),'achieved_far':float(pred[y[test]==0].mean())}
   delta={k:arms['combined'][k]-arms['IC_only'][k] for k in arms['combined']};seedrows.append({'IC_only':arms['IC_only'],'combined':arms['combined'],'combined_minus_IC':delta})
  summary={}
  for section in ['IC_only','combined','combined_minus_IC']:
   keys=seedrows[0][section];summary[section]={'mean':{k:float(np.mean([r[section][k] for r in seedrows])) for k in keys},'std':{k:float(np.std([r[section][k] for r in seedrows])) for k in keys}}
  entries.append({'requested_n':int(nreq),'actual_n':int(n),'is_full_pool':bool(nreq==len(pool)),'summary':summary,'seeds':seedrows})
  print(f'f={f:.2f} train={n} IC={summary["IC_only"]["mean"]["auc"]:.5f} combined={summary["combined"]["mean"]["auc"]:.5f} delta={summary["combined_minus_IC"]["mean"]["auc"]:+.5f}',flush=True)
 result['horizons'].append({'f':float(f),'t_observation_outer':float(300*f),'full_inplay_train_pool':int(len(pool)),'n_cal':len(cal),'n_test':len(test),'entries':entries})
with open(OUT/'training_size_curve.json','w') as f:json.dump(result,f,indent=1)
manifest={'status':'complete','files':{}}
for p in OUT.iterdir():
 if p.is_file():manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
with open(OUT/'OUTPUT_MANIFEST.json','w') as f:json.dump(manifest,f,indent=2)
zip_path=shutil.make_archive('/kaggle/working/training_size_curve','zip',root_dir=str(OUT));print('DOWNLOAD',zip_path)
