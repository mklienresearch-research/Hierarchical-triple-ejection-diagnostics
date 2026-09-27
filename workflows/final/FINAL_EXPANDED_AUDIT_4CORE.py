# FINAL EXPANDED AUDIT — 4-core Kaggle CPU
# Repairs secondary protocols and produces parity-calibrated baselines,
# retention/landmark curves, score vectors, bootstrap intervals, and corrected
# boundary/conditional tests. Performs NO N-body simulation.

import os, sys, json, time, gc, subprocess, shutil, hashlib
from pathlib import Path
import numpy as np

subprocess.run([sys.executable,"-m","pip","install","-q","xgboost","scikit-learn"],check=False)
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (roc_auc_score,average_precision_score,accuracy_score,
    balanced_accuracy_score,matthews_corrcoef,precision_score,recall_score,
    f1_score,confusion_matrix,brier_score_loss)

N_JOBS=4; FIT_CAP=200000; SEED=26001; FARS=[0.001,0.01,0.05]; BOOT=300
ROOT_CHUNKS=Path('/kaggle/input/datasets/klienm/v2chunks')
ROOT_TRIPLES=Path('/kaggle/input/datasets/klienm/mergedtriples')
OUT=Path('/kaggle/working/final_expanded_audit'); OUT.mkdir(parents=True,exist_ok=True)
for p in OUT.iterdir():
    if p.is_file(): p.unlink()
START=time.time()
TRI_FRACS=np.array([.05,.1,.15,.2,.3,.4,.5,.6,.75,.9,1],np.float32)
ENC_FRACS=np.array([.05,.1,.15,.2,.25,.3,.35,.4,.45,.5,.55,.6,.65,.7,.75,.8,.85,.9,.95,1],np.float32)
TRI_USE=[0,2,4,6,8]; ENC_USE=list(range(0,19,2))
SAFE=np.array([i for i in range(79) if i not in (72,73)])

def log(x): print(f'[{(time.time()-START)/60:6.1f} min] {x}',flush=True)
def dump(name,x):
    with open(OUT/name,'w') as f: json.dump(x,f,indent=1,allow_nan=True)
def find(root,name):
    hits=sorted(root.rglob(name),key=lambda p:(len(p.parts),str(p)))
    if not hits: raise FileNotFoundError(f'{name} under {root}')
    return hits[0]
def load(path,fracs):
    log(f'loading {path}')
    with np.load(path,allow_pickle=False) as z: d={k:z[k] for k in z.files if k!='fractions'}
    d['fractions']=fracs.copy(); d['feats'][:,:,72:74]=0.0
    assert np.all(d['feats'][:,:,72:74]==0) and len(np.unique(d['ids']))==len(d['ids'])
    return d
def model(seed=0):
    return XGBClassifier(n_estimators=300,max_depth=3,learning_rate=.05,subsample=.8,
      colsample_bytree=.8,reg_lambda=2,objective='binary:logistic',eval_metric='logloss',
      random_state=seed,n_jobs=N_JOBS,tree_method='hist')
def mc_model(C,seed=0):
    return XGBClassifier(n_estimators=300,max_depth=3,learning_rate=.05,subsample=.8,
      colsample_bytree=.8,reg_lambda=2,objective='multi:softprob',num_class=C,
      eval_metric='mlogloss',random_state=seed,n_jobs=N_JOBS,tree_method='hist')
def cap(idx,n,seed):
    idx=np.asarray(idx); return np.random.default_rng(seed).choice(idx,n,False) if len(idx)>n else idx
def split_valid(y):
    valid=np.where(y>=0)[0]
    tr,hold=train_test_split(valid,test_size=.4,random_state=SEED,stratify=y[valid])
    ca,te=train_test_split(hold,test_size=.5,random_state=SEED+1,stratify=y[hold])
    return tr,ca,te
def ic_tri(ic):
    return np.column_stack([ic[:,0],ic[:,1],ic[:,2],ic[:,3],ic[:,4],ic[:,9],ic[:,10],ic[:,11],
      ic[:,12]/(ic[:,0]+ic[:,1]+1e-30),ic[:,9]/(ic[:,3]+1e-30),
      ic[:,9]*(1-ic[:,10])/(ic[:,3]*(1+ic[:,4])+1e-30),np.cos(ic[:,11]),np.sin(ic[:,11]),ic[:,15],ic[:,16]]).astype(np.float32)
