"""Byte-exact v1.0.3 Figure 3b transcription and provenance checks."""

import ast
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "results" / "final_manifest.json"
DISPLAY_PATH = ROOT / "paper" / "display_sources" / "MAIN_DISPLAY_SOURCE_MANIFEST.json"
FIGURE_DATA_PATH = ROOT / "paper" / "figure_data" / "fig03_robustness_endpoints.json"
SCRIPT_PATH = ROOT / "scripts" / "production" / "make_a1_main_results_figures.py"
DRAFT_PATH = ROOT / "paper" / "drafts" / "main.tex"
APPROVAL_PATH = ROOT / "docs" / "reviews" / "framework" / "A1_FIG3B_PREMERGE_APPROVAL.md"

APPROVED_FILES = {
    "scripts/production/make_a1_main_results_figures.py": (
        11542,
        "70057a0d8f87ae26ec7beb20c2e3467070b7d616c8e51b916162fac02914b9f9",
    ),
    "paper/figure_data/fig03_robustness_endpoints.json": (
        3198,
        "2ca4bbaa01c2fef3e5db19b3dfd71f0b1e08cdfc89fb88425e0a4c679d8de3d7",
    ),
    "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json": (
        10504,
        "34bc46e7f3b3eef16a1cbd22dc08bb3cd8032b5f9298e4f1d379c15b0145424a",
    ),
    "paper/drafts/main.tex": (
        47162,
        "f43b05a3e096b313859660f8b49ef8d0c611abdc5997cddd4e5614bcabeaa610",
    ),
    "docs/reviews/framework/A1_FIG3B_PREMERGE_APPROVAL.md": (
        1485,
        "eebf3a6aa8d38cb25228d1d143e64fa51136eda51a479d61740b063633b021c8",
    ),
}

TAIL_CUTOFFS = [100, 300, 1000, 3000]
TAIL_INCIDENCE = [31.077, 34.989, 38.104, 40.079]
TAIL_INPUT_MODE = (
    "hash-pinned transcription from human numerical ledger; "
    "not parsed or machine-read by this generator"
)
TAIL_SOURCE_RECORDS = [
    {
        "path": "docs/RESULTS_MANIFEST_FINAL.md",
        "sha256": "54440fee9bb862e28c900250757ce686f8c7b98fccc3ee261d2ddb968b33c686",
    },
    {
        "path": "results/step1_provenance_addendum.json",
        "sha256": "3a11572ac21eb7e80ff4b78cbc760a60a78da016699e98eb2436690f967bc778",
    },
]

