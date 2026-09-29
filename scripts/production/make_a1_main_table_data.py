#!/usr/bin/env python3
"""Write machine-readable source data for the two A1 main-text tables.

Reads only v1.0.0-pinned derived artifacts. Display-only arithmetic is limited
to exact count ratios and percent conversion; no model fit or resampling occurs.
"""
from __future__ import annotations
import csv, json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
R=ROOT/'results'; OUT=ROOT/'paper_draft'/'table_data';OUT.mkdir(parents=True,exist_ok=True)

def load(p):
    with open(p) as f:return json.load(f)

tri=load(R/'final_expanded_audit_json'/'triples_parity.json')
lit=load(R/'literature_baseline'/'literature_baseline_results.json')
first,last=tri['horizons'][0],tri['horizons'][-1]
methods=[]
for key,label,info,training,endpoint in [
 ('MA01_margin','MA01 margin','t=0','published analytic score','external rule'),
 ('V22_formula','V22 formula','t=0','published algebraic score','external transfer'),
 ('V22_MLP_semimajor','V22 semimajor MLP','t=0','public pretrained MLP','external transfer'),
 ('V23_MLP_ghost','V23 ghost MLP','t=0','public pretrained MLP','external transfer')]:
    f=lit['horizons'][0]['models'][key];l=lit['horizons'][-1]['models'][key]
    ff=next(x for x in l['fixed_far'] if np.isclose(x['target_far'],.01))
    methods.append(dict(method=label,information=info,training_relation=training,endpoint_relation=endpoint,
                        auc_15=f['roc_auc'],auc_225=l['roc_auc'],recall_225_target_far_0p01=ff['recall']))
for key,label,info in [('IC_only','In-domain IC-only','t=0'),('window','Trajectory history','t<=t_h'),('combined','Combined','t=0 and t<=t_h')]:
    f=first['models'][key];l=last['models'][key];ff=next(x for x in l['fixed_far'] if np.isclose(x['target_far'],.01))
    methods.append(dict(method=label,information=info,training_relation='matched A1 split/model',
                        endpoint_relation='endpoint adapted' if key=='IC_only' else 'horizon specific',
                        auc_15=f['roc_auc'],auc_225=l['roc_auc'],recall_225_target_far_0p01=ff['recall']))
with open(OUT/'table1_baselines.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(methods[0]));w.writeheader();w.writerows(methods)

rows=[]
n_pos=tri['lead_by_far'][0]['n_test_positive'];n_ctrl=tri['split_sizes']['test']-n_pos
for x in tri['lead_by_far']:
    false=round(x['cumulative_false_alert_fraction']*n_ctrl)
    rows.append(dict(population_endpoint='primary_300',operating_status=f"target_far_{x['target_far']}",
      n_event_denominator=x['n_first_horizon_eligible'],n_control_denominator=n_ctrl,
      coverage=x['coverage_eligible'],n_controls_alerted=false,
      cumulative_control_alert_fraction=x['cumulative_false_alert_fraction'],
      precision=x['n_warned']/(x['n_warned']+false),median_lead=x['median_lead'],p25=x['p25'],p75=x['p75']))
bd=load(R/'final_expanded_audit_json'/'boundary_parity.json');x=next(y for y in bd['lead_by_far'] if np.isclose(y['target_far'],.01));n_ctrl=bd['split_sizes']['test']-x['n_test_positive'];false=round(x['cumulative_false_alert_fraction']*n_ctrl)
rows.append(dict(population_endpoint='boundary_100',operating_status='target_far_0.01',n_event_denominator=x['n_first_horizon_eligible'],n_control_denominator=n_ctrl,coverage=x['coverage_eligible'],n_controls_alerted=false,cumulative_control_alert_fraction=x['cumulative_false_alert_fraction'],precision=x['n_warned']/(x['n_warned']+false),median_lead=x['median_lead'],p25=x['p25'],p75=x['p75']))
attr=load(R/'attribution_growth_v2'/'prospective_model_attribution.json')
for key,label in [('IC_only','delayed_300_3000_IC'),('combined','delayed_300_3000_combined')]:
    x=next(y for y in attr['models'][key]['lead_by_frozen_far'] if np.isclose(y['target_far'],.01))
    rows.append(dict(population_endpoint=label,operating_status='frozen_original_target_far_0.01',n_event_denominator=x['n_delayed'],n_control_denominator=x['n_controls'],coverage=x['coverage'],n_controls_alerted=round(x['cumulative_control_false_alert']*x['n_controls']),cumulative_control_alert_fraction=x['cumulative_control_false_alert'],precision=x['precision'],median_lead=x['median_lead'],p25=x['p25'],p75=x['p75']))
with open(OUT/'table2_warning_operation.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

# Tolerance rows are kept separate because they are not warning operating points.
tol=load(R/'tolerance_validation'/'tolerance_report.json')
tol_join=load(R/'tolerance_validation'/'delayed_tolerance_join_summary.json')
tol_rows=[
 {'cohort':'preselected_500','n':tol['n'],
  'production_incidence':tol['baseline_status_counts']['ejected']/tol['n'],
  'tight_incidence':tol['tight_status_counts']['ejected']/tol['n'],
  'agreement':tol['outcome_agreement'],'n_label_changes':tol['n_outcome_flips'],
  'source':'results/tolerance/tolerance_report.json'},
 {'cohort':'main_stable_330','n':tol_join['cohort']['n'],
  'production_incidence':tol_join['production_tolerance']['fraction'],
  'tight_incidence':tol_join['tight_tolerance']['fraction'],'agreement':'',
  'n_label_changes':tol_join['paired_label_changes']['n_changed'],
  'source':'results/tolerance/delayed_tolerance_join_summary.json'},
]
with open(OUT/'table2_tolerance.csv','w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(tol_rows[0]));w.writeheader();w.writerows(tol_rows)
print(OUT)