def ic_enc(ic):
    return np.column_stack([ic[:,0],ic[:,1],ic[:,2],ic[:,4],ic[:,15],ic[:,16],ic[:,17],ic[:,15]/(ic[:,16]+1e-30)]).astype(np.float32)
def pout(ic): return np.sqrt(ic[:,9]**3/(ic[:,0]+ic[:,1]+ic[:,2]+1e-30))
def ece(y,p,bins=15):
    edges=np.linspace(0,1,bins+1); ans=0.
    for a,b in zip(edges[:-1],edges[1:]):
        m=(p>=a)&(p<(b if b<1 else 1+1e-12))
        if m.any(): ans+=m.mean()*abs(y[m].mean()-p[m].mean())
    return float(ans)
def metrics(y,p):
    # ROC/PR accept arbitrary ranking scores. Brier/ECE and a 0.5 decision
    # threshold are meaningful only for probability-valued model outputs.
    y=np.asarray(y); p=np.asarray(p,float)
    is_probability=bool(np.all(np.isfinite(p)) and p.min()>=0.0 and p.max()<=1.0)
    out=dict(n=len(y),prevalence=float(y.mean()),roc_auc=float(roc_auc_score(y,p)),
      pr_auc=float(average_precision_score(y,p)),pr_baseline=float(y.mean()),
      score_is_probability=is_probability)
    if is_probability:
        pred=p>=.5; tn,fp,fn,tp=confusion_matrix(y,pred,labels=[0,1]).ravel()
        out.update(balanced_accuracy=float(balanced_accuracy_score(y,pred)),
          mcc=float(matthews_corrcoef(y,pred)),brier=float(brier_score_loss(y,p)),
          ece15=ece(y,p),precision=float(precision_score(y,pred,zero_division=0)),
          recall=float(recall_score(y,pred,zero_division=0)),
          tn=int(tn),fp=int(fp),fn=int(fn),tp=int(tp))
    else:
        out.update(balanced_accuracy=np.nan,mcc=np.nan,brier=np.nan,ece15=np.nan,
          precision=np.nan,recall=np.nan,tn=None,fp=None,fn=None,tp=None)
    return out
def threshold_rows(ycal,scal,ytest,stest):
    out=[]; neg=scal[ycal==0]
    for far in FARS:
        th=float(np.quantile(neg,1-far,method='higher')); pred=stest>=th; n=ytest==0; p=ytest==1
        out.append(dict(target_far=far,threshold=th,achieved_far=float(pred[n].mean()),
          recall=float(pred[p].mean()),precision=float(ytest[pred].mean()) if pred.any() else np.nan,n_alerts=int(pred.sum())))
    return out
def bootstrap(y,scores,seed):
    rng=np.random.default_rng(seed); n=len(y); names=list(scores); vals={k:[] for k in names}; dif=[]
    for _ in range(BOOT):
        ii=rng.integers(0,n,n)
        if len(np.unique(y[ii]))<2: continue
        for k in names: vals[k].append(roc_auc_score(y[ii],scores[k][ii]))
        if 'combined' in scores and 'IC_only' in scores: dif.append(vals['combined'][-1]-vals['IC_only'][-1])
    out={k:{'lo':float(np.percentile(v,2.5)),'hi':float(np.percentile(v,97.5))} for k,v in vals.items()}
    if dif: out['combined_minus_IC']={'lo':float(np.percentile(dif,2.5)),'hi':float(np.percentile(dif,97.5))}
    return out

def labels_tri(status):
    y=np.full(len(status),-1,np.int8); y[status=='stable']=0; y[status=='ejected']=1; return y

def retention(d,y,fracs,idxs,anchor):
    te=np.where(np.isnan(d['t_event']),np.inf,d['t_event']); valid=y>=0; rows=[]
    for fi in idxs:
        h=float(fracs[fi])*d[anchor]; ip=valid&(te>h)
        rows.append(dict(f=float(fracs[fi]),n_valid=int(valid.sum()),n_in_play=int(ip.sum()),
          retained_fraction=float(ip.sum()/valid.sum()),n_future_positive=int((ip&(y==1)).sum()),
          future_prevalence=float(y[ip].mean()) if ip.any() else np.nan,
          n_positive_excluded=int(((y==1)&~ip).sum()),n_negative_excluded=int(((y==0)&~ip).sum())))
    return rows

