# Hierarchical Triple Ejection

Causal, finite-time prediction of ejection in hierarchical triple systems and outcomes in binary-single encounters.

> **Repository status:** active research build. The simulation and audit pipelines are present; the manuscript, final survival analysis, figures, citation metadata, and license are still being assembled.

## Scientific scope

This project uses REBOUND/IAS15 integrations and physical-time observation windows to study:

- ejection by a finite integration cutoff in hierarchical triples;
- inner-member versus outer-member ejection;
- flyby, exchange, and ionization in binary-single encounters;
- warning lead time at calibrated false-alarm rates;
- time remaining to ejection;
- right-censoring and delayed ejection in a matched deep-tail sample.

The term **stable** means *not ejected by the stated integration cutoff*. It does not mean permanently stable.

## Current production samples

| Suite | Size | Integration/evaluation |
|---|---:|---|
| Main triples | 500,000 | up to 300 outer periods |
| Near-MA01 boundary triples | 100,000 | causal boundary-stratum evaluation |
| Binary-single encounters | 1,000,000 | flyby/exchange/ionization |
| Matched deep tail | 100,000 planned/running | up to 3000 outer periods |

## Leakage correction and provenance

The original stored 79-feature schema contained a future-length-dependent feature, `n_frac` (index 73). It was retired and forced to zero in corrected analyses. During repository assembly, `first_breach` (index 72) was also found to have used the full recorded length as its normalization denominator. The source now normalizes `first_breach` by the causal window length (`nmax`).

The existing adversarial audit includes a no-time-anchor ablation that excludes indices 72, 73, 74, and 76. Its performance is nearly unchanged, showing that the physical result is not driven by these anchors. Nevertheless, final paper-level outputs will be regenerated with both future-length-dependent stored columns 72 and 73 disabled.

Do not use any earlier uncorrected outputs. Result directories in this repository are retained with explicit provenance and audit metadata.

## Repository layout

```text
src/hierarchical_triple_ejection/  simulation and causal-feature package
workflows/kaggle/                  direct Kaggle production/analysis scripts
results/corrected_analysis_4core/ corrected analysis outputs (provisional: see provenance)
results/adversarial_audit_4core/  negative controls, ablations, blocked splits, fixed-FAR tests
tests/                             causal invariance and physics tests
docs/                              methods, data schema, and correction notes
paper/                             manuscript source (to be added)
figures/                           generated publication figures (to be added)
```

## Installation

```bash
python -m pip install -e .
```

Development installation:

```bash
python -m pip install -e '.[dev]'
pytest
```

## Minimal example

```python
from hierarchical_triple_ejection import TripleConfig, simulate_triple

cfg = TripleConfig(t_max_outer_periods=30, n_per_orbit=20, seed=42)
record = simulate_triple(system_id=0, cfg=cfg)
print(record["status"], record["t_event"])
```

## Reproducibility

- System initial conditions are generated deterministically from `SeedSequence([seed, system_id])`.
- Main production uses seed 42.
- Large NPZ and PKL artifacts are not committed to Git. They should be archived through a versioned data release (for example Zenodo) with checksums.
- Small JSON result products and SHA-256 manifests are committed.

## License and citation

License and author/citation metadata are intentionally pending confirmation from the repository owner.
