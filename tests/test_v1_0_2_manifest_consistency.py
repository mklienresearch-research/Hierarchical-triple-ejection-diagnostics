"""Historical v1.0.2 manifest corrections remain preserved in v1.0.3."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results" / "final_manifest.json"
FRAMEWORK_RECORD = "docs/provenance/FRAMEWORK_AGENT_MATCHED_TOLERANCE_JOIN.md"
FRAMEWORK_SHA256 = "5e48fa5034226448e7fbbf25298abe488ea507dd7cfe33f6d0724f0fa1ecf0e6"
DISPLAY_MANIFEST = "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json"
DISPLAY_MANIFEST_SHA256 = "34bc46e7f3b3eef16a1cbd22dc08bb3cd8032b5f9298e4f1d379c15b0145424a"
V1_0_0_SCIENTIFIC_VIEW_SHA256 = "eaa77eaf4660bf5e506dc062938c5b898ed6e87fdf336183ff448af3845c53a4"


def load_manifest():
    return json.loads(MANIFEST.read_text())


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_of(path):
    return sha256_bytes(path.read_bytes())


def scientific_view(manifest):
    """The v1.0.0 scientific view retained through both patch releases."""
    frozen = manifest["frozen_hashes"]
    patched = {
        "results/tolerance/tolerance_raw_artifact_disposition.json",
        "results/tolerance/SHA256SUMS.txt",
        "results/tolerance/delayed_tolerance_join_summary.json",
    }
    return {
        "final_scripts_sha256": frozen["final_scripts_sha256"],
        "primary_data_sha256": frozen["primary_data_sha256"],
        "committed_result_files_sha256_excluding_patch": {
            key: value
            for key, value in frozen["committed_result_files_sha256"].items()
            if key not in patched
        },
        "control_documents_sha256": frozen["control_documents_sha256"],
        "tail_ledger": manifest["tail_ledger"],
        "runtime_environment": manifest["runtime_environment"],
        "canonical_form_notes": manifest["canonical_form_notes"],
        "partial_auc_claim_boundary": manifest["partial_auc_claim_boundary"],
        "release_policy": manifest["release_policy"],
        "tight_tail_500_disposition_raw": {
            key: manifest["tight_tail_500_disposition"][key]
            for key in (
                "expected_filename",
                "recorded_sha256",
                "availability",
                "statement",
                "future_archive_rule",
            )
        },
        "superseded_explicitly_excluded": manifest["superseded_explicitly_excluded"],
        "committed_but_non_authoritative": manifest["committed_but_non_authoritative"],
        "unresolved": manifest["unresolved"],
        "resolved_2026_09_27": manifest["resolved_2026_09_27"],
        "resolved_2026_09_29": manifest["resolved_2026_09_29"],
    }


def scientific_view_digest(manifest):
    blob = json.dumps(
        scientific_view(manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode()
    return sha256_bytes(blob)


def test_v1_0_1_and_v1_0_2_patch_records_remain_historical_and_unchanged():
    manifest = load_manifest()
    assert manifest["manifest_version"] == "1.0.3"
    assert manifest["release"]["tag"] == "v1.0.3"
    assert manifest["v1_0_1_patch"]["scientific_values_changed"] is False
    assert manifest["v1_0_1_patch"]["manuscript_results_changed"] is False
    assert manifest["v1_0_1_patch"]["raw_npz_added_or_reconstructed"] is False
    assert "present at docs/provenance/FRAMEWORK_AGENT_MATCHED_TOLERANCE_JOIN.md" in (
        manifest["v1_0_1_patch"]["author_followup"]
    )
    assert FRAMEWORK_SHA256 in manifest["v1_0_1_patch"]["author_followup"]

    patch = manifest["v1_0_2_patch"]
    assert patch["scope"] == "Provenance-consistency patch to the v1.0.1 final manifest only."
    assert len(patch["corrected_items"]) == 2
    assert patch["scientific_values_changed"] is False
    assert patch["display_bytes_changed"] is False
    assert patch["manuscript_bytes_changed"] is False
    assert patch["pins_changed"] is False
    assert "v1.0.0" in patch["tag_policy"] and "v1.0.1" in patch["tag_policy"]
    assert "author approval" in patch["tag_policy"]


def test_framework_record_and_historical_corrected_absence_statement_remain_resolved():
    manifest = load_manifest()
    author_followup = manifest["v1_0_1_patch"]["author_followup"]
    assert f"present at {FRAMEWORK_RECORD}" in author_followup
    assert FRAMEWORK_SHA256 in author_followup
    assert "frozen delayed_tolerance_join_summary bytes" in author_followup
    assert "is not present in the release tree" not in json.dumps(manifest)
    assert "NOT present in this tree" not in json.dumps(manifest)
    assert not re.search(
        r"framework record[^\n\"]*\b(?:absent|missing)\b",
        author_followup,
        flags=re.IGNORECASE,
    )
    path = ROOT / FRAMEWORK_RECORD
    assert path.is_file()
    assert sha256_of(path) == FRAMEWORK_SHA256
    assert manifest["frozen_hashes"]["provenance_documents_sha256"][FRAMEWORK_RECORD] == FRAMEWORK_SHA256


def test_all_fifteen_display_sources_resolve_and_corrected_manifest_is_pinned():
    manifest = load_manifest()
    display_path = ROOT / DISPLAY_MANIFEST
    display = json.loads(display_path.read_text())
    release_paths = {
        entry["release_path"]
        for sources in display["panel_and_table_sources"].values()
        for entry in sources
    }
    assert len(release_paths) == 15
    for release_path in release_paths:
        assert (ROOT / release_path).is_file(), release_path
    assert sha256_of(display_path) == DISPLAY_MANIFEST_SHA256
    assert (
        manifest["frozen_hashes"]["manuscript_display_sha256"][DISPLAY_MANIFEST]
        == DISPLAY_MANIFEST_SHA256
    )
    assert "15 unique release_path sources" in json.dumps(manifest)
    assert "14 unique release_path sources" not in json.dumps(manifest)
    assert "14 unique release_path entries" not in json.dumps(manifest)
    assert "All 15 unique release_path entries" in (
        manifest["display_provenance"]["verified_2026_09_29"]
    )


def test_scientific_view_and_unchanged_representative_file_pins_are_preserved():
    manifest = load_manifest()
    assert scientific_view_digest(manifest) == V1_0_0_SCIENTIFIC_VIEW_SHA256
    unchanged = {
        "paper/main.tex": "8225cfe83f5a883f71f2aa0a54f1b1a5b165e40c11be232ab5663550c70020c9",
        "paper/figures/fig_tail_ledger.pdf": "c4a636845d533fec3d710e3263e25dadbc4eec33b7f17b745e2fc34fdc173bcb",
        "paper/figures/fig_tail_ledger.svg": "5db595fb297f5526a9929c649aa92d20c8ef6ff4aef4e78b1c53e097f6115530",
        "paper/tables/tab_final_mask.tex": "e37687cce19ba0eb7199e64e7a5bb4251b80647833a9fa830e2639442f5c2540",
        "paper/tables/tab_tail_ledger.tex": "2d657568866630a52813da55f75679bb0b4b62f51956b3bf6561f6ccb27eab9e",
        "paper/tables/tab_triples_decision.tex": "cf32f2a441ecee9361b9959b99775c08ad507fd5e7ab030e1682acbc52e50325",
        "scripts/production/make_a1_main_table_data.py": "1df4725c9e9afffd30cbdafdf4046b4b4e103caf8e06373d6c8a672f51612909",
        "results/tolerance/SHA256SUMS.txt": "7d5a420587e294b2b87b9885158de48cd665666a11a78c07b5ebb2990dcc8e23",
        "results/tolerance/delayed_tolerance_join_summary.json": "40c51ba011edb1ec3c6d8d0012b4de5649817af7bdb7a4199676a90b8dd21d22",
        "results/tolerance/preselected_ids.txt": "b3d1e29b1b538a6521816552b559e353f62c30a818e5fbe7a3d867e0fb5e5986",
        "results/tolerance/tolerance_raw_artifact_disposition.json": "a5c373605f349b9406a8536b4a310c3fd7d34b902bd89d48a1f6666942d96c6f",
        "results/tolerance/tolerance_report.json": "e7e570c04bae947a86a12be4af6598c7a131fc5f444c04e850364cc450fb2434",
    }
    for rel, expected in unchanged.items():
        assert sha256_of(ROOT / rel) == expected, rel

    frozen = manifest["frozen_hashes"]
    for rel, expected in unchanged.items():
        for pins in (
            frozen["committed_result_files_sha256"],
            frozen["manuscript_display_sha256"],
            frozen["patch_control_documents_sha256"],
            frozen["provenance_documents_sha256"],
        ):
            if rel in pins:
                assert pins[rel] == expected


def test_no_raw_npz_was_added_or_reconstructed():
    manifest = load_manifest()
    disposition = manifest["tight_tail_500_disposition"]
    assert disposition["availability"] == "UNAVAILABLE_FOR_RELEASE"
    assert disposition["expected_filename"] == "tight_tail_500.npz"
    assert not list(ROOT.rglob("tight_tail_500.npz"))
    binary_suffixes = {".npz", ".npy", ".pkl", ".pickle", ".h5", ".hdf5", ".parquet"}
    assert not any(
        path.suffix.lower() in binary_suffixes
        for path in ROOT.rglob("*")
        if path.is_file() and not any(part in {".git", ".venv", "venv"} for part in path.parts)
    )
