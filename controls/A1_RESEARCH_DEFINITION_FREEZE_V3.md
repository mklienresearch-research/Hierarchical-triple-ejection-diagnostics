# A1 Research Definition Freeze v3

> **Purpose.** This document freezes what will be measured, compared, and interpreted. It is not a source for final numerical values. Provenance authority is `results/final_manifest.json` (release-candidate commit `f35a90e`, SHA-256 `a83e5d31f9ae8f16b692f5519941bae33a1e32c36be5886b57f2ab842881fe5a` for the fetched manifest) and its hash-pinned files. The numerical ledger is `docs/RESULTS_MANIFEST_FINAL.md` (source artifact SHA-256 `54440fee9bb862e28c900250757ce686f8c7b98fccc3ee261d2ddb968b33c686`) until the final merged tag replaces the release-candidate commit.

## 1. Research question and estimand hierarchy

### Primary research question

Among hierarchical triples that remain in play at a fixed physical observation time, does a model using initial conditions plus pre-horizon trajectory history rank finite-time ejection better than the same model family using initial conditions alone?

`Pre-horizon` or `causal observation window` means only temporal availability: no feature uses samples after the observation time. It does not imply intervention-level causation.

### Primary A1 estimand

For ejection by the 300-outer-period endpoint, estimate at each prespecified horizon

\[
\Delta_{\mathrm{AUC}}(f)
=
\mathrm{AUC}(s_{\mathrm{IC+W}};\mathcal R_f)
-
\mathrm{AUC}(s_{\mathrm{IC}};\mathcal R_f),
\]

where \(\mathcal R_f\) is the horizon-specific in-play risk set. Test the gain trend jointly under:

1. ordinary changing in-play risk sets;
2. a fixed later-landmark survivor cohort.

### Primary operational companion

For the original 300-period endpoint, at prespecified horizon-specific thresholds derived from calibration negatives, compare paired event-warning coverage while reporting:

- target and achieved per-horizon FAR;
- cumulative system-level control-alert fraction;
- precision;
- all-event and first-horizon-eligible coverage;
- lead-time distribution.

Matched-budget retrospective rows are secondary ranking diagnostics and are not prospective operating points.

### Secondary estimands

- PR-AUC relative to horizon-specific prevalence;
- recall at prespecified FAR;
- continuous/published analytic stability baselines;
- frozen external-model transfer;
- near-boundary in-stratum performance and calibration shift;
- numerical sensitivity of long-endpoint labels;
- frozen transfer from the 300-period target to delayed ejection by 3000 periods.

### Exploratory/supplementary estimands

- escaper identity;
- remaining-time regression and landmark hazards;
- binary--single flyby/exchange/ionization outcomes;
- descriptive full-record torque-spike analysis.

### Not studied as primary claims

A1 does not estimate an intervention effect, prove a physical causal mechanism, identify an optimal feature set, predict exact trajectories, establish permanent stability, or derive a universal ejection law.

---

## 2. A1 scope matrix

| Component | Placement | Role |
|---|---|---|
| Main 500k triples; IC/window/combined; 300-period endpoint | Main paper | Primary claim |
| Horizon trend and fixed-landmark control | Main paper, compact display | Primary-estimand robustness |
| Calibrated warning coverage/lead | Main paper | Operational companion |
| Modern static literature transfer | Main paper baseline table | External comparator |
| Near-boundary suite | Main paper robustness panel or compact subsection | Hard-population stress test, not second headline |
| 100k matched 3000-period extension | Short main subsection | Separate endpoint/censoring |
| Frozen delayed-endpoint transfer | Short main subsection or appendix if space-limited | Secondary prospective endpoint |
| Tighter-tolerance validation | Main limitation/robustness sentence/table | Label-sensitivity floor |
| Escaper class and TTE/Cox | Supplement/appendix | Exploratory mechanism/limitation |
| Binary--single encounters | Supplement or separate paper leg | Not a second A1 headline |
| Full-record spike study | Supplement, descriptive only | Not prospective causal evidence |
| Four-body/N-body/relativistic/planetary/observed systems | Excluded; A2+ | Future work |

No new A1 simulation, feature search, or observational application is permitted unless a reproducibility defect is found.

---

## 3. Endpoints, labels, competing outcomes, and risk sets

### Main triples

```text
population: 500,000
endpoint: 300 initial outer periods
binary event: physical ejection of any body
censoring: unejected at endpoint
competing/separate outcomes: collision, numerical_error, timeout
observation times: 15, 45, 90, 150, 225 outer periods
```

A system enters the risk set at a horizon only if its event time exceeds that horizon. Event-truncated shorter windows are never scored.

### Boundary suite

```text
population: 100,000 sampled near MA01 boundary
endpoint: 100 outer periods
observation times: 5, 15, 30, 50, 75 outer periods
```

