"""Controlled v1.0.2 final-manifest consistency patch tests.

The v1.0.2 patch is metadata-only.  It resolves two stale prose statements in
v1.0.1's final manifest and changes the proposed release identity; it must not
change any scientific, display, manuscript, result, source-data, generator, or
tolerance bytes or pins.
"""

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "results" / "final_manifest.json"
FRAMEWORK_RECORD = "docs/provenance/FRAMEWORK_AGENT_MATCHED_TOLERANCE_JOIN.md"
FRAMEWORK_SHA256 = "5e48fa5034226448e7fbbf25298abe488ea507dd7cfe33f6d0724f0fa1ecf0e6"
DISPLAY_MANIFEST = "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json"
DISPLAY_MANIFEST_SHA256 = "09d8ffdf578011fd7db9228400215dc78bee0272341e4346f4837ba68daa1370"
SCIENTIFIC_VIEW_SHA256 = "eaa77eaf4660bf5e506dc062938c5b898ed6e87fdf336183ff448af3845c53a4"

# These constants are calculated from the public v1.0.1 tag.  The tests use
# content digests rather than `git show v1.0.1`, because the CI checkout is
# intentionally shallow and does not have to fetch historical tags.
V1_0_1_FROZEN_HASHES_SHA256 = "5abbec5c8cae5d468007bc78bb74dd935f1ea32f6b1b8c0ba4a8eed439af6f0e"
V1_0_1_NONPERMITTED_TREE_SHA256 = "76d41757a09b2f9b9f215ea8dc227ff91f07b09172709e707099c3b798a1d91e"
V1_0_1_NONPERMITTED_FILE_COUNT = 154

# Release metadata, the manifest itself, tests, and release documentation are
# the only classes of paths that this patch may change.
PERMITTED_EXACT = {"CITATION.cff", "README.md", "results/final_manifest.json"}

# Representative byte pins for the explicitly protected scientific/display
# objects.  The complete non-permitted tree digest below protects every other
# tracked scientific, manuscript, generator, and result file as well.
PROTECTED_HASHES = {
    "paper/main.tex": "8225cfe83f5a883f71f2aa0a54f1b1a5b165e40c11be232ab5663550c70020c9",
    "paper/drafts/main.tex": "fdcbfdb3a8e64dc4097b3b1b8ea5a2cc35b5c271f214436cb8eaf8d1894eb063",
    "paper/figures/fig_tail_ledger.pdf": "c4a636845d533fec3d710e3263e25dadbc4eec33b7f17b745e2fc34fdc173bcb",
    "paper/figures/fig_tail_ledger.svg": "5db595fb297f5526a9929c649aa92d20c8ef6ff4aef4e78b1c53e097f6115530",
    "paper/tables/tab_final_mask.tex": "e37687cce19ba0eb7199e64e7a5bb4251b80647833a9fa830e2639442f5c2540",
    "paper/tables/tab_tail_ledger.tex": "2d657568866630a52813da55f75679bb0b4b62f51956b3bf6561f6ccb27eab9e",
    "paper/tables/tab_triples_decision.tex": "cf32f2a441ecee9361b9959b99775c08ad507fd5e7ab030e1682acbc52e50325",
    "scripts/production/make_a1_main_results_figures.py": "e5a55e7a7c82e5813750d0241685c70e580ca1861f2d6a0baaf6f50958011f8a",
    "scripts/production/make_a1_main_table_data.py": "1df4725c9e9afffd30cbdafdf4046b4b4e103caf8e06373d6c8a672f51612909",
    "results/tolerance/SHA256SUMS.txt": "7d5a420587e294b2b87b9885158de48cd665666a11a78c07b5ebb2990dcc8e23",
    "results/tolerance/delayed_tolerance_join_summary.json": "40c51ba011edb1ec3c6d8d0012b4de5649817af7bdb7a4199676a90b8dd21d22",
    "results/tolerance/preselected_ids.txt": "b3d1e29b1b538a6521816552b559e353f62c30a818e5fbe7a3d867e0fb5e5986",
    "results/tolerance/tolerance_raw_artifact_disposition.json": "a5c373605f349b9406a8536b4a310c3fd7d34b902bd89d48a1f6666942d96c6f",
    "results/tolerance/tolerance_report.json": "e7e570c04bae947a86a12be4af6598c7a131fc5f444c04e850364cc450fb2434",
}


def load_manifest():
    with MANIFEST.open() as handle:
        return json.load(handle)


def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()


def sha256_of(path):
    return sha256_bytes(path.read_bytes())


def scientific_view(manifest):
    """The v1.0.0 scientific view retained by both patch releases."""
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


def tracked_paths():
    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return output.decode().split("\0")[:-1]


def permitted(path):
    return path.startswith(("docs/", "tests/")) or path in PERMITTED_EXACT


