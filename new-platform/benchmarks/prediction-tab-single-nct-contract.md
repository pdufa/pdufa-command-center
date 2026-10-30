# PREDICTION tab — single NCT input contract

Status: DESIGN REQUIREMENT, not a deployed capability.

## Only user-editable input
An exact ClinicalTrials.gov identifier matching `NCT[0-9]{8}`. The user changes only this code.

## On code change
1. Validate NCT syntax; clear the previous trial's visible values immediately to prevent cross-trial contamination.
2. Fetch the exact study and its linked immutable archive record where available. Record retrieval status and source timestamps.
3. Auto-populate sponsor, product, indication, trial phase, arms, endpoints, efficacy, safety, completion dates, regulatory identifiers, special designations and PDUFA target **only where independently evidenced**.
4. Resolve program-level associations (drug/indication/sponsor/filing) with source-backed identity matching. An NCT code does not necessarily uniquely identify a drug submission or PDUFA action; ambiguous links must show NEEDS VERIFICATION.
5. Populate 40 SCIENCE assessments, 12 headline metrics, 48 supporting metrics and OUTCOME/MAIN only from verified applicable evidence. Mark unsupported values UNKNOWN and decision ABSTAIN.
6. Show each metric's source, verification date, evidence completeness, uncertainty and last successful daily refresh.
7. Preserve frozen historical Benchmark 1 inputs and predictions; never allow future evidence to leak into pre-decision evaluation.
8. Avoid automatic trading, changes to existing PIPELINE/GEM JR/GEM/WT restrictions, or GEM FS/FA preset associations.

## Acceptance tests
- Change from NCT A to NCT B: no A values remain.
- Invalid or nonexistent NCT: visible error, no stale prediction.
- Multiple drugs/indications: require source-backed disambiguation, do not fabricate a single PDUFA outcome.
- Missing FDA target date: UNKNOWN, not estimated as fact.
- Source unavailable: display failure and last verified snapshot timestamp.
- Historical benchmark: post-cutoff evidence excluded.
- All 40/12/48 fields render with provenance or explicit UNKNOWN; never fill with invented numbers.
