# Artifact / data registry (human companion)

Machine-readable source of truth: [`results/artifact_registry.json`](../results/artifact_registry.json)
(114 files across 12 Kaggle datasets, every entry with bytes + SHA-256).
Frozen release hashes: [`results/final_manifest.json`](../results/final_manifest.json).

## Placement rules

| Placement | Meaning |
|---|---|
| `git` | Small JSON/TXT/CSV (roughly ≤ 100 KB) committed under `results/` after hash verification. |
| `zenodo` | NPZ/NPY/PKL and multi-MB CSV/JSON: recorded here, staged pre-acceptance, deposited on Zenodo upon acceptance. Never in git. |
| `record` | Superseded/duplicates: provenance only. |

## Review-stage policy (binding)

- The manuscript cites the frozen GitHub code/results release **only if compatible
  with ApJ dual-anonymous instructions**; otherwise the commit/archive goes privately
  to editor/referees and the public URL appears in the accepted version.
- Large NPZ/PKL products stay in staging and are available to editor/referees on request.
- **Do not cite Kaggle datasets in the manuscript.**

Suggested review-stage Data Availability wording:

> The frozen analysis code and machine-readable derived results are available in a
> versioned GitHub repository [anonymous/private-review reference as required]. The
> multi-gigabyte simulation products will be deposited in a versioned Zenodo archive
> upon acceptance and are available to the editor and referees during review.

## Acceptance-stage policy

1. Verify every staged file against `results/artifact_registry.json` (SHA-256 + bytes).
2. Deposit the verified bundle as a versioned Zenodo archive.
3. Mint the DOI; update Data Availability, GitHub release notes, and proofs.

Suggested accepted-version wording:

> Source code, tests, derived result tables, and figure-generation workflows are
> available at [GitHub release/commit]. The versioned simulation and score archives
> are available at Zenodo [DOI], with SHA-256 manifests and machine-readable schemas.

## Kaggle-side cleanup (owner track, analysis agent confirmed 2026-09-27)

- Recreate `tail-tolernace` as `tail-tolerance-validation`; mark the old slug superseded.
- Delete `OUTPUT_MANIFEST (1).json` from `trainingcurve`.
- Standardize on CC BY-SA 4.0 for data/result datasets (software stays MIT); add the
  one-paragraph data card to every dataset page.
- Mark `attribution-growth` v1 superseded by `attribution-growth-v2`.
- Delete duplicate `final_analysis_all_jsons/`; keep `analysis_final_4core/`.
- Align both tail chunks under `v2out/chunk_tail_{0,1}_of_2.npz` in the archival version.
- Ship SHA256SUMS + manifest + metas for `v2chunks/` and `mergedtriples/` without
  modifying NPZ bytes.
- Publish §10 partial-AUC and §12 literature-baseline artifacts (currently not public).

## Receiving files into git

1. Copy the file to its `repo_path` from the registry.
2. `sha256sum` it; the hash MUST equal the registry entry (and the directory
   `PENDING.json` entry, where present).
3. Append it to the directory `SHA256SUMS.txt`, remove it from `PENDING.json`,
   and flip the registry status to `committed`.
4. Never `git add` an `.npz`, `.npy`, `.pkl`, or `.pickle` — the `.gitignore`
   blocks them and CI asserts none are tracked.
