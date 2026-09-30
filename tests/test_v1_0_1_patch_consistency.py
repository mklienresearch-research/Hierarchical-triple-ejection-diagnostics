"""v1.0.1 tolerance-provenance patch consistency.

The v1.0.1 patch is provenance-only: it adds a hash-pinned derived summary for the
already-closed 330-ID delayed-tolerance join, revises the tolerance disposition and
its checksums, and pins the manuscript-display generators plus the display source
manifest. It must not move any v1.0.0 scientific value.

``V1_0_0_SCIENTIFIC_VIEW_SHA256`` is the digest of the tagged v1.0.0 manifest taken
over exactly the sections this patch may not touch. If any scientific pin, ledger
row, script hash, or frozen statement drifts, that digest changes and these tests
fail. The only manifest leaves the patch is allowed to rewrite are the release
identity, the manifest version/status, the two revised tolerance records, and the
citable-tolerance wording; everything else is additive.
"""

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOLERANCE = ROOT / "results" / "tolerance"

# Digest of the v1.0.0 scientific view (see scientific_view() below), computed from
# tag v1.0.0 (results/final_manifest.json @ v1.0.0).
V1_0_0_SCIENTIFIC_VIEW_SHA256 = "eaa77eaf4660bf5e506dc062938c5b898ed6e87fdf336183ff448af3845c53a4"

# Records this patch revises in place, with their v1.0.0 and v1.0.1 SHA-256.
REVISED = {
    "results/tolerance/tolerance_raw_artifact_disposition.json": {
        "v1.0.0": "63a44d1ca7be3eef870b7dc225a406e5e9ca93c106d8b4ef736c4ac48bbcfa39",
        "v1.0.1": "a5c373605f349b9406a8536b4a310c3fd7d34b902bd89d48a1f6666942d96c6f",
    },
    "results/tolerance/SHA256SUMS.txt": {
        "v1.0.0": "53115635870bb4fd7827c861ac9daa15d055332361230d6623971489fbf28fa4",
        "v1.0.1": "7d5a420587e294b2b87b9885158de48cd665666a11a78c07b5ebb2990dcc8e23",
    },
}
ADDED = {
    "results/tolerance/delayed_tolerance_join_summary.json":
        "40c51ba011edb1ec3c6d8d0012b4de5649817af7bdb7a4199676a90b8dd21d22",
}
PATCHED = set(REVISED) | set(ADDED)

# Author package files pinned by the release manifest, expected SHA-256.
PACKAGE_FILES = {
    "docs/A1_V1.0.1_TOLERANCE_PROVENANCE_HANDOFF.md":
        "aa1bcbd401580e76edfea7cdb6e6c64efb0a65636ef843d55c61c08d8da2e0bb",
    "results/tolerance/delayed_tolerance_join_summary.json":
        "40c51ba011edb1ec3c6d8d0012b4de5649817af7bdb7a4199676a90b8dd21d22",
    "results/tolerance/tolerance_raw_artifact_disposition.json":
        "a5c373605f349b9406a8536b4a310c3fd7d34b902bd89d48a1f6666942d96c6f",
    "results/tolerance/SHA256SUMS.txt":
        "7d5a420587e294b2b87b9885158de48cd665666a11a78c07b5ebb2990dcc8e23",
    "scripts/production/make_a1_main_results_figures.py":
        "e5a55e7a7c82e5813750d0241685c70e580ca1861f2d6a0baaf6f50958011f8a",
    "scripts/production/make_a1_main_table_data.py":
        "1df4725c9e9afffd30cbdafdf4046b4b4e103caf8e06373d6c8a672f51612909",
}

# Two original package files were superseded by the author's pre-tag amendment
# (2026-09-29). The amended bytes are what the release pins; these original bytes
# stay recorded as the reversal target the amendment guards are checked against.
RECEIVED_SUPERSEDED_FILES = {
    "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json":
        "143fd26d51781846315f08c4f8a11577dd3b81d313ddf1bf380e0a42efc0789e",
    "paper/drafts/main.tex":
        "c4be2de4edf61eaa2ff1e079f133d09cb5fce0126b0e5781615626d8987fa5a4",
}

