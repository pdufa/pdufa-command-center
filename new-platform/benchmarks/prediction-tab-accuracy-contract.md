# PREDICTION tab: accuracy and freshness contract

Status: REQUIREMENTS — not proof of UI deployment or predictive accuracy.

## Required display
- Show verified data, scientific assessment, forecast, and actual outcome as separate labeled sections.
- Each source-backed datum must have source URL, as-of/publication time, retrieved/verified time, scope, and source hash.
- Display last successful daily verification in America/Los_Angeles, freshness threshold, failure state and stale warning. Never imply a daily check ran if it did not.
- For each program show sponsor, drug, indication, regulatory pathway, PDUFA target date and its provenance. Unknown values must display UNKNOWN rather than inferred.
- Main decision must be PASS / CRL / EXTENSION / ABSTAIN. ABSTAIN if critical evidence is missing, contradictory, or not independently verifiable.
- Show 12 headline metrics and 48 expandable supporting metrics, with missingness, conflict and uncertainty markers.
- Show 40 SCIENCE assessments with citations and individual readiness states; no fabricated scores.
- Distinguish model confidence from measured predictive accuracy. Do not display unsupported success rates.
- Preserve immutable historical prediction timestamp, input evidence cutoff, rules/model version, source manifest hash and prediction hash.
- Record actual FDA outcomes separately after prediction freeze; score only eligible genuinely pre-outcome predictions.
- For historical Benchmark 1, exclude all post-cutoff knowledge from SCIENCE, OUTCOME and MAIN prediction inputs.
- A fresh registry record is not FDA approval or a confirmed PDUFA date.
- On source, archive, or verification failure: surface explicit FAILED/STALE status, retain last verified snapshot, suppress unsupported decision changes and trading signals.
- Keep PIPELINE/GEM JR/GEM/WT restrictions and original GEM JR/GEM FS/FA memberships unchanged.
- No automatic trade authorization.

## Acceptance criteria
1. Every headline value links to a provenance record.
2. A failed daily refresh is visibly marked failed, not successful.
3. Post-cutoff evidence cannot change a frozen historical prediction.
4. Unverified or contradictory PDUFA facts trigger UNKNOWN/ABSTAIN.
5. Accuracy metrics use only timestamped predictions made before real FDA outcomes.
6. End-to-end test confirms actual UI rendering and source drill-down.
