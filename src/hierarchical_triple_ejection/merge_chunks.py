#!/usr/bin/env python3
"""Merge per-chunk production outputs into one dataset npz + series pkl."""
import argparse
import json
import pickle
from pathlib import Path

import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--merged-out", default=None,
                    help="where to write merged files (default: out-dir; "
                         "needed on Kaggle where input dirs are read-only)")
    ap.add_argument("--n-chunks", type=int, required=True)
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    merged_dir = Path(args.merged_out) if args.merged_out else out_dir
    merged_dir.mkdir(parents=True, exist_ok=True)
    parts, metas, series = [], [], []
    for k in range(args.n_chunks):
        tag = f"{args.task}_{k}_of_{args.n_chunks}"
        npz_p = out_dir / f"chunk_{tag}.npz"
        meta_p = out_dir / f"chunk_{tag}_meta.json"
        ser_p = out_dir / f"chunk_{tag}_series.pkl"
        if not npz_p.exists():
            print(f"missing {npz_p} — skipping"); continue
        parts.append(np.load(npz_p))
        metas.append(json.loads(meta_p.read_text()))
        if ser_p.exists():
            with open(ser_p, "rb") as f:
                series.extend(pickle.load(f))

    if not parts:
        raise SystemExit("no chunks found")

    def cat(key):
        return np.concatenate([p[key] for p in parts])

    merged = dict(
        ids=cat("ids"), statuses=cat("statuses"), labels=cat("labels"),
        t_event=cat("t_event"), t_max=cat("t_max"),
        E0=cat("E0"), max_rel_err=cat("max_rel_err"),
        ic=cat("ic"), feats=cat("feats"),
    )
    if "fractions" in parts[0].files:
        merged["fractions"] = parts[0]["fractions"]
    if args.task == "encounters":
        merged["t_peri"] = cat("t_peri")
        merged["t_approach"] = cat("t_approach")
        merged["min_pair_dist"] = cat("min_pair_dist")
    else:
        for k in ("exchange", "escaper"):
            if k in parts[0]:
                merged[k] = cat(k)

    # sort by id
    order = np.argsort(merged["ids"])
    for k in list(merged):
        if k != "fractions":
            merged[k] = merged[k][order]

    out_p = merged_dir / f"merged_{args.task}.npz"
    np.savez_compressed(out_p, **merged)
    if series:
        series.sort(key=lambda x: x[0])
        with open(merged_dir / f"merged_{args.task}_series.pkl", "wb") as f:
            pickle.dump(series, f)

    total = int(sum(m["n_systems"] for m in metas))
    with open(merged_dir / f"merged_{args.task}_meta.json", "w") as f:
        json.dump(dict(n_chunks=len(parts), n_systems=total, metas=metas), f, indent=1)
    print(f"merged {total} systems -> {out_p}")
    print("status counts:", {s: int(np.sum(merged['statuses'] == s))
                            for s in np.unique(merged['statuses'])})


if __name__ == "__main__":
    main()
