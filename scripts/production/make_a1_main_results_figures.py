#!/usr/bin/env python3
"""Create the three frozen A1 main-text figures from v1.0.0-pinned JSONs.

No model fitting or statistical recomputation is performed. The script reads
frozen derived results, performs display-only arithmetic (percent conversion and
cumulative precision from exact event/control counts), writes machine-readable
figure-source JSON, and saves PDF/PNG displays.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results"
OUT = ROOT / "paper_draft" / "figures"
DATA = ROOT / "paper_draft" / "figure_data"
OUT.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

COLORS = {
    "ic": "#4477AA",
    "window": "#EE6677",
    "combined": "#228833",
    "gray": "#666666",
    "gold": "#CCBB44",
    "purple": "#AA3377",
}


def load(path: Path):
    with path.open() as f:
        return json.load(f)


def panel(ax, letter):
    ax.text(-0.14, 1.05, f"({letter})", transform=ax.transAxes,
            fontweight="bold", va="top")


def save(fig, stem):
    fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight")
    fig.savefig(OUT / f"{stem}.png", dpi=220, bbox_inches="tight")
    plt.close(fig)


plt.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "legend.fontsize": 8,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 140,
})

# ---------------------------------------------------------------- Figure 1
parity = load(RESULTS / "final_expanded_audit_json" / "triples_parity.json")
growth = load(RESULTS / "attribution_growth_v2" / "triples_joint_gain_growth.json")
rows = parity["horizons"]
t = np.array([300 * r["f"] for r in rows])
auc = {k: np.array([r["models"][k]["roc_auc"] for r in rows])
       for k in ["IC_only", "window", "combined"]}
gain = auc["combined"] - auc["IC_only"]
gain_lo = np.array([r["bootstrap_auc95"]["combined_minus_IC"]["lo"] for r in rows])
gain_hi = np.array([r["bootstrap_auc95"]["combined_minus_IC"]["hi"] for r in rows])
ordinary = growth["ordinary"]
fixed = growth["fixed_landmark"]

fig, axes = plt.subplots(1, 3, figsize=(11.0, 3.05))
ax = axes[0]
for key, label, color, marker in [
    ("IC_only", "Initial conditions", COLORS["ic"], "o"),
    ("window", "Trajectory history", COLORS["window"], "s"),
    ("combined", "Combined", COLORS["combined"], "^"),
]:
    ax.plot(t, auc[key], marker=marker, color=color, lw=1.8, ms=4.5, label=label)
ax.set(xlabel=r"Observation time [$T_{\rm out}$]", ylabel="ROC--AUC",
       xticks=t, ylim=(0.974, 0.997))
ax.legend(frameon=False, loc="lower left")
panel(ax, "a")

ax = axes[1]
yerr = np.vstack([gain - gain_lo, gain_hi - gain])
ax.errorbar(t, gain, yerr=yerr, color=COLORS["combined"], marker="o",
            lw=1.6, capsize=2.5, ms=4.5)
ax.axhline(0, color="0.55", lw=0.8)
ax.set(xlabel=r"Observation time [$T_{\rm out}$]",
       ylabel=r"Combined $-$ IC AUC", xticks=t)
panel(ax, "b")

ax = axes[2]
ax.plot(t, ordinary["point_gains"], marker="o", color=COLORS["purple"],
        lw=1.7, label="Changing risk set")
ax.plot(t, fixed["point_gains"], marker="s", color=COLORS["gold"],
        lw=1.7, label=r"Fixed $f=0.75$ cohort")
ax.axhline(0, color="0.55", lw=0.8)
ax.set(xlabel=r"Observation time [$T_{\rm out}$]",
       ylabel=r"Combined $-$ IC AUC", xticks=t)
ax.legend(frameon=False, loc="upper left")
panel(ax, "c")
fig.tight_layout(w_pad=2.0)
save(fig, "fig01_primary_ranking")

fig1_data = {
    "source_files": [
        "results/final_audit_expanded/triples_parity.json",
        "results/attribution_v2/triples_joint_gain_growth.json",
    ],
    "observation_Tout": t.tolist(),
    "auc": {k: v.tolist() for k, v in auc.items()},
    "combined_minus_ic": {
        "point": gain.tolist(), "lo": gain_lo.tolist(), "hi": gain_hi.tolist()
    },
    "changing_risk_set": ordinary,
    "fixed_landmark": fixed,
}
(DATA / "fig01_primary_ranking.json").write_text(json.dumps(fig1_data, indent=2))

# ---------------------------------------------------------------- Figure 2
lead = parity["lead_by_far"]
far = np.array([r["target_far"] for r in lead])
coverage = 100 * np.array([r["coverage_eligible"] for r in lead])
control = 100 * np.array([r["cumulative_false_alert_fraction"] for r in lead])
n_event = np.array([r["n_warned"] for r in lead])
n_test_positive = int(lead[0]["n_test_positive"])
n_controls = parity["split_sizes"]["test"] - n_test_positive
n_false = np.rint(np.array([r["cumulative_false_alert_fraction"] for r in lead]) * n_controls).astype(int)
precision = 100 * n_event / (n_event + n_false)
median = np.array([r["median_lead"] for r in lead])
p25 = np.array([r["p25"] for r in lead])
p75 = np.array([r["p75"] for r in lead])

fig, axes = plt.subplots(1, 3, figsize=(10.8, 3.05))
ax = axes[0]
ax.plot(100 * far, coverage, "o-", color=COLORS["combined"], lw=1.8, label="Eligible-event coverage")
ax.plot(100 * far, control, "s--", color=COLORS["gray"], lw=1.5, label="Cumulative controls alerted")
ax.set_xscale("log")
ax.set(xlabel="Target FAR [%]", ylabel="Systems [%]", xticks=[0.1, 1, 5])
ax.set_xticklabels(["0.1", "1", "5"])
ax.legend(frameon=False, loc="center left")
panel(ax, "a")

ax = axes[1]
ax.plot(100 * far, precision, "o-", color=COLORS["ic"], lw=1.8)
ax.set_xscale("log")
ax.set(xlabel="Target FAR [%]", ylabel="Cumulative warning precision [%]",
       xticks=[0.1, 1, 5], ylim=(70, 101))
ax.set_xticklabels(["0.1", "1", "5"])
panel(ax, "b")

ax = axes[2]
ax.errorbar(100 * far, median, yerr=np.vstack([median-p25, p75-median]),
            fmt="o-", color=COLORS["purple"], lw=1.8, capsize=3)
ax.set_xscale("log")
ax.set(xlabel="Target FAR [%]", ylabel=r"Lead [$T_{\rm out}$]",
       xticks=[0.1, 1, 5])
ax.set_xticklabels(["0.1", "1", "5"])
panel(ax, "c")
fig.tight_layout(w_pad=2.1)
save(fig, "fig02_target_far_operation")

fig2_data = {
    "source_file": "results/final_audit_expanded/triples_parity.json",
    "target_far": far.tolist(),
    "n_test_positive": n_test_positive,
    "n_test_controls": int(n_controls),
    "eligible_coverage": (coverage/100).tolist(),
    "cumulative_control_alert_fraction": (control/100).tolist(),
    "n_warned_events": n_event.tolist(),
    "n_alerted_controls": n_false.tolist(),
    "cumulative_precision_display_derived": (precision/100).tolist(),
    "lead_median_Tout": median.tolist(),
    "lead_p25_Tout": p25.tolist(),
    "lead_p75_Tout": p75.tolist(),
}
(DATA / "fig02_target_far_operation.json").write_text(json.dumps(fig2_data, indent=2))

# ---------------------------------------------------------------- Figure 3
boundary = load(RESULTS / "final_expanded_audit_json" / "boundary_parity.json")
tol = load(RESULTS / "tolerance_validation" / "tolerance_report.json")
tol_join = load(RESULTS / "tolerance_validation" / "delayed_tolerance_join_summary.json")
attr = load(RESULTS / "attribution_precision_addon" / "attribution_precision_addon.json")
# Exact release-ledger incidence ladder.
tail_t = np.array([100, 300, 1000, 3000])
tail_inc = np.array([31.077, 34.989, 38.104, 40.079])
# Boundary f=0.50 and 0.75.
br = [r for r in boundary["horizons"] if np.isclose(r["f"], .5) or np.isclose(r["f"], .75)]
bt = np.array([100*r["f"] for r in br])
bauc = {k: np.array([r["models"][k]["roc_auc"] for r in br])
        for k in ["IC_only", "window", "combined"]}
# Frozen original 1% delayed operating row.
frozen = next(r for r in attr["frozen_threshold_paired_coverage"]
              if np.isclose(r["target_original_far"], .01))
models = ["IC_only", "window", "combined", "MA01_margin"]
labels = ["IC", "History", "Combined", "MA01"]
dcov = 100*np.array([frozen["arms"][m]["coverage"] for m in models])
dctrl = np.array([frozen["arms"][m]["control_alerts"] for m in models])

fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.0))
ax = axes[0,0]
for key, label, color, marker in [
    ("IC_only", "Initial conditions", COLORS["ic"], "o"),
    ("window", "Trajectory history", COLORS["window"], "s"),
    ("combined", "Combined", COLORS["combined"], "^"),
]:
    ax.plot(bt, bauc[key], marker=marker, color=color, lw=1.7, label=label)
ax.set(xlabel=r"Boundary observation [$T_{\rm out}$]", ylabel="ROC--AUC",
       xticks=bt, ylim=(0.90, 0.975))
ax.legend(frameon=False, loc="lower left")
panel(ax, "a")

ax = axes[0,1]
ax.plot(tail_t, tail_inc, "o-", color=COLORS["purple"], lw=1.8)
ax.set_xscale("log")
ax.set(xlabel=r"Independent tail cutoff [$T_{\rm out}$]",
       ylabel="Cumulative ejection incidence [%]", xticks=tail_t)
ax.set_xticklabels(["100", "300", "1000", "3000"])
panel(ax, "b")

ax = axes[1,0]
x = np.arange(2); w=.34
production = np.array([
    100 * tol["baseline_status_counts"]["ejected"] / tol["n"],
    100 * tol_join["production_tolerance"]["fraction"],
])
tight = np.array([
    100 * tol["tight_status_counts"]["ejected"] / tol["n"],
    100 * tol_join["tight_tolerance"]["fraction"],
])
ax.bar(x-w/2, production, width=w, color=COLORS["gray"], label="Production tolerance")
ax.bar(x+w/2, tight, width=w, color=COLORS["gold"], label=r"IAS15 $\epsilon=10^{-11}$")
ax.set(ylabel="Incidence [%]", xticks=x,
       xticklabels=["Final ejection\n(500 IDs)", "Delayed ejection\n(330 main-stable IDs)"], ylim=(0,45))
ax.legend(frameon=False, loc="upper right")
panel(ax, "c")

ax = axes[1,1]
bars=ax.bar(np.arange(4), dcov, color=[COLORS["ic"],COLORS["window"],COLORS["combined"],COLORS["gray"]])
ax.set(ylabel="Delayed-event coverage [%]", xticks=np.arange(4), xticklabels=labels, ylim=(0,31))
for bar,nc in zip(bars,dctrl):
    ax.text(bar.get_x()+bar.get_width()/2,bar.get_height()+.8,f"{int(nc)} controls",ha="center",va="bottom",fontsize=7,rotation=0)
panel(ax, "d")
fig.tight_layout(h_pad=2.2, w_pad=2.0)
save(fig, "fig03_robustness_endpoints")

fig3_data = {
    "source_files": [
        "results/final_audit_expanded/boundary_parity.json",
        "docs/RESULTS_MANIFEST_FINAL.md (tail incidence ladder)",
        "results/tolerance/tolerance_report.json",
        "results/tolerance/delayed_tolerance_join_summary.json",
        "results/attribution_precision/attribution_precision_addon.json",
    ],
    "boundary_observation_Tout": bt.tolist(),
    "boundary_auc": {k:v.tolist() for k,v in bauc.items()},
    "tail_cutoff_Tout": tail_t.tolist(),
    "tail_cumulative_ejection_percent": tail_inc.tolist(),
    "tolerance_percent": {"production": production.tolist(), "tight": tight.tolist()},
    "delayed_tolerance_join": tol_join,
    "delayed_models": models,
    "delayed_coverage": (dcov/100).tolist(),
    "delayed_control_alerts": dctrl.tolist(),
}
(DATA / "fig03_robustness_endpoints.json").write_text(json.dumps(fig3_data, indent=2))

print(OUT)