def parity_task(d,y,icX,fracs,idxs,anchor,task,do_boot=False):
    tr0,ca0,te0=split_valid(y); event=np.where(np.isnan(d['t_event']),np.inf,d['t_event'])
    raw={'test_ids':d['ids'][te0],'y':y[te0],'fractions':fracs[idxs]}; rows=[]
    score_matrix={name:np.full((len(te0),len(idxs)),np.nan,np.float32) for name in ['IC_only','window','combined','dur_only','H_min','MA01_margin']}
    threshold_store={}
    for jj,fi in enumerate(idxs):
        f=float(fracs[fi]); h=f*d[anchor]; tr=tr0[event[tr0]>h[tr0]]; ca=ca0[event[ca0]>h[ca0]]; te=te0[event[te0]>h[te0]]
        tr=cap(tr,FIT_CAP,30000+fi); Xw=d['feats'][:,fi][:,SAFE]; both=np.hstack([icX,Xw]); dur=d['feats'][:,fi,74:75]
        designs={'IC_only':icX,'window':Xw,'combined':both,'dur_only':dur}; scores_cal={}; scores_test={}
        for kk,(name,X) in enumerate(designs.items()):
            m=model(31000+fi*10+kk); m.fit(X[tr],y[tr]); scores_cal[name]=m.predict_proba(X[ca])[:,1]; scores_test[name]=m.predict_proba(X[te])[:,1]
        scores_cal['H_min']=-d['feats'][ca,fi,0]; scores_test['H_min']=-d['feats'][te,fi,0]
        if task!='encounters':
            scores_cal['MA01_margin']=-d['ic'][ca,16]; scores_test['MA01_margin']=-d['ic'][te,16]
        else:
            scores_cal.pop('MA01_margin',None); scores_test.pop('MA01_margin',None)
        posmap={int(v):i for i,v in enumerate(te0)}
        loc=np.array([posmap[int(v)] for v in te])
        for name,sc in scores_test.items(): score_matrix[name][loc,jj]=sc.astype(np.float32)
        models={}
        for name,sc in scores_test.items():
            row=metrics(y[te],sc); row['fixed_far']=threshold_rows(y[ca],scores_cal[name],y[te],sc); models[name]=row
        # Controls: raw duration may encode orbital/approach scale; normalized duration should be constant.
        normdur=(d['feats'][te,fi,74]/(pout(d['ic'][te]) if task!='encounters' else d['t_approach'][te]))
        controls={'raw_duration_std':float(np.std(d['feats'][te,fi,74])),
                  'normalized_duration_mean':float(np.mean(normdur)),'normalized_duration_std':float(np.std(normdur)),
                  'expected_normalized_duration':f}
        boot=bootstrap(y[te],{k:scores_test[k] for k in ['IC_only','window','combined']},40000+fi) if do_boot else None
        rows.append(dict(f=f,n_train=len(tr),n_cal=len(ca),n_test=len(te),models=models,controls=controls,bootstrap_auc95=boot))
        threshold_store[str(f)]={name:models[name]['fixed_far'] for name in models}
        log(f'{task} parity f={f:.2f} combined AUC={models["combined"]["roc_auc"]:.4f}')
    # Frozen-threshold earliest-warning summaries on the untouched test cohort.
    combined_scores=score_matrix['combined']; lead_rows=[]
    if task=='encounters':
        units=d['ic'][:,20] if d['ic'].shape[1]>20 else np.full(len(y),4.443)
        reference=d['t_peri']
    else:
        units=pout(d['ic']); reference=d['t_event']
    pos_test=te0[y[te0]==1]; neg_test=te0[y[te0]==0]
    first_h=float(fracs[idxs[0]])*d[anchor]
    eligible=int(np.sum(np.isfinite(d['t_event'][pos_test]) & (d['t_event'][pos_test]>first_h[pos_test])))
    posmap={int(v):i for i,v in enumerate(te0)}
    for far in FARS:
        thresholds=[]
        for fi in idxs:
            entries=threshold_store[str(float(fracs[fi]))]['combined']
            thresholds.append(next(x['threshold'] for x in entries if abs(x['target_far']-far)<1e-12))
        leads=[]
        for idx in pos_test:
            row=posmap[int(idx)]
            for jj,fi in enumerate(idxs):
                score=combined_scores[row,jj]
                if np.isfinite(score) and score>=thresholds[jj]:
                    leads.append(float((reference[idx]-float(fracs[fi])*d[anchor][idx])/units[idx])); break
        false_systems=0
        for idx in neg_test:
            row=posmap[int(idx)]
            if any(np.isfinite(combined_scores[row,jj]) and combined_scores[row,jj]>=thresholds[jj] for jj in range(len(idxs))):
                false_systems+=1
        leads=np.asarray(leads,float); positive=leads[leads>0]
        lead_rows.append(dict(target_far=far,n_test_positive=int(len(pos_test)),n_first_horizon_eligible=eligible,
          n_warned=int(len(leads)),coverage_all=float(len(leads)/max(len(pos_test),1)),
          coverage_eligible=float(len(leads)/max(eligible,1)),
          cumulative_false_alert_fraction=float(false_systems/max(len(neg_test),1)),
          positive_lead_fraction=float(len(positive)/max(len(leads),1)),
          median_lead=float(np.median(leads)) if len(leads) else np.nan,
          p25=float(np.percentile(leads,25)) if len(leads) else np.nan,
          p75=float(np.percentile(leads,75)) if len(leads) else np.nan,
          median_positive_lead=float(np.median(positive)) if len(positive) else np.nan))
    for name,arr in score_matrix.items(): raw['score_'+name]=arr
    np.savez_compressed(OUT/f'{task}_untouched_test_scores.npz',**raw)
    np.savez_compressed(OUT/f'{task}_split_ids.npz',train_ids=d['ids'][tr0],calibration_ids=d['ids'][ca0],test_ids=d['ids'][te0])
    parity_output={'task':task,'split_sizes':{'train':len(tr0),'calibration':len(ca0),'test':len(te0)},
                   'horizons':rows,'lead_by_far':lead_rows}
    dump(f'{task}_parity.json',parity_output); dump(f'{task}_thresholds.json',threshold_store)
    return parity_output,(tr0,ca0,te0)