# Author pre-tag amendment package (2026-09-29): installs the matched-tolerance
# framework record and replaces those two files. Every hash is the delivered one.
AMENDMENT_FILES = {
    "docs/A1_V1.0.1_PRETAG_AMENDMENT.md":
        "27f2d9e5460befb2ea7177dfad633fb585b287e2aa72da10bcbd034ef1242416",
    "docs/provenance/FRAMEWORK_AGENT_MATCHED_TOLERANCE_JOIN.md":
        "5e48fa5034226448e7fbbf25298abe488ea507dd7cfe33f6d0724f0fa1ecf0e6",
    "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json":
        "09d8ffdf578011fd7db9228400215dc78bee0272341e4346f4837ba68daa1370",
    "paper/drafts/main.tex":
        "fdcbfdb3a8e64dc4097b3b1b8ea5a2cc35b5c271f214436cb8eaf8d1894eb063",
}

# The matched-tolerance framework record: the delayed-join summary cites the
# framework agent's handoff path, while the identical bytes are installed, per the
# author's amendment, at the canonical docs/provenance/ path.
FRAMEWORK_RECORD = "docs/provenance/FRAMEWORK_AGENT_MATCHED_TOLERANCE_JOIN.md"
FRAMEWORK_CITED_HANDOFF_PATH = (
    "docs/reviews/framework/FRAMEWORK_AGENT_MATCHED_TOLERANCE_JOIN.md")
FRAMEWORK_SHA256 = (
    "5e48fa5034226448e7fbbf25298abe488ea507dd7cfe33f6d0724f0fa1ecf0e6")

# paper/main.tex must be untouched by the whole patch chain: its content must hash
# to the git blob it has at tag v1.0.0 (computed in-tree; CI needs no tags).
SUBMISSION_MANUSCRIPT = "paper/main.tex"
SUBMISSION_MANUSCRIPT_BLOB_V1_0_0 = "c168c9f36fb5b1ceb396d10bf72afbb39cc6fa55"

# The display manifest was delivered twice: byte-frozen on receipt (b2610fa, below)
# and re-supplied amended by the author, whose bytes are the release pin.
DISPLAY_MANIFEST = "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json"
DISPLAY_MANIFEST_RECEIVED_SHA256 = \
    RECEIVED_SUPERSEDED_FILES[DISPLAY_MANIFEST]
DISPLAY_MANIFEST_AMENDED_SHA256 = \
    AMENDMENT_FILES[DISPLAY_MANIFEST]
MANUSCRIPT_DRAFT = "paper/drafts/main.tex"
MANUSCRIPT_RECEIVED_SHA256 = RECEIVED_SUPERSEDED_FILES[MANUSCRIPT_DRAFT]
MANUSCRIPT_AMENDED_SHA256 = AMENDMENT_FILES[MANUSCRIPT_DRAFT]

# The amendment's two edits to the display manifest, and their exact reversal.
# Reverse edit 1: append the Table 2 entry last instead of inserting it mid-array.
TABLE2_AMENDED_TAIL = (
    '      },\n'
    '      {\n'
    '        "release_path": "results/attribution_v2/prospective_model_attribution.json",\n'
    '        "local_path": "results/attribution_growth_v2/prospective_model_attribution.json",\n'
    '        "sha256": "fed578d6d63fc52ebe602eccba4da413a36e7e2057550d95a78111d9892f8701"\n'
    '      }\n'
)
TABLE2_RECEIVED_TAIL = '      }\n'
# Reverse edit 2: reword the release-candidate note.
NOTE_AMENDED = (
    '"release_candidate_note": "The delayed-tolerance summary, revised disposition, and '
    'complete display-input map require the v1.0.1 provenance patch before these rows '
    'are citable from the public tag."')
NOTE_RECEIVED = (
    '"release_candidate_note": "The delayed-tolerance summary and revised disposition '
    'require a patch release before these rows are citable from the public tag."')

TABLE2_CANONICAL_INPUT = "results/attribution_v2/prospective_model_attribution.json"
TABLE2_STAGING_ALIAS = "results/attribution_growth_v2/prospective_model_attribution.json"
TABLE2_CANONICAL_SHA256 = \
    "fed578d6d63fc52ebe602eccba4da413a36e7e2057550d95a78111d9892f8701"

# The amendment's single edit to the working manuscript: it names the canonical
# Table 2 attribution input in the delayed-warning provenance note. Built without a
# literal backslash so the LaTeX path macro survives any quoting context.
BS = chr(92)
_PATH = lambda ref: f"{BS}path{{{ref}}}"  # noqa: E731
DRAFT_TAIL_SCORING = "results/prospective/prospective_tail_scoring.json"
DRAFT_PRECISION = "results/attribution_precision/attribution_precision_addon.json"
DRAFT_SENTENCE_RECEIVED = (
    f"delayed-warning sources are {_PATH(DRAFT_TAIL_SCORING)} and "
    f"{_PATH(DRAFT_PRECISION)}.")
