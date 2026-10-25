# HOP — Historical Outcome Prediction (foundation)

Status: design and implementation branch; NOT deployed, trained, or validated.

## Purpose
HOP is an independent, parallel evidence engine for the PDUFA scientific platform. It compares an active drug/indication/application with historically comparable FDA decisions, then provides evidence for a separately validated prediction model.

## Non-negotiable boundaries
- Do not change Pipeline, GEM JR, GEM, WT restrictions, scores, or original FS/FA preset associations.
- Do not activate trading, scheduled scans, or production deployment from this branch.
- Do not display unvalidated estimates as calibrated approval probabilities.
- Avoid look-ahead bias: historical features must be available before each prediction cutoff.
- Separate clinical efficacy, safety, and CMC/manufacturing risks; label unknowns.
- Distinguish application-level FDA decisions from trial-level results; link trials to drug, indication, sponsor, and application.

## Proposed records
1. Historical application: application ID, drug, sponsor, indication, submission type, pathway, review dates, decision, CRL/withdrawal classification, evidence source and publication date.
2. Trial: NCT ID, phase, population, design, intervention, comparator, endpoints, effect estimates, statistical results, safety, evidence provenance, information-available date.
3. Match: target application/trial, historical comparator, feature-level similarity, missingness, similarity rationale, source links.
4. Prediction: model version, cutoff date, data version, cohort definition, comparable case counts, estimate (only if validated), confidence interval, calibration and audit trail.

## Execution stages
1. Inspect current scientific schema and sources; create read-only mappings.
2. Ingest adjudicated FDA historical outcomes with provenance and as-of timestamps.
3. Implement transparent nearest-neighbor comparison with minimum sample-size checks.
4. Validate with chronological holdout and disease-specific evaluation; report Brier score, calibration and subgroup performance.
5. Expose HOP as a separate tab and optional drill-down from trial reports after review.

## Acceptance criteria
- Every cited outcome is traceable to an FDA or other documented primary source.
- Missing data never silently becomes negative evidence.
- No future knowledge is used in historical backtests.
- Reproducible output for same input/data/model versions.
- Existing platform functionality and presets remain unchanged.
- Predictions are disabled when insufficient validated evidence exists.
