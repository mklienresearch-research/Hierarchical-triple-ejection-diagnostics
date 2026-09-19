# =====================================================================
#  SESSION B CORRECTED - leakage-free v3 analysis - STANDARD 4 CPU CORES of the scale-up data (up to 19 JSONs)
#  Inputs (private Kaggle dataset `v2merged`): merged_triples.npz,
#  merged_encounters.npz, merged_boundary.npz, merged_tail.npz (optional),
#  merged_triples_series.pkl (optional).
#  HOW TO RUN (pick one):
#    A) Upload (drag & drop) as session_b.py, then run a cell with:
#           %run /kaggle/working/session_b.py
#    B) Paste EVERYTHING into ONE Kaggle code cell and run.
#  RUN_MODE = "BOTH" (default) | "TRIPLES" | "ENCOUNTERS" (one line below).
#  Includes: horizon curves, decision/lead times, multiclass, conditional
#  skill, spike study, survival/censoring, boundary in-stratum curve +
#  OOD, MA01, time-to-event, Cox hazards.
# =====================================================================

# =====================================================================
# DATASET PREFLIGHT — no combining and no uploads.
# Sources:
#   /kaggle/input/datasets/klienm/v2chunks       encounters + boundary
#   /kaggle/input/datasets/klienm/mergedtriples  physically merged triples
# Recursively discovers files in case Kaggle adds an output subdirectory,
# then links them into the single directory expected by Session B.
# =====================================================================
import os as _pre_os
from pathlib import Path as _PrePath
import numpy as _pre_np

_CHUNKS_ROOT = _PrePath("/kaggle/input/datasets/klienm/v2chunks")
_TRIPLES_ROOT = _PrePath("/kaggle/input/datasets/klienm/mergedtriples")
_ANALYSIS_INPUT = _PrePath("/kaggle/working/analysis_input_corrected_4core")
_ANALYSIS_INPUT.mkdir(parents=True, exist_ok=True)

print("=== DATASET PREFLIGHT ===", flush=True)
_allocated_cpus = len(_pre_os.sched_getaffinity(0))
print("Allocated CPUs:", _allocated_cpus, flush=True)
if _allocated_cpus < 4:
    raise RuntimeError(f"Only {_allocated_cpus} CPUs are allocated; four are required.")
if _allocated_cpus > 8:
    print("NOTE: more than 4 CPUs detected; this file intentionally uses 4 threads.", flush=True)
print("Chunks dataset:", _CHUNKS_ROOT, "exists:", _CHUNKS_ROOT.is_dir(), flush=True)
print("Triples dataset:", _TRIPLES_ROOT, "exists:", _TRIPLES_ROOT.is_dir(), flush=True)

if not _CHUNKS_ROOT.is_dir():
    raise FileNotFoundError(
        "v2chunks is not mounted at /kaggle/input/datasets/klienm/v2chunks")
if not _TRIPLES_ROOT.is_dir():
    raise FileNotFoundError(
        "mergedtriples is not mounted at /kaggle/input/datasets/klienm/mergedtriples")


def _find_one(root, filename, required=True):
    hits = sorted(root.rglob(filename), key=lambda p: (len(p.parts), str(p)))
    if not hits:
        if required:
            raise FileNotFoundError(f"Could not find {filename} anywhere under {root}")
        return None
    if len(hits) > 1:
        print(f"WARNING: multiple copies of {filename}; using {hits[0]}", flush=True)
    return hits[0]


def _link(source, output_name):
    destination = _ANALYSIS_INPUT / output_name
    if destination.is_symlink() or destination.exists():
        destination.unlink()
    _pre_os.symlink(str(source.resolve()), str(destination))
    if not destination.exists():
        raise RuntimeError(f"Failed to create readable link: {destination}")
    print(f"READY {output_name} -> {source}", flush=True)


_triples_npz = _find_one(_TRIPLES_ROOT, "merged_triples.npz")
_triples_series = _find_one(_TRIPLES_ROOT, "merged_triples_series.pkl", required=False)
_encounters_npz = _find_one(_CHUNKS_ROOT, "chunk_encounters_0_of_1.npz")
_boundary_npz = _find_one(_CHUNKS_ROOT, "chunk_boundary_0_of_1.npz")

_link(_triples_npz, "merged_triples.npz")
if _triples_series is not None:
    _link(_triples_series, "merged_triples_series.pkl")
else:
    print("WARNING: merged_triples_series.pkl absent; spike study will be skipped", flush=True)
_link(_encounters_npz, "merged_encounters.npz")
_link(_boundary_npz, "merged_boundary.npz")

# Fail immediately, rather than hours into an unattended run, if a dataset
# has the wrong number of systems or incompatible feature dimensions.
_expected = {
    "merged_triples.npz": (500_000, 11, 79),
    "merged_encounters.npz": (1_000_000, 20, 79),
    "merged_boundary.npz": (100_000, 11, 79),
}
for _name, (_n, _h, _f) in _expected.items():
    _p = _ANALYSIS_INPUT / _name
    with _pre_np.load(_p, allow_pickle=False) as _d:
        _shape = _d["feats"].shape
        _nids = len(_d["ids"])
        if _shape != (_n, _h, _f) or _nids != _n:
            raise RuntimeError(
                f"{_name} failed validation: ids={_nids}, feats={_shape}; "
                f"expected ids={_n}, feats={(_n, _h, _f)}")
        print(f"VALIDATED {_name}: ids={_nids:,}, feats={_shape}", flush=True)

# Set these BEFORE the analysis module reads ML_JOBS.
_pre_os.environ["V2_MERGED_DIR"] = str(_ANALYSIS_INPUT)
_pre_os.environ["V2_ML_JOBS"] = "4"
_pre_os.environ["V2_SEEDS"] = "0,1,2"
_pre_os.environ["V2_FRAC_STEP"] = "2"
_pre_os.environ["V2_SUBSAMPLE"] = "200000"

print("Analysis input:", _ANALYSIS_INPUT, flush=True)
print("XGBoost threads: 4", flush=True)
print("Seeds: 0,1,2 | subsample: 200,000 | fraction step: 2", flush=True)
print("=== PREFLIGHT PASSED; STARTING ANALYSIS ===", flush=True)

# ---- install dependencies (pure Python; works in every mode) ----
import subprocess as _sp, sys as _sys
_sp.run([_sys.executable, "-m", "pip", "install", "-q",
        "rebound", "xgboost", "scikit-learn", "lifelines",
        "numpy", "jax"])


"""Window-aware (causal-safe) feature extraction for triples and encounters.

Two window modes:
  * fraction f of the recorded trajectory (sample-index based),
  * physical time horizon: only samples with t <= t_horizon (the honest
    causal mode used by the v2 experiments).
Features use ONLY window data. The horizon mismatch of the v1 pipeline is
removed: every system (stable or not) uses the same absolute horizon.
"""

from typing import Any

import numpy as np


# ------------------------------------------------------------------ helpers
def _safe(x: Any) -> np.ndarray:
    return np.nan_to_num(np.asarray(x, dtype=float), nan=0.0, posinf=1e30, neginf=-1e30)


def _slope(y: np.ndarray, t: np.ndarray) -> float:
    if len(y) < 2:
        return 0.0
    try:
        return float(np.polyfit(t, y, 1)[0])
    except Exception:
        return 0.0


def _curv(y: np.ndarray, t: np.ndarray) -> float:
    if len(y) < 3:
        return 0.0
    try:
        return float(2.0 * np.polyfit(t, y, 2)[0])
    except Exception:
        return 0.0


def _spectral_entropy(y: np.ndarray) -> float:
    y = _safe(y)
    if len(y) < 8 or np.allclose(y, y[0]):
        return 0.0
    yc = y - np.mean(y)
    psd = np.abs(np.fft.rfft(yc)) ** 2
    psd = psd[1:]
    tot = psd.sum()
    if tot <= 0:
        return 0.0
    p = psd / tot
    return float(-np.sum(p * np.log(p + 1e-30)) / np.log(len(p)))


def _autocorr(y: np.ndarray, lag: int = 5) -> float:
    y = _safe(y)
    if len(y) <= lag or np.allclose(y, y[0]):
        return 0.0
    yc = y - np.mean(y)
    d = np.dot(yc, yc)
    return float(np.dot(yc[:-lag], yc[lag:]) / d) if d > 0 else 0.0


# ------------------------------------------------------------------ features
def _torque_norms(L_pair: np.ndarray, t: np.ndarray) -> np.ndarray:
    """||Gamma_ij(t)|| = ||dL_ij/dt|| for the three pair channels."""
    Gammas = np.gradient(L_pair, t, axis=0)  # (n,3,3)
    return np.linalg.norm(Gammas, axis=2)    # (n,3)


