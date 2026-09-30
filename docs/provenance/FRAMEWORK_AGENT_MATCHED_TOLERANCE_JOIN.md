# Matched tolerance join: delayed-endpoint sensitivity

## Data integrity

Public `klienm/tail-tolernace` contains the precommitted 500 IDs, `tight_tail_500.npz`, and `tolerance_report.json`. The IDs match seed 20260922. The tighter run uses REBOUND 5.2.0 and IAS15 epsilon 1e-11.

## Overall 3000-period outcome

```text
baseline: ejected 199, stable 300, numerical_error 1
tight:    ejected 193, stable 307
agreement: 486/500 = 97.2%
individual final-status flips: 14/500 = 2.8% [Wilson 95%: 1.68%--4.64%]
```

The net ejection fraction changes from 39.8% to 38.6% (-1.2 pp); the paired direction test is not significant (exact p≈0.18). Population cumulative incidence is more stable than individual identity.

## Main-stable subset and delayed endpoint

Of the 500 preselected IDs, 330 were labelled stable/censored in the main 300-period run.

### Baseline tail classification of those 330

```text
delayed ejection (300--3000): 29
stable at 3000:              300
numerical error:               1
baseline delayed fraction: 29/330 = 8.79%
```

### Tight-tail classification of the same 330 main-stable IDs

```text
delayed ejection (300--3000): 19
ejection before/equal 300:     4
stable at 3000:               307
numerical error:                0
tight delayed fraction: 19/330 = 5.76%
```

Transitions:

```text
baseline delayed -> tight delayed: 15
baseline delayed -> tight stable:  10
baseline delayed -> tight early:    4
baseline stable  -> tight delayed:  3
baseline stable  -> tight stable: 297
baseline numerical -> tight delayed: 1
```

Treating delayed/not-delayed as a binary endpoint over all 330 main-stable IDs gives 18 label changes (5.45%): 14 baseline-positive to tight-negative and 4 baseline-negative to tight-positive. The net delayed fraction changes by -3.03 percentage points. Approximate paired 95% interval for the difference is about -5.5 to -0.5 pp; exact discordant-direction p≈0.031.

The baseline and tighter Wilson intervals overlap:

```text
baseline 29/330: 8.79% [6.19%, 12.34%]
tight    19/330: 5.76% [3.72%,  8.82%]
```

## Interpretation

The overall 3000-period ejection incidence is comparatively stable, but the conditional `stable at 300 -> delayed ejection by 3000` endpoint is materially tolerance/trajectory sensitive. Four baseline delayed events move across the 300-period boundary under the tighter run, ten become stable through 3000, and four new delayed positives appear.

Therefore:

1. Do not quote 7.6799% with binomial SE alone as if numerical labeling were negligible.
2. Report the full-cohort baseline estimate as the primary production result, but pair it with the precommitted sensitivity result.
3. Use wording such as:

> In the production run, 7.68% of systems censored as stable at 300 outer periods ejected by 3000. In a preselected 500-system tolerance experiment, the corresponding delayed fraction among 330 main-stable systems changed from 8.79% at the production tolerance to 5.76% at epsilon 1e-11, with 5.45% of delayed/not-delayed labels changing. Thus the existence of a several-percent delayed population is robust, while its precise incidence and individual membership are numerically/chaotically sensitive.

4. Prospective delayed-ejection metrics use the production-tail endpoint and must carry this label-sensitivity limitation.
5. No additional large simulation is automatically required. A same-cadence/tolerance replication or a larger sensitivity set would refine the incidence but is referee-stage work unless the paper insists on a high-precision delayed percentage.

## Event-time sensitivity

Among 189 systems ejected in both runs, median absolute event-time difference is 0.00189 outer periods and the 90th percentile is 108.66 outer periods. The distribution is sharply concentrated with a chaotic heavy tail.
