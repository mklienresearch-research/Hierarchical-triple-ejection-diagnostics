"""Causal experiment (v2, corrected protocol).

For each horizon fraction f we build features ONLY from samples with
t <= t_horizon, where the horizon is anchored in PHYSICAL time:
  * triples    : t_horizon = f * t_max  (t_max = 100 T_out in the full run)
  * encounters : t_horizon = f * t_peri (fraction of the infall phase)

Evaluation per horizon is restricted to systems still "in play"
(t_event > t_horizon), so the classifier can never see its own label inside
the window. Systems that terminated before the horizon are reported
separately (survival curve) — those are detectable, not predictable.
"""
from __future__ import annotations

from typing import Callable

import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, recall_score, \
    precision_score, f1_score, confusion_matrix

from .features import extract_window_features

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except Exception:
    HAS_XGB = False


FRACTIONS = [0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.6, 0.75, 0.9, 1.0]


def make_model(seed: int = 0):
    if HAS_XGB:
        return XGBClassifier(
            n_estimators=250, max_depth=3, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8, reg_lambda=2.0,
            objective="binary:logistic", eval_metric="logloss",
            random_state=seed, n_jobs=4, tree_method="hist")
    from sklearn.ensemble import HistGradientBoostingClassifier
    return HistGradientBoostingClassifier(
        max_iter=250, learning_rate=0.05, max_leaf_nodes=15,
        l2_regularization=0.05, random_state=0)


def _horizon(rec: dict, f: float, anchor: str) -> float:
    if anchor == "peri_frac":
        return f * float(rec["t_peri"])
    return f * float(rec["t_max"])


def run_causal_experiment(records: list, positive_label_fn: Callable,
                          fractions=FRACTIONS, seed: int = 0,
                          test_size: float = 0.3,
                          anchor: str = "tmax_frac") -> list:
    """anchor: 'tmax_frac' (triples: f*t_max) or 'peri_frac' (encounters:
    f*t_peri). Returns per-horizon rows incl. survival/excluded counts."""
    y = np.array([positive_label_fn(r) for r in records], dtype=int)
    if y.sum() == 0 or y.sum() == len(y):
        raise ValueError("only one class")

    rows = []
    for f in fractions:
        horizon = np.array([_horizon(r, f, anchor) for r in records])
        t_event = np.array([r["t_event"] if r["t_event"] is not None
                            else np.inf for r in records])
        in_play = t_event > horizon  # not yet terminated at horizon
        n_excl_pos = int(((t_event <= horizon) & (y == 1)).sum())
        n_excl_neg = int(((t_event <= horizon) & (y == 0)).sum())
        idx = np.where(in_play)[0]
        if len(idx) < 20 or y[idx].sum() < 5 or y[idx].sum() == len(idx):
            rows.append(dict(fraction=f, accuracy=np.nan, auc=np.nan,
                             recall_pos=np.nan, precision_pos=np.nan,
                             f1_pos=np.nan, tn=0, fp=0, fn=0, tp=0,
                             n_in_play=len(idx), n_excl_pos=n_excl_pos,
                             n_excl_neg=n_excl_neg))
            continue
        X = np.vstack([extract_window_features(records[i], 1.0,
                                               t_horizon=horizon[i])
                       for i in idx])
        X = np.nan_to_num(X, nan=0.0, posinf=1e30, neginf=-1e30)
        y_sub = y[idx]
        X_train, X_val, y_train, y_val = train_test_split(
            X, y_sub, test_size=test_size, random_state=seed, stratify=y_sub)
        clf = make_model(seed)
        clf.fit(X_train, y_train)
        p = clf.predict_proba(X_val)[:, 1]
        pred = (p >= 0.5).astype(int)
        tn, fp, fn, tp = confusion_matrix(y_val, pred, labels=[0, 1]).ravel()
        rows.append(dict(
            fraction=f,
            accuracy=float(accuracy_score(y_val, pred)),
            auc=float(roc_auc_score(y_val, p)),
            recall_pos=float(recall_score(y_val, pred, zero_division=0)),
            precision_pos=float(precision_score(y_val, pred, zero_division=0)),
            f1_pos=float(f1_score(y_val, pred, zero_division=0)),
            tn=int(tn), fp=int(fp), fn=int(fn), tp=int(tp),
            n_in_play=int(len(idx)), n_excl_pos=n_excl_pos, n_excl_neg=n_excl_neg,
        ))
    return rows


def print_causal_table(rows: list) -> None:
    hdr = (f"{'f':>5} {'acc':>7} {'AUC':>7} {'rec+':>6} {'prec+':>6} "
           f"{'F1+':>6} {'inplay':>6} {'excl+':>5} {'excl-':>5} {'FN':>4} {'TP':>5}")
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['fraction']:5.2f} {r['accuracy']*100:6.1f}% {r['auc']:7.4f} "
              f"{r['recall_pos']*100:5.1f}% {r['precision_pos']*100:5.1f}% "
              f"{r['f1_pos']:6.3f} {r['n_in_play']:6d} {r['n_excl_pos']:5d} "
              f"{r['n_excl_neg']:5d} {r['fn']:4d} {r['tp']:5d}")
    print("(excl+ / excl- : systems that already terminated by the horizon;")
    print(" metrics are evaluated on in-play systems only)")