def nonpermitted_tree_digest(paths):
    digest = hashlib.sha256()
    selected = sorted(path for path in paths if not permitted(path))
    for path in selected:
        digest.update(path.encode())
        digest.update(b"\0")
        digest.update(sha256_of(ROOT / path).encode())
        digest.update(b"\n")
    return len(selected), digest.hexdigest()


def test_manifest_has_v1_0_2_identity_and_only_the_declared_corrections():
    manifest = load_manifest()
    assert manifest["manifest_version"] == "1.0.2"
    assert manifest["release"]["tag"] == "v1.0.2"
    assert manifest["release"]["url"] == (
        manifest["release"]["repository"] + "/releases/tag/v1.0.2"
    )
    patch = manifest["v1_0_2_patch"]
    assert len(patch["corrected_items"]) == 2
    assert patch["scientific_values_changed"] is False
    assert patch["display_bytes_changed"] is False
    assert patch["manuscript_bytes_changed"] is False
    assert patch["pins_changed"] is False
    assert "v1.0.0" in patch["tag_policy"] and "v1.0.1" in patch["tag_policy"]
    assert "author approval" in patch["tag_policy"]


def test_framework_record_is_present_and_the_stale_absence_claim_is_gone():
    manifest = load_manifest()
    author_followup = manifest["v1_0_1_patch"]["author_followup"]
    assert f"present at {FRAMEWORK_RECORD}" in author_followup
    assert FRAMEWORK_SHA256 in author_followup
    assert "frozen delayed_tolerance_join_summary bytes" in author_followup
    assert "is not present in the release tree" not in json.dumps(manifest)
    assert "NOT present in this tree" not in json.dumps(manifest)
    assert not re.search(
        r"framework record[^\n\"]*\b(?:absent|missing)\b", author_followup, flags=re.IGNORECASE
    )
    assert (ROOT / FRAMEWORK_RECORD).is_file()
    assert sha256_of(ROOT / FRAMEWORK_RECORD) == FRAMEWORK_SHA256
    assert (
        manifest["frozen_hashes"]["provenance_documents_sha256"][FRAMEWORK_RECORD]
        == FRAMEWORK_SHA256
    )


def test_manifest_consistently_reports_fifteen_display_sources():
    manifest = load_manifest()
    display = json.loads((ROOT / DISPLAY_MANIFEST).read_text())
    release_paths = {
        entry["release_path"]
        for sources in display["panel_and_table_sources"].values()
        for entry in sources
    }
    assert len(release_paths) == 15
    text = json.dumps(manifest)
    assert "14 unique release_path sources" not in text
    assert "14 unique release_path entries" not in text
    assert "15 unique release_path sources" in text
    assert (
        "All 15 unique release_path entries"
        in manifest["display_provenance"]["verified_2026_09_29"]
    )
    assert "all 15 unique release_path sources" in manifest["resolved_2026_09_29_v1_0_1_patch"][2]
    assert sha256_of(ROOT / DISPLAY_MANIFEST) == DISPLAY_MANIFEST_SHA256


def test_scientific_view_and_all_frozen_pins_are_unchanged():
    manifest = load_manifest()
    assert scientific_view_digest(manifest) == SCIENTIFIC_VIEW_SHA256
    frozen_digest = sha256_bytes(
        json.dumps(
            manifest["frozen_hashes"], sort_keys=True, separators=(",", ":"), ensure_ascii=True
        ).encode()
    )
    assert frozen_digest == V1_0_1_FROZEN_HASHES_SHA256
    for path, expected in PROTECTED_HASHES.items():
        assert (ROOT / path).is_file(), path
        assert sha256_of(ROOT / path) == expected, path
    assert sha256_of(ROOT / FRAMEWORK_RECORD) == FRAMEWORK_SHA256


def test_every_nonpermitted_file_matches_v1_0_1_tree_digest():
    """All non-release-metadata bytes and paths match the public v1.0.1 tag."""
    count, digest = nonpermitted_tree_digest(tracked_paths())
    assert count == V1_0_1_NONPERMITTED_FILE_COUNT
    assert digest == V1_0_1_NONPERMITTED_TREE_SHA256


def test_raw_npz_disposition_and_absence_are_unchanged():
    disposition = load_manifest()["tight_tail_500_disposition"]
    assert disposition["availability"] == "UNAVAILABLE_FOR_RELEASE"
    assert disposition["expected_filename"] == "tight_tail_500.npz"
    assert not list(ROOT.rglob("tight_tail_500.npz"))
    assert not any(
        path.suffix.lower() in {".npz", ".npy", ".pkl", ".pickle", ".h5", ".hdf5", ".parquet"}
        for path in ROOT.rglob("*")
        if path.is_file() and ".git" not in path.parts
    )
