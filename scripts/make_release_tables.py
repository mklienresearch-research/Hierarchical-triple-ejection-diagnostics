#!/usr/bin/env python3
"""Generate machine-checked LaTeX tables for the A1 manuscript.

Reads committed FINAL JSON products and writes booktabs tables under
paper/tables/. Inputs that have not arrived yet (see results/*/PENDING.json)
are reported as SKIP lines; the script still exits 0 so partial releases work.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path: Path):
    with open(path) as f:
        return json.load(f)


def fmt_int(n) -> str:
    return f"{int(n):,}"


def fmt_float(x, nd=4) -> str:
    return f"{float(x):.{nd}f}"


def render_ledger_table(meta0: dict, meta1: dict) -> str:
    totals = {}
    for meta in (meta0, meta1):
        for k, v in meta["outcome_counts"].items():
            totals[k] = totals.get(k, 0) + v
    keys = ["ejected", "stable", "numerical_error", "collision"]
    lines = [
        r"\begin{table}",
        r"  \centering",
        r"  \caption{Matched 3000-outer-period deep-tail ledger by reintegration chunk (seed 42).}",
        r"  \label{tab:tail_ledger}",
        r"  \begin{tabular}{lrrr}",
        r"    \toprule",
        r"    Outcome & Chunk 0 & Chunk 1 & Merged \\",
        r"    \midrule",
    ]
    for k in keys:
        label = k.replace("_", r"\_")
        lines.append(
            f"    {label} & {fmt_int(meta0['outcome_counts'].get(k, 0))}"
            f" & {fmt_int(meta1['outcome_counts'].get(k, 0))}"
            f" & {fmt_int(totals.get(k, 0))} \\\\"
        )
    lines += [
        r"    \midrule",
        f"    Total & {fmt_int(meta0['n_systems'])} & {fmt_int(meta1['n_systems'])}"
        f" & {fmt_int(meta0['n_systems'] + meta1['n_systems'])} \\\\",
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


def render_mask_table(audit: dict) -> str:
    feats = ", ".join(f"\\texttt{{{f}}}" for f in audit["future_length_features_disabled"])
    idx = ", ".join(str(i) for i in audit["stored_feature_indices"])
    lines = [
        r"\begin{table}",
        r"  \centering",
        r"  \caption{FINAL train/serve mask: future-length-dependent stored columns are identically zero in every model input.}",
        r"  \label{tab:final_mask}",
        r"  \begin{tabular}{ll}",
        r"    \toprule",
        r"    Item & Value \\",
        r"    \midrule",
        f"    Disabled features & {feats} \\\\",
        f"    Stored indices & {idx} \\\\",
        f"    Values used & {fmt_float(audit['values_used_in_all_models'][0], 1)}, "
        f"{fmt_float(audit['values_used_in_all_models'][1], 1)} \\\\",
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


def render_decision_table(decision: dict) -> str:
    rows = [
        ("Systems warned", fmt_int(decision["n_warned"])),
        ("Positive systems", fmt_int(decision["n_pos"])),
        ("Warning fraction", fmt_float(decision["warning_fraction"])),
        ("Median lead [outer periods]", fmt_float(decision["median_lead"], 2)),
        ("Lead p25--p75", f"{fmt_float(decision['p25'], 2)}--{fmt_float(decision['p75'], 2)}"),
    ]
    lines = [
        r"\begin{table}",
        r"  \centering",
        r"  \caption{Triples operating-point summary at the calibrated warning threshold (FINAL).}",
        r"  \label{tab:triples_decision}",
        r"  \begin{tabular}{lr}",
        r"    \toprule",
        r"    Metric & Value \\",
        r"    \midrule",
    ]
    lines += [f"    {k} & {v} \\\\" for k, v in rows]
    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


def render_causal_head_table(rows: list) -> str:
    """Headline horizon table from triples_causal.json (generated once committed)."""
    rows = [r for r in rows if isinstance(r, dict) and "auc_b" in r][:6]
    lines = [
        r"\begin{table}",
        r"  \centering",
        r"  \caption{Causal binary discrimination vs horizon for hierarchical triples (FINAL). IC = initial conditions only; W = dynamical window; B = combined.}",
        r"  \label{tab:causal_head}",
        r"  \begin{tabular}{rrrrr}",
        r"    \toprule",
        r"    $f$ & $n$ in play & AUC(IC) & AUC(W) & AUC(B) \\",
        r"    \midrule",
    ]
    for r in rows:
        n = r.get("n_in_play_total", r.get("n_eval", float("nan")))
        n_str = fmt_int(n) if n == n else "--"
        lines.append(
            f"    {fmt_float(r.get('f', float('nan')))} & {n_str}"
            f" & {fmt_float(r.get('auc_ic', float('nan')))}"
            f" & {fmt_float(r.get('auc_w', float('nan')))}"
            f" & {fmt_float(r.get('auc_b', float('nan')))} \\\\"
        )
    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        r"\end{table}",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--provenance", default=str(ROOT / "results" / "provenance"))
    ap.add_argument("--analysis", default=str(ROOT / "results" / "final_analysis_4core"))
    ap.add_argument("--out", default=str(ROOT / "paper" / "tables"))
    args = ap.parse_args()
    prov, analysis, out = Path(args.provenance), Path(args.analysis), Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written, skipped = [], []

    def need(path: Path):
        if path.is_file():
            return read(path)
        skipped.append(path.name)
        return None

    meta0 = need(prov / "chunk_tail_0_of_2_meta.json")
    meta1 = need(prov / "chunk_tail_1_of_2_meta.json")
    if meta0 is not None and meta1 is not None:
        (out / "tab_tail_ledger.tex").write_text(render_ledger_table(meta0, meta1))
        written.append("tab_tail_ledger.tex")

    audit = need(analysis / "analysis_audit.json")
    if audit is not None:
        (out / "tab_final_mask.tex").write_text(render_mask_table(audit))
        written.append("tab_final_mask.tex")

    decision = need(analysis / "triples_decision.json")
    if decision is not None:
        (out / "tab_triples_decision.tex").write_text(render_decision_table(decision))
        written.append("tab_triples_decision.tex")

    causal = need(analysis / "triples_causal.json")
    if causal is not None:
        (out / "tab_causal_head.tex").write_text(render_causal_head_table(causal))
        written.append("tab_causal_head.tex")

    for name in written:
        print(f"WROTE {name}")
    for name in skipped:
        print(f"SKIP (input pending): {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