DRAFT_SENTENCE_AMENDED = (
    f"delayed-warning sources are {_PATH(DRAFT_TAIL_SCORING)}, "
    f"{_PATH(DRAFT_PRECISION)}, and {_PATH(TABLE2_CANONICAL_INPUT)}.")

BINARY_SUFFIXES = {".npz", ".npy", ".pkl", ".pickle", ".h5", ".hdf5", ".parquet"}
RAW_NPZ_NAME = "tight_tail_500.npz"


def load(path):
    with open(path) as f:
        return json.load(f)


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def manifest():
    return load(ROOT / "results" / "final_manifest.json")


def summary():
    return load(TOLERANCE / "delayed_tolerance_join_summary.json")


def disposition():
    return load(TOLERANCE / "tolerance_raw_artifact_disposition.json")


def display_manifest():
    return load(ROOT / "paper" / "display_sources" / "MAIN_DISPLAY_SOURCE_MANIFEST.json")


def scientific_view(m: dict) -> dict:
    """The v1.0.0 sections the v1.0.1 patch may not touch."""
    fh = m["frozen_hashes"]
    return {
        "final_scripts_sha256": fh["final_scripts_sha256"],
        "primary_data_sha256": fh["primary_data_sha256"],
        "committed_result_files_sha256_excluding_patch": {
            k: v for k, v in fh["committed_result_files_sha256"].items()
            if k not in PATCHED
        },
        "control_documents_sha256": fh["control_documents_sha256"],
        "tail_ledger": m["tail_ledger"],
        "runtime_environment": m["runtime_environment"],
        "canonical_form_notes": m["canonical_form_notes"],
        "partial_auc_claim_boundary": m["partial_auc_claim_boundary"],
        "release_policy": m["release_policy"],
        "tight_tail_500_disposition_raw": {
            k: m["tight_tail_500_disposition"][k]
            for k in ("expected_filename", "recorded_sha256", "availability",
                      "statement", "future_archive_rule")
        },
        "superseded_explicitly_excluded": m["superseded_explicitly_excluded"],
        "committed_but_non_authoritative": m["committed_but_non_authoritative"],
        "unresolved": m["unresolved"],
        "resolved_2026_09_27": m["resolved_2026_09_27"],
        "resolved_2026_09_29": m["resolved_2026_09_29"],
    }


def scientific_view_digest(m: dict) -> str:
    blob = json.dumps(scientific_view(m), sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True).encode()
    return hashlib.sha256(blob).hexdigest()


# --------------------------------------------------------------------- science


def test_no_v1_0_0_scientific_value_changed():
    """Strongest patch invariant: the scientific view is byte-identical to v1.0.0."""
    m = manifest()
    assert scientific_view_digest(m) == V1_0_0_SCIENTIFIC_VIEW_SHA256
    committed = m["frozen_hashes"]["committed_result_files_sha256"]
    assert len(committed) == 74                      # 71 unchanged + 2 revised + 1 added
    assert len(scientific_view(m)["committed_result_files_sha256_excluding_patch"]) == 71
    for rel in PATCHED:
        assert rel in committed


def test_only_the_patched_tolerance_records_moved():
    m = manifest()
    committed = m["frozen_hashes"]["committed_result_files_sha256"]
    for rel, hashes in REVISED.items():
        assert committed[rel] == hashes["v1.0.1"]
        assert hashes["v1.0.0"] != hashes["v1.0.1"]
        assert sha256_of(ROOT / rel) == hashes["v1.0.1"]
    for rel, want in ADDED.items():
        assert committed[rel] == want
        assert sha256_of(ROOT / rel) == want


def test_v1_0_1_patch_metadata_is_preserved_under_v1_0_2():
    m = manifest()
    assert m["manifest_version"] == "1.0.2"
    assert m["release"]["tag"] == "v1.0.2"
    assert m["release"]["url"] == m["release"]["repository"] + "/releases/tag/v1.0.2"
    assert "not amended" in m["release"]["note"]
    patch = m["v1_0_1_patch"]
    assert patch["scientific_values_changed"] is False
    assert patch["manuscript_results_changed"] is False
    assert patch["raw_npz_added_or_reconstructed"] is False
    assert "Do not amend or move tag v1.0.0" in patch["tag_policy"]