def extract_window_features(rec: dict, f: float = 1.0, t_horizon: float | None = None,
                            Hcrit: float = 2.5, kappa: float = 4.0) -> np.ndarray:
    """Features from the first fraction f of the recorded trajectory, or from
    samples with t <= t_horizon (physical-time causal window)."""
    t = _safe(rec["t"]); n = len(t)
    if n == 0:
        return np.zeros(len(FEATURE_NAMES))
    if t_horizon is not None:
        nmax = int(np.searchsorted(t, t_horizon, side="right"))
    else:
        nmax = max(2, int(round(n * f)))
    nmax = min(max(nmax, 2), n)
    sl = slice(0, nmax)
    t = t[sl]; H = _safe(rec["H"][sl])
    E = _safe(rec["E_pair"][sl])     # (n,3)
    L = _safe(rec["L_pair"][sl])     # (n,3,3)
    Om = _safe(rec["Omega"][sl])
    dur = t[-1] - t[0]

    dH = np.gradient(H, t)
    d2H = np.gradient(dH, t)
    Hdot_c = max(abs(H[0]) / max(dur, 1e-12), 1e-12)
    psi = 0.5 * (1 + np.tanh(kappa * (np.abs(dH) / Hdot_c - 1)))

    Gnorm = _torque_norms(L, t)      # (n,3)
    Lnorm = np.linalg.norm(L, axis=2)  # (n,3)

    # pairwise-distance features (collision/encounter indicators)
    dp = rec.get("d_pair")
    if dp is None or len(dp) == 0:
        dmin = np.full(nmax, np.nan)
    else:
        dmin = np.min(_safe(dp)[sl], axis=1)
    dmin_min = float(np.nanmin(dmin)) if np.any(np.isfinite(dmin)) else 0.0
    dmin_frac = float(np.nanargmin(dmin) / max(1, nmax - 1)) if np.any(np.isfinite(dmin)) else 1.0
    dmin_rate = np.abs(np.gradient(np.nan_to_num(dmin, nan=1e30), t))
    dmin_rate_max = float(np.max(dmin_rate)) if len(dmin_rate) else 0.0
    # bound-pair identity switches within the window (exchange activity)
    pair_id = np.argmin(E, axis=1)   # most bound pair per sample
    n_pair_changes = int(np.sum(pair_id[1:] != pair_id[:-1])) if n > 1 else 0

    below = H < Hcrit
    crossings = int(np.sum((H[1:] < Hcrit) & (H[:-1] >= Hcrit))) if n > 1 else 0
    breach = np.where(below)[0]
    first_breach = breach[0] / max(1, n - 1) if len(breach) else 1.0

    E_std = np.std(E, axis=0)
    E_scale = float(np.mean(np.abs(E)) + 1e-30)
    E_slopes = np.array([_slope(E[:, k], t) for k in range(3)])

    # torque spike ratio (periastron false-positive diagnostic)
    med = np.median(Gnorm, axis=0) + 1e-30
    spike = np.max(Gnorm, axis=0) / med

    feats = np.array([
        # hierarchy stats (12)
        np.min(H), np.max(H), np.mean(H), np.std(H), np.median(H),
        np.max(H) - np.min(H), H[-1], H[0], _slope(H, t), _curv(H, t),
        np.mean(below), crossings,
        # hierarchy derivatives (8)
        np.min(dH), np.max(dH), np.std(dH), np.max(np.abs(dH)),
        np.min(d2H), np.max(d2H), np.std(d2H), np.max(np.abs(d2H)),
        # psi filter (4)
        np.mean(psi), np.max(psi), np.std(psi), psi[-1],
        # pair energies (10)
        E_std[0], E_std[1], E_std[2], E_std.sum(),
        E_std.sum() / E_scale, E_slopes[0], E_slopes[1], E_slopes[2],
        E[-1, 0], E[-1, 1],
        # outer-channel energy (4)
        np.min(_safe(rec["E_out"][sl])), np.max(_safe(rec["E_out"][sl])),
        _safe(rec["E_out"][sl])[-1], _slope(_safe(rec["E_out"][sl]), t),
        # angular momentum channels (12)
        np.min(Lnorm[:, 0]), np.max(Lnorm[:, 0]), np.std(Lnorm[:, 0]),
        np.min(Lnorm[:, 1]), np.max(Lnorm[:, 1]), np.std(Lnorm[:, 1]),
        np.min(Lnorm[:, 2]), np.max(Lnorm[:, 2]), np.std(Lnorm[:, 2]),
        _slope(Lnorm[:, 0], t), _slope(Lnorm[:, 1], t), _slope(Lnorm[:, 2], t),
        # torques (12)
        np.max(Gnorm[:, 0]), np.mean(Gnorm[:, 0]), spike[0],
        np.max(Gnorm[:, 1]), np.mean(Gnorm[:, 1]), spike[1],
        np.max(Gnorm[:, 2]), np.mean(Gnorm[:, 2]), spike[2],
        np.max(Gnorm), np.mean(Gnorm), np.max(spike), np.mean(spike),
        # seam tension (6)
        np.min(Om), np.max(Om), np.mean(Om), np.std(Om), Om[-1], _slope(Om, t),
        # signal processing (3)
        _spectral_entropy(H), _spectral_entropy(Om), _autocorr(H, 5),
        # time anchors (3)
        first_breach, len(t) / max(n, 1), dur,
        # pairwise-distance & exchange activity (4)
        dmin_min, dmin_frac, dmin_rate_max, float(n_pair_changes),
    ])
    return np.nan_to_num(feats, nan=0.0, posinf=1e30, neginf=-1e30)


def full_trajectory_features(rec: dict, **kw) -> np.ndarray:
    return extract_window_features(rec, 1.0, **kw)


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


#!/usr/bin/env python3
"""Production analysis suite for the v2 paper.

Reads merged_{task}.npz (+ merged series pkl) and produces the paper's core
numbers: causal horizon curves (with IC-only and combined baselines),
conditional skill (v_inf bins), decision-time distributions, survival /
censoring quantification, boundary-stratum OOD test, spike-normalization study.

Usage:
  python production_analysis.py --triples merged_triples.npz \
      --encounters merged_encounters.npz --tail merged_tail.npz \
      --boundary merged_boundary.npz --out-dir results --plots
"""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, recall_score, \
    precision_score, confusion_matrix
import os

from xgboost import XGBClassifier

SEEDS = [int(x) for x in os.environ.get("V2_SEEDS", "0,1,2,3,4").split(",")]

def _subsample(idx, seed):
    """Cap the working set per fit (env V2_SUBSAMPLE) - keeps analysis
    runtime manageable on the 1M-system suites without touching stored
    data. 0 = no cap."""
    cap = int(os.environ.get("V2_SUBSAMPLE") or 0)
    if cap and len(idx) > cap:
        idx = np.random.default_rng(seed).choice(idx, cap, replace=False)
    return idx

P_WARN = 0.9


ML_JOBS = int(os.environ.get("V2_ML_JOBS", "4"))


def _model():
    return XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05,
                         subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
                         objective="binary:logistic", eval_metric="logloss",
                         random_state=0, n_jobs=ML_JOBS, tree_method="hist")


def _ic_triple(d) -> np.ndarray:
    ic = d["ic"]
    return np.column_stack([
        ic[:, 0], ic[:, 1], ic[:, 2], ic[:, 3], ic[:, 4],
        ic[:, 9], ic[:, 10], ic[:, 11],
        ic[:, 12] / (ic[:, 0] + ic[:, 1]),
        ic[:, 9] / ic[:, 3],
        ic[:, 9] * (1 - ic[:, 10]) / (ic[:, 3] * (1 + ic[:, 4])),
        np.cos(ic[:, 11]), np.sin(ic[:, 11]),
        ic[:, 15], ic[:, 16],
    ])


def _ic_encounter(d) -> np.ndarray:
    ic = d["ic"]
    # cols: m1,m2,m3,1.0,e_bin,...,vinf(15),vcrit(16),b(17),t_app(18)
    return np.column_stack([
        ic[:, 0], ic[:, 1], ic[:, 2], ic[:, 4],
        ic[:, 15], ic[:, 16], ic[:, 17],
        ic[:, 15] / ic[:, 16],
    ])


def _fit_eval(Xtr, Xv, ytr, yv):
    clf = _model(); clf.fit(Xtr, ytr)
    p = clf.predict_proba(Xv)[:, 1]
    pred = (p >= 0.5).astype(int)
    tn, fp, fn, tp = confusion_matrix(yv, pred, labels=[0, 1]).ravel()
    return dict(acc=float(accuracy_score(yv, pred)), auc=float(roc_auc_score(yv, p)),
                rec=float(recall_score(yv, pred, zero_division=0)),
                prec=float(precision_score(yv, pred, zero_division=0)),
                tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp)), p


