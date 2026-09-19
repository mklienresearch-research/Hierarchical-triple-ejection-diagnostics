# Causal-feature correction record

## Background

Physical-time horizons are defined independently of the eventual recorded trajectory length. For the main triple sample, the horizon is `f * t_max`; for encounters it is `f * t_approach`. Systems whose event occurred before a horizon are excluded from that horizon's in-play cohort.

## Retired feature: `n_frac` (stored index 73)

The former definition was:

```python
len(window_samples) / len(full_recorded_trajectory)
```

For event-truncated records, the denominator ended at the future event. This allowed the feature to encode eventual termination time. Corrected analyses set stored column 73 identically to zero. New extraction retains a zero placeholder only for compatibility with the existing 79-column schema.

## Corrected feature: `first_breach` (stored index 72)

During repository assembly, a second full-length normalization was identified:

```python
first_breach_index / (full_record_length - 1)
```

The corrected source uses:

```python
first_breach_index / (causal_window_length - 1)
```

Existing audit results include an `all_window_no_time` model that removes `first_breach`, `n_frac`, `dur`, and `dmin_frac`. Performance changed only slightly:

- triples, f=0.05: ROC-AUC 0.9910 to 0.9906;
- triples, f=0.50: ROC-AUC 0.9882 to 0.9880;
- encounters, f=0.05: ROC-AUC 0.8850 to 0.8783;
- encounters, f=0.75: ROC-AUC 0.8996 to 0.8986.

This supports the physical robustness of the result, but final paper tables and fixed-FAR outputs must still be regenerated with stored indices 72 and 73 disabled.

## Negative controls

Shuffled-label ROC-AUC values were 0.4994–0.5033 across triple, boundary, and encounter tests. No duplicate IDs were found. Blocked physical-parameter splits and feature-family ablations are archived under `results/adversarial_audit_4core/`.

## Policy

Any future causal feature must pass an invariance test: modifying or extending samples strictly after the observation horizon must not change the extracted feature vector.
