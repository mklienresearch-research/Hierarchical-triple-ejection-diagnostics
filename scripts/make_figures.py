#!/usr/bin/env python3
"""Generate core paper figures from analysis and audit JSON products."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


def read(path):
    with open(path) as f:
        return json.load(f)


def save(fig, out: Path, stem: str):
    fig.tight_layout()
    fig.savefig(out / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(out / f"{stem}.svg", bbox_inches="tight")
    plt.close(fig)


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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--analysis", default="results/corrected_analysis_4core")
    ap.add_argument("--audit", default="results/adversarial_audit_4core")
    ap.add_argument("--out", default="figures/generated")
    args = ap.parse_args()
    analysis = Path(args.analysis); audit = Path(args.audit); out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True); style()

    # Figure 1: causal binary skill.
    fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.0), sharey=True)
    panels = [
        ("triples_causal.json", "Hierarchical triples", 300.0),
        ("boundary_causal.json", "Near-MA01 boundary", 100.0),
        ("enc_causal.json", "Binary–single encounters", 1.0),
    ]
    for ax, (name, title, scale) in zip(axes, panels):
        rows = [r for r in read(analysis/name) if "auc_w" in r]
        x = np.array([r["f"] for r in rows]) * scale
        xlabel = r"Observation time [$T_{\rm out}$]" if scale > 1 else r"Approach fraction $f$"
        for key, label, ls in [("auc_ic", "IC only", "--"),
                               ("auc_w", "Window", ":"),
                               ("auc_b", "IC + window", "-")]:
            ax.plot(x, [r[key] for r in rows], marker="o", ms=3, lw=1.4, ls=ls, label=label)
        ax.set_title(title); ax.set_xlabel(xlabel); ax.grid(alpha=.2)
    axes[0].set_ylabel("ROC–AUC")
    axes[0].legend(frameon=False, loc="lower left")
    save(fig, out, "fig01_causal_auc")

    # Figure 2: feature-family PR-AUC at early/late horizons.
    tri = read(audit/"feature_ablation_triples.json")
    families = ["IC_only", "hierarchy", "energy", "angular_momentum", "torque",
                "signal", "all_window_no_time", "IC_plus_all_window"]
    labels = ["IC", "Hierarchy", "Energy", "Angular\nmomentum", "Torque",
              "Entropy/\nsignal", "Window\n(no time)", "IC + window"]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    xx = np.arange(len(families)); width=.36
    for j, f in enumerate([0.05, 0.5]):
        vals=[]
        for fam in families:
            vals.append(next(r["pr_auc_mean"] for r in tri if r["f"] == f and r["family"] == fam))
        ax.bar(xx+(j-.5)*width, vals, width, label=f"f={f:g}")
    ax.set_xticks(xx, labels); ax.set_ylabel("PR–AUC"); ax.set_ylim(0,1)
    ax.legend(frameon=False); ax.grid(axis="y", alpha=.2)
    save(fig, out, "fig02_triple_ablation")

    # Figure 3: fixed-FAR coverage and lead.
    tri_far = read(audit/"fixed_far_triples.json")["lead_by_far"]
    enc_far = read(audit/"fixed_far_encounters.json")["lead_by_far"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.0))
    for rows, label, marker in [(tri_far,"Triples","o"),(enc_far,"Encounters","s")]:
        x=100*np.array([r["target_far"] for r in rows])
        axes[0].plot(x,100*np.array([r["coverage_eligible"] for r in rows]),marker=marker,label=label)
        axes[1].plot(x,[r["median_lead"] for r in rows],marker=marker,label=label)
    axes[0].set_ylabel("Eligible events warned [%]")
    axes[1].set_ylabel("Median lead [orbital periods]")
    for ax in axes:
        ax.set_xscale("log"); ax.set_xlabel("Target FAR per horizon [%]"); ax.grid(alpha=.2); ax.legend(frameon=False)
    save(fig, out, "fig03_fixed_far")

    # Figure 4: multiclass horizon curves.
    fig, axes = plt.subplots(1,2,figsize=(7.2,3.0),sharey=True)
    for ax, fname, title in [(axes[0],"triples_multiclass.json","Triples: stable / outer / inner"),
                             (axes[1],"enc_multiclass.json","Encounters: flyby / exchange / ionization")]:
        rows=[r for r in read(analysis/fname) if "macro_f1_w" in r and r["f"] < .999]
        x=[r["f"] for r in rows]
        for key,label,ls in [("macro_f1_ic","IC","--"),("macro_f1_w","Window",":"),("macro_f1_b","Combined","-")]:
            ax.plot(x,[r[key] for r in rows],marker="o",ms=3,ls=ls,label=label)
        ax.set_title(title); ax.set_xlabel("Horizon fraction"); ax.grid(alpha=.2)
    axes[0].set_ylabel("Macro-F1"); axes[0].legend(frameon=False)
    save(fig,out,"fig04_multiclass")

    # Figure 5: remaining-time regression.
    tte=read(analysis/"tte_regression.json")
    fig,ax1=plt.subplots(figsize=(4.2,3.1)); x=300*np.array([r["f"] for r in tte])
    ax1.plot(x,[r["r2"] for r in tte],"o-",label=r"$R^2$")
    ax1.set_xlabel(r"Observation time [$T_{\rm out}$]"); ax1.set_ylabel(r"$R^2$")
    ax2=ax1.twinx(); ax2.plot(x,[r["mae_dex"] for r in tte],"s--",color="tab:orange",label="MAE")
    ax2.set_ylabel("MAE [dex]"); ax1.grid(alpha=.2)
    lines=ax1.lines+ax2.lines; ax1.legend(lines,[l.get_label() for l in lines],frameon=False)
    save(fig,out,"fig05_time_to_ejection")

    print("Generated:")
    for p in sorted(out.iterdir()): print(" ",p)


if __name__ == "__main__":
    main()
