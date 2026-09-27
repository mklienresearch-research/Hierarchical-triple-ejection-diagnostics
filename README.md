# Hierarchical Triple Ejection Diagnostics

Causal, finite-time forecasting of ejection in hierarchical triple systems and of outcomes in binary–single encounters — with calibrated warning lead times and censoring-aware validation.

> **Release status:** A1 release candidate (INTERIM). Hashes are frozen in
> [`results/final_manifest.json`](results/final_manifest.json), but the nine
> FINAL scripts and the §10/§12 products are not yet committed and **no tag has
> been cut**. Do not cite a frozen commit until the manifest status reads FINAL
> (see [`docs/FINAL_MANIFEST.md`](docs/FINAL_MANIFEST.md)).

## Scientific scope

REBOUND/IAS15 integrations plus physical-time observation windows are used to study:

- ejection by a finite integration cutoff in hierarchical triples;
- inner-member versus outer-member ejection;
- flyby, exchange, and ionization in binary–single encounters;
- warning lead time at calibrated false-alarm rates;
- time remaining to ejection;
- right-censoring and delayed ejection in a matched deep-tail sample.

The term **stable** means *not ejected by the stated integration cutoff*. It does not mean permanently stable. High IID discrimination is not exact prediction of chaotic trajectories; the boundary suite, blocked splits, PR curves, and fixed-FAR tests are the stringent checks.

## Production samples (final)

| Suite | Size | Integration / evaluation |
|---|---:|---|
| Main triples | 500,000 | to 300 outer periods, seed 42 |
| Near-MA01 boundary triples | 100,000 | causal boundary-stratum evaluation |
| Binary–single encounters | 1,000,000 | flyby / exchange / ionization |
| Matched deep tail | 100,000 (2 × 50,000) | to 3000 outer periods, seed 42 |

Deep-tail ledger (verified): chunk 0 ejected 20,064 / chunk 1 ejected 20,015; merged ejected 40,079, stable 59,853, numerical-error 67, collision 1.

## Leakage policy (FINAL)

The historical 79-column stored schema contained two future-length-dependent columns: index 73 (`n_frac`) and index 72 (`first_breach` under full-record normalization). In every FINAL model input, **both are identically zero at training and serving time** (see `results/final_analysis_4core/analysis_audit.json`, the `apply_final_mask` helper, and `docs/LEAKAGE_CORRECTION.md`). New extraction keeps a zero placeholder at 73 and normalizes 72 by the causal window. Invariance tests require post-horizon modifications to leave feature vectors bit-identical.

## Explicitly superseded (do not use for paper claims)

- `results/corrected_analysis_4core/` — index 73 only; superseded by `results/final_analysis_4core/`.
- `workflows/kaggle/CORRECTED_*` and earlier `FINAL_*` drafts — provenance only; paper outputs come from `workflows/final/` (frozen nine, receipt tracked in `SCRIPT_REGISTRY.json`).
- Kaggle `attribution-growth` v1 — superseded by `attribution-growth-v2`.
- `results/adversarial_audit_4core/` remains valid as the adversarial-controls record.

## Review / release policy

- During review the manuscript cites the frozen GitHub release only if compatible with ApJ dual-anonymous instructions; otherwise the commit/archive goes privately to editor/referees. The manuscript never cites Kaggle datasets.
- Large NPZ/PKL products stay staged (available to editor/referees on request) and are deposited on Zenodo upon acceptance, verified against [`results/artifact_registry.json`](results/artifact_registry.json). See [`docs/ARTIFACT_REGISTRY.md`](docs/ARTIFACT_REGISTRY.md).

## Repository layout

```text
src/hierarchical_triple_ejection/  simulation and causal-feature package
workflows/final/                   frozen FINAL run scripts + SHA-256 registry
workflows/kaggle/                  earlier direct-Kaggle scripts (provenance)
results/final_analysis_4core/      FINAL analysis JSONs (hash-verified on arrival)
results/final_audit_expanded/      expanded audit JSONs + checksums (NPZs excluded)
results/provenance/                chunk metas, deep-tail manifest + checksums
results/final_manifest.json        frozen hashes, ledger, unresolved fields
results/artifact_registry.json     95-file artifact map + Zenodo plan
scripts/make_release_tables.py     machine-checked LaTeX tables from results
scripts/make_release_figures.py    machine-checked figures from results
tests/                             invariance, mask, schema, compilation, release tests
docs/                              methods, manifests, registries, verification log
paper/                             anonymous AASTeX manuscript (structure; prose by manuscript agent)
```

## Installation

Pinned release environment:

```bash
python -m pip install -r requirements-release.txt
python -m pip install -e . --no-deps
pytest
```

Development installation:

```bash
python -m pip install -e '.[dev]'
pytest
```

## Reproduce tables and figures

```bash
python scripts/make_release_tables.py
python scripts/make_release_figures.py
```

Outputs land in `paper/tables/` and `paper/figures/`. Inputs that have not arrived yet print `SKIP (input pending)` lines; see `results/*/PENDING.json` and [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## License and citation

The software is released under the [MIT License](LICENSE). Citation metadata are provided in [`CITATION.cff`](CITATION.cff); the release DOI is minted on acceptance.
