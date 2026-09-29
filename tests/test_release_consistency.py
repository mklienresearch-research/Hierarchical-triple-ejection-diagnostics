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
        if p.is_file() and p.suffix.lower() in BINARY_SUFFIXES and ".git/" not in str(p)
    ]
    assert offenders == [], offenders


FINAL_CONTROL_SHA256 = {
    "results/step1_provenance_addendum.json":
        "3a11572ac21eb7e80ff4b78cbc760a60a78da016699e98eb2436690f967bc778",
    "controls/A1_RESEARCH_DEFINITION_FREEZE_V3.md":
        "0d5ab404a33c8f7ba8185bb3e77be059eaf4864e2a3a7cbeb534e722989453a6",
    "results/tolerance/tolerance_raw_artifact_disposition.json":
        "63a44d1ca7be3eef870b7dc225a406e5e9ca93c106d8b4ef736c4ac48bbcfa39",
    "results/tolerance/SHA256SUMS.txt":
        "53115635870bb4fd7827c861ac9daa15d055332361230d6623971489fbf28fa4",
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
    assert manifest["manifest_version"] == "1.0.0"
    assert "FINAL" in manifest["status"]
    release = manifest["release"]
    assert release["tag"] == "v1.0.0"
    assert release["url"].endswith("/releases/tag/v1.0.0")
    assert not [k for k in release if "commit" in k.lower()], "no commit pin by design"
    frozen = manifest["frozen_hashes"]
    committed = frozen["committed_result_files_sha256"]
    assert len(committed) == 73
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
    assert 'version: "1.0.0"' in (ROOT / "CITATION.cff").read_text()