def landmark(d,y,icX,fracs,idxs,anchor,task,landmark_f):
    tr0,ca0,te0=split_valid(y); ev=np.where(np.isnan(d['t_event']),np.inf,d['t_event']); lm=landmark_f*d[anchor]
    trbase=tr0[ev[tr0]>lm[tr0]]; tebase=te0[ev[te0]>lm[te0]]; rows=[]
    for fi in idxs:
        if float(fracs[fi])>landmark_f+1e-7: continue
        tr=cap(trbase,FIT_CAP,50000+fi); Xw=d['feats'][:,fi][:,SAFE]; designs={'IC_only':icX,'window':Xw,'combined':np.hstack([icX,Xw])}; out={}
        for k,(name,X) in enumerate(designs.items()):
            m=model(51000+fi*10+k); m.fit(X[tr],y[tr]); p=m.predict_proba(X[tebase])[:,1]; out[name]=metrics(y[tebase],p)
        rows.append(dict(f=float(fracs[fi]),landmark_f=landmark_f,n_train=len(tr),n_test=len(tebase),models=out))
    dump(f'{task}_landmark_fixed_cohort.json',rows); return rows

def shuffle_control(d,y,icX,fi,anchor,task):
    ev=np.where(np.isnan(d['t_event']),np.inf,d['t_event']); idx=np.where((y>=0)&(ev>float(d['fractions'][fi])*d[anchor]))[0]; idx=cap(idx,100000,60001)
    X=np.hstack([icX,d['feats'][:,fi][:,SAFE]]); out=[]
    for seed in [0,1,2]:
        ys=y[idx].copy(); np.random.default_rng(seed+60010).shuffle(ys); a,b=train_test_split(np.arange(len(idx)),test_size=.3,random_state=seed,stratify=ys)
        m=model(seed);m.fit(X[idx[a]],ys[a]);p=m.predict_proba(X[idx[b]])[:,1];out.append(float(roc_auc_score(ys[b],p)))
    return dict(task=task,f=float(d['fractions'][fi]),auc=out,mean=float(np.mean(out)))

