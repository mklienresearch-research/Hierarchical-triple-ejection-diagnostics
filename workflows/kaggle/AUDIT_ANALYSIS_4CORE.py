# ============================================================================
# ADVERSARIAL AUDIT — corrected causal analysis — standard Kaggle 4-core CPU
#
# Inputs (mounted Kaggle datasets):
#   /kaggle/input/datasets/klienm/v2chunks
#   /kaggle/input/datasets/klienm/mergedtriples
#
# Outputs:
#   /kaggle/working/audit_corrected_4core/*.json
#
# Tests:
#   * duplicate/schema checks and forced neutralization of leaked n_frac[73]
#   * shuffled-label negative controls
#   * single-feature monotone AUC scan
#   * physical feature-family ablations and time-anchor ablation
#   * blocked extrapolation splits in initial-condition space
#   * PR-AUC, MCC, Brier, ECE and balanced accuracy
#   * recall/precision/lead at fixed FAR = 0.1%, 1%, 5%
#
# This file performs NO N-body simulations and does not modify mounted data.
# ============================================================================

import os
import sys
import json
import time
import gc
import subprocess
from pathlib import Path

import numpy as np

subprocess.run(
    [sys.executable, "-m", "pip", "install", "-q", "xgboost", "scikit-learn"],
    check=False,
)

from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    roc_auc_score,
    average_precision_score,
    balanced_accuracy_score,
    matthews_corrcoef,
    brier_score_loss,
    precision_score,
    recall_score,
    confusion_matrix,
)

# ---------------------------------------------------------------- configuration
CPU = len(os.sched_getaffinity(0))
if CPU < 4:
    raise RuntimeError(f"Only {CPU} CPUs available; four required")

N_JOBS = 4
SEEDS = [0, 1, 2]
FIT_CAP = 200_000
TEST_CAP = 200_000
FARS = [0.001, 0.01, 0.05]

CHUNKS_ROOT = Path("/kaggle/input/datasets/klienm/v2chunks")
TRIPLES_ROOT = Path("/kaggle/input/datasets/klienm/mergedtriples")
OUT = Path("/kaggle/working/audit_corrected_4core")
OUT.mkdir(parents=True, exist_ok=True)
for old in OUT.glob("*.json"):
    old.unlink()

TRIPLE_FRACS = np.array(
    [0.05, 0.10, 0.15, 0.20, 0.30, 0.40, 0.50, 0.60, 0.75, 0.90, 1.00],
    dtype=np.float32,
)
ENC_FRACS = np.array(
    [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35, 0.40, 0.45, 0.50,
     0.55, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90, 0.95, 1.00],
    dtype=np.float32,
)

FEATURE_NAMES = [
    "H_min", "H_max", "H_mean", "H_std", "H_med", "H_range", "H_final", "H_initial",
    "H_slope", "H_curv", "H_below_frac", "H_crossings",
    "dH_min", "dH_max", "dH_std", "abs_dH_max",
    "d2H_min", "d2H_max", "d2H_std", "abs_d2H_max",
    "psi_mean", "psi_max", "psi_std", "psi_final",
    "E01_std", "E02_std", "E12_std", "E_exch", "E_exch_norm",
    "E01_slope", "E02_slope", "E12_slope", "E01_final", "E02_final",
    "Eout_min", "Eout_max", "Eout_final", "Eout_slope",
    "L01_min", "L01_max", "L01_std", "L02_min", "L02_max", "L02_std",
    "L12_min", "L12_max", "L12_std", "L01_slope", "L02_slope", "L12_slope",
    "G01_max", "G01_mean", "G01_spike", "G02_max", "G02_mean", "G02_spike",
    "G12_max", "G12_mean", "G12_spike", "G_all_max", "G_all_mean",
    "G_spike_max", "G_spike_mean",
    "Om_min", "Om_max", "Om_mean", "Om_std", "Om_final", "Om_slope",
    "H_entropy", "Om_entropy", "H_autocorr",
    "first_breach", "n_frac", "dur",
    "dmin_min", "dmin_frac", "dmin_rate_max", "n_pair_changes",
]
assert len(FEATURE_NAMES) == 79 and FEATURE_NAMES[73] == "n_frac"

# n_frac is always excluded/zero. Time-anchor ablation also excludes 72, 74, 76.
SAFE_FEATURES = np.array([i for i in range(79) if i != 73], dtype=int)
NO_TIME_FEATURES = np.array([i for i in SAFE_FEATURES if i not in (72, 74, 76)], dtype=int)

