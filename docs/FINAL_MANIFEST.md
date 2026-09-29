# Final manifest (human companion)

Machine-readable source of truth: [`results/final_manifest.json`](../results/final_manifest.json).
Full artifact inventory: [`results/artifact_registry.json`](../results/artifact_registry.json)
and [`docs/ARTIFACT_REGISTRY.md`](ARTIFACT_REGISTRY.md).
Dataset verification evidence: [`docs/KAGGLE_DATASETS_VERIFICATION.md`](KAGGLE_DATASETS_VERIFICATION.md).

## Status: FINAL (A1 release v1.0.0)

- the nine FINAL scripts are received, hash-verified, and committed
  (see [`workflows/final/SCRIPT_REGISTRY.json`](../workflows/final/SCRIPT_REGISTRY.json));
- the §10 partial-AUC, §12 literature-baseline, and attribution-precision artifacts
  are committed receipt-verified;
- the A1 closeout control documents (freeze V3, Final ledger, provenance addendum,
  tolerance disposition) are committed and hash-verified;
- release tag `v1.0.0` is cut on merge of PR #1.

Cite the release tag (`results/final_manifest.json` → `release.url`); no commit SHA
is pinned in-manifest by design.

## Frozen script hashes (received and hash-verified)

| Script | SHA-256 |
|---|---|
| `FINAL_ANALYSIS_ALL_4CORE.py` | `aed3c915…f8fc9` |
| `FINAL_EXPANDED_AUDIT_4CORE.py` | `7b9b4e0f…a875` |
| `PROSPECTIVE_TAIL_SCORING_4CORE.py` | `1dae34f0…201f` |
| `TAIL_TOLERANCE_500_4CORE.py` | `dc262aac…0c13` |
| `ATTRIBUTION_AND_GROWTH_POSTPROCESS_V2.py` | `43954c31…10a` |
| `ATTRIBUTION_PRECISION_ADDON.py` | `9794323e…da8e` |
| `PARTIAL_AUC_POSTPROCESS.py` | `b27c4ef2…4b75` |
| `LITERATURE_BASELINE_VYNATHEYA_4CORE.py` | `ec7b13ee…0d9` |
| `TRAINING_SIZE_LEARNING_CURVE_4CORE.py` | `35de5724…8602` |

Full hashes live in `results/final_manifest.json`. Each script was verified on receipt
before commit under `workflows/final/`.

## Frozen data hashes

- `mergedtriples/merged_triples.npz` — `187835e0b45964f8…`
- `3000t-out/v2out/chunk_tail_0_of_2.npz` — `ece95247a8b3ab9c…`
- `3000t-outpart-2/chunk_tail_1_of_2.npz` — `5029ad433ce368a0…`

All three confirmed by full SHA-256 against the owner walk (2026-09-26).

## Tail ledger (verified)

| | ejected | stable | num_err | collision | total |
|---|---|---|---|---|---|
| chunk 0 (seed 42) | 20064 | 29905 | 31 | 0 | 50000 |
| chunk 1 (seed 42) | 20015 | 29948 | 36 | 1 | 50000 |
| merged | 40079 | 59853 | 67 | 1 | 100000 |

The Δ103/Δ98 values are cross-run transitions, not ledger discrepancies
(see `final_manifest.json` → `tail_ledger.delta_103_98`).

## Environment honesty

- The FINAL-run scikit-learn version was **not captured** (unpinned installs, absent
  from run logs) and must not be guessed. `requirements-release.txt` pins the
  going-forward environment instead.
- The Vynatheya pickles declare scikit-learn 1.2.2 (compatibility warnings observed
  under the Kaggle runtime).
- Simulation seed is 42 throughout.
- The separately rerun literature baseline used scikit-learn 1.6.1; that version
  applies ONLY to that workflow and is never imputed to the earlier FINAL runs.

## Canonical-form rulings

- Prospective scores: the six public NPY arrays are canonical. The original NPZ
  container hash `3978f8aa…` is provenance-only; a reconstructed NPZ gets a new hash.
- `merged_triples.npz` is uncompressed `np.savez` (≈1.82 GB); production chunks are
  compressed (≈481+482 MB). No unexplained bytes.

## Release control documents (A1 closeout)

- `controls/A1_RESEARCH_DEFINITION_FREEZE_V3.md` — `0d5ab404…`
- `docs/RESULTS_MANIFEST_FINAL.md` — `54440fee…` (Final numeric ledger; supersedes the draft)
- `results/step1_provenance_addendum.json` — `3a11572a…`
- `results/tolerance/tolerance_raw_artifact_disposition.json` — `63a44d1c…`
- `results/tolerance/SHA256SUMS.txt` — `53115635…`

Full hashes live in `results/final_manifest.json`.

## Explicitly excluded from paper claims

`results/corrected_analysis_4core/`, Kaggle attribution v1, the duplicate
`final_analysis_all_jsons/` folder, the `tail-tolernace` typo slug, and the
`OUTPUT_MANIFEST (1).json` duplicate.