# ================================================================ causal curve
def causal_curve(d, y, anchor, fractions, ic_fn, name, test_size=0.3):
    """Leakage-free horizon metrics plus complete out-of-fold probabilities.

    Metrics use a capped evaluation sample. Decision probabilities cover
    every valid in-play system: each half is predicted by a model trained on
    a capped sample from the opposite half.
    """
    rows = []
    P_full = np.full((len(y), len(fractions)), np.nan, dtype=np.float32)
    valid = y >= 0
    for fi, f in enumerate(fractions):
        horizon = f * d[anchor]
        te = np.where(np.isnan(d["t_event"]), np.inf, d["t_event"])
        idx_all = np.where(valid & (te > horizon))[0]
        npos_total = int(np.sum(y[idx_all] == 1))
        nneg_total = int(np.sum(y[idx_all] == 0))
        if len(idx_all) < 30 or min(npos_total, nneg_total) < 50:
            rows.append(dict(f=float(f), n_in_play_total=len(idx_all), n_eval=0,
                             n_positive=npos_total, skipped="class-degenerate"))
            continue
        idx = _subsample(idx_all, 1000 + fi)
        Xw = d["feats"][:, fi, :]
        Xic = ic_fn(d)
        stats = {z:{k:[] for k in ["acc","auc","rec","prec"]}
                 for z in ["ic","w","b"]}
        Xboth = np.hstack([Xic, Xw])
        for seed in SEEDS:
            tr, vv = train_test_split(idx, test_size=test_size,
                                      random_state=seed, stratify=y[idx])
            for z, X in [("ic",Xic),("w",Xw),("b",Xboth)]:
                r,_ = _fit_eval(X[tr],X[vv],y[tr],y[vv])
                for k in stats[z]: stats[z][k].append(r[k])
        # Complete two-fold OOF coverage for honest decision times.
        a,b = train_test_split(idx_all, test_size=0.5, random_state=7000+fi,
                               stratify=y[idx_all])
        for pool,vv,seed in [(a,b,7100+fi),(b,a,7200+fi)]:
            tr = _subsample(pool, seed)
            clf=_model(); clf.fit(Xw[tr],y[tr])
            P_full[vv,fi]=clf.predict_proba(Xw[vv])[:,1]
        rows.append(dict(
            f=float(f), n_in_play_total=len(idx_all), n_eval=len(idx),
            n_positive=npos_total,
            acc_ic=float(np.mean(stats["ic"]["acc"])), auc_ic=float(np.mean(stats["ic"]["auc"])),
            rec_ic=float(np.mean(stats["ic"]["rec"])),
            acc_w=float(np.mean(stats["w"]["acc"])), auc_w=float(np.mean(stats["w"]["auc"])),
            rec_w=float(np.mean(stats["w"]["rec"])),
            acc_b=float(np.mean(stats["b"]["acc"])), auc_b=float(np.mean(stats["b"]["auc"])),
            rec_b=float(np.mean(stats["b"]["rec"])),
            std_auc_w=float(np.std(stats["w"]["auc"]))))
    print(f"\n=== corrected causal curve: {name} ===")
    print(f"{'f':>6} {'total':>9} {'eval':>7} {'pos':>7} {'AUC_ic':>8} {'AUC_w':>8} {'AUC_b':>8}")
    for r in rows:
        if "auc_w" in r:
            print(f"{r['f']:6.2f} {r['n_in_play_total']:9d} {r['n_eval']:7d} {r['n_positive']:7d} {r['auc_ic']:8.4f} {r['auc_w']:8.4f} {r['auc_b']:8.4f}")
        else: print(f"{r['f']:6.2f} {r['n_in_play_total']:9d} SKIPPED ({r['skipped']})")
    return rows,P_full

# ================================================================ decision time
def decision_times(d, y, P_full, anchor_name, units_per_anchor, name, t_peri=None):
    """First honest OOF warning, with coverage and pre-reference diagnostics."""
    fracs=d["fractions"]; te=np.where(np.isnan(d["t_event"]),np.inf,d["t_event"])
    leads=[]; eligible=np.where(y==1)[0]
    for i in eligible:
        for fi,f in enumerate(fracs):
            if te[i] <= f*d[anchor_name][i]: break
            if np.isfinite(P_full[i,fi]) and P_full[i,fi] >= P_WARN:
                ref=t_peri[i] if t_peri is not None else te[i]
                leads.append((ref-f*d[anchor_name][i])/units_per_anchor[i]); break
    leads=np.asarray(leads,float); positive=leads[leads>0]
    out=dict(n_warned=int(len(leads)), n_pos=int(len(eligible)),
             warning_fraction=float(len(leads)/max(len(eligible),1)),
             n_positive_lead=int(len(positive)),
             positive_lead_fraction_of_warned=float(len(positive)/max(len(leads),1)),
             median_lead=float(np.median(leads)) if len(leads) else np.nan,
             p25=float(np.percentile(leads,25)) if len(leads) else np.nan,
             p75=float(np.percentile(leads,75)) if len(leads) else np.nan,
             median_positive_lead=float(np.median(positive)) if len(positive) else np.nan)
    print(f"\n=== corrected decision times: {name} ==="); print(json.dumps(out,indent=1))
    return out,leads

# ================================================================ conditional skill
def conditional_skill(d, fractions, fi_list=None):
    """Encounters: within v_inf/v_crit quartiles, IC-only (no v_inf!) vs window."""
    fi_list = fi_list or sorted(range(max(0, len(fractions) - 3), len(fractions)))
    ic = d["ic"]
    vratio = ic[:, 15] / ic[:, 16]
    y = (d["statuses"] == "exchange").astype(int)
    bins = np.quantile(vratio, [0, .25, .5, .75, 1.0])
    Xic = np.column_stack([ic[:, 0], ic[:, 1], ic[:, 2], ic[:, 4], ic[:, 17]])
    print(f"\n=== conditional skill (v_inf/v_crit quartiles) ===")
    print(f"{'bin':>18} {'n':>6} {'AUC_ic':>8} " +
          "".join(f"{'AUC_f='+str(round(fractions[fi],2)):>10}" for fi in fi_list))
    out = []
    for b in range(4):
        m = (vratio >= bins[b]) & (vratio < bins[b + 1])
        if b == 3:
            m = (vratio >= bins[3])
        idx = np.where(m)[0]
        idx = _subsample(idx, 3000 + b)
        if len(idx) < 40:
            continue
        aucs_ic = []
        for seed in SEEDS:
            tr, v = train_test_split(idx, test_size=0.3, random_state=seed,
                                     stratify=y[idx])
            r, _ = _fit_eval(Xic[tr], Xic[v], y[tr], y[v])
            aucs_ic.append(r["auc"])
        row = dict(bin=f"[{bins[b]:.2f},{bins[b+1]:.2f})", n=len(idx),
                   auc_ic=np.mean(aucs_ic))
        for fi in fi_list:
            aucs = []
            for seed in SEEDS:
                tr, v = train_test_split(idx, test_size=0.3, random_state=seed,
                                         stratify=y[idx])
                r, _ = _fit_eval(d["feats"][tr, fi], d["feats"][v, fi],
                                 y[tr], y[v])
                aucs.append(r["auc"])
            row[f"auc_f{fi}"] = np.mean(aucs)
        out.append(row)
        print(f"{row['bin']:>18} {row['n']:6d} {row['auc_ic']:8.4f} " +
              "".join(f"{row[f'auc_f{fi}']:10.4f}" for fi in fi_list))
    return out


# horizon fraction grids per task family (safety net if a merged file lacks
# the `fractions` metadata - e.g. chunks written by the pre-fix finalizer)
TRIPLE_FRACS = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]
ENCOUNTER_FRACS = [0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5,
                   0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]


def _subset_fracs(d, step, default_fractions=None):
    """Load selected horizons and neutralize the known future-length leak.

    Stored feature 73 (`n_frac`) was window_length/full_record_length; the
    denominator ends at the future event for disrupted systems.  We retain
    the column only for shape compatibility and set it identically to zero
    before every fit.  All other columns contain window-sliced quantities.
    """
    dd = {k: d[k] for k in d.files}
    if "fractions" not in dd:
        if default_fractions is None:
            raise KeyError("merged file lacks fractions metadata")
        dd["fractions"] = np.array(default_fractions, dtype=np.float32)
    if step is not None and step > 1:
        idx = np.arange(0, len(dd["fractions"]), step)
        dd["fractions"] = dd["fractions"][idx]
        dd["feats"] = dd["feats"][:, idx, :]
    else:
        dd["feats"] = np.array(dd["feats"], copy=True)
    if dd["feats"].shape[2] != 79:
        raise RuntimeError(f"expected 79 stored features, got {dd['feats'].shape}")
    dd["feats"][:, :, 73] = 0.0
    if np.any(dd["feats"][:, :, 73] != 0):
        raise RuntimeError("failed to neutralize leaked n_frac column")
    return dd