FAMILIES = {
    "hierarchy": list(range(0, 12)),
    "derivatives_psi": list(range(12, 24)),
    "energy": list(range(24, 38)),
    "angular_momentum": list(range(38, 50)),
    "torque": list(range(50, 63)),
    "omega": list(range(63, 69)),
    "signal": list(range(69, 72)),
    "time_anchors": [72, 74, 76],
    "distance_exchange": [75, 77, 78],
    "all_window_safe": SAFE_FEATURES.tolist(),
    "all_window_no_time": NO_TIME_FEATURES.tolist(),
}

START = time.time()

def stamp(msg):
    print(f"[{(time.time()-START)/60:7.1f} min] {msg}", flush=True)


def dump(name, obj):
    with open(OUT / name, "w") as f:
        json.dump(obj, f, indent=1, allow_nan=True)


def find_one(root, filename):
    hits = sorted(root.rglob(filename), key=lambda p: (len(p.parts), str(p)))
    if not hits:
        raise FileNotFoundError(f"Could not find {filename} under {root}")
    return hits[0]


TRIPLE_FILE = find_one(TRIPLES_ROOT, "merged_triples.npz")
ENC_FILE = find_one(CHUNKS_ROOT, "chunk_encounters_0_of_1.npz")
BOUNDARY_FILE = find_one(CHUNKS_ROOT, "chunk_boundary_0_of_1.npz")

stamp(f"CPUs={CPU}; XGBoost threads={N_JOBS}")
stamp(f"triples={TRIPLE_FILE}")
stamp(f"encounters={ENC_FILE}")
stamp(f"boundary={BOUNDARY_FILE}")


def model(seed=0):
    return XGBClassifier(
        n_estimators=300,
        max_depth=3,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        reg_lambda=2.0,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=seed,
        n_jobs=N_JOBS,
        tree_method="hist",
    )


def cap_idx(idx, cap, seed):
    idx = np.asarray(idx, dtype=np.int64)
    if cap and len(idx) > cap:
        return np.random.default_rng(seed).choice(idx, cap, replace=False)
    return idx


def expected_calibration_error(y, p, bins=15):
    y = np.asarray(y); p = np.asarray(p)
    edges = np.linspace(0, 1, bins + 1)
    out = 0.0
    for lo, hi in zip(edges[:-1], edges[1:]):
        m = (p >= lo) & (p < hi if hi < 1 else p <= hi)
        if m.any():
            out += m.mean() * abs(float(y[m].mean()) - float(p[m].mean()))
    return float(out)


