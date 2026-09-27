# A1 ApJ Risk Register and Freeze Rules

## 1. Contribution framing

### Required claim

> Initial-condition information provides near-ceiling early discrimination of finite-time ejection. Prospective trajectory-history diagnostics add little at the earliest horizon but provide increasing operational value for late, long-lived, and near-boundary risk sets under calibrated false-alarm constraints.

### Prohibited claim

- a universally superior stability classifier;
- replacement of static initial-condition screening;
- exact prediction of chaotic trajectories;
- a universal ejection law.

### Evidence required in final text

- IC/window/combined decomposition;
- fixed-cohort growth result;
- PR-AUC and calibrated FAR recall;
- boundary bootstrap intervals;
- learning-curve sanity check.

## 2. Baseline transparency

State explicitly:

- Vynatheya et al. is a strong external static baseline trained on ~1 million MSTAR systems;
- its original labels are semimajor-axis-change or ghost-orbit stability, not this paper's physical ejection-by-300 endpoint;
- it transfers without refitting;
- the combined model is trained in-domain, uses horizon-specific fits, and receives causal trajectory history;
- combined-versus-Vynatheya is an end-to-end comparison at unequal information/latency budgets, not an equal-input algorithm contest.

Report the gain decomposition:

```text
combined - V22 = (our IC - V22) + (combined - our IC)
```

## 3. Causal vocabulary

Use:

- prospective;
- temporally causal window;
- information available before the endpoint;
- early-warning/risk updating.

Do not use for A1:

- causal mechanism;
- intervention effect;
- treatment effect;
- proof that changing a diagnostic changes ejection.

Ablations test model dependence, not physical causation.

## 4. Feature-set scope

Required limitation:

> The tested feature families are physically motivated but not exhaustive, and optimality of the representation is not established.

Do not present the 79-feature tensor as uniquely derived or complete. Report feature-family ablations and the equal-training-size curve. New feature search is out of scope before submission.

## 5. Manuscript/package quality gates

Do not submit the current v2 draft. Freeze only after:

- abstract satisfies ApJ length/style;
- all figures regenerated from manifest-authorized outputs;
- labels and font sizes are publication readable;
- every caption states cohort, horizon units, metric provenance, and uncertainty convention;
- Data Availability uses versioned immutable artifacts and checksums;
- code-release wording distinguishes software and data licenses;
- historical/provisional results are absent from headline text;
- `RESULTS_MANIFEST.md` Final rows are populated;
- anonymous AASTeX and dual-anonymous checks pass;
- repository commit/release identifiers are fixed;
- literature baseline and learning-curve outputs are archived;
- leakage correction and invariance tests are documented once, clearly, without dominating the paper.

## Submission go/no-go

A1 is ready when the equal-training check is interpreted, Final manifest is complete, figures/tables regenerate without manual number entry, and every abstract/result number traces to a hashed output artifact.