def boundary_ood(main,ym,bd,yb,idxs):
    out=[]; evm=np.where(np.isnan(main['t_event']),np.inf,main['t_event']); evb=np.where(np.isnan(bd['t_event']),np.inf,bd['t_event']); ICM=ic_tri(main['ic']); ICB=ic_tri(bd['ic'])
    tr0,ca0,_=split_valid(ym)
    for fi in idxs:
        f=float(main['fractions'][fi]); hm=f*main['t_max']; hb=f*bd['t_max']; tr=tr0[evm[tr0]>hm[tr0]]; ca=ca0[evm[ca0]>hm[ca0]]; te=np.where((yb>=0)&(evb>hb))[0]; tr=cap(tr,FIT_CAP,70000+fi)
        wm=main['feats'][:,fi][:,SAFE]; wb=bd['feats'][:,fi][:,SAFE]; designs=[('IC_only',ICM,ICB),('window',wm,wb),('combined',np.hstack([ICM,wm]),np.hstack([ICB,wb]))]; rows={}
        for k,(name,Xm,Xb) in enumerate(designs):
            m=model(71000+fi*10+k);m.fit(Xm[tr],ym[tr]);pt=m.predict_proba(Xb[te])[:,1];pc=m.predict_proba(Xm[ca])[:,1];rows[name]=metrics(yb[te],pt);rows[name]['fixed_far']=threshold_rows(ym[ca],pc,yb[te],pt)
        out.append(dict(f=f,n_train=len(tr),n_boundary_inplay=len(te),models=rows));log(f'boundary OOD in-play f={f:.2f}')
    dump('boundary_ood_inplay_corrected.json',out);return out

def encounter_conditionals(d,y,idxs):
    ic=d['ic'];vr=ic[:,15]/(ic[:,16]+1e-30);bins=np.quantile(vr,[0,.25,.5,.75,1]);tr0,_,te0=split_valid(y);ev=d['t_event'];IC=ic_enc(ic);binary=[];multi=[]
    ym=np.array([{'flyby':0,'exchange':1,'ionization':2}[s] for s in d['statuses']],int)
    for b in range(4):
        lo,hi=bins[b],bins[b+1];base=(vr>=lo)&((vr<hi) if b<3 else (vr<=hi));
        for fi in [14,16,18]:  # exactly f=0.75, 0.85, 0.95 in ENC_FRACS
            f=float(d['fractions'][fi]);h=f*d['t_approach'];tr=tr0[base[tr0]&(ev[tr0]>h[tr0])];te=te0[base[te0]&(ev[te0]>h[te0])];tr=cap(tr,FIT_CAP,80000+b*100+fi);W=d['feats'][:,fi][:,SAFE]
            br={'bin':[float(lo),float(hi)],'f':f,'n_train':len(tr),'n_test':len(te),'models':{}}
            for k,(name,X) in enumerate([('IC_only',IC),('window',W),('combined',np.hstack([IC,W]))]):
                m=model(81000+b*100+fi*10+k);m.fit(X[tr],y[tr]);p=m.predict_proba(X[te])[:,1];br['models'][name]=metrics(y[te],p)
            binary.append(br)
            mr={'bin':[float(lo),float(hi)],'f':f,'n_train':len(tr),'n_test':len(te),'models':{}}
            for k,(name,X) in enumerate([('IC_only',IC),('window',W),('combined',np.hstack([IC,W]))]):
                # Some velocity-bin/horizon training cohorts can omit a rare
                # class. Remap the classes present in training to contiguous
                # local labels, then map argmax predictions back to global
                # flyby/exchange/ionization labels. predict_proba+argmax also
                # avoids XGBoost versions returning a probability matrix from
                # predict() for multi:softprob.
                classes=np.unique(ym[tr])
                if len(classes)<2:
                    mr['models'][name]={'skipped':'fewer than two training classes','train_classes':classes.tolist()}
                    continue
                local_train=np.searchsorted(classes,ym[tr])
                m=mc_model(len(classes),82000+b*100+fi*10+k)
                m.fit(X[tr],local_train)
                proba=m.predict_proba(X[te])
                if proba.ndim==1:
                    proba=np.column_stack([1-proba,proba])
                pred=classes[np.argmax(proba,axis=1)]
                cm=confusion_matrix(ym[te],pred,labels=[0,1,2])
                rec=np.diag(cm)/np.maximum(cm.sum(1),1)
                mr['models'][name]={'macro_f1':float(f1_score(ym[te],pred,labels=[0,1,2],average='macro',zero_division=0)),'accuracy':float(accuracy_score(ym[te],pred)),'recall':rec.tolist(),'cm':cm.tolist(),'train_classes':classes.tolist()}
            multi.append(mr);log(f'enc conditional bin={b} f={f:.2f}')
    dump('enc_conditional_inplay_corrected.json',binary);dump('enc_multiclass_conditional_inplay_corrected.json',multi)

