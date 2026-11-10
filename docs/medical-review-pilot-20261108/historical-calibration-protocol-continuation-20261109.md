# Historical probability-calibration protocol continuation

This increment continues the existing R38 original FDA source receipts, R39 blinded Phase III replay, R47 parallel research tracks and R48 application/source-identity audit. It does not reset or rerun those collections, create a new cohort, assign a clinical grade, or release an FDA prediction.

The remaining software gap was a fitted probability-calibration stage between a frozen base forecaster and an untouched temporal test. `hop_probability_calibration.py` adds that stage using the existing exact-indication/application/review-cycle evaluator and original blinded evidence packet format. Approval, CRL and review delay are separate targets; a missing extension history cannot become a negative delay label.

## Implemented boundary

1. Require explicit, complete and nonoverlapping program-family rosters for training, validation and test. Reject omitted or newly introduced families, duplicate cycles and indication borrowing. Original cohort completeness and family truth remain externally audited claims, not facts proven by a Boolean.
2. Require original reviewed training labels public before the training cutoff, one unchanged base-model artifact and a training/application/publication-clock manifest shared by validation and test. This module does not train the base forecaster.
3. Revalidate every validation/test predecision evidence packet through the existing R39 freezer, including its original source versions, first-publication cutoffs, exact NCTs, program family and input digest. Source-role controls and delayed-outcome labels reuse the existing gates.
4. Fit pooled-adjacent-violators isotonic regression **only on eligible validation forecasts and labels**. Tied input probabilities are pooled before adjacent monotonicity violations. The immutable artifact digest binds the target, frozen base model, validation inputs/source hashes, prespecified split windows and program/training rosters. No test outcome enters that digest.
5. Freeze that artifact before evaluating test labels. If the configured validation minimum or both binary classes are absent, return a blocked result without opening test labels. The configurable minimum is an engineering contract, not a claim that a given sample size establishes clinical model adequacy.
6. Apply the monotone step function within the validation score range. Gaps take the next block's value; unsupported extrapolation and supplied abstentions stay abstentions. Retain all eligible held-out cases in coverage denominators, including abstentions, and retain exclusions separately.
7. Reuse existing Brier score, log loss, reliability-bin counts, event-rate Wilson intervals and accuracy Wilson intervals. These are conditional research mathematics on supplied inputs. They do not include model/label/source uncertainty or prove outcome-vault independence. A calibration-wide confidence interval is still unavailable.

Neither caller flags nor good mathematical metrics can set `modelValidated` or `trainingAuthorized`; outputs retain `ABSTAIN`, `NOT_VALIDATED`, and `NOT_CALIBRATED`. No HTTP route, startup fit, external database, vault activation, reviewer write, production action or numerical FDA forecast is added.

## Actual historical-data state

The committed [R38 source receipt](../../new-platform/backend/app/research_sources/hop_fda_source_recovery_receipt_r38.json) preserves **412 outcome-selected research leads**, derived from FDA-approved-product and selectively published CRL exports. Those were authenticated source-export observations, not a complete consecutive NDA/BLA filing cohort. This increment obtains **0 new historical records** and creates **0 independently adjudicated review-cycle labels, 0 real training/validation/test cases, and 0 real calibration fits**. The source archive has an explicit expiry; a local metadata export does not create permanent custody or fresh retrieval.

[The generated readiness artifact](../../reports/deep-medical-intelligence/calibration-protocol-readiness.json) exposes these counts and blockers without fabricating a model sample size or measured accuracy. The existing outcome-selected identity worklist remains prohibited as blinded forecast input. Live Track B may pass its already validated `MAIN_R47_HISTORICAL_SOURCE_BUILD_CHECKPOINT` to `calibration_readiness_status(source_checkpoint=report)`: its current candidate count, byte hashes and timestamp are retained instead of the pinned412 count. The projection rejects attempts to promote source rows into real cycles, accuracy or fit authority and performs no new source retrieval.

The next data dependencies remain a complete filing denominator including pending, withdrawn and negative cases; exact indication/cycle/action/publication adjudication; original predecision versioned scientific features; independent outcome-vault custody; and prespecified program-disjoint temporal partitions. Only after those exist can an authorized real calibration/evaluation use this tested software.

## Verification

Sixteen new synthetic tests cover known PAV pooling, untouched test-label independence of the fitted artifact, row-order invariance, abstention coverage, unsupported extrapolation, insufficient validation without opening holdout labels, temporal/family/roster/indication leaks, altered model/source digests, missing denominator claims and separate CRL/delay targets. No synthetic identity or probability is exported as an authentic historical case.

Focused validation: **90 passed, 0 failed**, combining the new protocol tests with the existing exact-target, metric and blinded-replay tests. The parent installation run performs broader backend and retirement checks before committing the increment.

Reproduce the local metadata export without network access or fitting:

```sh
python new-platform/backend/scripts/export_hop_calibration_readiness.py --output reports/deep-medical-intelligence/calibration-protocol-readiness.json
PYTHONPATH=new-platform/backend .venv/bin/python -m pytest -q new-platform/backend/tests/test_hop_probability_calibration.py
```
