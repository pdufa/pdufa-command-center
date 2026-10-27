# Parallel Historical Trials — prediction workstream

Status: design specification; not deployed or validated.

## Goal
When a Pipeline trial is opened, show historical parallel trials from earliest development through FDA disposition, ordered by evidence-based similarity. Preserve original GEM JR/GEM FS/FA presets.

## Data model
- current_program: stable NCT ID(s), sponsor, asset, indication, population, mechanism, modality, route, dose, trial stage, regulatory application, PDUFA date, evidence timestamps.
- historical_program: NCT IDs and application IDs, trials by phase, endpoints, effect sizes, safety, design, FDA correspondence/public review documents, regulatory pathway, CMC risk disclosures, decision and date, cited sources.
- historical_snapshot: information known as of a chosen cutoff; exclude all later evidence from model inputs.
- match: current program ID, historical program ID, comparison date, dimension scores, missingness, rationale, citations, model version.
- outcome: distinguish FDA approval, CRL, withdrawal, and no application; separate trial failure from PDUFA rejection.

## Matching rules
1. Candidate retrieval: same indication and line of therapy first, then related populations/mechanisms and endpoint families.
2. Compare disease severity, unmet need, study design, endpoint definitions, effect size, safety, submission type, FDA pathway, precedent, disclosed manufacturing risk, and sponsor regulatory history.
3. Do not invent similarity percentages or outcome probabilities. Show "unscored" until weights and calibration are validated.
4. Prevent leakage: compare historical cases using evidence available before their own FDA decision and use temporal holdout validation.
5. Distinguish trial-level similarity from application-level outcome; multiple NCT IDs may map to one application.
6. Record missing evidence and contradictions; expose them prominently.

## Trial details UI
- Immediately beneath current trial summary: expandable "Parallel Historical Trials" with top matches, their similarity status, indication, phase, FDA disposition, decision date, and evidence links.
- Expand a match to show a phase-by-phase timeline, similarities, differences, cited source documents, missing data, and FDA decision rationale.
- Separate tabs/filters: "FDA decisions" (approved/CRL/withdrawn) and "Development parallels" (never submitted, terminated, etc.).
- Clearly label unverified data and insufficient comparator sample sizes.

## Prediction integration
- SCIENCE: independently analyze candidate evidence and historical parallels.
- OUTCOME: estimate calibrated PDUFA approval probabilities only after training and validation, with uncertainty intervals and comparable case counts.
- GOAL: separate readiness/evidence grade from approval probability and from investment recommendations.
- SCAN: refresh on material new disclosures, retain versioned snapshots and audit logs.
- MAIN: show parallel trials on every eligible Pipeline detail view.

## Acceptance criteria
1. Every eligible Pipeline trial can request historical matches; empty results show an explicit no-verified-parallels state.
2. No case displays invented similarity, outcome, or confidence.
3. Historical cases are deduplicated by FDA application for PDUFA outcome calculations.
4. Each match has dated citations and an as-of evidence cutoff.
5. Backtesting uses time-split holdouts, calibration plots, Brier score, log loss, and subgroup evaluation.
6. No deployment or trading authorization implied by this specification.

## Implementation order
Audit source trial and FDA application tables; build normalized historical application/decision dataset; add evidence-grounded retrieval; implement trial detail component; backtest and calibrate; deploy to review and verify on real cases before production.