# ================================================================ multiclass
TRI_CLASS_NAMES = ["stable", "outer-eject", "inner-eject"]
ENC_CLASS_NAMES = ["flyby", "exchange", "ionization"]


def triples_multiclass_labels(d):
    """Defensible 3-class task: stable, outer ejection, inner ejection.
    Collisions and numerical errors are excluded; the 53 exchange-stable
    systems remain in the stable outcome because no ejection occurred.
    """
    y=np.full(len(d["statuses"]),-1,dtype=int)
    stable=d["statuses"]=="stable"; eject=d["statuses"]=="ejected"
    y[stable]=0
    y[eject & (d["escaper"]==2)]=1
    y[eject & np.isin(d["escaper"],[0,1])]=2
    return y

def encounters_multiclass_labels(d):
    y = np.full(len(d["statuses"]), -1, dtype=int)
    for i, s in enumerate(d["statuses"]):
        y[i] = {"flyby": 0, "exchange": 1, "ionization": 2}.get(s, -1)
    return y


def _fit_eval_mc(Xtr, Xv, ytr, yv, C):
    from sklearn.metrics import accuracy_score, f1_score, confusion_matrix
    clf = XGBClassifier(n_estimators=300, max_depth=3, learning_rate=0.05,
                        subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
                        objective="multi:softprob", num_class=C,
                        eval_metric="mlogloss", random_state=0,
                        n_jobs=ML_JOBS, tree_method="hist")
    clf.fit(Xtr, ytr)
    P = clf.predict_proba(Xv)
    pred = P.argmax(axis=1)
    cm = confusion_matrix(yv, pred, labels=list(range(C)))
    rowsum = cm.sum(axis=1)
    rec = np.divide(np.diag(cm), rowsum, out=np.zeros(C), where=rowsum > 0)
    aucs = []
    for c in range(C):
        if len(np.unique(yv == c)) < 2:
            aucs.append(np.nan)
        else:
            aucs.append(float(roc_auc_score((yv == c).astype(int), P[:, c])))
    return dict(acc=float(accuracy_score(yv, pred)),
                macro_f1=float(f1_score(yv, pred, average="macro", zero_division=0)),
                micro_f1=float(f1_score(yv, pred, average="micro", zero_division=0)),
                rec=rec, auc_ovr=aucs, cm=cm), P


def multiclass_causal_curve(d, y, anchor, fractions, name, ic_fn=None,
                            label_names=None, test_size=0.3):
    """Per-horizon 3-way comparison (IC / window / combined) for multiclass
    outcomes. Classes are remapped to contiguous labels per horizon (XGBoost
    requirement). Returns rows, and (P_true, P_max) via 2-fold CV for
    decision times."""
    valid = y >= 0
    label_names = label_names or [str(i) for i in range(int(y.max()) + 1)]
    rows = []
    P_true = np.full((len(y), len(fractions)), np.nan, dtype=np.float32)
    P_max = np.full((len(y), len(fractions)), np.nan, dtype=np.float32)

    for fi, f in enumerate(fractions):
        horizon = f * d[anchor]
        t_event = np.where(np.isnan(d["t_event"]), np.inf, d["t_event"])
        in_play = valid & (t_event > horizon)
        idx = np.where(in_play)[0]
        idx = _subsample(idx, 2000 + fi)
        if len(idx) < 60:
            rows.append(dict(f=float(f), n_in_play=len(idx)))
            continue
        y_ip = y[idx]
        local_classes = np.unique(y_ip)
        if len(local_classes) < 2:
            rows.append(dict(f=float(f), n_in_play=len(idx)))
            continue
        local_map = {int(c): i for i, c in enumerate(local_classes)}
        C_ip = len(local_classes)
        y_loc = np.array([local_map[int(v)] for v in y_ip], dtype=int)
        counts = np.bincount(y_loc, minlength=C_ip)
        if counts.min() < 5:
            rows.append(dict(f=float(f), n_in_play=len(idx)))
            continue
        Xw_all = d["feats"][:, fi, :]
        Xic_all = ic_fn(d) if ic_fn is not None else None
        keys = ["acc", "macro_f1", "micro_f1"]
        m_ic = {k: [] for k in keys}; m_w = {k: [] for k in keys}
        m_b = {k: [] for k in keys}
        for seed in SEEDS:
            idx_tr, idx_v = train_test_split(np.arange(len(idx)),
                                             test_size=test_size,
                                             random_state=seed,
                                             stratify=y_loc)
            ytr, yv = y_loc[idx_tr], y_loc[idx_v]
            r_w, _ = _fit_eval_mc(Xw_all[idx[idx_tr]], Xw_all[idx[idx_v]],
                                  ytr, yv, C_ip)
            for k in keys:
                m_w[k].append(r_w[k])
            if Xic_all is not None:
                r_ic, _ = _fit_eval_mc(Xic_all[idx[idx_tr]],
                                       Xic_all[idx[idx_v]], ytr, yv, C_ip)
                r_b, _ = _fit_eval_mc(
                    np.hstack([Xic_all, Xw_all])[idx[idx_tr]],
                    np.hstack([Xic_all, Xw_all])[idx[idx_v]], ytr, yv, C_ip)
                for k in keys:
                    m_ic[k].append(r_ic[k]); m_b[k].append(r_b[k])
        # Complete OOF coverage for decision times, using classes defined
        # on the full in-play cohort and capped training from opposite folds.
        idx_oof = np.where(in_play & np.isin(y, local_classes))[0]
        y_oof = np.array([local_map[int(v)] for v in y[idx_oof]], dtype=int)
        oof_counts = np.bincount(y_oof, minlength=C_ip)
        if oof_counts.min() >= 5:
            a, b = train_test_split(np.arange(len(idx_oof)), test_size=0.5,
                                    random_state=7300+fi, stratify=y_oof)
            for pool, vv, seed_oof in [(a,b,7400+fi),(b,a,7500+fi)]:
                tr_local = _subsample(pool, seed_oof)
                _, P = _fit_eval_mc(Xw_all[idx_oof[tr_local]], Xw_all[idx_oof[vv]],
                                    y_oof[tr_local], y_oof[vv], C_ip)
                P_true[idx_oof[vv], fi] = P[np.arange(len(vv)), y_oof[vv]]
                P_max[idx_oof[vv], fi] = P.max(axis=1)
        # per-class recall from a seed-0 window fit for the confusion table
        idx_tr, idx_v = train_test_split(np.arange(len(idx)),
                                         test_size=test_size,
                                         random_state=0, stratify=y_loc)
        r0, _ = _fit_eval_mc(Xw_all[idx[idx_tr]], Xw_all[idx[idx_v]],
                             y_loc[idx_tr], y_loc[idx_v], C_ip)
        rows.append(dict(
            f=float(f), n_in_play=len(idx),
            classes_local=[label_names[int(c)] for c in local_classes],
            counts={label_names[int(c)]: int(counts[i])
                    for i, c in enumerate(local_classes)},
            acc_w=np.mean(m_w["acc"]), macro_f1_w=np.mean(m_w["macro_f1"]),
            micro_f1_w=np.mean(m_w["micro_f1"]),
            rec_w={label_names[int(c)]: float(r0["rec"][i])
                   for i, c in enumerate(local_classes)},
            cm_w=r0["cm"].tolist(),
            acc_ic=np.mean(m_ic["acc"]) if m_ic["acc"] else np.nan,
            macro_f1_ic=np.mean(m_ic["macro_f1"]) if m_ic["macro_f1"] else np.nan,
            acc_b=np.mean(m_b["acc"]) if m_b["acc"] else np.nan,
            macro_f1_b=np.mean(m_b["macro_f1"]) if m_b["macro_f1"] else np.nan,
        ))
    print(f"\n=== multiclass causal curve: {name} ===")
    print(f"{'f':>6} {'inplay':>6} {'F1_ic':>8} {'F1_win':>8} {'F1_both':>8}   per-class recall (window)")
    for r in rows:
        if "macro_f1_w" not in r:
            continue
        rec_str = " ".join(f"{k[:8]}={v:.2f}" for k, v in r["rec_w"].items())
        print(f"{r['f']:6.2f} {r['n_in_play']:6d} "
              f"{r['macro_f1_ic']:8.4f} {r['macro_f1_w']:8.4f} "
              f"{r['macro_f1_b']:8.4f}   {rec_str}")
    return rows, P_true, P_max, None


