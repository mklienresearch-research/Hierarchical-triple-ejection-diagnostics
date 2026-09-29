# A1 Numerical Results Ledger — Release Candidate

> Numerical source for A1 manuscript values. Every value must also trace to a file pinned in `results/final_manifest.json`. Historical/provisional outputs are excluded from headline use. The ledger is release-candidate complete; final Git commit/tag is inserted at repository freeze.

## 1. Frozen protocol

```text
Main triples:       500,000 systems to 300 T_out
Boundary triples:   100,000
Binary-single:    1,000,000
Matched deep tail:  100,000 systems to 3000 T_out
Seed: 42 with deterministic system-ID SeedSequence
Stored feature mask: [0..71, 74..78]; historical indices 72/73 set to zero everywhere
Final split seed: 26001
Main split: train 299,955 / calibration 99,985 / test 99,985
Boundary split: 59,983 / 19,995 / 19,995
Encounter split: 600,000 / 200,000 / 200,000
Horizons: physical-time/in-play only; post-horizon data excluded
Warning probabilities: complete OOF or untouched fixed test, as named per table
```

Valid binary labels exclude and separately report collision/numerical failure.

## 2. Input provenance

```text
merged 500k main triples SHA-256:
187835e0b45964f8ef0c295952eb49569ce5a5f9c9ec779e490d35f7aa352687

tail IDs 0--49,999 raw chunk:
ece95247a8b3ab9c85428f78c13071b9b82f6ab5f0b2e9e0f07057ac74cd55e5

tail IDs 50,000--99,999 raw chunk:
5029ad433ce368a0763d51322976106e89a76e67ea77b1f1b9ddfee446d7c4db
```

Tail is an independent re-integration from t=0 with exactly matched ICs (`max_abs_initial_condition_difference=0`), not continuation from a 300-period state.

## 3. Population ledgers

```text
Main:     stable 325,787; ejected 174,138; numerical_error 73; collision 2
Boundary: stable  18,860; ejected  81,113; numerical_error 24; collision 3
Encounter: flyby 400,978; exchange 544,987; ionization 54,035
```

Matched tail:

```text
ejected by 100/300/1000/3000 T_out: 31.077% / 34.989% / 38.104% / 40.079%
main-stable at 300: 65,001
delayed ejection 300--3000: 4,992 (production estimate 7.6799%)
inner/outer delayed escapers: 4,977 / 15
still stable at 3000: 59,852
delayed collision: 1 (count only; no collision curve claim)
numerical failure after 300: 53
```

## 4. Main triple binary result (fixed untouched test)

| Observation | IC AUC | Window AUC | Combined AUC | Combined PR-AUC | Combined-IC gain 95% CI |
|---:|---:|---:|---:|---:|---:|
| 15 T_out | 0.9940 | 0.9901 | 0.9946 | 0.9753 | [0.00043, 0.00067] |
| 45 T_out | 0.9897 | 0.9892 | 0.9918 | 0.9274 | [0.00180, 0.00240] |
| 90 T_out | 0.9857 | 0.9885 | 0.9903 | 0.8611 | [0.00415, 0.00515] |
| 150 T_out | 0.9820 | 0.9889 | 0.9900 | 0.7642 | [0.00722, 0.00898] |
| 225 T_out | 0.9780 | 0.9894 | 0.9903 | 0.5612 | [0.01073, 0.01385] |

At target per-horizon FAR 1%:

```text
eligible coverage 94.71%
cumulative stable-system false alert 2.050%
median lead 26.03 T_out (all positive)
```

## 5. Fixed-cohort growth

Main fixed f=0.75 landmark cohort: n=66,091; future-event prevalence 1.413%.

```text
combined-IC gain slope 0.01657 per unit f
95% interval [0.01428, 0.01889]
non-decreasing fraction 0.9907 +/- 0.0025 MC SE (1,500 resamples)
```

Boundary fixed cohort: n=4,012; prevalence 5.982%.

```text
gain slope 0.06516 [0.04767, 0.08535]
non-decreasing fraction 0.8487 +/- 0.0093
```

Claim positive joint trend, not strict boundary monotonicity.

## 6. Boundary in-stratum

| f | IC AUC | Window AUC | Combined AUC | Combined PR-AUC | Gain CI |
|---:|---:|---:|---:|---:|---:|
| 0.50 | 0.9260 | 0.9606 | 0.9638 | 0.7971 | [0.0323, 0.0448] |
| 0.75 | 0.9123 | 0.9648 | 0.9665 | 0.5637 | [0.0407, 0.0683] |

At target FAR 1%: eligible coverage 86.17%, cumulative false alert 2.651%, median lead 4.76 T_out.

Corrected OOD: ranking transfers, calibration does not. At f=0.05 combined AUC 0.9849, but main-calibrated target FAR 1% becomes boundary FAR 8.99%.

## 7. Multiclass and timing

Triple combined macro-F1 (seed means): 0.7218, 0.7482, 0.7113, 0.7144, 0.4758 at 15/45/90/150/225 T_out. Confusion/per-class rows are representative seed 0. Long-horizon escaper identity is declined: 74 high-confidence outer warnings versus 24,255 outer events; 59,396/149,883 inner.

TTE:

```text
15 T_out: MAE 0.380 dex, R2 0.505
225 T_out: MAE 0.294 dex, R2 0.214
```

Landmark Cox: C-index 0.9487; leading per-SD HRs H entropy 1.074, orientation entropy 1.062, H slope 1.047, H minimum 0.969. Lead on effect sizes, not p-values.

## 8. Encounters

Combined AUC rises 0.9000 at f=0.05 to 0.9767 at f=0.95. At target FAR 1%: exchange coverage 78.51%, cumulative non-exchange false alert 3.301%, positive-lead fraction 61.9%, median all-warning lead 1.77 binary periods.