# v1.0.2 baseline digests for groups that this v1.0.3 patch must not change.
V1_0_2_UNCHANGED_GROUP_SHA256 = {
    "final_scripts_sha256": "59492a019942069acadf25abec14a76fc21ab9113d2f44907a21c2d70da65823",
    "primary_data_sha256": "64c97cb6e3be8bbe4987ef674b300004b41b5b7406d96e561bf1a6b56c076646",
    "committed_result_files_sha256": "d457725767492eadd5d8a83b00e640ceb0e91d912edd3bb9eecfe10eeac87527",
    "control_documents_sha256": "9c038913b51c5eed58b6e347bf5d3e86456450d9a4394122318943f1f2223c28",
    "provenance_documents_sha256": "8ae0f8c9baa75bb83c3e3ca134d0c4ee3cda45f017078615055ec7d0da96efe1",
    "verified_checksum_files": "d1bbedd52dec57f685284694cb1b45f34cb5ce01db6bbb7e49e834492d5bee15",
}
V1_0_0_SCIENTIFIC_VIEW_SHA256 = (
    "eaa77eaf4660bf5e506dc062938c5b898ed6e87fdf336183ff448af3845c53a4"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256(path.read_bytes())


def load_json(path: Path):
    return json.loads(path.read_text())


def canonical_digest(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256(payload)


def figure3b_assignments():
    """Return the literal input lists assigned to tail_t and tail_inc in the generator."""
    tree = ast.parse(SCRIPT_PATH.read_text())
    found = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id in {"tail_t", "tail_inc"}:
            call = node.value
            assert isinstance(call, ast.Call)
            assert isinstance(call.func, ast.Attribute) and call.func.attr == "array"
            found[target.id] = ast.literal_eval(call.args[0])
    return found


def test_all_five_framework_approved_files_match_exact_bytes_and_hashes():
    for rel, (expected_bytes, expected_sha) in APPROVED_FILES.items():
        path = ROOT / rel
        data = path.read_bytes()
        assert len(data) == expected_bytes, rel
        assert sha256(data) == expected_sha, rel


def test_figure3b_json_is_exact_transcription_without_terminal_lf():
    raw = FIGURE_DATA_PATH.read_bytes()
    data = json.loads(raw)
    assert len(raw) == 3198
    assert not raw.endswith(b"\n")
    assert data["tail_cutoff_Tout"] == TAIL_CUTOFFS
    assert data["tail_cumulative_ejection_percent"] == TAIL_INCIDENCE
    assert data["tail_incidence_input_mode"] == TAIL_INPUT_MODE
    assert data["tail_incidence_sources"] == TAIL_SOURCE_RECORDS


def test_generator_uses_literal_figure3b_arrays_and_does_not_parse_the_ledger():
    arrays = figure3b_assignments()
    assert arrays["tail_t"] == TAIL_CUTOFFS
    assert arrays["tail_inc"] == TAIL_INCIDENCE
    source = SCRIPT_PATH.read_text()
    assert "explicit display transcription" in source
    assert "does not parse prose from the Markdown file" in source
    assert "does not claim that these arrays are machine-read from the source" in source
    assert TAIL_INPUT_MODE in source
    # Ledger/provenance paths are recorded in output metadata, not passed to load().
    load_calls = [
        ast.get_source_segment(source, node)
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "load"
    ]
    assert all("RESULTS_MANIFEST_FINAL.md" not in call for call in load_calls)
    assert all("step1_provenance_addendum.json" not in call for call in load_calls)


def test_figure3b_data_sources_and_access_mode_match_the_transcription_record():
    data = load_json(FIGURE_DATA_PATH)
    display = load_json(DISPLAY_PATH)
    assert data["tail_incidence_sources"] == TAIL_SOURCE_RECORDS
    entries = display["panel_and_table_sources"]["fig03_b_tail"]
    assert len(entries) == 2
    assert [
        {"path": entry["release_path"], "sha256": entry["sha256"]}
        for entry in entries
    ] == TAIL_SOURCE_RECORDS
    assert all(entry["local_path"] == entry["release_path"] for entry in entries)
    assert all(
        entry["access_mode"] == "hash-pinned transcription; source is not parsed by generator"
        for entry in entries
    )
    for record in TAIL_SOURCE_RECORDS:
        assert sha256_file(ROOT / record["path"]) == record["sha256"]


def test_only_figure3b_is_transcribed_and_all_other_panels_remain_machine_read():
    display = load_json(DISPLAY_PATH)
    modes = display["panel_generation_modes"]
    assert modes["fig03_b_tail"].startswith("hash-pinned transcription from human ledger;")
    for panel, mode in modes.items():
        if panel != "fig03_b_tail":
            assert mode == "machine-read from tagged JSON", panel
    assert "Figure 3b is an explicit hash-pinned transcription" in display["statement"]
    assert "its generator does not parse those files" in display["statement"]
    assert "no displayed value changes" in display["release_candidate_note"]
    assert len(
        {
            entry["release_path"]
            for source_list in display["panel_and_table_sources"].values()
            for entry in source_list
        }
    ) == 15


def test_display_bundle_and_final_manifest_pin_each_approved_file():
    display = load_json(DISPLAY_PATH)
    bundle = display["generated_display_bundle"]
    assert bundle["scripts/production/make_a1_main_results_figures.py"] == {
        "bytes": APPROVED_FILES["scripts/production/make_a1_main_results_figures.py"][0],
        "sha256": APPROVED_FILES["scripts/production/make_a1_main_results_figures.py"][1],
    }
    assert bundle["paper_draft/figure_data/fig03_robustness_endpoints.json"] == {
        "bytes": 3198,
        "sha256": APPROVED_FILES["paper/figure_data/fig03_robustness_endpoints.json"][1],
    }

    manifest = load_json(MANIFEST_PATH)
    pins = manifest["frozen_hashes"]["manuscript_display_sha256"]
    for rel in (
        "scripts/production/make_a1_main_results_figures.py",
        "paper/figure_data/fig03_robustness_endpoints.json",
        "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json",
        "paper/drafts/main.tex",
    ):
        assert pins[rel] == APPROVED_FILES[rel][1]
    assert manifest["frozen_hashes"]["patch_control_documents_sha256"][
        "docs/reviews/framework/A1_FIG3B_PREMERGE_APPROVAL.md"
    ] == APPROVED_FILES["docs/reviews/framework/A1_FIG3B_PREMERGE_APPROVAL.md"][1]


def test_manuscript_captions_and_provenance_describe_figure3b_honestly():
    text = DRAFT_PATH.read_text()
    assert "four plotted ladder values are an explicit hash-pinned transcription" in text
    assert "cross-checked against" in text
    assert "display generator records these values and hashes but does not parse the Markdown ledger" in text
    assert "All JSON/CSV panels are machine-read from their listed artifacts except Figure" in text
    for source in ("docs/RESULTS_MANIFEST_FINAL.md", "results/step1_provenance_addendum.json"):
        assert source in text
    assert "31.077\\% by $100" in text
    assert "34.989\\% by 300" in text
    assert "38.104\\% by 1000" in text
    assert "40.079\\% by 3000" in text


def test_final_manifest_is_v1_0_3_candidate_based_on_v1_0_2_and_holds_for_author_approval():
    manifest = load_json(MANIFEST_PATH)
    assert manifest["manifest_version"] == "1.0.3"
    assert manifest["release"]["tag"] == "v1.0.3"
    assert manifest["release"]["url"].endswith("/releases/tag/v1.0.3")
    assert manifest["v1_0_3_patch"]["base_tag"] == "v1.0.2"
    assert manifest["v1_0_3_patch"]["scientific_values_changed"] is False
    assert manifest["v1_0_3_patch"]["display_values_changed"] is False
    assert manifest["v1_0_3_patch"]["cohorts_endpoints_uncertainties_or_table_values_changed"] is False
    assert "only after author approval" in manifest["v1_0_3_patch"]["tag_policy"]
    assert "only after author approval" in manifest["release"]["note"]


def test_all_non_display_source_pins_and_v1_0_0_scientific_view_are_preserved():
    manifest = load_json(MANIFEST_PATH)
    frozen = manifest["frozen_hashes"]
    for group, expected in V1_0_2_UNCHANGED_GROUP_SHA256.items():
        assert canonical_digest(frozen[group]) == expected, group
    assert len(frozen["committed_result_files_sha256"]) == 74
    assert canonical_digest(manifest["release_policy"]) == (
        "4b6aaeda174aab041509db1169dd843361a74579392efd4a9e11db97444c074e"
    )
    # Keep the v1.0.0 scientific-view digest independent of this provenance patch.
    view = {
        "final_scripts_sha256": frozen["final_scripts_sha256"],
        "primary_data_sha256": frozen["primary_data_sha256"],
        "committed_result_files_sha256_excluding_patch": {
            key: value
            for key, value in frozen["committed_result_files_sha256"].items()
            if key not in {
                "results/tolerance/tolerance_raw_artifact_disposition.json",
                "results/tolerance/SHA256SUMS.txt",
                "results/tolerance/delayed_tolerance_join_summary.json",
            }
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
    assert canonical_digest(view) == V1_0_0_SCIENTIFIC_VIEW_SHA256


def test_paper_main_tex_remains_the_anonymous_submission_skeleton():
    path = ROOT / "paper" / "main.tex"
    data = path.read_bytes()
    assert sha256_file(path) == "8225cfe83f5a883f71f2aa0a54f1b1a5b165e40c11be232ab5663550c70020c9"
    assert b"mklienresearch" not in data.lower()
    assert b"Anonymous" in data