def test_release_policy_is_preserved_verbatim():
    m = manifest()
    addendum = load(ROOT / "results" / "step1_provenance_addendum.json")
    for key in ("code_and_derived_results", "large_simulation_and_score_artifacts_during_review",
                "large_zenodo_archive", "kaggle"):
        assert m["release_policy"][key] == addendum["release_policy"][key], key
    assert "not a Zenodo-first policy" in m["release_policy"]["note"]


# ------------------------------------------------------- delayed-join summary


def test_summary_cohort_counts_and_fractions():
    s = summary()
    assert s["cohort"]["n"] == 330
    assert s["production_tolerance"]["n_delayed_ejection_300_to_3000"] == 29
    assert s["tight_tolerance"]["n_delayed_ejection_300_to_3000"] == 19
    assert s["paired_label_changes"]["n_changed"] == 18
    n = s["cohort"]["n"]
    assert s["production_tolerance"]["fraction"] == 29 / n
    assert s["tight_tolerance"]["fraction"] == 19 / n
    assert s["paired_label_changes"]["fraction"] == 18 / n
    assert s["tight_tolerance"]["ias15_epsilon"] == 1e-11
    assert s["status"] == "FROZEN_DERIVED_SUMMARY_FROM_EXISTING_CLOSED_JOIN"
    assert s["scientific_change"] is False
    assert "was not reconstructed" in s["raw_artifact_status"]


def test_summary_discordant_directions_sum_to_changed_labels():
    changes = summary()["paired_label_changes"]
    down = changes["production_delayed_to_tight_not_delayed"]
    up = changes["production_not_delayed_to_tight_delayed"]
    assert (down, up) == (14, 4)
    assert down + up == changes["n_changed"] == 18
    n = summary()["cohort"]["n"]
    assert changes["net_fraction_difference_tight_minus_production"] == (up - down) / n
    # direction bookkeeping is internally consistent with the count pair
    prod = summary()["production_tolerance"]["n_delayed_ejection_300_to_3000"]
    tight = summary()["tight_tolerance"]["n_delayed_ejection_300_to_3000"]
    assert prod - down + up == tight


def test_summary_source_records_and_no_silent_skip():
    s = summary()
    records = {r["path"]: r["sha256"] for r in s["source_records"]}
    ledger = "docs/RESULTS_MANIFEST_FINAL.md"
    assert ledger in records
    assert sha256_of(ROOT / ledger) == records[ledger]
    assert records[ledger] == "54440fee9bb862e28c900250757ce686f8c7b98fccc3ee261d2ddb968b33c686"
    # The matched-join framework record was supplied by the author's pre-tag
    # amendment and is installed: the summary's declared source hash resolves to the
    # installed bytes. The gap is closed, not skipped.
    assert FRAMEWORK_CITED_HANDOFF_PATH in records
    declared = records[FRAMEWORK_CITED_HANDOFF_PATH]
    assert declared == FRAMEWORK_SHA256
    installed = ROOT / FRAMEWORK_RECORD
    assert installed.is_file(), FRAMEWORK_RECORD
    assert sha256_of(installed) == declared, "installed framework record != declared hash"
    block = manifest()["delayed_tolerance_join_summary"]
    avail = block["source_record_availability"]
    assert FRAMEWORK_CITED_HANDOFF_PATH in avail and FRAMEWORK_RECORD in avail
    assert "NOT present in this tree" not in avail
    assert FRAMEWORK_SHA256 in avail


def test_manifest_mirrors_summary_values():
    s, block = summary(), manifest()["delayed_tolerance_join_summary"]
    assert block["cohort"]["n"] == s["cohort"]["n"] == 330
    assert block["production_delayed_300_to_3000"] == \
        s["production_tolerance"]["n_delayed_ejection_300_to_3000"]
    assert block["production_fraction"] == s["production_tolerance"]["fraction"]
    assert block["tight_delayed_300_to_3000"] == \
        s["tight_tolerance"]["n_delayed_ejection_300_to_3000"]
    assert block["tight_fraction"] == s["tight_tolerance"]["fraction"]
    assert block["paired_label_changes"] == s["paired_label_changes"]
    assert block["scientific_change"] is False


# ------------------------------------------------------------- disposition