# ---------------- triples + boundary
tri=load(find(ROOT_TRIPLES,'merged_triples.npz'),TRI_FRACS);yt=labels_tri(tri['statuses']);ICT=ic_tri(tri['ic'])
dump('triples_retention.json',retention(tri,yt,TRI_FRACS,TRI_USE,'t_max'))
tri_parity,tri_split=parity_task(tri,yt,ICT,TRI_FRACS,TRI_USE,'t_max','triples',True)
landmark(tri,yt,ICT,TRI_FRACS,TRI_USE,'t_max','triples',.75)
neg=[shuffle_control(tri,yt,ICT,0,'t_max','triples')]

bd=load(find(ROOT_CHUNKS,'chunk_boundary_0_of_1.npz'),TRI_FRACS);yb=labels_tri(bd['statuses']);ICB=ic_tri(bd['ic'])
dump('boundary_retention.json',retention(bd,yb,TRI_FRACS,TRI_USE,'t_max'))
bd_parity,bd_split=parity_task(bd,yb,ICB,TRI_FRACS,TRI_USE,'t_max','boundary',True)
landmark(bd,yb,ICB,TRI_FRACS,TRI_USE,'t_max','boundary',.75)
neg.append(shuffle_control(bd,yb,ICB,6,'t_max','boundary'))
boundary_ood(tri,yt,bd,yb,TRI_USE)

del tri,yt,ICT,bd,yb,ICB;gc.collect();log('released triple/boundary arrays')

# ---------------- encounters
enc=load(find(ROOT_CHUNKS,'chunk_encounters_0_of_1.npz'),ENC_FRACS);ye=(enc['statuses']=='exchange').astype(np.int8);ICE=ic_enc(enc['ic'])
dump('encounters_retention.json',retention(enc,ye,ENC_FRACS,ENC_USE,'t_approach'))
enc_parity,enc_split=parity_task(enc,ye,ICE,ENC_FRACS,ENC_USE,'t_approach','encounters',False)
landmark(enc,ye,ICE,ENC_FRACS,ENC_USE,'t_approach','encounters',.95)
neg.append(shuffle_control(enc,ye,ICE,0,'t_approach','encounters'))
encounter_conditionals(enc,ye,ENC_USE)
dump('negative_controls_final.json',neg)

del enc,ye,ICE;gc.collect()

# ---------------- final manifest/archive
summary={'status':'complete','runtime_minutes':(time.time()-START)/60,'disabled_indices':[72,73],
 'bootstrap_replicates':BOOT,'fars':FARS,'split_seed':SEED,
 'outputs':[p.name for p in sorted(OUT.iterdir())]}
dump('audit_summary.json',summary)
manifest={'status':'complete','files':{}}
for p in sorted(OUT.iterdir()):
    if p.is_file(): manifest['files'][p.name]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
dump('OUTPUT_MANIFEST.json',manifest)
with open(OUT/'SHA256SUMS.txt','w') as f:
    for name,info in manifest['files'].items(): f.write(f"{info['sha256']}  {name}\n")
zip_path=shutil.make_archive('/kaggle/working/final_expanded_audit','zip',root_dir=str(OUT))
log('EXPANDED AUDIT COMPLETE')
print('OUTPUTS:',sorted(p.name for p in OUT.iterdir()),flush=True)
print('DOWNLOAD NOW:',zip_path,flush=True)
print('Then Save Version.',flush=True)
