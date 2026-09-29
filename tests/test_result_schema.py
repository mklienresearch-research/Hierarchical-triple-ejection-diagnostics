"""Schema + internal-consistency tests for committed FINAL JSON products."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANALYSIS = ROOT / "results" / "final_analysis_4core"
AUDIT = ROOT / "results" / "final_audit_expanded"
PROV = ROOT / "results" / "provenance"


def load(path):
    with open(path) as f:
        return json.load(f)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_final_analysis_audit_declares_72_73_zeroed():
    audit = load(ANALYSIS / "analysis_audit.json")
    assert audit["stored_feature_indices"] == [72, 73]
    assert audit["values_used_in_all_models"] == [0.0, 0.0]
    assert "n_frac" in audit["future_length_features_disabled"]
    assert len(audit["future_length_features_disabled"]) == 2


def test_triples_decision_internal_consistency():
    d = load(ANALYSIS / "triples_decision.json")
    assert d["n_warned"] == d["n_positive_lead"]
    assert 0.0 <= d["warning_fraction"] <= 1.0
    assert d["warning_fraction"] == d["n_warned"] / d["n_pos"]
    assert d["p25"] <= d["median_lead"] <= d["p75"]
    assert d["median_positive_lead"] == d["median_lead"]


def test_chunk_metas_sum_to_50000_and_match_ledger():
    totals = {"ejected": 0, "stable": 0, "numerical_error": 0, "collision": 0}
    for i in (0, 1):
        meta = load(PROV / f"chunk_tail_{i}_of_2_meta.json")
        assert meta["task"] == "tail"
        assert meta["chunk_id"] == i
        assert meta["n_chunks"] == 2
        assert meta["seed"] == 42
        assert meta["n_systems"] == 50000
        assert sum(meta["outcome_counts"].values()) == 50000
        for k in totals:
            totals[k] += meta["outcome_counts"].get(k, 0)
    assert totals == {"ejected": 40079, "stable": 59853, "numerical_error": 67, "collision": 1}
    manifest = load(ROOT / "results" / "final_manifest.json")
    assert manifest["tail_ledger"]["merged"]["ejected"] == 40079
    assert manifest["tail_ledger"]["chunk0"]["ejected"] == 20064


def test_deeptail_manifest_matches_committed_files_and_sources():
    manifest = load(PROV / "deeptail_manifest.json")
    assert manifest["status"] == "complete"
    committed = {
        "chunk_tail_0_of_2_meta.json": PROV / "chunk_tail_0_of_2_meta.json",
        "chunk_tail_1_of_2_meta.json": PROV / "chunk_tail_1_of_2_meta.json",
    }
    for name, entry in manifest["files"].items():
        if name in committed:
            p = committed[name]
            assert p.stat().st_size == entry["bytes"], name
            assert sha256_of(p) == entry["sha256"], name
    frozen = load(ROOT / "results" / "final_manifest.json")["frozen_hashes"]["primary_data_sha256"]
    assert manifest["source"]["chunk0_sha256"] == frozen["3000t-out/v2out/chunk_tail_0_of_2.npz"]
    assert manifest["source"]["chunk1_sha256"] == frozen["3000t-outpart-2/chunk_tail_1_of_2.npz"]
    assert manifest["source"]["main_sha256"] == frozen["mergedtriples/merged_triples.npz"]


def _check_pending(directory, keys):
    pending = load(directory / "PENDING.json")
    for key in keys:
        for entry in pending[key]:
            assert set(entry) >= {"name", "sha256", "bytes"}, entry
            assert len(entry["sha256"]) == 64
            int(entry["sha256"], 16)
            assert entry["bytes"] > 0
            if key != "zenodo_track_record_only":
                assert not (directory / entry["name"]).exists(), (
                    f"{entry['name']} arrived but is still listed in PENDING.json"
                )


def test_pending_lists_wellformed_and_current():
    _check_pending(ANALYSIS, ["pending"])
    _check_pending(AUDIT, ["pending_git", "zenodo_track_record_only"])


def test_committed_files_match_final_manifest():
    manifest = load(ROOT / "results" / "final_manifest.json")
    entries = manifest["frozen_hashes"]["committed_result_files_sha256"]
    assert len(entries) >= 7
    for rel, want in entries.items():
        p = ROOT / rel
        assert p.is_file(), rel
        assert sha256_of(p) == want, rel