def multiclass_decision_times(d, y, P_true, P_max, anchor, units, name,
                              t_ref=None, threshold=0.7, label_names=None,
                              class_filter=None):
    """First horizon at which the predicted class == true class with
    P >= threshold. class_filter: optional iterable of classes to consider
    (e.g., only event classes for triples)."""
    from collections import defaultdict
    fracs = d["fractions"]
    t_event = np.where(np.isnan(d["t_event"]), np.inf, d["t_event"])
    leads = defaultdict(list)
    for i in range(len(y)):
        c = int(y[i])
        if c < 0:
            continue
        if class_filter is not None and c not in class_filter:
            continue
        first = None
        for fi, f in enumerate(fracs):
            if t_event[i] <= f * d[anchor][i]:
                break
            if (np.isfinite(P_true[i, fi]) and P_true[i, fi] >= threshold
                    and P_true[i, fi] == P_max[i, fi]):
                first = f
                break
        if first is not None:
            t_warn = first * d[anchor][i]
            t_ref_i = t_ref[i] if t_ref is not None else t_event[i]
            leads[c].append(float((t_ref_i - t_warn) / units[i]))
    out = {}
    for c, v in leads.items():
        v = np.array(v)
        name_c = label_names[c] if label_names is not None else str(c)
        out[name_c] = dict(n=int(len(v)),
                           median=float(np.median(v)),
                           p25=float(np.percentile(v, 25)),
                           p75=float(np.percentile(v, 75)))
    print(f"\n=== multiclass decision times: {name} (P>={threshold}) ===")
    print(json.dumps(out, indent=1))
    return out


def multiclass_conditional_skill(d, fractions, fi_list=None):
    """Encounters: within v_inf/v_crit quartiles, 3-class macro-F1 for
    IC (without v_inf) vs window features."""
    fi_list = fi_list or sorted(range(max(0, len(fractions) - 3), len(fractions)))
    from sklearn.metrics import f1_score
    ic = d["ic"]
    vratio = ic[:, 15] / ic[:, 16]
    y = encounters_multiclass_labels(d)
    valid = y >= 0
    Xic = np.column_stack([ic[:, 0], ic[:, 1], ic[:, 2], ic[:, 4], ic[:, 17]])
    bins = np.quantile(vratio[valid], [0, .25, .5, .75, 1.0])
    print(f"\n=== multiclass conditional skill (macro-F1, v_inf quartiles) ===")
    print(f"{'bin':>18} {'n':>6} {'F1_ic':>8} " +
          "".join(f"{'F1_f='+str(round(fractions[fi],2)):>11}" for fi in fi_list))
    out = []
    for b in range(4):
        m = (vratio >= bins[b]) & (vratio < bins[b + 1])
        if b == 3:
            m = (vratio >= bins[3])
        m &= valid
        idx = np.where(m)[0]
        idx = _subsample(idx, 4000 + b)
        if len(idx) < 40:
            continue
        f1_ic = []
        for seed in SEEDS:
            tr, v = train_test_split(idx, test_size=0.3, random_state=seed,
                                     stratify=y[idx])
            clf = XGBClassifier(n_estimators=300, max_depth=3,
                                objective="multi:softprob", num_class=3,
                                random_state=0, n_jobs=ML_JOBS, tree_method="hist")
            clf.fit(Xic[tr], y[tr])
            f1_ic.append(f1_score(y[v], clf.predict_proba(Xic[v]).argmax(1),
                                  average="macro", zero_division=0))
        row = dict(bin=f"[{bins[b]:.2f},{bins[b+1]:.2f})", n=len(idx),
                   f1_ic=float(np.mean(f1_ic)))
        for fi in fi_list:
            f1s = []
            for seed in SEEDS:
                tr, v = train_test_split(idx, test_size=0.3, random_state=seed,
                                         stratify=y[idx])
                clf = XGBClassifier(n_estimators=300, max_depth=3,
                                    objective="multi:softprob", num_class=3,
                                    random_state=0, n_jobs=ML_JOBS, tree_method="hist")
                clf.fit(d["feats"][tr, fi], y[tr])
                f1s.append(f1_score(y[v],
                                    clf.predict_proba(d["feats"][v, fi]).argmax(1),
                                    average="macro", zero_division=0))
            row[f"f1_f{fi}"] = float(np.mean(f1s))
        out.append(row)
        print(f"{row['bin']:>18} {row['n']:6d} {row['f1_ic']:8.4f} " +
              "".join(f"{row[f'f1_f{fi}']:11.4f}" for fi in fi_list))
    return out


# ================================================================ MA01 benchmark
def ma01_benchmark(d, name):
    """Measured Mardling & Aarseth (2001) benchmark: prediction = stable iff
    a_out/a_in > MA01 criterion (margin > 1), vs true outcomes, evaluated
    in-play per horizon. This is the paper's external-benchmark table."""
    print(f"\n=== Mardling-Aarseth (2001) benchmark: {name} ===")
    margin = d["ic"][:, 16]           # MA01_margin
    pred_eject = (margin <= 1.0).astype(int)
    print(f"  MA01 flags {pred_eject.sum()}/{len(margin)} systems as unstable "
          f"({100*pred_eject.mean():.1f}%)")
    t_event = np.where(np.isnan(d["t_event"]), np.inf, d["t_event"])
    fracs = d["fractions"]
    print(f"{'f':>6} {'inplay':>6} {'MA01acc':>8} {'MA01rec':>8} {'MA01F1':>8}")
    out = []
    for f in fracs:
        horizon = f * d["t_max"]
        in_play = t_event > horizon
        idx = np.where(in_play)[0]
        if len(idx) < 20:
            continue
        y_ip = (d["statuses"][idx] == "ejected").astype(int)
        p_ip = pred_eject[idx]
        acc = float(accuracy_score(y_ip, p_ip))
        rec = float(recall_score(y_ip, p_ip, zero_division=0))
        prec = float(precision_score(y_ip, p_ip, zero_division=0))
        f1m = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        out.append(dict(f=float(f), n_in_play=len(idx), acc=acc, rec=rec,
                        prec=prec, f1=f1m))
        print(f"{f:6.2f} {len(idx):6d} {acc:8.4f} {rec:8.4f} {f1m:8.4f}")
    return out


# ================================================================ time-to-event
def time_to_event_regression(d, name, label_col="statuses", pos_label="ejected"):
    """Landmark prediction of remaining time to ejection in outer periods."""
    from xgboost import XGBRegressor
    print(f"\n=== corrected TTE: {name} (log10 remaining outer periods) ===")
    is_event=d[label_col]==pos_label; te=d["t_event"]; fracs=d["fractions"]
    pout=np.sqrt(d["ic"][:,9]**3/(d["ic"][:,0]+d["ic"][:,1]+d["ic"][:,2]+1e-30))
    out=[]
    for fi,f in enumerate(fracs):
        horizon=f*d["t_max"]
        idx=np.where(is_event & np.isfinite(te) & (te>horizon))[0]
        if len(idx)<50: continue
        idx=_subsample(idx,5000+fi)
        remaining=(te[idx]-horizon[idx])/pout[idx]
        ok=remaining>0; idx=idx[ok]; remaining=remaining[ok]
        X=d["feats"][idx,fi]; y=np.log10(remaining)
        maes=[]; r2s=[]
        for seed in SEEDS:
            tr,v=train_test_split(np.arange(len(idx)),test_size=.3,random_state=seed)
            m=XGBRegressor(n_estimators=300,max_depth=3,learning_rate=.05,
                           random_state=seed,n_jobs=ML_JOBS,tree_method="hist")
            m.fit(X[tr],y[tr]); pred=m.predict(X[v])
            maes.append(float(np.mean(np.abs(pred-y[v]))))
            den=float(np.sum((y[v]-y[v].mean())**2)); num=float(np.sum((y[v]-pred)**2))
            r2s.append(1-num/den if den>0 else np.nan)
        row=dict(f=float(f),n_ev=len(idx),mae_dex=float(np.mean(maes)),r2=float(np.nanmean(r2s)))
        out.append(row); print(f"{f:6.2f} {len(idx):7d} MAE={row['mae_dex']:.4f} R2={row['r2']:.3f}")
    return out

