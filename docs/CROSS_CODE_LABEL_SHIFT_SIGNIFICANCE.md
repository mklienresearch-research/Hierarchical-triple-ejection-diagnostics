# Why the MSTAR-to-REBOUND, stability-to-ejection transfer matters

## Core point

The Vynatheya models were trained on MSTAR simulations and on semimajor-axis-change or ghost-orbit stability labels. They were then applied, without refitting, to REBOUND/IAS15 systems labelled by physical ejection before 300 outer periods. Their strong performance is therefore a cross-integrator, cross-label, cross-dataset transfer result.

This has two consequences:

1. It validates that the initial-condition stability manifold learned by Vynatheya captures real dynamical structure rather than code-specific artifacts.
2. It raises the bar for any claim of improvement: our total advantage contains both in-domain endpoint adaptation and genuinely new causal-dynamical information.

## Gain decomposition

At each horizon:

```text
combined - V22 MLP
= (our IC-only - V22 MLP)      [in-domain/endpoint adaptation]
+ (combined - our IC-only)     [increment from causal dynamics]
```

| observation | total combined-V22 | our IC-V22 | dynamics combined-our IC |
|---:|---:|---:|---:|
| 15 T_out | +0.00262 | +0.00207 | +0.00054 |
| 45 T_out | +0.00510 | +0.00300 | +0.00211 |
| 90 T_out | +0.00769 | +0.00303 | +0.00466 |
| 150 T_out | +0.01074 | +0.00272 | +0.00801 |
| 225 T_out | +0.01393 | +0.00156 | +0.01237 |

Early total gain is mostly explained by fitting an IC model directly to the paper's endpoint. Late total gain is overwhelmingly the causal-dynamics increment. This is the fairest evidence that the late advantage is not merely label/domain adaptation.

## What this licenses

> A published initial-condition classifier trained with a different N-body code and stability definition transfers remarkably well to finite-time ejection, demonstrating a robust shared stability structure. Fitting ICs directly to the ejection endpoint yields a small additional gain, while the dominant late-horizon improvement comes from causal dynamical evolution measured after initialization.

## What this does not license

- Do not claim an equal-input algorithmic victory: combined uses more information and later observation.
- Do not claim Vynatheya is weak; its transfer is exceptionally strong.
- Do not compare published headline accuracy directly with late in-play accuracy because prevalence and risk sets differ.
- Do not attribute the entire combined-V22 difference to dynamics; use the decomposition above.

## Scientific value

The transfer acts as external validation across integrators and label semantics. The decomposition then isolates the new contribution: not a replacement static stability boundary, but dynamic risk updating for systems that survive into difficult late risk sets.
