#!/usr/bin/env python3
"""Matched 300 -> 3000 outer-period censoring and competing-risk analysis."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np


def load_npz(path: str | Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as z:
        return {k: z[k] for k in z.files}


def outer_period(ic: np.ndarray) -> np.ndarray:
    return np.sqrt(ic[:, 9] ** 3 / (ic[:, 0] + ic[:, 1] + ic[:, 2] + 1e-30))


def event_table(status: np.ndarray, t_event: np.ndarray, t_max: np.ndarray,
                pout: np.ndarray) -> dict[str, np.ndarray]:
    event = np.isin(status, ["ejected", "collision"])
    stop = np.where(event & np.isfinite(t_event), t_event, t_max) / pout
    kind = np.where(status == "ejected", 1, np.where(status == "collision", 2, 0))
    # Numerical errors/timeouts are censored at their termination time when available.
    failed = np.isin(status, ["numerical_error", "timeout"])
    stop[failed & np.isfinite(t_event)] = t_event[failed & np.isfinite(t_event)] / pout[failed & np.isfinite(t_event)]
    return {"time": stop.astype(float), "kind": kind.astype(int)}


def competing_risk_curve(time: np.ndarray, kind: np.ndarray) -> list[dict]:
    """Aalen-Johansen-style discrete event table for ejection/collision."""
    order = np.argsort(time, kind="stable")
    time = time[order]; kind = kind[order]
    unique_event_times = np.unique(time[kind > 0])
    n_risk = len(time); survival = 1.0; cif_ej = 0.0; cif_col = 0.0
    rows = [{"t_outer": 0.0, "survival": 1.0, "cif_ejection": 0.0,
             "cif_collision": 0.0, "n_risk": int(n_risk)}]
    for t in unique_event_times:
        at = time == t
        d_ej = int(np.sum(at & (kind == 1)))
        d_col = int(np.sum(at & (kind == 2)))
        d_all = d_ej + d_col
        n_risk = int(np.sum(time >= t))
        if n_risk <= 0:
            continue
        cif_ej += survival * d_ej / n_risk
        cif_col += survival * d_col / n_risk
        survival *= 1.0 - d_all / n_risk
        rows.append({"t_outer": float(t), "survival": float(survival),
                     "cif_ejection": float(cif_ej), "cif_collision": float(cif_col),
                     "n_risk": n_risk, "d_ejection": d_ej, "d_collision": d_col})
    return rows


def status_counts(x: np.ndarray) -> dict[str, int]:
    return {str(k): int(np.sum(x == k)) for k in np.unique(x)}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--main", required=True, help="merged 500k triples NPZ")
    ap.add_argument("--tail", required=True, help="matched 100k x 3000 NPZ")
    ap.add_argument("--out", default="survival_results")
    args = ap.parse_args()

    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    main_d = load_npz(args.main); tail = load_npz(args.tail)

    main_order = np.argsort(main_d["ids"]); tail_order = np.argsort(tail["ids"])
    main_ids = main_d["ids"][main_order]; tail_ids = tail["ids"][tail_order]
    if len(np.unique(tail_ids)) != len(tail_ids):
        raise RuntimeError("duplicate tail IDs")
    if not np.array_equal(tail_ids, np.arange(100000, dtype=tail_ids.dtype)):
        raise RuntimeError("tail IDs must be exactly 0..99,999")

    pos = np.searchsorted(main_ids, tail_ids)
    if np.any(pos >= len(main_ids)) or not np.array_equal(main_ids[pos], tail_ids):
        raise RuntimeError("tail IDs are not a matched subset of main IDs")
    m_idx = main_order[pos]

    # Initial-condition identity is a hard matching check.
    ic_delta = np.max(np.abs(main_d["ic"][m_idx, :15] - tail["ic"][tail_order, :15]))
    if not np.isfinite(ic_delta) or ic_delta > 1e-6:
        raise RuntimeError(f"initial-condition mismatch; max abs difference={ic_delta}")

    ms = main_d["statuses"][m_idx]
    ts = tail["statuses"][tail_order]
    mt = main_d["t_event"][m_idx]
    tt = tail["t_event"][tail_order]
    tmax_tail = tail["t_max"][tail_order]
    ic_tail = tail["ic"][tail_order]
    pout = outer_period(ic_tail)
    tt_outer = tt / pout

    stable300 = ms == "stable"
    delayed_eject = stable300 & (ts == "ejected") & (tt_outer > 300.0)
    delayed_collision = stable300 & (ts == "collision") & (tt_outer > 300.0)
    stable3000 = stable300 & (ts == "stable")

    # Events before 300 should agree between independently rerun matched records.
    main_ej300 = ms == "ejected"
    tail_ej300 = (ts == "ejected") & (tt_outer <= 300.0 + 1e-5)
    agreement = float(np.mean(main_ej300 == tail_ej300))

    ladder = []
    for cutoff in [100.0, 300.0, 1000.0, 3000.0]:
        ladder.append({
            "t_outer": cutoff,
            "n_ejected": int(np.sum((ts == "ejected") & (tt_outer <= cutoff))),
            "fraction_ejected": float(np.mean((ts == "ejected") & (tt_outer <= cutoff))),
            "n_collision": int(np.sum((ts == "collision") & (tt_outer <= cutoff))),
            "fraction_collision": float(np.mean((ts == "collision") & (tt_outer <= cutoff))),
        })

    ev = event_table(ts, tt, tmax_tail, pout)
    curve = competing_risk_curve(ev["time"], ev["kind"])

    result = {
        "protocol": {
            "main_cutoff_outer_periods": 300,
            "tail_cutoff_outer_periods": 3000,
            "matched_ids": "0..99,999",
            "ejection_event": True,
            "collision_competing_event": True,
            "numerical_error_handling": "censored at termination time",
        },
        "matching": {
            "n_matched": int(len(tail_ids)),
            "max_abs_ic_difference": float(ic_delta),
            "ejection_by_300_status_agreement": agreement,
        },
        "main_status_counts_matched": status_counts(ms),
        "tail_status_counts": status_counts(ts),
        "delayed_outcomes": {
            "n_stable_at_300": int(stable300.sum()),
            "n_ejected_300_to_3000": int(delayed_eject.sum()),
            "fraction_delayed_ejection_among_stable300": float(delayed_eject.sum() / max(stable300.sum(), 1)),
            "n_collided_300_to_3000": int(delayed_collision.sum()),
            "n_still_stable_at_3000": int(stable3000.sum()),
        },
        "censoring_ladder": ladder,
        "competing_risk_curve": curve,
    }
    with open(out / "survival.json", "w") as f:
        json.dump(result, f, indent=1)

    # Compact curve CSV for plotting without reparsing a large JSON list.
    cols = ["t_outer", "survival", "cif_ejection", "cif_collision", "n_risk"]
    with open(out / "survival_curve.csv", "w") as f:
        f.write(",".join(cols) + "\n")
        for row in curve:
            f.write(",".join(str(row[c]) for c in cols) + "\n")

    print(json.dumps({k: result[k] for k in ["matching", "main_status_counts_matched",
                                             "tail_status_counts", "delayed_outcomes",
                                             "censoring_ladder"]}, indent=1))
    print("Wrote", out / "survival.json")
    print("Wrote", out / "survival_curve.csv")


if __name__ == "__main__":
    main()