Primary boundary estimand is in-stratum performance. Main-to-boundary OOD ranking and calibration are separate.

### Encounters

```text
population: 1,000,000
outcomes: flyby, exchange, ionization
binary target: exchange versus non-exchange
observation clock: fraction of t_approach
lead reference: periastron
```

Negative lead is allowed and denotes post-periastron recognition.

### Matched 3000-period extension

The 100,000-system tail is independently re-integrated from t=0 using deterministic ICs matching main IDs 0--99,999. Distinguish:

1. tail-run population incidence at each cutoff;
2. delayed outcome conditional on main-run stable-at-300 membership;
3. cross-run by-300 label disagreement.

These are different estimands and never share an unlabeled denominator.

### Tolerance cohort rows

1. 100,000-system production tail;
2. precommitted 500-system tighter-tolerance integration;
3. 330 main-stable IDs inside that sample for delayed-label sensitivity;
4. 90 IDs overlapping the untouched test split, of which only four are tight delayed positives---bookkeeping only, not a powered AUC/coverage analysis.

### Fixed landmark cohorts

Main/boundary systems surviving to f=0.75 and encounters surviving to f=0.95 form constant cohorts evaluated at every earlier horizon.

### Warning denominators

Define separately:

- all-event coverage;
- first-horizon-eligible coverage;
- per-horizon FAR;
- cumulative system-level control alerts;
- frozen-threshold prospective performance;
- retrospective equal-budget ranking.

---

## 4. Information sets and feature contract

### Initial-condition information

Available at t=0: masses, orbital scales/eccentricities, mutual inclination representation, derived hierarchy/pericentre/mass ratios, and MA01 quantities. Exact deployed columns are documented in the code/schema.

### Trajectory-history information

Computed only from samples at or before the observation horizon:

- hierarchy levels/trends/crossings/complexity;
- subsystem energy exchange;
- angular momentum and torque;
- orientation evolution;
- entropy/autocorrelation;
- closest-approach and bound-pair activity.

### Leakage contract

- historical stored indices 72 and 73 are zero in training, calibration, validation, test, and inference;
- no contaminated model, score, scaler, or threshold is reused;
- corrected extraction passes all-column future-extension invariance;
- legacy definitions fail exactly the intended two columns;
- every A2 feature must pass the same future-extension test at definition time.

### Feature-set limitation

The feature set is physically motivated but non-exhaustive and not proven optimal. Ablations test predictive dependence, not physical intervention causality.

---

## 5. Baseline and training/information-budget contract

### Direct baselines

- MA01 published rule and continuous margin;
- Vynatheya et al. 2022 algebraic formula;
- Vynatheya et al. 2022 semimajor-change MLP;
- Vynatheya et al. 2023 ghost-orbit MLP;
- in-domain IC-only XGBoost;
- causal H-min and raw-duration scores.

### Comparison parity

All direct same-data rows use identical endpoint labels, in-play test IDs, and named calibration/test splits. Continuous scores receive per-horizon calibration; published rules are shown separately.

### External transfer caveat

Vynatheya models were trained on approximately one million MSTAR systems using semimajor-change or ghost-orbit stability labels and six t=0 inputs. A1 evaluates them without refitting against REBOUND/IAS15 ejection-by-300 labels. This is cross-integrator/cross-label transfer, not reproduction of published accuracy.

### Information and latency budget

The combined model observes trajectory history and is horizon-specific; Vynatheya is a single fast t=0 screen. Combined-versus-Vynatheya is an end-to-end comparison at unequal information, training, capacity, and latency budgets. The clean in-domain dynamics estimand is combined versus IC-only.

### Training-size control

The equal-ID learning curve is **complete** (not pending): IC-only and combined use matched nested training IDs, fixed test/calibration IDs, identical horizons/model family/seeds, and the complete eligible training pool. It is a bounded sensitivity check, not a new feature search and not an equalized Vynatheya retraining.

Provenance pointer: `results/training_curve/training_size_curve.json`, SHA-256 `a55ec950b5978ab1e6b45d9fd51c029b471e61c40184566eccd2910e97dd9126`; generating script `TRAINING_SIZE_LEARNING_CURVE_4CORE.py`, SHA-256 `35de5724b0fde07a5bfa4f84b7efde6267fac4493a36a8157cef96a9e9d08602`. Numerical values remain in the authoritative ledger, not this definition freeze.

---

## 6. Cohort and sensitivity definitions

Required sensitivity analyses:

- changing versus fixed risk-set growth;
- shuffled labels;
- blocked parameter-space splits;
- feature-family/no-time ablations;
- all-column corrected/legacy invariance;
- equal-training learning curves;
- independent tolerance integration;
- paired/bootstrap low-FPR and coverage comparisons;
- target-stratum calibration shift.

Multiplicity is handled by prespecifying the primary gain curve and operational companion; secondary/exploratory results are labeled rather than promoted by significance.

