"""Release-hygiene tests: registries tell the truth, manuscript stays anonymous."""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IDENTIFYING = re.compile(r"klien|mklienresearch|m\.klienresearch@gmail\.com", re.IGNORECASE)
BINARY_SUFFIXES = {".npz", ".npy", ".pkl", ".pickle", ".h5", ".hdf5", ".parquet"}


def load(path):
    with open(path) as f:
        return json.load(f)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def test_script_registry_hashes_valid_and_received_files_match():
    reg = load(ROOT / "workflows" / "final" / "SCRIPT_REGISTRY.json")
    assert len(reg["scripts"]) == 9
    registered = set()
    for entry in reg["scripts"]:
        assert len(entry["sha256"]) == 64
        int(entry["sha256"], 16)
        assert entry["status"] in ("pending", "received")
        assert entry["name"].endswith(".py")
        registered.add(entry["name"])
        target = ROOT / "workflows" / "final" / entry["name"]
        if entry["status"] == "received":
            assert target.is_file(), entry["name"]
            assert sha256_of(target) == entry["sha256"], entry["name"]
        else:
            assert not target.exists(), f"{entry['name']} present but still pending"
    on_disk = {p.name for p in (ROOT / "workflows" / "final").glob("*.py")}
    assert on_disk <= registered, f"unregistered scripts: {on_disk - registered}"


def test_artifact_registry_matches_working_tree():
    reg = load(ROOT / "results" / "artifact_registry.json")
    seen = 0
    for dataset in reg["datasets"]:
        for entry in dataset["files"]:
            assert len(entry["sha256"]) == 64
            int(entry["sha256"], 16)
            assert entry["bytes"] > 0
            if entry["status"] == "committed":
                assert entry["placement"] == "git"
                p = ROOT / entry["repo_path"]
                assert p.is_file(), entry["repo_path"]
                assert sha256_of(p) == entry["sha256"], entry["repo_path"]
                seen += 1
            elif entry["status"] == "pending-transfer":
                assert "repo_path" in entry
                assert not (ROOT / entry["repo_path"]).exists(), (
                    f"{entry['repo_path']} present but registry still says pending"
                )
    assert seen >= 7  # the hash-verified seed files


def test_manuscript_has_no_identifying_strings():
    tex_files = [ROOT / "paper" / "main.tex", *sorted((ROOT / "paper" / "sections").glob("*.tex"))]
    assert tex_files[0].is_file()
    for path in tex_files:
        if path.is_file():
            assert not IDENTIFYING.search(path.read_text()), path


def test_no_large_binary_artifacts_in_tree():
    offenders = [
        p for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in BINARY_SUFFIXES
        and not any(part in {".git", ".venv", "venv"} for part in p.parts)
    ]
    assert offenders == [], offenders


FINAL_CONTROL_SHA256 = {
    "results/step1_provenance_addendum.json":
        "3a11572ac21eb7e80ff4b78cbc760a60a78da016699e98eb2436690f967bc778",
    "controls/A1_RESEARCH_DEFINITION_FREEZE_V3.md":
        "0d5ab404a33c8f7ba8185bb3e77be059eaf4864e2a3a7cbeb534e722989453a6",
    # revised in the v1.0.1 tolerance-provenance patch; v1.0.0 bytes stay at tag v1.0.0
    "results/tolerance/tolerance_raw_artifact_disposition.json":
        "a5c373605f349b9406a8536b4a310c3fd7d34b902bd89d48a1f6666942d96c6f",
    "results/tolerance/SHA256SUMS.txt":
        "7d5a420587e294b2b87b9885158de48cd665666a11a78c07b5ebb2990dcc8e23",
    "docs/RESULTS_MANIFEST_FINAL.md":
        "54440fee9bb862e28c900250757ce686f8c7b98fccc3ee261d2ddb968b33c686",
}


def test_final_control_documents_match_pinned_hashes():
    for rel, expected in FINAL_CONTROL_SHA256.items():
        target = ROOT / rel
        assert target.is_file(), rel
        assert sha256_of(target) == expected, rel


def test_final_manifest_is_final_and_self_consistent():
    manifest = load(ROOT / "results" / "final_manifest.json")
    assert manifest["manifest_version"] == "1.0.3"
    assert "FINAL" in manifest["status"]
    release = manifest["release"]
    assert release["tag"] == "v1.0.3"
    assert release["url"].endswith("/releases/tag/v1.0.3")
    assert not [k for k in release if "commit" in k.lower()], "no commit pin by design"
    frozen = manifest["frozen_hashes"]
    committed = frozen["committed_result_files_sha256"]
    assert len(committed) == 74  # 71 unchanged + 2 revised in-place + 1 added by v1.0.1
    for rel, expected in committed.items():
        target = ROOT / rel
        assert target.is_file(), rel
        assert sha256_of(target) == expected, rel
    controls = frozen["control_documents_sha256"]
    assert len(controls) == 2
    for rel, expected in controls.items():
        target = ROOT / rel
        assert target.is_file(), rel
        assert sha256_of(target) == expected, rel
    registry = {e["name"]: e["sha256"]
                for e in load(ROOT / "workflows" / "final" / "SCRIPT_REGISTRY.json")["scripts"]}
    for name, expected in frozen["final_scripts_sha256"].items():
        if name == "note":
            continue
        assert registry[name] == expected, name
    assert 'version: "1.0.3"' in (ROOT / "CITATION.cff").read_text()