def test_disposition_pins_summary_and_keeps_raw_npz_unavailable():
    d = disposition()
    assert d["raw_artifact"]["expected_filename"] == RAW_NPZ_NAME
    assert d["raw_artifact"]["availability"] == "UNAVAILABLE_FOR_RELEASE"
    assert d["raw_artifact"]["recorded_sha256"] == \
        "4d26c6dd876dd7b9f6e5317b20305aa0ccea890f4c60a77e25184d60feb0bc0b"
    citable = d["citable_derived_artifacts"]
    assert set(citable) == {"preselected_ids", "tolerance_report",
                            "delayed_tolerance_join_summary"}
    assert citable["delayed_tolerance_join_summary"]["sha256"] == ADDED[
        "results/tolerance/delayed_tolerance_join_summary.json"]
    for name, entry in citable.items():
        assert sha256_of(ROOT / entry["path"]) == entry["sha256"], name
    assert "delayed-tolerance join summary are citable" in d["citation_rule"]
    assert "must not be silently substituted" in d["future_archive_rule"]


def test_manifest_mirrors_disposition_verbatim():
    d = disposition()
    t = manifest()["tight_tail_500_disposition"]
    for key in ("expected_filename", "recorded_sha256", "availability", "statement"):
        assert t[key] == d["raw_artifact"][key], key
    for key in ("citation_rule", "future_archive_rule"):
        assert t[key] == d[key], key
    assert t["citation_rule"] == d["citation_rule"]
    citable = t["citable_derived_artifacts"]
    assert set(citable) == set(d["citable_derived_artifacts"])
    for name, entry in citable.items():
        assert entry == d["citable_derived_artifacts"][name], name
        assert sha256_of(ROOT / entry["path"]) == entry["sha256"], name


def test_tolerance_sha256sums_verifies_and_lists_the_four_records():
    sums = TOLERANCE / "SHA256SUMS.txt"
    lines = [ln.split() for ln in sums.read_text().splitlines() if ln.strip()]
    listed = {name: digest for digest, name in lines}
    assert set(listed) == {
        "preselected_ids.txt", "tolerance_report.json",
        "delayed_tolerance_join_summary.json",
        "tolerance_raw_artifact_disposition.json",
    }
    assert len(lines) == 4
    for name, digest in listed.items():
        assert sha256_of(TOLERANCE / name) == digest, name
    assert manifest()["frozen_hashes"]["verified_checksum_files"][
        "tolerance/SHA256SUMS.txt"].startswith("4/4 entries match committed bytes")


def test_raw_tight_npz_remains_absent():
    """Author request 5: the raw tight-tolerance NPZ stays out of the release."""
    found = [str(q.relative_to(ROOT)) for q in ROOT.rglob(RAW_NPZ_NAME)]
    assert not found, f"raw NPZ present: {found}"
    disposition = manifest()["tight_tail_500_disposition"]
    assert "UNAVAILABLE_FOR_RELEASE" in json.dumps(disposition)
    assert "tight_tail_500.npz" in json.dumps(disposition)


def test_no_raw_npz_present_or_reconstructed():
    """The raw tight-tolerance NPZ must not appear anywhere, under any name."""
    assert not list(ROOT.rglob(RAW_NPZ_NAME)), "raw NPZ present; patch must not add it"
    offenders = [
        p.relative_to(ROOT).as_posix()
        for p in ROOT.rglob("*")
        if p.is_file() and p.suffix.lower() in BINARY_SUFFIXES and ".git/" not in str(p)
    ]
    assert offenders == [], offenders


# --------------------------------------------------------------- displays


def test_package_files_match_release_manifest_pins():
    m = manifest()
    pin_sets = [
        m["frozen_hashes"]["committed_result_files_sha256"],
        m["frozen_hashes"]["manuscript_display_sha256"],
        m["frozen_hashes"]["patch_control_documents_sha256"],
        m["frozen_hashes"]["provenance_documents_sha256"],
    ]
    for rel, want in PACKAGE_FILES.items():
        assert sha256_of(ROOT / rel) == want, rel
        assert any(pins.get(rel) == want for pins in pin_sets), f"{rel} not pinned in manifest"
    # the amended files are pinned at their delivered hashes: display manifest and
    # manuscript draft under manuscript_display_sha256, control/provenance docs under
    # patch_control_documents_sha256 / provenance_documents_sha256
    for rel, want in AMENDMENT_FILES.items():
        assert sha256_of(ROOT / rel) == want, rel
        assert any(pins.get(rel) == want for pins in pin_sets), f"{rel} not pinned"
    assert pin_sets[1][DISPLAY_MANIFEST] == DISPLAY_MANIFEST_AMENDED_SHA256
    assert pin_sets[1][MANUSCRIPT_DRAFT] == MANUSCRIPT_AMENDED_SHA256
    assert pin_sets[2]["docs/A1_V1.0.1_PRETAG_AMENDMENT.md"] == \
        AMENDMENT_FILES["docs/A1_V1.0.1_PRETAG_AMENDMENT.md"]
    assert manifest()["frozen_hashes"]["provenance_documents_sha256"][FRAMEWORK_RECORD] \
        == FRAMEWORK_SHA256
    assert set(manifest()["frozen_hashes"]["manuscript_display_sha256"]) == {
        "scripts/production/make_a1_main_results_figures.py",
        "scripts/production/make_a1_main_table_data.py",
        "paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json",
        "paper/drafts/main.tex",
    }