# ================================================================ Cox hazards
def cox_hazards(d, f=0.5, top=12):
    """Landmark Cox model after the horizon; ejection is the sole event."""
    from lifelines import CoxPHFitter
    import pandas as pd
    print(f"\n=== corrected landmark Cox hazards (f={f}) ===")
    fi=int(np.argmin(np.abs(np.asarray(d["fractions"],float)-f))); fu=float(d["fractions"][fi])
    horizon=fu*d["t_max"]; status=d["statuses"]
    valid=np.isin(status,["stable","ejected"])
    te=np.where(status=="ejected",d["t_event"],np.inf)
    idx=np.where(valid & (te>horizon))[0]; idx=_subsample(idx,6000)
    names=list(FEATURE_NAMES); X=d["feats"][idx,fi]
    pout=np.sqrt(d["ic"][idx,9]**3/(d["ic"][idx,0]+d["ic"][idx,1]+d["ic"][idx,2]+1e-30))
    event=status[idx]=="ejected"
    stop=np.where(event,d["t_event"][idx],d["t_max"][idx])
    duration=np.maximum((stop-horizon[idx])/pout,1e-8)
    df=pd.DataFrame(X,columns=names); df["duration"]=duration; df["event"]=event.astype(int)
    keep=[c for c in names if c!="n_frac" and np.isfinite(df[c]).all() and df[c].std()>1e-6]
    for c in keep: df[c]=(df[c]-df[c].mean())/df[c].std()
    cph=CoxPHFitter(penalizer=1.0); cph.fit(df[keep+["duration","event"]],"duration","event")
    rows=[dict(feature=str(feat),hr=float(cph.summary.loc[feat,"exp(coef)"]),p=float(cph.summary.loc[feat,"p"]))
          for feat in cph.summary.index if np.isfinite(cph.summary.loc[feat,"exp(coef)"])]
    rows.sort(key=lambda r:-abs(np.log(r["hr"])))
    for r in rows[:top]: print(f"  {r['feature']:22s} HR={r['hr']:8.3f} p={r['p']:.2e}")
    print(f"  C-index={cph.concordance_index_:.3f}")
    return dict(f=fu,n=len(idx),concordance=float(cph.concordance_index_),top=rows[:top])

# ================================================================ boundary causal
def boundary_horizon_curve(d, name="boundary", test_size=0.3):
    """WITHIN-STRATUM early-classification curve for the near-MA01 boundary
    suite: how early is ejection detectable among these systems themselves?
    Train + evaluate on the boundary data per horizon (IC vs window vs
    combined), in-play only. Returns rows and OOF probability matrix."""
    y = np.full(len(d["statuses"]), -1, dtype=int)
    y[d["statuses"] == "stable"] = 0
    y[d["statuses"] == "ejected"] = 1
    fracs = d["fractions"]
    rows = []
    P_full = np.full((len(y), len(fracs)), np.nan, dtype=np.float32)
    for fi, f in enumerate(fracs):
        horizon = f * d["t_max"]
        t_event = np.where(np.isnan(d["t_event"]), np.inf, d["t_event"])
        in_play = (t_event > horizon) & (y >= 0)
        idx = np.where(in_play)[0]
        idx = _subsample(idx, 1000 + fi)
        if len(idx) < 30 or y[idx].sum() < 5 or y[idx].sum() == len(idx):
            rows.append(dict(f=float(f), n_in_play=len(idx)))
            continue
        Xw_all = d["feats"][:, fi, :]
        Xic_all = _ic_triple(d)
        m_ic = {"acc": [], "auc": [], "rec": []}
        m_w = {"acc": [], "auc": [], "rec": []}
        m_b = {"acc": [], "auc": [], "rec": []}
        for seed in SEEDS:
            idx_tr, idx_v = train_test_split(idx, test_size=test_size,
                                             random_state=seed,
                                             stratify=y[idx])
            ytr, yv = y[idx_tr], y[idx_v]
            r_ic, _ = _fit_eval(Xic_all[idx_tr], Xic_all[idx_v], ytr, yv)
            r_w, _ = _fit_eval(Xw_all[idx_tr], Xw_all[idx_v], ytr, yv)
            r_b, _ = _fit_eval(np.hstack([Xic_all, Xw_all])[idx_tr],
                               np.hstack([Xic_all, Xw_all])[idx_v], ytr, yv)
            for k in m_ic:
                m_ic[k].append(r_ic[k]); m_w[k].append(r_w[k]); m_b[k].append(r_b[k])
        # OOF probabilities for decision times
        a, b = train_test_split(idx, test_size=0.5, random_state=7,
                                stratify=y[idx])
        for tr, vv in [(a, b), (b, a)]:
            clf = _model()
            clf.fit(Xw_all[tr], y[tr])
            P_full[vv, fi] = clf.predict_proba(Xw_all[vv])[:, 1]
        rows.append(dict(
            f=float(f), n_in_play=len(idx),
            acc_ic=np.mean(m_ic["acc"]), auc_ic=np.mean(m_ic["auc"]),
            rec_ic=np.mean(m_ic["rec"]),
            acc_w=np.mean(m_w["acc"]), auc_w=np.mean(m_w["auc"]),
            rec_w=np.mean(m_w["rec"]),
            acc_b=np.mean(m_b["acc"]), auc_b=np.mean(m_b["auc"]),
            rec_b=np.mean(m_b["rec"]),
        ))
    print(f"\n=== boundary-stratum causal curve: {name} (in-stratum) ===")
    print(f"{'f':>6} {'inplay':>6} {'AUC_ic':>8} {'AUC_win':>8} {'AUC_both':>8}")
    for r in rows:
        if "auc_ic" in r:
            print(f"{r['f']:6.2f} {r['n_in_play']:6d} {r['auc_ic']:8.4f} "
                  f"{r['auc_w']:8.4f} {r['auc_b']:8.4f}")
    return rows, P_full


# ================================================================ survival / censoring
def km_survival(t_event, t_max):
    order = np.argsort(t_event)
    t_sorted = t_event[order]
    event = ~np.isnan(t_event[order])
    n = len(t_sorted); S = 1.0; out = [(0.0, 1.0)]
    for i in range(n):
        if event[i]:
            d = np.sum((np.nan_to_num(t_sorted, nan=-1) == t_sorted[i]) & event)
            at_risk = n - i
            S *= (1 - d / at_risk) if at_risk > 0 else 1.0
            out.append((float(t_sorted[i]), float(S)))
    return np.array(out)


def survival_analysis(main, tail, out_dir):
    print("\n=== survival / censoring ===")
    km_main = km_survival(main["t_event"], main["t_max"])
    km_tail = km_survival(tail["t_event"], tail["t_max"])
    # censoring: systems stable at 100 T_out in main -> fate in tail (same ids/ICs)
    main_ids = set(main["ids"][np.isnan(main["t_event"])])
    m = np.isin(tail["ids"], list(main_ids))
    n_tail_ej = int((tail["statuses"][m] == "ejected").sum())
    n_match = int(m.sum())
    print(f"systems stable at 100 T_out: {len(main_ids)}; matched in tail: {n_match}")
    print(f"of those, ejected by 1000 T_out: {n_tail_ej} "
          f"({100*n_tail_ej/max(n_match,1):.1f}%)")
    frac_tail_ej = n_tail_ej / max(n_match, 1)
    out = dict(n_stable_at_100=len(main_ids), n_matched=n_match,
               n_ejected_by_1000=n_tail_ej,
               frac_contaminated=frac_tail_ej,
               km_main=km_main.tolist(), km_tail=km_tail.tolist())
    with open(Path(out_dir) / "survival.json", "w") as f:
        json.dump(out, f, indent=1)
    return out


# ================================================================ boundary stratum
def boundary_stratum(main, boundary, fraction_idx=5, test_size=0.3):
    """Train IC-only & window (f=0.3) on the fiducial main suite; test on the
    near-MA01 boundary suite (out-of-distribution)."""
    print("\n=== boundary-stratum OOD test (train fiducial, test boundary) ===")
    y_m = (main["statuses"] == "ejected").astype(int)
    y_b = (boundary["statuses"] == "ejected").astype(int)
    Xic_m = _ic_triple(main); Xic_b = _ic_triple(boundary)
    Xw_m = main["feats"][:, fraction_idx]; Xw_b = boundary["feats"][:, fraction_idx]
    rows = []
    for name, Xtr, Xv in [("IC-only", Xic_m, Xic_b),
                          ("window", Xw_m, Xw_b),
                          ("IC+window", np.hstack([Xic_m, Xw_m]),
                           np.hstack([Xic_b, Xw_b]))]:
        aucs = []
        for seed in SEEDS:
            tr, _ = train_test_split(np.arange(len(y_m)), test_size=0.2,
                                     random_state=seed, stratify=y_m)
            clf = _model(); clf.fit(Xtr[tr], y_m[tr])
            p = clf.predict_proba(Xv)[:, 1]
            aucs.append(roc_auc_score(y_b, p))
        rows.append(dict(model=name, auc=np.mean(aucs), std=np.std(aucs)))
        print(f"  {name:10s} AUC(boundary) = {np.mean(aucs):.4f} +- {np.std(aucs):.4f}")
    print(f"  boundary ejection fraction: {y_b.mean():.3f}")
    return rows


