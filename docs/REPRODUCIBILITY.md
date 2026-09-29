# Reproducibility workflow

## Small tests

```bash
python -m pip install -e '.[dev]'
pytest
```

The suite covers causal-invariance (post-horizon future extension leaves horizon
features bit-identical), the FINAL 72/73 train/serve mask, committed-result
schemas, compilation of every script, generator behavior on fixtures, and
release consistency (registries match the tree, manuscript stays anonymous, no
binary artifacts tracked).

## Pinned environment

```bash
python -m pip install -r requirements-release.txt
python -m pip install -e . --no-deps
pytest
```

The pins are the going-forward release environment (validated by the `pinned-env`
CI job on Python 3.12). They are not a record of the Kaggle FINAL runtime, whose
package versions were unpinned and uncaptured — see
`results/final_manifest.json`, `runtime_environment`. The Vynatheya baseline
pickles declare scikit-learn 1.2.2 and may warn under the pinned version.

## Verify result integrity

Each committed result directory carries `SHA256SUMS.txt`:

```bash
cd results/final_analysis_4core && sha256sum -c SHA256SUMS.txt
cd ../provenance && sha256sum -c SHA256SUMS.txt
```

Registry truth is enforced by tests:

```bash
pytest tests/test_release_consistency.py tests/test_result_schema.py
```

## Regenerate paper tables and figures

```bash
python scripts/make_release_tables.py
python scripts/make_release_figures.py
```

Tables go to `paper/tables/`, figures to `paper/figures/`. Missing inputs print
`SKIP (input pending)` and exit 0. The legacy `scripts/make_figures.py` targets
the superseded corrected-analysis layout; do not use it for the A1 paper.

## Kaggle production scripts

- `workflows/final/` — the nine frozen FINAL scripts (receipt tracked in
  `SCRIPT_REGISTRY.json`; each MUST hash-verify on arrival). Paper outputs come
  only from these.
- `workflows/kaggle/` — earlier direct-Kaggle scripts, retained for provenance.

## Large artifacts

NPZ/NPY/PKL files are blocked by `.gitignore` and asserted absent by CI. They
are recorded by filename/size/SHA-256 in `results/artifact_registry.json`,
staged during review, and deposited on Zenodo upon acceptance after re-verification.