def test_display_manifest_release_sources_resolve_in_tree():
    dm = display_manifest()
    entries = {}
    for sources in dm["panel_and_table_sources"].values():
        for entry in sources:
            assert set(entry) == {"release_path", "local_path", "sha256"}, entry
            assert len(entry["sha256"]) == 64
            entries[entry["release_path"]] = entry["sha256"]
    assert len(entries) == 15, f"expected 15 unique release sources, got {len(entries)}"
    for release_path, want in entries.items():
        target = ROOT / release_path
        assert target.is_file(), release_path
        assert sha256_of(target) == want, release_path


def test_display_manifest_generated_bundle_matches_generators():
    bundle = display_manifest()["generated_display_bundle"]
    for rel in ("scripts/production/make_a1_main_results_figures.py",
                "scripts/production/make_a1_main_table_data.py"):
        assert rel in bundle
        assert bundle[rel]["sha256"] == PACKAGE_FILES[rel]
        assert bundle[rel]["bytes"] == (ROOT / rel).stat().st_size
    for rel in ("results/tolerance_validation/delayed_tolerance_join_summary.json",
                "results/tolerance_validation/tolerance_raw_artifact_disposition.json",
                "results/tolerance_validation/SHA256SUMS.txt"):
        assert rel in bundle
        canonical = ROOT / rel.replace("tolerance_validation", "tolerance")
        assert sha256_of(canonical) == bundle[rel]["sha256"]
        assert canonical.stat().st_size == bundle[rel]["bytes"]


GENERATOR_INPUT = re.compile(r"(?:RESULTS|R)\s*/\s*([\"'])([^\"']+)\1\s*/\s*([\"'])([^\"']+)\3")


def _generator_inputs(path: Path):
    text = path.read_text()
    return {(d, f) for _, d, _, f in GENERATOR_INPUT.findall(text)}


def test_generators_have_no_hard_coded_delayed_counts_and_load_the_summary():
    figures = ROOT / "scripts" / "production" / "make_a1_main_results_figures.py"
    tables = ROOT / "scripts" / "production" / "make_a1_main_table_data.py"
    for path in (figures, tables):
        src = path.read_text()
        assert "delayed_tolerance_join_summary.json" in src, path
        for literal in ("29/330", "19/330", "18/330", "0.08787878787878788",
                        "0.05757575757575758", "0.05454545454545454"):
            assert literal not in src, f"{literal} hard-coded in {path.name}"
        assert not re.search(r"n_delayed[^\n=]*=\s*(29|19|18)\b", src), path
    assert 'tol_join["production_tolerance"]["fraction"]' in figures.read_text()
    assert 'tol_join["tight_tolerance"]["fraction"]' in figures.read_text()
    assert "tol_join['production_tolerance']['fraction']" in tables.read_text()
    assert "tol_join['tight_tolerance']['fraction']" in tables.read_text()
    assert "tol_join['paired_label_changes']['n_changed']" in tables.read_text()


def test_every_generator_input_resolves_or_is_recorded():
    dm = display_manifest()
    aliases = manifest()["display_provenance"]["staging_alias_map"]
    local_to_release = {}
    for sources in dm["panel_and_table_sources"].values():
        for entry in sources:
            local_to_release[entry["local_path"]] = entry["release_path"]
    generators = [
        ROOT / "scripts" / "production" / "make_a1_main_results_figures.py",
        ROOT / "scripts" / "production" / "make_a1_main_table_data.py",
    ]
    seen = set()
    for path in generators:
        inputs = _generator_inputs(path)
        assert inputs, f"no inputs parsed from {path.name}"
        for directory, name in inputs:
            rel = f"results/{directory}/{name}"
            seen.add(rel)
            if (ROOT / rel).is_file():
                continue
            alias = aliases.get(f"results/{directory}/")
            mapped = f"{alias}{name}" if alias else None
            if mapped and (ROOT / mapped).is_file():
                continue
            release = local_to_release.get(rel)
            assert release and (ROOT / release).is_file(), (
                f"generator input {rel} does not resolve and is not recorded")
    # the input that was previously unlisted is now carried by the display manifest
    assert TABLE2_STAGING_ALIAS in seen
    assert TABLE2_STAGING_ALIAS in local_to_release
    assert local_to_release[TABLE2_STAGING_ALIAS] == TABLE2_CANONICAL_INPUT
    note = manifest()["display_provenance"]["generator_inputs_not_in_display_manifest"]
    assert note.startswith("None.")