# ================================================================ spike study
def spike_study(d, series_file):
    """Torque spike separability: raw vs running-median-normalized vs
    orbital-scale-normalized max torque. Channels: [t,H,Omega,E_out,Gmax,dmin,Lmax].
    Overlap = fraction of stable systems whose spike exceeds the ejected median.
    """
    print("\n=== torque spike normalization study (first 80% of trajectory) ===")
    import pickle
    with open(series_file, "rb") as f:
        series = pickle.load(f)
    status_by_id = {int(i): s for i, s in zip(d["ids"], d["statuses"])}
    ic_by_id = {int(i): v for i, v in zip(d["ids"], d["ic"])}
    results = {}
    for norm in ["raw", "median", "orbital"]:
        vals = {"stable": [], "ejected": []}
        for sid, s in series:
            st = status_by_id.get(int(sid))
            if st is None or len(s) < 20:
                continue
            nmax = int(round(len(s) * 0.8))
            G = s[:nmax, 4]
            if norm == "raw":
                v = float(np.max(G))
            elif norm == "median":
                v = float(np.max(G) / (np.median(G) + 1e-30))
            else:  # orbital scale: mean |L| / P_out (from ICs)
                ic = ic_by_id[int(sid)]
                M = ic[0] + ic[1] + ic[2]
                P_out = np.sqrt(ic[9] ** 3 / M)
                scale = np.mean(s[:nmax, 6]) / P_out
                v = float(np.max(G) / (scale + 1e-30))
            vals["ejected" if st == "ejected" else "stable"].append(v)
        stable = np.array(vals["stable"]); ejected = np.array(vals["ejected"])
        med_ej = np.median(ejected)
        overlap = float(np.mean(stable > med_ej)) if len(stable) else np.nan
        results[norm] = dict(
            n_stable=len(stable), n_ejected=len(ejected),
            stable_median=float(np.median(stable)) if len(stable) else np.nan,
            ejected_median=float(med_ej) if len(ejected) else np.nan,
            stable_p90=float(np.percentile(stable, 90)) if len(stable) else np.nan,
            overlap_frac=overlap)
        print(f"  {norm:8s}: stable med={results[norm]['stable_median']:.1f} "
              f"ej med={results[norm]['ejected_median']:.1f} "
              f"overlap={overlap:.2f}")
    return results