---

## 7. Literature map with citation-level provenance

| Work | Stable source | Inputs | Original target/data | Public code/weights | A1 use |
|---|---|---|---|---|---|
| Mardling \& Aarseth 2001 | DOI 10.1046/j.1365-8711.2001.03974.x | mass ratio, outer eccentricity, inclination, hierarchy | empirical analytic stability boundary | equation | published rule + calibrated margin |
| Vynatheya et al. 2022 | DOI 10.1093/mnras/stac2540 | q_in, q_out, a_in/a_out, e_in, e_out, i_mut | MSTAR; semimajor-axis-change stability; ~1M systems | public formula, MLP, pinned model hash | frozen cross-label transfer |
| Vynatheya et al. 2023 | MNRAS 525, 2388; DOI 10.1093/mnras/stad2410; model source commit `c6d4a293bc8bfb888d4a6a905e29c2aff81a31c7` | same six IC inputs | ghost-orbit divergence stability | public ghost MLP; pinned weight hash | frozen cross-label transfer |
| Tory et al. 2022 | DOI 10.1017/pasa.2022.57 | empirical IC boundary variables | different boundary/instability definition | published fit | contextual discussion |
| Hayashi et al. 2022 | DOI 10.3847/1538-4357/ac8f48 | ICs and long integrations | disruption timescale/Lagrange stability | published results | endpoint/censoring context |
| Hayashi et al. 2023 | DOI 10.3847/1538-4357/acac1e | mutual inclination and long dynamics | Lagrange versus Lyapunov stability | published results | label-definition context |
| Lalande \& Trani 2022 | DOI 10.3847/1538-4357/ac8eab | early orbital time series; equal-mass/tsunami-oriented | time-series stability | public code/models | contextual; not direct frozen row |

Each manuscript comparison states whether it is published-rule application, calibrated score, external transfer, or contextual citation.

---

## 8. Uncertainty and multiplicity plan

- aggregate classification metrics: split seeds 0--2 unless fixed-split table;
- representative confusion/per-class rows: seed 0;
- warning lead: fixed complete OOF or named untouched test;
- gain curves: correlated ID bootstrap under changing and fixed cohorts;
- attribution/coverage: paired ID bootstrap;
- partial AUC: standardized partial ROC-AUC with paired bootstrap;
- tail counts: exact ledgers and explicitly separated estimands;
- tolerance: paired discordance and event-time quantiles;
- low-support subclasses remain counts, not fitted rates.

Do not use binomial SE alone for delayed incidence, convert seed-0 rows into seed-mean claims, or treat per-horizon FAR as cumulative FAR.

---

## 9. Permitted and banned claims

### Permitted

- near-ceiling early IC screening;
- increasing combined-over-IC gain within the 300-period endpoint;
- robust positive gain slope under fixed survivor cohorts;
- larger near-boundary dynamics increment;
- fixed-FAR warning coverage and lead distribution for eligible events at the stated endpoint;
- public modern static baselines transfer strongly;
- late combined gains primarily reflect trajectory-history information after endpoint-adapted IC decomposition;
- head-of-ranking delayed enrichment at equal achieved alert budget;
- a several-percent delayed population with material label sensitivity;
- population-level risk monitoring.

### Banned

- universally best stability classifier;
- equal-input algorithmic victory over Vynatheya;
- replacement of static screening;
- intervention-level causal mechanism;
- exact trajectory/event-time prediction;
- useful long-lead outer-escaper prediction;
- precise universal delayed-incidence claim without tolerance qualification;
- permanent stability at any finite cutoff;
- universal curvature/tanh/ejection law;
- inference for individual real systems;
- historical leakage-era metrics as current results.

---

## 10. Manuscript and source-of-truth rules

1. This definition freeze contains no quotable observed values.
2. `results/final_manifest.json` Final pins and linked authoritative result files control every manuscript number.
3. Superseded/provisional files may remain for provenance but are excluded from claims and figure generators.
4. Captions name endpoint, cohort, horizon units, uncertainty, and metric provenance.
5. Abstract is written last, after Results/Discussion approval.
6. Scope additions go to A2/referee-stage work unless they repair a reproducibility defect.

### Release and review policy

- A1 is submitted without a dual-anonymous request. The public May preprint is disclosed in the cover letter and identified as a superseded predecessor.
- Public code and machine-readable derived result data are frozen on GitHub before submission with a stable commit/tag and checksums in Data Availability.
- Multi-gigabyte raw simulation/score artifacts may remain separately staged during review, with editor/referee access available; the archival Zenodo deposit is created upon acceptance and inserted into the accepted version/proofs.
- Kaggle remains compute/staging and is not cited.
- The final repository commit/tag is inserted only after manuscript/figure freeze.
- The earlier FINAL-run scikit-learn version remains explicitly uncaptured and is never imputed from later environments.