def test_manuscript_draft_is_not_the_submission_manuscript():
    """The identifying author draft must never become the anonymous submission file."""
    draft = ROOT / "paper" / "drafts" / "main.tex"
    assert draft.is_file()
    assert sha256_of(draft) == MANUSCRIPT_AMENDED_SHA256
    # the amendment only names the canonical Table 2 input in the provenance note
    amended_text = draft.read_text()
    assert amended_text.count(DRAFT_SENTENCE_AMENDED) == 1
    reversed_bytes = amended_text.replace(
        DRAFT_SENTENCE_AMENDED, DRAFT_SENTENCE_RECEIVED, 1).encode()
    assert hashlib.sha256(reversed_bytes).hexdigest() == MANUSCRIPT_RECEIVED_SHA256
    assert "mklienresearch-research" in draft.read_text()
    submission = (ROOT / "paper" / "main.tex").read_text()
    assert "mklienresearch" not in submission.lower()
    assert "Anonymous" in submission
    note = manifest()["display_provenance"]["manuscript_draft"]
    assert "NOT the submission manuscript" in note


def test_table2_source_map_carries_canonical_attribution_v2_input():
    """The Table 2 source map lists the canonical v1.0.0-pinned attribution_v2 input."""
    table2 = display_manifest()["panel_and_table_sources"]["table2"]
    match = [e for e in table2 if e["release_path"] == TABLE2_CANONICAL_INPUT]
    assert len(match) == 1, "canonical Table 2 input must be listed exactly once"
    entry = match[0]
    assert entry["local_path"] == TABLE2_STAGING_ALIAS
    assert entry["sha256"] == \
        "fed578d6d63fc52ebe602eccba4da413a36e7e2057550d95a78111d9892f8701"
    # agrees with the v1.0.0 committed-result pin, and the bytes are present
    committed = manifest()["frozen_hashes"]["committed_result_files_sha256"]
    assert entry["sha256"] == committed[TABLE2_CANONICAL_INPUT]
    assert sha256_of(ROOT / entry["release_path"]) == entry["sha256"]
    # the generator reads the staging alias, which maps onto the canonical path
    aliases = manifest()["display_provenance"]["staging_alias_map"]
    assert aliases["results/attribution_growth_v2/"] == "results/attribution_v2/"
    src = (ROOT / "scripts" / "production" / "make_a1_main_table_data.py").read_text()
    assert "attribution_growth_v2" in src
    assert "prospective_model_attribution.json" in src


def test_display_provenance_notes_match_reality():
    """Prose counts in display_provenance must track the display manifest itself."""
    dp = manifest()["display_provenance"]
    dm = display_manifest()
    entries = {e["release_path"]
               for sources in dm["panel_and_table_sources"].values()
               for e in sources}
    assert len(entries) == 15
    assert f"All {len(entries)} unique release_path entries" in dp["verified_2026_09_29"]
    assert dp["generator_inputs_not_in_display_manifest"].startswith("None.")
    # every release_path in the display manifest is pinned somewhere in the manifest,
    # at exactly the hash the display manifest records for it
    by_path = {}
    for sources in dm["panel_and_table_sources"].values():
        for e in sources:
            by_path[e["release_path"]] = e["sha256"]
    frozen = manifest()["frozen_hashes"]
    pins = {}
    pins.update(frozen["committed_result_files_sha256"])
    pins.update(frozen["control_documents_sha256"])
    pins.update(frozen["manuscript_display_sha256"])
    for release_path, sha in by_path.items():
        assert release_path in pins, f"{release_path} not pinned in final_manifest.json"
        assert pins[release_path] == sha, f"{release_path} pin disagrees with display manifest"