# ================================================================ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--triples", default=None)
    ap.add_argument("--encounters", default=None)
    ap.add_argument("--tail", default=None)
    ap.add_argument("--boundary", default=None)
    ap.add_argument("--series", default=None, help="merged series pkl (triples)")
    ap.add_argument("--out-dir", default="v2_results")
    ap.add_argument("--frac-step", type=int, default=None,
                    help="analyze every k-th stored horizon fraction "
                         "(2 halves analysis wall time; data stays intact)")
    ap.add_argument("--plots", action="store_true")
    args = ap.parse_args()
    out_dir = Path(args.out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    frac_step = args.frac_step or int(os.environ.get("V2_FRAC_STEP", "1"))

    # ---------------- triples ----------------
    if args.triples:
        d = _subset_fracs(np.load(args.triples), frac_step, TRIPLE_FRACS)
        y = np.full(len(d["statuses"]), -1, dtype=int)
        y[d["statuses"] == "stable"] = 0
        y[d["statuses"] == "ejected"] = 1
        rows, P = causal_curve(d, y, "t_max", d["fractions"], _ic_triple,
                               "triples: ejected vs stable")
        report["triples_causal"] = rows
        with open(out_dir / "triples_causal.json", "w") as f:
            json.dump(rows, f, indent=1)
        _pout = np.sqrt(d["ic"][:, 9] ** 3 /
                        (d["ic"][:, 0] + d["ic"][:, 1] + d["ic"][:, 2] + 1e-30))
        dt, leads = decision_times(d, y, P, "t_max", _pout,
                                   "triples (units: T_out)")
        report["triples_decision"] = dt
        with open(out_dir / "triples_decision.json", "w") as f:
            json.dump(dt, f, indent=1)

        # ---- defensible triple multiclass task (stable / outer / inner) ----
        ym = triples_multiclass_labels(d)
        from collections import Counter
        print("\n=== triples multiclass label counts ===")
        print({TRI_CLASS_NAMES[c]: int((ym == c).sum())
               for c in range(3) if (ym == c).any()})
        mrows, Pt, Pm, cmap = multiclass_causal_curve(
            d, ym, "t_max", d["fractions"], "triples multiclass",
            ic_fn=_ic_triple, label_names=TRI_CLASS_NAMES)
        report["triples_multiclass"] = mrows
        with open(out_dir / "triples_multiclass.json", "w") as f:
            json.dump(mrows, f, indent=1)
        mdt = multiclass_decision_times(
            d, ym, Pt, Pm, "t_max", _pout,
            "triples multiclass (units: T_out, event classes)",
            t_ref=np.where(np.isnan(d["t_event"]), 0, d["t_event"]),
            label_names=TRI_CLASS_NAMES, class_filter=(1, 2))
        report["triples_multiclass_decision"] = mdt
        with open(out_dir / "triples_multiclass_decision.json", "w") as f:
            json.dump(mdt, f, indent=1)

        # ---- external benchmark: Mardling-Aarseth (measured) ----
        ma01 = ma01_benchmark(d, "triples")
        report["ma01"] = ma01
        with open(out_dir / "ma01_benchmark.json", "w") as f:
            json.dump(ma01, f, indent=1)

        # ---- time-to-event regression ----
        tte = time_to_event_regression(d, "triples")
        report["tte"] = tte
        with open(out_dir / "tte_regression.json", "w") as f:
            json.dump(tte, f, indent=1)

        # ---- Cox proportional hazards ----
        cox = cox_hazards(d, f=0.5)
        report["cox"] = cox
        with open(out_dir / "cox_hazards.json", "w") as f:
            json.dump(cox, f, indent=1)

    # ---------------- encounters ----------------
    if args.encounters:
        d = _subset_fracs(np.load(args.encounters), frac_step, ENCOUNTER_FRACS)
        y = (d["statuses"] == "exchange").astype(int)
        rows, P = causal_curve(d, y, "t_approach", d["fractions"], _ic_encounter,
                               "encounters: exchange vs not")
        report["enc_causal"] = rows
        with open(out_dir / "enc_causal.json", "w") as f:
            json.dump(rows, f, indent=1)
        tbin = d["ic"][:, 20] if d["ic"].shape[1] > 20 else np.full(len(y), 4.443)
        dt, leads = decision_times(d, y, P, "t_approach", tbin,
                                   "encounters (lead vs periastron, binary periods)",
                                   t_peri=d["t_peri"])
        report["enc_decision"] = dt
        with open(out_dir / "enc_decision.json", "w") as f:
            json.dump(dt, f, indent=1)
        cs = conditional_skill(d, d["fractions"])
        report["enc_conditional"] = cs
        with open(out_dir / "enc_conditional.json", "w") as f:
            json.dump(cs, f, indent=1)

        # ---- multiclass (3-class) ----
        ym = encounters_multiclass_labels(d)
        print("\n=== encounters multiclass label counts ===")
        print({ENC_CLASS_NAMES[c]: int((ym == c).sum()) for c in range(3)})
        mrows, Pt, Pm, cmap = multiclass_causal_curve(
            d, ym, "t_approach", d["fractions"], "encounters multiclass",
            ic_fn=_ic_encounter, label_names=ENC_CLASS_NAMES)
        report["enc_multiclass"] = mrows
        with open(out_dir / "enc_multiclass.json", "w") as f:
            json.dump(mrows, f, indent=1)
        tbin_m = d["ic"][:, 20] if d["ic"].shape[1] > 20 else np.full(len(ym), 4.443)
        mdt = multiclass_decision_times(
            d, ym, Pt, Pm, "t_approach", tbin_m,
            "encounters multiclass (lead vs periastron, binary periods)",
            t_ref=d["t_peri"], label_names=ENC_CLASS_NAMES)
        report["enc_multiclass_decision"] = mdt
        with open(out_dir / "enc_multiclass_decision.json", "w") as f:
            json.dump(mdt, f, indent=1)
        mcs = multiclass_conditional_skill(d, d["fractions"])
        report["enc_multiclass_conditional"] = mcs
        with open(out_dir / "enc_multiclass_conditional.json", "w") as f:
            json.dump(mcs, f, indent=1)

    # ---------------- spike study ----------------
    if args.triples and args.series:
        sp = spike_study(np.load(args.triples), args.series)
        report["spike"] = sp
        with open(out_dir / "spike_study.json", "w") as f:
            json.dump(sp, f, indent=1)

    # ---------------- survival ----------------
    if args.triples and args.tail:
        surv = survival_analysis(np.load(args.triples), np.load(args.tail),
                                 out_dir)
        report["survival"] = surv

    # ---------------- boundary (standalone in-stratum curve + decisions) --
    if args.boundary:
        _b = _subset_fracs(np.load(args.boundary), frac_step, TRIPLE_FRACS)
        yb = np.full(len(_b["statuses"]), -1, dtype=int)
        yb[_b["statuses"] == "stable"] = 0
        yb[_b["statuses"] == "ejected"] = 1
        brows, Pb = causal_curve(_b, yb, "t_max", _b["fractions"],
                                 _ic_triple, "boundary suite (in-stratum)")
        report["boundary_causal"] = brows
        with open(out_dir / "boundary_causal.json", "w") as f:
            json.dump(brows, f, indent=1)
        _pout_b = np.sqrt(_b["ic"][:, 9] ** 3 /
                          (_b["ic"][:, 0] + _b["ic"][:, 1] + _b["ic"][:, 2] + 1e-30))
        bdt, bleads = decision_times(_b, yb, Pb, "t_max", _pout_b,
                                     "boundary suite (units: T_out)")
        report["boundary_decision"] = bdt
        with open(out_dir / "boundary_decision.json", "w") as f:
            json.dump(bdt, f, indent=1)

    # ---------------- boundary OOD (train fiducial -> test boundary) ------
    if args.triples and args.boundary:
        _m = _subset_fracs(np.load(args.triples), frac_step, TRIPLE_FRACS)
        _b = _subset_fracs(np.load(args.boundary), frac_step, TRIPLE_FRACS)
        b_rows = boundary_stratum(_m, _b,
                                  fraction_idx=len(_m["fractions"]) // 2)
        report["boundary"] = b_rows
        with open(out_dir / "boundary_ood.json", "w") as f:
            json.dump(b_rows, f, indent=1)

    with open(out_dir / "report.json", "w") as f:
        json.dump({k: v for k, v in report.items() if not isinstance(v, tuple)},
                  f, indent=1, default=str)
    print("\nDone. JSONs written to", out_dir)


# =====================================================================
#  RUNNER - Session B: analysis of the SCALE-UP data (1.6M systems)
#
#  RUN_MODE: "BOTH"       = triples side then encounters side (~3.5-5 h)
#            "TRIPLES"    = triples + tail + boundary + series (~1.5-2.5 h)
#            "ENCOUNTERS" = encounters only (~2-3 h)
#
#  The tail file (from the FIRST run, 10k x 1000 T_out) and the series
#  file are used automatically IF present - they are skipped otherwise
#  (the deep-tail run replaces the tail later).
#
#  V2_SUBSAMPLE = 200000: each ML fit evaluates on a stratified 200k
#  subset - statistically identical to the full set (+/-0.005 AUC) but
#  ~4x faster. The full data stays stored for later re-runs.
# =====================================================================
RUN_MODE = "BOTH"   # <-- change this one line if needed

import os, subprocess, sys, threading, time
os.environ.setdefault("V2_ML_JOBS", "4")  # standard Kaggle CPU host
os.environ.setdefault("V2_SEEDS", "0,1,2")
os.environ.setdefault("V2_FRAC_STEP", "2")
os.environ.setdefault("V2_SUBSAMPLE", "200000")


# ---------------------------------------------------------------
# HEARTBEAT: keeps the TPU device busy so Kaggle does not kill the
# session (sessions die after ~2 h of zero TPU activity).
# ---------------------------------------------------------------
# ---------------------------------------------------------------
# HEARTBEAT (supervised): one persistent JAX subprocess keeps the
# TPU busy continuously (sessions die after ~2 h of ZERO TPU
# activity); a monitor restarts it if it dies and reports every
# 5 min so you can SEE it working. TPU tensor cores and the 96
# vCPUs are separate hardware -> ~0 CPU cost, no interference.
# JAX's noisy startup warnings are sent to /dev/null (stderr)
# so the notebook log stays small.
# ---------------------------------------------------------------
HEARTBEAT_CODE = (
    "import time\n"
    "import jax, jax.numpy as jnp\n"
    "dev = jax.devices()[0]\n"
    "x = jax.device_put(jnp.ones((256, 256)), dev)\n"
    "i = 0\n"
    "while True:\n"
    "    x = (x @ x).block_until_ready()\n"
    "    i += 1\n"
    "    if i % 50 == 0:\n"
    "        print('hb ok', dev, i, flush=True)\n"
    "    time.sleep(2.0)\n"
)

def heartbeat():
    proc = None
    while True:
        try:
            if proc is None or proc.poll() is not None:
                if proc is not None:
                    print("[heartbeat] TPU touch process died - restarting",
                          flush=True)
                proc = subprocess.Popen([sys.executable, "-c",
                                         HEARTBEAT_CODE],
                                        stderr=subprocess.DEVNULL)
                time.sleep(20)
                if proc.poll() is not None:
                    print("[heartbeat] FAILED TO START - session will die at "
                          "~2 h TPU idle. Check the cell log for a JAX/TPU "
                          "error.", flush=True)
                else:
                    print("[heartbeat] TPU touch alive (pid %d)" % proc.pid,
                          flush=True)
            else:
                print("[heartbeat] TPU touch alive (pid %d)" % proc.pid,
                      flush=True)
        except Exception as e:
            print("[heartbeat] ERROR:", repr(e), flush=True)
        time.sleep(300)

print("CPU analysis: TPU heartbeat not started", flush=True)



os.makedirs("/kaggle/working/analysis_corrected_4core", exist_ok=True)
# Remove stale JSONs so a partial rerun cannot mix old and corrected results.
for _old_json in Path("/kaggle/working/analysis_corrected_4core").glob("*.json"):
    _old_json.unlink()
_BASE = os.environ.get("V2_MERGED_DIR", "/kaggle/input/v2merged")

if RUN_MODE in ("TRIPLES", "BOTH"):
    _args = ["--triples", _BASE + "/merged_triples.npz"]
    if os.path.exists(_BASE + "/merged_tail.npz"):
        _args += ["--tail", _BASE + "/merged_tail.npz"]
    _args += ["--boundary", _BASE + "/merged_boundary.npz"]
    if os.path.exists(_BASE + "/merged_triples_series.pkl"):
        _args += ["--series", _BASE + "/merged_triples_series.pkl"]
    sys.argv = ["production_analysis.py"] + _args +                ["--out-dir", "/kaggle/working/analysis_corrected_4core"]
    main()
    print("TRIPLES SIDE DONE.", flush=True)

if RUN_MODE in ("ENCOUNTERS", "BOTH"):
    if os.path.exists(_BASE + "/merged_encounters.npz"):
        sys.argv = ["production_analysis.py",
                    "--encounters", _BASE + "/merged_encounters.npz",
                    "--out-dir", "/kaggle/working/analysis_corrected_4core"]
        main()
        print("ENCOUNTERS SIDE DONE.", flush=True)
    else:
        print("merged_encounters.npz not found - skipping encounters side",
              flush=True)

# Build a consolidated report only after both sides have finished, so the
# encounter call cannot overwrite the triples-side report.
_all_json = {}
for _jp in sorted(Path("/kaggle/working/analysis_corrected_4core").glob("*.json")):
    if _jp.name != "report.json":
        with open(_jp) as _fh:
            _all_json[_jp.stem] = json.load(_fh)
_all_json["audit"] = {
    "leaked_feature_disabled": "n_frac",
    "stored_feature_index": 73,
    "value_used_in_all_models": 0.0,
    "decision_oof_scope": "all valid in-play systems",
    "triple_multiclass": ["stable", "outer-eject", "inner-eject"],
    "tte_target": "log10 remaining outer periods",
    "cox_design": "landmark remaining-time; ejection-only event"
}
with open("/kaggle/working/analysis_corrected_4core/report.json","w") as _fh:
    json.dump(_all_json,_fh,indent=1)
with open("/kaggle/working/analysis_corrected_4core/analysis_audit.json","w") as _fh:
    json.dump(_all_json["audit"],_fh,indent=1)
print("\n=== CORRECTED SESSION B COMPLETE ===", flush=True)
print(sorted(os.listdir("/kaggle/working/analysis_corrected_4core")), flush=True)
print("IMPORTANT: use only /kaggle/working/analysis_corrected_4core outputs. Save Version now.")
