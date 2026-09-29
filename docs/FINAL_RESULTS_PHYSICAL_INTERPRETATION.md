# Final Results: Physical Interpretation and Paper-Level Meaning

## Status and provenance

This document interprets the final 72/73-neutralized four-core analysis of:

- 500,000 hierarchical triples to 300 outer periods;
- 100,000 near-MA01 boundary triples;
- 1,000,000 binary-single encounters;
- 100,000 exactly matched triples followed to 3000 outer periods.

Stored historical feature indices 72 (`first_breach`, old normalization) and 73 (`n_frac`) were disabled before refitting. Earlier analysis products are provenance only and must not supply headline paper numbers.

---

## 1. Meaning of ROC-AUC and macro-F1

ROC-AUC is a ranking statistic. An AUC of 0.989 means that a randomly selected future event receives a higher score than a randomly selected non-event approximately 98.9% of the time. It does not mean 98.9% accuracy, calibrated probabilities, negligible false alarms, or universal early-warning coverage.

Macro-F1 gives every outcome class equal weight. It is therefore more informative than ordinary accuracy for rare outer-ejection and ionization classes. PR-AUC and calibrated fixed-FAR recall remain essential because event prevalence falls strongly at late horizons.

---

## 2. Triple binary prediction

| Observation horizon | IC AUC | Window AUC | Combined AUC |
|---:|---:|---:|---:|
| 15 T_out | 0.9938 | 0.9900 | 0.9944 |
| 45 T_out | 0.9898 | 0.9892 | 0.9918 |
| 90 T_out | 0.9858 | 0.9887 | 0.9902 |
| 150 T_out | 0.9819 | 0.9882 | 0.9893 |
| 225 T_out | 0.9763 | 0.9886 | 0.9894 |

The broad synthetic population is highly predictable from initial conditions. The combined improvement over IC-only increases with time:

```text
15 T_out:   +0.0006
45 T_out:   +0.0020
90 T_out:   +0.0044
150 T_out:  +0.0074
225 T_out:  +0.0131
```

IC discrimination declines as early events leave the risk set, while causal-window discrimination remains nearly constant. The physical result is therefore not merely high AUC: initial conditions encode broad finite-time risk, while measured dynamical evolution becomes increasingly important among long-lived survivors.

### High-confidence warning lead

At P >= 0.9:

```text
Total ejections:                   174,138
Warned ejections:                   50,821
Coverage of all ejections:           29.2%
Approx. first-horizon-eligible coverage: 69.6%
Median lead:                        16.53 T_out
Interquartile range:              5.77--42.05 T_out
Positive-lead fraction:             100%
```

The all-event coverage is limited because many ejections occur before the first 15-T_out observation horizon. Final paper operating points should use calibration-set FAR thresholds rather than the arbitrary P=0.9 threshold.

---

## 3. Escaper identity

```text
Stable/censored:  325,787
Outer ejection:    24,255
Inner ejection:   149,883
```

Approximately 86% of ejections involve an inner member. This demonstrates why a tertiary-only escape criterion is incomplete.

Combined macro-F1:

```text
15 T_out:   0.7218
45 T_out:   0.7482
90 T_out:   0.7113
150 T_out:  0.7144
225 T_out:  0.4758
```

At 45 T_out, window recalls are approximately stable=0.98, outer-eject=0.27, inner-eject=0.83. At 225 T_out, outer-eject recall falls to zero and inner-eject recall to 0.32.

High-confidence event-class warnings:

```text
Inner-eject warnings: 59,396; median lead 27.54 T_out
Outer-eject warnings:     74; median lead 13.65 T_out
```

Generic disruption risk is much easier to predict than escaper identity. Useful early outer-escaper identification has not been demonstrated.

---

## 4. Remaining time to ejection

The regression target is log10[(t_event - t_h)/T_out].

| f | MAE (dex) | R2 | Approx. multiplicative error |
|---:|---:|---:|---:|
| 0.05 | 0.3803 | 0.505 | x2.40 |
| 0.15 | 0.3459 | 0.406 | x2.22 |
| 0.30 | 0.3244 | 0.339 | x2.11 |
| 0.50 | 0.3031 | 0.293 | x2.01 |
| 0.75 | 0.2936 | 0.214 | x1.97 |

Broad event risk is predictable, but exact event timing remains substantially chaotic. The declining MAE and declining R2 are compatible because the remaining-time distribution narrows at late horizons.

---

## 5. Landmark hazard model

The corrected landmark Cox model at f=0.5 has C-index 0.949. Leading standardized effects include:

```text
H entropy:      HR 1.074
Omega entropy:  HR 1.062
H slope:        HR 1.047
H minimum:      HR 0.969
```

The very small p-values primarily reflect sample size. Interpretation should emphasize modest effect sizes and high concordance: complexity and variability raise hazard, while stronger retained hierarchy lowers hazard.

---

## 6. Boundary systems

| Horizon fraction | IC AUC | Window AUC | Combined AUC |
|---:|---:|---:|---:|
| 0.05 | 0.9829 | 0.9846 | 0.9872 |
| 0.15 | 0.9652 | 0.9745 | 0.9775 |
| 0.30 | 0.9460 | 0.9675 | 0.9704 |
| 0.50 | 0.9275 | 0.9612 | 0.9640 |
| 0.75 | 0.9099 | 0.9636 | 0.9667 |

