#!/usr/bin/env python3
"""Generate machine-checked release figures for the A1 manuscript.

Reads committed FINAL JSON products and writes PDF+SVG under paper/figures/.
Inputs that have not arrived yet are reported as SKIP lines; exit code stays 0.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path):
    with open(path) as f:
        return json.load(f)


def style():
    plt.rcParams.update({
        "font.size": 9,
        "axes.labelsize": 10,
        "axes.titlesize": 10,
        "legend.fontsize": 8,
        "figure.dpi": 150,
        "savefig.dpi": 300,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def save(fig, out: Path, stem: str):
    fig.tight_layout()
    fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(out / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


def plot_ledger(meta0: dict, meta1: dict, out: Path):
    keys = ["ejected", "stable", "numerical_error", "collision"]
    labels = ["Ejected", "Stable", "Num.\nerror", "Collision"]
    vals0 = [meta0["outcome_counts"].get(k, 0) for k in keys]
    vals1 = [meta1["outcome_counts"].get(k, 0) for k in keys]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8), sharey=False)
    for ax, vals, title in zip(axes, (vals0, vals1), ("Chunk 0 (n=50,000)", "Chunk 1 (n=50,000)")):
        ax.bar(labels, vals, color=["tab:blue", "tab:gray", "tab:orange", "tab:red"])
        ax.set_title(title)
        ax.set_ylabel("Systems")
        for x, v in zip(labels, vals):
            ax.text(x, v, f"{v:,}", ha="center", va="bottom", fontsize=7)
    save(fig, out, "fig_tail_ledger")


def plot_causal_auc_final(rows: list, out: Path):
    rows = [r for r in rows if isinstance(r, dict) and "auc_b" in r]
    x = np.array([r["f"] for r in rows]) * 300.0
    fig, ax = plt.subplots(figsize=(4.4, 3.1))
    for key, label, ls in [("auc_ic", "IC only", "--"), ("auc_w", "Window", ":"),
                            ("auc_b", "IC + window", "-")]:
        ax.plot(x, [r[key] for r in rows], marker="o", ms=3, lw=1.4, ls=ls, label=label)
    ax.set_xlabel(r"Observation time [$T_{\rm out}$]")
    ax.set_ylabel("ROC-AUC")
    ax.legend(frameon=False)
    ax.grid(alpha=0.2)
    save(fig, out, "fig_causal_auc_final")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provenance", default=str(ROOT / "results" / "provenance"))
    ap.add_argument("--analysis", default=str(ROOT / "results" / "final_analysis_4core"))
    ap.add_argument("--out", default=str(ROOT / "paper" / "figures"))
    args = ap.parse_args()
    prov, analysis, out = Path(args.provenance), Path(args.analysis), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    style()

    skipped = []
    meta0_p, meta1_p = prov / "chunk_tail_0_of_2_meta.json", prov / "chunk_tail_1_of_2_meta.json"
    if meta0_p.is_file() and meta1_p.is_file():
        plot_ledger(read(meta0_p), read(meta1_p), out)
        print("WROTE fig_tail_ledger.pdf/svg")
    else:
        skipped.append("chunk metas")

    causal_p = analysis / "triples_causal.json"
    if causal_p.is_file():
        plot_causal_auc_final(read(causal_p), out)
        print("WROTE fig_causal_auc_final.pdf/svg")
    else:
        skipped.append("triples_causal.json")

    for name in skipped:
        print(f"SKIP (input pending): {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