Corrected f=0.95 conditional combined AUC by v_inf/v_crit quartile: 0.9807, 0.9927, 0.9788, 0.9617. Combined multiclass macro-F1: 0.605, 0.633, 0.675, 0.775; ionization recall 0, 0, 0.112, 0.477. Ionization is supported mainly in fast, near-periastron strata.

## 9. Prospective delayed endpoint

Untouched matched cohort: n=12,809; delayed=1,011; controls=11,798; prevalence 7.893%.

Frozen original 1% thresholds:

```text
IC:       coverage 17.21%, 5 control alerts
window:   coverage 27.60%, 10 alerts
combined: coverage 24.83%, 5 alerts, precision 98.05%, median lead 424 T_out
MA01:      coverage 3.07%, 74 alerts
```

Paired combined-IC coverage difference at equal observed five-alert count: +7.616 pp [5.440, 9.844]. Retrospective equal five-control budget: +10.98 pp [1.08, 19.20]. Label retrospective row as non-prospective.

Full delayed-endpoint AUC is IC-dominated; combined improves the actionable ranking head rather than global ranking.

## 10. Low-FPR partial AUC

Standardized partial AUC (random=0.5), paired 1,000-bootstrap:

```text
Combined-IC at FPR <=1%:
15: +0.02349 [0.01067,0.03785]
45: +0.03298 [0.01614,0.04813]
90: +0.03796 [0.01992,0.05589]
150:+0.02527 [0.00399,0.04766]
225:+0.00936 [-0.01663,0.03484]
```

No learned-family superiority is detected at FPR <=0.1%; intervals include zero.

## 11. Tolerance sensitivity

Preselected 500 IDs, IAS15 epsilon 1e-11 versus production tolerance:

```text
final-status agreement 97.2%; flips 14/500=2.8% [1.68%,4.64%]
net ejection incidence 39.8% -> 38.6%, difference -1.2 pp (not significant; exact p~0.18)
```

Among 330 main-stable IDs:

```text
production delayed 29/330=8.79%
tight delayed 19/330=5.76%
delayed/not-delayed label changes 18/330=5.45%
net difference -3.03 pp, exact paired p~0.031
```

Conclusion: several-percent delayed population exists, but precise incidence and individual membership are tolerance/chaos sensitive.

Tolerance artifact hashes:

```text
preselected IDs b3d1e29b1b538a6521816552b559e353f62c30a818e5fbe7a3d867e0fb5e5986
tight NPZ       4d26c6dd876dd7b9f6e5317b20305aa0ccea890f4c60a77e25184d60feb0bc0b
report           e7e570c04bae947a86a12be4af6598c7a131fc5f444c04e850364cc450fb2434
```

## 12. Literature baseline

Same-data transfer, not reproduction of original labels:

```text
overall: V22 formula AUC 0.9966; V22 MLP 0.9965; V23 ghost MLP 0.9881
```

Combined-minus-V22 MLP AUC gain grows from +0.00262 at 15 T_out to +0.01393 at 225 T_out; all paired intervals exclude zero. At calibrated 1% FAR at 225 T_out: combined recall 65.8%, V22 formula 32.0%, V22 MLP 33.3%.

Gain decomposition versus V22 MLP:

```text
15 T_out:  total +0.00262 = endpoint-adapted IC +0.00207 + dynamics +0.00054
225 T_out: total +0.01393 = endpoint-adapted IC +0.00156 + dynamics +0.01237
```

Pinned model hashes:

```text
V22 MLP f8bc2f192813145f42683669adaef6448a287523875895343453055b3acf1436
V23 ghost a260845fc9c5b80ede3ab0028ac582bffa8450dad0c23f3ce78d73987932b866
```

Runtime scikit-learn for the separately rerun literature baseline: 1.6.1; pickle-declared version: 1.2.2. Earlier FINAL-run scikit-learn version was not captured and is not imputed.

## 13. Equal-training learning curve

Complete eligible pools: 239,179 / 218,221 / 208,467 / 202,436 / 198,196.

```text
full combined-IC gains: +0.00052, +0.00217, +0.00467, +0.00798, +0.01247
```

Both arms plateau by ~100k--200k. Small-N exaggerates late gain (0.01654 at 10k -> 0.01247 full) because IC improves faster, but the increment persists. No larger A1 simulation/training expansion is justified.

## 14. Metric provenance

- Scalar classification AUC/macro-F1 in main analysis: mean over split seeds 0--2 unless table marked fixed split.
- Confusion matrices/per-class precision-recall: representative seed 0.
- Warning coverage/lead: one fixed complete two-fold OOF assignment or named fixed untouched test.
- Bootstrap intervals: retained fixed-test scores, no refit.
- Survival/tolerance: deterministic count ledgers.

## 15. Non-final/excluded claims

- Historical 99.43%/0.99974 leakage-era values: provenance only, never headline.
- Old `boundary_ood.json` and conditional files: superseded by corrected in-play audit.
- Spike study: descriptive full-record robustness only.
- Universal curvature/tanh law: rejected negative result, repository record only.
- Long-lead outer-escaper prediction: declined for insufficient support.

## 16. Script hashes committed on release-candidate branch

```text
final analysis aed3c915...
expanded audit 7b9b4e0f...
prospective 1dae34f0...
tolerance dc262aac...
attribution growth 43954c31...
attribution precision 9794323e...
partial AUC b27c4ef2...
literature baseline ec7b13ee...
learning curve 35de5724...
```

Repository release-candidate provenance manifest: commit `f35a90e`; final merged commit/tag pending manuscript freeze. Large-data Zenodo DOI is acceptance-stage metadata and is not required for numerical ledger validity.
