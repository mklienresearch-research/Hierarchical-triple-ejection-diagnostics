# Data schema

## Triple NPZ fields

- `ids`: deterministic integer system IDs.
- `statuses`: `stable`, `ejected`, `collision`, `numerical_error`, or timeout status.
- `labels`: binary ejection labels used during production.
- `exchange`: whether the final most-bound pair differs for a non-ejected system.
- `escaper`: body index for ejections; `-1` otherwise.
- `t_event`: event time in simulation units; NaN if censored at cutoff.
- `t_max`: per-system integration cutoff in simulation units.
- `E0`: initial total energy.
- `max_rel_err`: maximum recorded relative energy error.
- `ic`: packed initial-condition vector.
- `feats`: `(N, horizons, 79)` causal-window feature tensor when present.
- `fractions`: physical-horizon fractions.

## Deep-tail NPZ fields

The matched 3000-outer-period survival product intentionally omits `feats` and trajectory series. It retains IDs, outcomes, event/censoring times, initial conditions, and numerical-quality fields.

## Stored feature compatibility

The historical tensor has 79 columns. Index 73 (`n_frac`) is deprecated and must be zero. Existing stored index 72 (`first_breach`) is excluded from final analysis until regenerated; new extraction uses causal-window normalization.

## Large artifacts

NPZ and PKL files are intentionally ignored by Git. A public data release should contain:

1. immutable artifacts;
2. SHA-256 checksums;
3. simulation and analysis commit hashes;
4. environment/package versions;
5. a machine-readable manifest.