def test_framework_record_is_installed_at_recorded_hash():
    """Author request 1: the delayed-join summary's declared source hash resolves."""
    summary_records = {r["path"]: r["sha256"]
                       for r in summary()["source_records"]}
    assert summary_records[FRAMEWORK_CITED_HANDOFF_PATH] == FRAMEWORK_SHA256
    installed = ROOT / FRAMEWORK_RECORD
    assert installed.is_file(), f"{FRAMEWORK_RECORD} not installed"
    assert sha256_of(installed) == FRAMEWORK_SHA256
    pins = manifest()["frozen_hashes"]["provenance_documents_sha256"]
    assert pins[FRAMEWORK_RECORD] == FRAMEWORK_SHA256
    # ... and the file is real provenance, not a stub: it carries the join counts
    # the summary already reported, unchanged.
    body = installed.read_text()
    counts = manifest()["delayed_tolerance_join_summary"]
    for token in ("330", "19", "18"):
        assert token in body, token
    assert counts["cohort"]["n"] == 330
    assert counts["production_delayed_300_to_3000"] == 29
    assert counts["tight_delayed_300_to_3000"] == 19


def test_every_generator_input_appears_in_display_source_manifest():
    """Author request 2: both generators' inputs are all named in the source map."""
    dm = display_manifest()
    listed = {e["local_path"] for sources in dm["panel_and_table_sources"].values()
              for e in sources}
    aliases = manifest()["display_provenance"]["staging_alias_map"]
    generators = [
        ROOT / "scripts" / "production" / "make_a1_main_results_figures.py",
        ROOT / "scripts" / "production" / "make_a1_main_table_data.py",
    ]
    parsed_any = False
    for path in generators:
        inputs = _generator_inputs(path)
        assert inputs, f"no inputs parsed from {path.name}"
        for directory, name in inputs:
            parsed_any = True
            rel = f"results/{directory}/{name}"
            assert rel in listed, f"{rel} opened by {path.name} but not in source map"
    assert parsed_any


def test_prospective_attribution_pin_matches_canonical_result_file():
    """Author request 3: the prospective-attribution pin is the canonical file."""
    entry = [e for e in display_manifest()["panel_and_table_sources"]["table2"]
             if e["release_path"] == TABLE2_CANONICAL_INPUT]
    assert len(entry) == 1
    entry = entry[0]
    assert entry["sha256"] == TABLE2_CANONICAL_SHA256
    assert sha256_of(ROOT / TABLE2_CANONICAL_INPUT) == TABLE2_CANONICAL_SHA256
    pins = manifest()["frozen_hashes"]["committed_result_files_sha256"]
    assert pins[TABLE2_CANONICAL_INPUT] == TABLE2_CANONICAL_SHA256
    assert pins[TABLE2_CANONICAL_INPUT] == entry["sha256"]


def test_submission_manuscript_is_untouched_by_the_patch():
    """paper/main.tex must still be the v1.0.0 anonymous submission skeleton."""
    data = (ROOT / SUBMISSION_MANUSCRIPT).read_bytes()
    blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
    assert blob == SUBMISSION_MANUSCRIPT_BLOB_V1_0_0, (
        "paper/main.tex changed: the draft must not be promoted in this patch")
    text = data.decode()
    assert "mklienresearch" not in text.lower()
    assert "Anonymous" in text


def test_display_manifest_amendment_is_purely_additive():
    """The author's two edits are the only change to the delivered display bytes."""
    path = ROOT / DISPLAY_MANIFEST
    amended = path.read_text()
    assert sha256_of(path) == DISPLAY_MANIFEST_AMENDED_SHA256
    assert amended.count(TABLE2_AMENDED_TAIL) == 1
    assert amended.count(NOTE_AMENDED) == 1
    reversed_bytes = (amended
                      .replace(TABLE2_AMENDED_TAIL, TABLE2_RECEIVED_TAIL, 1)
                      .replace(NOTE_AMENDED, NOTE_RECEIVED, 1)
                      .encode())
    assert hashlib.sha256(reversed_bytes).hexdigest() == DISPLAY_MANIFEST_RECEIVED_SHA256
    rev = manifest()["display_provenance"]["display_manifest_revision"]
    assert DISPLAY_MANIFEST_RECEIVED_SHA256 in rev
    assert DISPLAY_MANIFEST_AMENDED_SHA256 in rev
    # no displayed value moved: every other panel/table source still resolves
    for panel, sources in display_manifest()["panel_and_table_sources"].items():
        for entry in sources:
            if panel == "table2" and entry["release_path"] == TABLE2_CANONICAL_INPUT:
                continue
            assert sha256_of(ROOT / entry["release_path"]) == entry["sha256"], entry
