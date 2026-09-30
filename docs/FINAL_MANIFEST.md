# Final manifest (human companion)

Machine-readable source of truth: [`results/final_manifest.json`](../results/final_manifest.json).
Full artifact inventory: [`results/artifact_registry.json`](../results/artifact_registry.json)
and [`docs/ARTIFACT_REGISTRY.md`](ARTIFACT_REGISTRY.md).
Dataset verification evidence: [`docs/KAGGLE_DATASETS_VERIFICATION.md`](KAGGLE_DATASETS_VERIFICATION.md).

## Status: A1 science FINAL; v1.0.2 public; v1.0.3 pre-tag candidate pending author approval

- the nine FINAL scripts are received, hash-verified, and committed
  (see [`workflows/final/SCRIPT_REGISTRY.json`](../workflows/final/SCRIPT_REGISTRY.json));
- the §10 partial-AUC, §12 literature-baseline, and attribution-precision artifacts
  are committed receipt-verified;
- the A1 closeout control documents (freeze V3, Final ledger, provenance addendum,
  tolerance disposition) are committed and hash-verified;
- release tag `v1.0.0` is cut on merge of PR #1;
- `v1.0.1` adds the hash-pinned delayed-tolerance join summary, revises the tolerance
  disposition + checksums, and pins the display generators. **No scientific value
  changed:** `tests/test_v1_0_1_patch_consistency.py` re-derives a digest over the
  frozen v1.0.0 scientific view and requires it to be unchanged, and the raw
  `tight_tail_500.npz` remains unavailable;
- `v1.0.2` is a manifest-consistency patch only: it resolves the framework-record
  availability wording to the installed, hash-pinned canonical record and corrects
  the stale display-source statement to 15 unique `release_path` sources;
- proposed `v1.0.3` corrects Figure 3b provenance only. Its four plotted cutoff and
  incidence pairs are a hash-pinned transcription from the human numerical ledger
  and provenance addendum, not a machine-read ledger input. All values, scientific
  results, cohorts, endpoints, uncertainties, table values, and non-patch source
  pins are unchanged; every other panel/table remains machine-read. All five
  approved files and the framework approval record are pinned and byte-verified.

`v1.0.2` is the latest public release until the author approves this candidate.
Do not merge, tag, or release v1.0.3 before approval. The candidate manifest records
no commit SHA by design.

## Proposed v1.0.3 pre-tag record

- Base: public tag `v1.0.2`; proposed tag: `v1.0.3` (not yet created).
- Figure 3b cutoffs: `100/300/1000/3000`; cumulative incidence: `31.077/34.989/38.104/40.079` percent.
- Input mode: explicit, hash-pinned transcription from `docs/RESULTS_MANIFEST_FINAL.md`
  (`54440fee9bb862e28c900250757ce686f8c7b98fccc3ee261d2ddb968b33c686`) and
  `results/step1_provenance_addendum.json`
  (`3a11572ac21eb7e80ff4b78cbc760a60a78da016699e98eb2436690f967bc778`); the
  generator does not parse either source. All other panels/tables stay machine-read.
- Approved release files (all bytes installed as supplied):

  | Path | Bytes | SHA-256 |
  |---|---:|---|
  | `scripts/production/make_a1_main_results_figures.py` | 11,542 | `70057a0d8f87ae26ec7beb20c2e3467070b7d616c8e51b916162fac02914b9f9` |
  | `paper/figure_data/fig03_robustness_endpoints.json` | 3,198 | `2ca4bbaa01c2fef3e5db19b3dfd71f0b1e08cdfc89fb88425e0a4c679d8de3d7` |
  | `paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json` | 10,504 | `34bc46e7f3b3eef16a1cbd22dc08bb3cd8032b5f9298e4f1d379c15b0145424a` |
  | `paper/drafts/main.tex` | 47,162 | `f43b05a3e096b313859660f8b49ef8d0c611abdc5997cddd4e5614bcabeaa610` |
  | `docs/reviews/framework/A1_FIG3B_PREMERGE_APPROVAL.md` | 1,485 | `eebf3a6aa8d38cb25228d1d143e64fa51136eda51a479d61740b063633b021c8` |

- No scientific or displayed value, cohort, endpoint, uncertainty, or table value changes.
  All other source/result/control-file bytes and pins remain preserved. No raw NPZ
  was added or reconstructed.


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
- `results/tolerance/tolerance_raw_artifact_disposition.json` — `a5c37360…` (v1.0.1 revision)
- `results/tolerance/delayed_tolerance_join_summary.json` — `40c51ba0…` (v1.0.1 addition)
- `results/tolerance/SHA256SUMS.txt` — `7d5a4205…` (v1.0.1 revision)
- `scripts/production/make_a1_main_results_figures.py` — `70057a0d…` (v1.0.3 Figure 3b provenance correction)
- `scripts/production/make_a1_main_table_data.py` — `1df4725c…` (unchanged)
- `paper/figure_data/fig03_robustness_endpoints.json` — `2ca4bbaa…` (v1.0.3 Figure 3 source JSON)
- `paper/display_sources/MAIN_DISPLAY_SOURCE_MANIFEST.json` — `34bc46e7…` (v1.0.3 approved bytes)
- `paper/drafts/main.tex` — `f43b05a3…` (v1.0.3 author draft; not the submission manuscript)
- `docs/A1_V1.0.1_PRETAG_AMENDMENT.md` — `27f2d9e5…`
- `docs/provenance/FRAMEWORK_AGENT_MATCHED_TOLERANCE_JOIN.md` — `5e48fa50…` (canonical installed record)
- `docs/reviews/framework/A1_FIG3B_PREMERGE_APPROVAL.md` — `eebf3a6a…` (framework pre-merge approval record)

The v1.0.0 bytes of the two revised tolerance records remain retrievable from
tag `v1.0.0`; they were revised in place rather than duplicated.

Full hashes live in `results/final_manifest.json`.

## Explicitly excluded from paper claims

`results/corrected_analysis_4core/`, Kaggle attribution v1, the duplicate
`final_analysis_all_jsons/` folder, the `tail-tolernace` typo slug, and the
`OUTPUT_MANIFEST (1).json` duplicate.
