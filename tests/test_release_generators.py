"""Generator tests: table/figure builders work on fixtures and skip cleanly."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from make_release_tables import (  # noqa: E402
    render_causal_head_table,
    render_decision_table,
    render_ledger_table,
    render_mask_table,
)


def fixture_meta(chunk_id, ejected, stable, num_err=0, collision=0):
    counts = {"ejected": ejected, "stable": stable}
    if num_err:
        counts["numerical_error"] = num_err
    if collision:
        counts["collision"] = collision
    return {
        "task": "tail", "chunk_id": chunk_id, "n_chunks": 2, "seed": 42,
        "n_systems": 50000, "outcome_counts": counts, "runtime_min": 130.0,
    }


def test_render_ledger_table_contains_counts_and_label():
    tex = render_ledger_table(fixture_meta(0, 20064, 29905, 31),
                              fixture_meta(1, 20015, 29948, 36, 1))
    assert r"\label{tab:tail_ledger}" in tex
    assert "20,064" in tex and "29,948" in tex and "100,000" in tex


def test_render_mask_and_decision_tables():
    audit = {"future_length_features_disabled": ["first_breach_old", "n_frac"],
             "stored_feature_indices": [72, 73], "values_used_in_all_models": [0.0, 0.0]}
    tex = render_mask_table(audit)
    assert r"\label{tab:final_mask}" in tex and "72" in tex and "73" in tex
    decision = {"n_warned": 10, "n_pos": 100, "warning_fraction": 0.1,
                "median_lead": 16.5, "p25": 5.0, "p75": 42.0}
    tex = render_decision_table(decision)
    assert r"\label{tab:triples_decision}" in tex and "16.50" in tex


def test_render_causal_head_table_tolerates_missing_fields():
    rows = [{"f": 0.05, "n_in_play_total": 1000, "auc_ic": 0.9, "auc_w": 0.91, "auc_b": 0.92},
            {"f": 0.5}]
    tex = render_causal_head_table(rows)
    assert r"\label{tab:causal_head}" in tex and "0.9200" in tex


def test_table_script_runs_and_skips_missing_inputs(tmp_path):
    prov = tmp_path / "prov"
    analysis = tmp_path / "analysis"
    prov.mkdir()
    analysis.mkdir()
    (prov / "chunk_tail_0_of_2_meta.json").write_text(
        json.dumps(fixture_meta(0, 1, 2)))
    out = tmp_path / "out"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_release_tables.py"),
                           "--provenance", str(prov), "--analysis", str(analysis),
                           "--out", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert "SKIP (input pending)" in proc.stdout
    assert not (out / "tab_tail_ledger.tex").exists()  # needs both metas


def test_figure_script_runs_on_fixtures(tmp_path):
    pytest = pytest_importorskip_matplotlib()
    prov = tmp_path / "prov"
    prov.mkdir()
    (prov / "chunk_tail_0_of_2_meta.json").write_text(
        json.dumps(fixture_meta(0, 20064, 29905, 31)))
    (prov / "chunk_tail_1_of_2_meta.json").write_text(
        json.dumps(fixture_meta(1, 20015, 29948, 36, 1)))
    out = tmp_path / "out"
    proc = subprocess.run([sys.executable, str(ROOT / "scripts" / "make_release_figures.py"),
                           "--provenance", str(prov), "--analysis", str(tmp_path),
                           "--out", str(out)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    assert (out / "fig_tail_ledger.pdf").is_file()
    assert (out / "fig_tail_ledger.svg").is_file()


def pytest_importorskip_matplotlib():
    import pytest

    return pytest.importorskip("matplotlib")