def test_final_manifest_checklist_rows():
    manifest = load(ROOT / "results" / "final_manifest.json")
    addendum = load(ROOT / "results" / "step1_provenance_addendum.json")
    disposition = load(ROOT / "results" / "tolerance" / "tolerance_raw_artifact_disposition.json")
    # Row 5: 65,001-system main-stable-at-300 partition (addendum).
    part = addendum["tail_partition"]
    assert part["categories"] == {
        "tail_rerun_ejected_by_300": 103,
        "tail_rerun_ejected_after_300_by_3000": 4992,
        "tail_rerun_collision_after_300_by_3000": 1,
        "tail_rerun_numerical_error_after_300": 53,
        "tail_rerun_stable_censored_at_3000": 59852,
    }
    assert sum(part["categories"].values()) == part["sum"] == 65001
    assert "not delayed ejections" in part["interpretation"]
    # Row 6: slopes stay separate estimands (addendum).
    assert addendum["changing_risk_set_gain"]["slope_per_unit_f"] == 0.016922619162444908
    assert addendum["changing_risk_set_gain"]["slope_95"] == [0.014677915529109652, 0.019146152184825186]
    assert addendum["fixed_cohort_gain"]["slope_per_unit_f"] == 0.016566844611057722
    assert addendum["fixed_cohort_gain"]["slope_95"] == [0.014276002617060714, 0.01888992912108712]
    # Row 7: per-arm threshold provenance (addendum + pinned file).
    warn = addendum["warning_contract"]
    assert warn["threshold_source_path_release"] == "results/final_audit_expanded/triples_thresholds.json"
    assert warn["threshold_source_sha256"] == "d09d023f8094e63965cf58e8239bf678906051e009480761d1ebcf4ea8e6cfb8"
    assert warn["split_seed"] == 26001 and warn["main_calibration_n"] == 99985
    assert "own calibration" in warn["threshold_selection"]
    assert "without test-set recalibration" in warn["threshold_selection"]
    assert sha256_of(ROOT / warn["threshold_source_path_release"]) == warn["threshold_source_sha256"]
    # Row 8: delayed-endpoint clock and transfer status (addendum).
    delayed = addendum["delayed_warning_contract"]
    assert delayed["observation_clock"] == "f * 300 T_out, not a fraction of 3000"
    assert warn["observation_times_T_out"] == [15, 45, 90, 150, 225]
    assert "without refit or recalibration" in delayed["model_and_threshold_status"]
    assert "not prospective" in delayed["equal_budget_status"]
    # Row 9: point estimate versus interval (addendum).
    f075 = addendum["f075_reconciliation"]
    assert f075["changing_risk_set_point_gain"] == 0.012365438261640493
    assert f075["expanded_audit_gain_interval"] == [0.010733865886125588, 0.013931805803821851]
    assert f075["expanded_audit_gain_interval"][1] != f075["changing_risk_set_point_gain"]
    # Row 10: partial-AUC pins + claim boundary (manifest-side).
    auc = manifest["partial_auc_claim_boundary"]
    assert "no learned-family superiority detected at FPR <= 0.1%" in auc["boundary"]
    frozen = manifest["frozen_hashes"]
    assert frozen["final_scripts_sha256"]["PARTIAL_AUC_POSTPROCESS.py"] == \
        "b27c4ef2116d4734360dc29f513efd9bb2382aa274dae0cef1f90cb30bf04b75"
    assert frozen["committed_result_files_sha256"]["results/partial_auc/partial_auc_results.json"] == \
        "1e8b7ed1e1b5a665c308f5e9132eccaaa08e7b9e5564d21f4c8c5fa184e60602"
    assert frozen["committed_result_files_sha256"]["results/partial_auc/OUTPUT_MANIFEST.json"] == \
        "33558a01987aa30c6b6f3b23421451851e9300a420b974021c508a0b83976dc8"
    # Row 11: raw tight-NPZ disposition (manifest-side, mirrors disposition file).
    tight = manifest["tight_tail_500_disposition"]
    assert tight["expected_filename"] == "tight_tail_500.npz" == disposition["raw_artifact"]["expected_filename"]
    assert tight["recorded_sha256"] == "4d26c6dd876dd7b9f6e5317b20305aa0ccea890f4c60a77e25184d60feb0bc0b"
    assert tight["recorded_sha256"] == disposition["raw_artifact"]["recorded_sha256"]
    assert tight["availability"] == "UNAVAILABLE_FOR_RELEASE"
    assert "preselected-ID list, and delayed-tolerance join summary are citable" in tight["citation_rule"]
    assert "must not be silently substituted" in tight["future_archive_rule"]
    for art in tight["citable_derived_artifacts"].values():
        assert sha256_of(ROOT / art["path"]) == art["sha256"]
    # Row 12: release identity has tag + repository + release URL, no commit pin.
    assert manifest["release"]["tag"] == "v1.0.3"
    assert manifest["release"]["repository"] == \
        "https://github.com/mklienresearch-research/Hierarchical-triple-ejection-diagnostics"
    assert manifest["release"]["url"] == manifest["release"]["repository"] + "/releases/tag/v1.0.3"
    # Row 13: release policy exact (manifest-side, mirrors addendum).
    policy = manifest["release_policy"]
    assert policy["code_and_derived_results"] == addendum["release_policy"]["code_and_derived_results"]
    assert policy["large_simulation_and_score_artifacts_during_review"] == \
        addendum["release_policy"]["large_simulation_and_score_artifacts_during_review"]
    assert policy["large_zenodo_archive"] == addendum["release_policy"]["large_zenodo_archive"]
    assert policy["kaggle"] == addendum["release_policy"]["kaggle"]
    assert "not a Zenodo-first policy" in policy["note"]