def binary_metrics(y, p, threshold=0.5):
    pred = (p >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, pred, labels=[0, 1]).ravel()
    return {
        "n": int(len(y)),
        "prevalence": float(np.mean(y)),
        "roc_auc": float(roc_auc_score(y, p)),
        "pr_auc": float(average_precision_score(y, p)),
        "pr_baseline": float(np.mean(y)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "mcc": float(matthews_corrcoef(y, pred)),
        "brier": float(brier_score_loss(y, p)),
        "ece15": expected_calibration_error(y, p, 15),
        "precision": float(precision_score(y, pred, zero_division=0)),
        "recall": float(recall_score(y, pred, zero_division=0)),
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def ic_triple(ic):
    return np.column_stack([
        ic[:, 0], ic[:, 1], ic[:, 2], ic[:, 3], ic[:, 4],
        ic[:, 9], ic[:, 10], ic[:, 11],
        ic[:, 12] / (ic[:, 0] + ic[:, 1] + 1e-30),
        ic[:, 9] / (ic[:, 3] + 1e-30),
        ic[:, 9] * (1 - ic[:, 10]) / (ic[:, 3] * (1 + ic[:, 4]) + 1e-30),
        np.cos(ic[:, 11]), np.sin(ic[:, 11]), ic[:, 15], ic[:, 16],
    ]).astype(np.float32)


def ic_encounter(ic):
    return np.column_stack([
        ic[:, 0], ic[:, 1], ic[:, 2], ic[:, 4],
        ic[:, 15], ic[:, 16], ic[:, 17],
        ic[:, 15] / (ic[:, 16] + 1e-30),
    ]).astype(np.float32)


def load_npz(path, fractions, task):
    stamp(f"loading {task}")
    with np.load(path, allow_pickle=False) as z:
        d = {k: z[k] for k in z.files if k != "fractions"}
    d["fractions"] = np.asarray(fractions, dtype=np.float32)
    if d["feats"].shape[2] != 79:
        raise RuntimeError(f"{task}: wrong feature shape {d['feats'].shape}")
    d["feats"][:, :, 73] = 0.0
    if np.any(d["feats"][:, :, 73] != 0):
        raise RuntimeError("n_frac neutralization failed")
    if len(np.unique(d["ids"])) != len(d["ids"]):
        raise RuntimeError(f"{task}: duplicate IDs")
    stamp(f"loaded {task}: N={len(d['ids']):,}, feats={d['feats'].shape}; n_frac=0 verified")
    return d


def horizon_index(fracs, f):
    return int(np.argmin(np.abs(np.asarray(fracs, float) - float(f))))


def valid_binary_triple(status):
    y = np.full(len(status), -1, dtype=np.int8)
    y[status == "stable"] = 0
    y[status == "ejected"] = 1
    return y


def inplay_indices(d, y, f, anchor):
    h = float(f) * d[anchor]
    te = np.where(np.isnan(d["t_event"]), np.inf, d["t_event"])
    return np.where((y >= 0) & (te > h))[0]


def repeated_random_eval(X, y, idx, title, seeds=SEEDS):
    idx = cap_idx(idx, FIT_CAP, 10001)
    rows = []
    for seed in seeds:
        tr, va = train_test_split(idx, test_size=0.30, random_state=seed,
                                  stratify=y[idx])
        m = model(seed); m.fit(X[tr], y[tr]); p = m.predict_proba(X[va])[:, 1]
        r = binary_metrics(y[va], p); r["seed"] = int(seed); rows.append(r)
    keys = ["roc_auc", "pr_auc", "balanced_accuracy", "mcc", "brier", "ece15",
            "precision", "recall"]
    out = {"name": title, "n_eval_pool": int(len(idx)), "seeds": rows}
    for k in keys:
        out[k + "_mean"] = float(np.mean([r[k] for r in rows]))
        out[k + "_std"] = float(np.std([r[k] for r in rows]))
    return out


def negative_control(X, y, idx, title):
    idx = cap_idx(idx, FIT_CAP, 11001)
    out = []
    for seed in SEEDS:
        rng = np.random.default_rng(12000 + seed)
        ys = y[idx].copy(); rng.shuffle(ys)
        a, b = train_test_split(np.arange(len(idx)), test_size=.30,
                                random_state=seed, stratify=ys)
        m = model(seed); m.fit(X[idx[a]], ys[a]); p = m.predict_proba(X[idx[b]])[:, 1]
        out.append({"seed": seed, "roc_auc": float(roc_auc_score(ys[b], p)),
                    "pr_auc": float(average_precision_score(ys[b], p)),
                    "prevalence": float(ys[b].mean())})
    stamp(f"negative control {title}: AUC={np.mean([x['roc_auc'] for x in out]):.4f}")
    return {"name": title, "rows": out,
            "auc_mean": float(np.mean([x["roc_auc"] for x in out])),
            "auc_std": float(np.std([x["roc_auc"] for x in out]))}


def univariate_scan(Xw, y, idx, task, f):
    idx = cap_idx(idx, FIT_CAP, 13001)
    rows = []
    yy = y[idx]
    for j, name in enumerate(FEATURE_NAMES):
        if j == 73:
            continue
        x = np.nan_to_num(Xw[idx, j], nan=0.0, posinf=1e30, neginf=-1e30)
        if np.std(x) <= 1e-12:
            auc = 0.5
        else:
            a = float(roc_auc_score(yy, x)); auc = max(a, 1-a)
        rows.append({"feature": name, "index": j, "absolute_monotone_auc": auc})
    rows.sort(key=lambda r: -r["absolute_monotone_auc"])
    stamp(f"single-feature scan {task} f={f}: top={rows[0]['feature']} AUC={rows[0]['absolute_monotone_auc']:.4f}")
    return {"task": task, "f": float(f), "n": int(len(idx)), "features": rows}


def ablation_suite(d, y, icX, horizons, task):
    out = []
    for f in horizons:
        fi = horizon_index(d["fractions"], f)
        idx = inplay_indices(d, y, f, "t_max" if task != "encounters" else "t_approach")
        idx = cap_idx(idx, FIT_CAP, 14000 + fi)
        stamp(f"ablation {task} f={f}: {len(idx):,} systems")
        designs = {"IC_only": icX, "IC_plus_all_window": np.hstack([icX, d["feats"][:, fi, SAFE_FEATURES]])}
        for name, cols in FAMILIES.items():
            designs[name] = d["feats"][:, fi, cols]
        for name, X in designs.items():
            r = repeated_random_eval(X, y, idx, f"{task}:{name}:f={f}")
            r.update(task=task, f=float(f), family=name, n_features=int(X.shape[1]))
            out.append(r)
            stamp(f"  {name:24s} AUC={r['roc_auc_mean']:.4f} PR={r['pr_auc_mean']:.4f}")
    return out


def blocked_splits(d, y, f=0.30):
    fi = horizon_index(d["fractions"], f)
    idx = inplay_indices(d, y, f, "t_max")
    ic = d["ic"]
    variables = {
        "MA01_margin": ic[:, 16],
        "aout_over_ain": ic[:, 9] / (ic[:, 3] + 1e-30),
        "e_outer": ic[:, 10],
        "inclination": ic[:, 11],
        "outer_mass_ratio": ic[:, 2] / (ic[:, 0] + ic[:, 1] + 1e-30),
    }
    X = np.hstack([ic_triple(ic), d["feats"][:, fi, SAFE_FEATURES]])
    rows = []
    for name, v in variables.items():
        q25, q75 = np.quantile(v[idx], [0.25, 0.75])
        directions = [
            ("high_tail", idx[v[idx] <= q75], idx[v[idx] > q75], q75),
            ("low_tail", idx[v[idx] >= q25], idx[v[idx] < q25], q25),
        ]
        for direction, tr0, te0, cut in directions:
            tr = cap_idx(tr0, FIT_CAP, 15001); te = cap_idx(te0, TEST_CAP, 15002)
            if len(np.unique(y[tr])) < 2 or len(np.unique(y[te])) < 2:
                row = {"variable": name, "direction": direction, "skipped": "single class"}
            else:
                m = model(0); m.fit(X[tr], y[tr]); p = m.predict_proba(X[te])[:, 1]
                row = binary_metrics(y[te], p)
                row.update(variable=name, direction=direction, cutoff=float(cut),
                           n_train=int(len(tr)), n_test=int(len(te)))
            rows.append(row)
            stamp(f"blocked {name}/{direction}: AUC={row.get('roc_auc', float('nan')):.4f}")
    return {"task": "triples", "f": float(f), "rows": rows}


def fixed_far_audit(d, y, icX, task, anchor, fractions, units, reference):
    """Global train/calibration/test split; horizon models never see test systems."""
    valid = np.where(y >= 0)[0]
    train_idx, hold = train_test_split(valid, test_size=0.40, random_state=16001,
                                       stratify=y[valid])
    cal_idx, test_idx = train_test_split(hold, test_size=0.50, random_state=16002,
                                         stratify=y[hold])
    train_idx = cap_idx(train_idx, FIT_CAP, 16003)
    # Keep full calibration/test cohorts for reliable low-FAR estimates.
    Ptest = np.full((len(y), len(fractions)), np.nan, dtype=np.float32)
    thresholds = {str(far): np.full(len(fractions), np.nan) for far in FARS}
    horizon_rows = []
    for fi, f in enumerate(fractions):
        h = float(f) * d[anchor]
        te = np.where(np.isnan(d["t_event"]), np.inf, d["t_event"])
        tr = train_idx[te[train_idx] > h[train_idx]]
        ca = cal_idx[te[cal_idx] > h[cal_idx]]
        tt = test_idx[te[test_idx] > h[test_idx]]
        if len(tr) < 100 or len(np.unique(y[tr])) < 2 or np.sum(y[tr] == 1) < 30:
            continue
        X = np.hstack([icX, d["feats"][:, fi, SAFE_FEATURES]])
        m = model(17000 + fi); m.fit(X[tr], y[tr])
        pca = m.predict_proba(X[ca])[:, 1]
        ptt = m.predict_proba(X[tt])[:, 1]
        Ptest[tt, fi] = ptt
        base = binary_metrics(y[tt], ptt)
        base.update(f=float(f), n_train=int(len(tr)), n_cal=int(len(ca)), n_test=int(len(tt)))
        fixed = []
        neg_cal = pca[y[ca] == 0]
        for far in FARS:
            threshold = float(np.quantile(neg_cal, 1-far, method="higher"))
            thresholds[str(far)][fi] = threshold
            pred = ptt >= threshold
            neg = y[tt] == 0; pos = y[tt] == 1
            fixed.append({
                "target_far": far,
                "threshold": threshold,
                "measured_far": float(np.mean(pred[neg])) if neg.any() else np.nan,
                "recall": float(np.mean(pred[pos])) if pos.any() else np.nan,
                "precision": float(np.mean(y[tt][pred])) if pred.any() else np.nan,
                "n_alerts": int(pred.sum()),
            })
        base["fixed_far"] = fixed; horizon_rows.append(base)
        stamp(f"fixed-FAR {task} f={float(f):.2f}: AUC={base['roc_auc']:.4f}, PR={base['pr_auc']:.4f}")

    # Earliest alert and lead on the untouched test systems.
    leads_out = []
    first_f = float(fractions[0])
    te_raw = d["t_event"]
    eligible = (y[test_idx] == 1) & np.isfinite(te_raw[test_idx]) & (te_raw[test_idx] > first_f*d[anchor][test_idx])
    n_pos_all = int(np.sum(y[test_idx] == 1)); n_eligible = int(eligible.sum())
    stable_test = test_idx[y[test_idx] == 0]
    for far in FARS:
        leads=[]; warned_ids=[]; false_systems=0
        ths=thresholds[str(far)]
        for i in test_idx[y[test_idx] == 1]:
            for fi,f in enumerate(fractions):
                if not np.isfinite(ths[fi]): continue
                if np.isfinite(te_raw[i]) and te_raw[i] <= float(f)*d[anchor][i]: break
                if np.isfinite(Ptest[i,fi]) and Ptest[i,fi] >= ths[fi]:
                    leads.append(float((reference[i]-float(f)*d[anchor][i])/units[i]))
                    warned_ids.append(int(i)); break
        for i in stable_test:
            if any(np.isfinite(ths[fi]) and np.isfinite(Ptest[i,fi]) and Ptest[i,fi] >= ths[fi]
                   for fi in range(len(fractions))):
                false_systems += 1
        leads=np.asarray(leads,float); poslead=leads[leads>0]
        row={
            "target_far": far,
            "n_test_positive_all": n_pos_all,
            "n_test_positive_first_horizon_eligible": n_eligible,
            "n_warned": int(len(leads)),
            "coverage_all_positive": float(len(leads)/max(n_pos_all,1)),
            "coverage_eligible": float(len(leads)/max(n_eligible,1)),
            "system_level_false_alert_fraction_stable": float(false_systems/max(len(stable_test),1)),
            "positive_lead_fraction": float(len(poslead)/max(len(leads),1)),
            "median_lead": float(np.median(leads)) if len(leads) else np.nan,
            "p25_lead": float(np.percentile(leads,25)) if len(leads) else np.nan,
            "p75_lead": float(np.percentile(leads,75)) if len(leads) else np.nan,
            "median_positive_lead": float(np.median(poslead)) if len(poslead) else np.nan,
        }
        leads_out.append(row)
        stamp(f"lead/FAR {task} {100*far:.1f}%: warned={len(leads)}, eligible coverage={row['coverage_eligible']:.3f}")
    return {"task": task, "split": {"train": int(len(train_idx)), "calibration": int(len(cal_idx)), "test": int(len(test_idx))},
            "horizons": horizon_rows, "lead_by_far": leads_out}


# ================================================================= TRIPLES
tr = load_npz(TRIPLE_FILE, TRIPLE_FRACS, "triples")
ytr = valid_binary_triple(tr["statuses"])
ictr = ic_triple(tr["ic"])

negative = []
single = []
for f in [0.05, 0.50]:
    fi = horizon_index(tr["fractions"], f)
    idx = inplay_indices(tr, ytr, f, "t_max")
    X = np.hstack([ictr, tr["feats"][:, fi, SAFE_FEATURES]])
    negative.append(negative_control(X, ytr, idx, f"triples_combined_f{f}"))
    single.append(univariate_scan(tr["feats"][:, fi, :], ytr, idx, "triples", f))

dump("negative_controls_partial.json", negative)
dump("single_feature_scan_partial.json", single)

ablations = ablation_suite(tr, ytr, ictr, [0.05, 0.50], "triples")
dump("feature_ablation_triples.json", ablations)

blocked = blocked_splits(tr, ytr, 0.30)
dump("blocked_splits.json", blocked)

pout = np.sqrt(tr["ic"][:, 9]**3/(tr["ic"][:,0]+tr["ic"][:,1]+tr["ic"][:,2]+1e-30))
tr_fixed = fixed_far_audit(tr, ytr, ictr, "triples", "t_max", TRIPLE_FRACS,
                           pout, np.where(np.isnan(tr["t_event"]), tr["t_max"], tr["t_event"]))
dump("fixed_far_triples.json", tr_fixed)

# Boundary negative control and single-feature scan.
bd = load_npz(BOUNDARY_FILE, TRIPLE_FRACS, "boundary")
yb = valid_binary_triple(bd["statuses"])
icbd = ic_triple(bd["ic"])
f = 0.50; fi = horizon_index(bd["fractions"], f); idx = inplay_indices(bd, yb, f, "t_max")
Xbd = np.hstack([icbd, bd["feats"][:, fi, SAFE_FEATURES]])
negative.append(negative_control(Xbd, yb, idx, "boundary_combined_f0.50"))
single.append(univariate_scan(bd["feats"][:, fi, :], yb, idx, "boundary", f))
dump("negative_controls_partial.json", negative)
dump("single_feature_scan_partial.json", single)
del bd, yb, icbd, Xbd
gc.collect()

# Release large triple arrays before loading encounters.
del tr, ytr, ictr
gc.collect()
stamp("triple and boundary audits complete; memory released")

# =============================================================== ENCOUNTERS
en = load_npz(ENC_FILE, ENC_FRACS, "encounters")
yen = (en["statuses"] == "exchange").astype(np.int8)
icen = ic_encounter(en["ic"])

for f in [0.05, 0.75]:
    fi = horizon_index(en["fractions"], f)
    idx = inplay_indices(en, yen, f, "t_approach")
    X = np.hstack([icen, en["feats"][:, fi, SAFE_FEATURES]])
    negative.append(negative_control(X, yen, idx, f"encounters_combined_f{f}"))
    single.append(univariate_scan(en["feats"][:, fi, :], yen, idx, "encounters", f))

dump("negative_controls.json", negative)
dump("single_feature_scan.json", single)
# Remove partial checkpoint names now that final files exist.
for temp in [OUT/"negative_controls_partial.json", OUT/"single_feature_scan_partial.json"]:
    if temp.exists(): temp.unlink()

# Encounter ablation at early and near-approach horizons.
enc_ab = ablation_suite(en, yen, icen, [0.05, 0.75], "encounters")
dump("feature_ablation_encounters.json", enc_ab)

# Fixed-FAR encounter audit. Reference is periastron; units are binary periods.
tbin = en["ic"][:,20] if en["ic"].shape[1] > 20 else np.full(len(yen),4.443,dtype=np.float32)
en_fixed = fixed_far_audit(en, yen, icen, "encounters", "t_approach", ENC_FRACS,
                           tbin, en["t_peri"])
dump("fixed_far_encounters.json", en_fixed)

del en, yen, icen
gc.collect()

# ================================================================ SUMMARY
# Hard gates are deliberately explicit and machine-readable.
shuffle_aucs = [r["auc_mean"] for r in negative]
top_features = []
for scan in single:
    top_features.append({"task": scan["task"], "f": scan["f"],
                         "top": scan["features"][:10]})

summary = {
    "runtime_minutes": float((time.time()-START)/60),
    "configuration": {
        "cpus": CPU, "xgboost_threads": N_JOBS, "seeds": SEEDS,
        "fit_cap": FIT_CAP, "fars": FARS,
        "leaked_feature_disabled": "n_frac", "leaked_feature_index": 73,
    },
    "gates": {
        "shuffle_auc_values": shuffle_aucs,
        "shuffle_pass_all_abs_from_half_le_0p02": bool(all(abs(a-0.5) <= 0.02 for a in shuffle_aucs)),
        "n_frac_zero_enforced": True,
        "duplicate_id_checks_passed": True,
    },
    "top_univariate_features": top_features,
    "outputs": sorted(p.name for p in OUT.glob("*.json")),
}
dump("audit_summary.json", summary)

manifest = {
    "status": "complete",
    "runtime_minutes": summary["runtime_minutes"],
    "files": sorted(p.name for p in OUT.glob("*.json")),
    "interpretation_rule": "Do not accept the paper-level model until shuffled-label, ablation, blocked-split, calibration, and fixed-FAR outputs have been reviewed.",
}
dump("audit_manifest.json", manifest)

stamp("AUDIT COMPLETE")
print("Outputs:", sorted(p.name for p in OUT.glob("*.json")), flush=True)
print("Save Version. Send every JSON in /kaggle/working/audit_corrected_4core", flush=True)