At f=0.75, combined exceeds IC-only by 0.0568. This is stronger evidence for causal dynamical diagnostics than broad-population AUC. Near the analytic boundary, ICs become insufficient and realized hierarchy variability, energy exchange, and torque history add substantial information.

Boundary warning summary:

```text
All-event coverage: approximately 43.6%
Eligible-event coverage: approximately 89.6%
Median lead: 5.31 T_out
```

The shorter lead reflects proximity to instability.

---

## 7. MA01 interpretation

MA01 flags 52,391/500,000 systems (10.5%) as unstable. Early in-play recall is 9.33% and declines later. This does not invalidate MA01: it is an analytic stability boundary, not a calibrated predictor of ejection in a selected future interval. The final audit must compare continuous MA01 margin at the same per-horizon FAR as other scores.

---

## 8. Torque-spike robustness

```text
Raw overlap:                0.16
Median-normalized overlap:  0.30
Orbital-normalized overlap: 0.26
```

Normalization reduces separation. Absolute torque excursions contain outcome information; aggressive normalization erases signal. This is a negative robustness result, not a central predictive claim.

---

## 9. Binary-single exchange prediction

| f | IC AUC | Window AUC | Combined AUC |
|---:|---:|---:|---:|
| 0.05 | 0.8884 | 0.8862 | 0.9000 |
| 0.35 | 0.8825 | 0.8832 | 0.8993 |
| 0.65 | 0.8775 | 0.8848 | 0.9080 |
| 0.75 | 0.8753 | 0.8984 | 0.9193 |
| 0.85 | 0.8728 | 0.9302 | 0.9442 |
| 0.95 | 0.8701 | 0.9740 | 0.9767 |

ICs dominate far from interaction; close-approach dynamics resolve exchange versus non-exchange. Combined improvement over IC-only rises from 0.0116 at f=0.05 to 0.1066 at f=0.95.

At P >= 0.9:

```text
Warned exchanges:       416,730 / 544,987 (76.5%)
Positive pre-periastron fraction: 62.7%
Median lead, all warnings: 2.18 binary periods
Median positive lead:     5.13 binary periods
```

Approximately 37.3% of warnings occur after periastron, so pre-, near-, and post-periastron decisions must be separated.

---

## 10. Encounter multiclass outcomes

Combined macro-F1:

```text
f=0.05: 0.5949
f=0.35: 0.5908
f=0.75: 0.6191
f=0.85: 0.6442
f=0.95: 0.7577
```

At f=0.95, recalls are flyby=0.95, exchange=0.91, ionization=0.30. Flyby and exchange become highly recognizable, while ionization remains difficult.

```text
Flyby decisions:     347,304; median lead  2.04 periods
Exchange decisions:  487,247; median lead  4.81 periods
Ionization decisions:  3,237; median lead -0.25 periods
```

Only about 6% of ionizations receive a high-confidence correct decision, and the median occurs after periastron. Ionization is usually recognized during or after the strongest interaction rather than forecast well in advance.

---

## 11. Matched deep tail and right-censoring

```text
Stable at 300 T_out:                  65,001
Ejected from 300 to 3000 T_out:        4,992
Delayed-ejection fraction:             7.680%
Binomial SE:                            0.104 percentage points
Still stable at 3000 T_out:           59,852
Delayed collision:                         1
Numerical failures after 300:             53
```

Ejection ladder:

```text
100 T_out:  31.077%
300 T_out:  34.989%
1000 T_out: 38.104%
3000 T_out: 40.079%
```

Delayed escapers:

```text
Inner member: 4,977
Outer member:    15
```

A non-negligible fraction of systems unejected at 300 outer periods disrupt later. Stable labels are therefore right-censored and horizon-dependent. The 99.795% outcome agreement through 300 T_out motivates the precommitted tighter-tolerance 300--500-system numerical-sensitivity test before a final uncertainty is assigned.

---

## 12. Outputs requiring protocol repair before causal use

The following secondary outputs are not final causal evidence:

1. `boundary_ood.json`: the transfer helper did not apply matched in-play masks consistently.
2. `enc_conditional.json`: velocity-stratified helper did not apply a separate in-play mask at every horizon.
3. `enc_multiclass_conditional.json`: same issue for multiclass strata.
4. `spike_study.json`: first 80% of each recorded trajectory is not one shared physical horizon; descriptive only.

These issues do not affect the primary in-play triple, boundary, encounter, decision-time, TTE, or Cox curves. They must be repaired or relabelled in the expanded audit.

---

## 13. Overall paper-level conclusions

1. Finite-time triple ejection risk is highly rankable from initial conditions across the broad population.
2. Causal dynamical history becomes increasingly valuable among long-lived and near-boundary systems.
3. Binary disruption is easier to predict than exact event time or escaper identity.
4. Inner-member ejections dominate prompt and delayed disruption.
5. Binary-single exchange becomes predictable near periastron, but ionization is rarely forecast early.
6. Approximately 7.68% of systems unejected at 300 periods eject by 3000 periods.
7. Hierarchy, energy exchange, entropy, torque, and closest-approach diagnostics provide the signal; no universal gauge-curvature law is supported or required.

The novelty is the combination of physical-time causal windows, in-play evaluation, IC-versus-dynamical decomposition, near-boundary validation, escaper-resolved outcomes, calibrated warning lead, one-million encounter outcomes, and matched long-horizon censoring.
