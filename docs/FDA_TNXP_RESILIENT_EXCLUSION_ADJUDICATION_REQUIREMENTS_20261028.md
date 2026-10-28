# RESILIENT ITT exclusion — adjudication requirements

Research-only, 2026-10-28. No retrospective outcome leakage.

## Question
Was the placebo participant randomized in error appropriately excluded
from the reported efficacy ITT population of 456 despite the October
2023 SAP's all-randomized ITT definition?

## Known source facts
- October 2023 SAP Section 7 defines ITT as all randomized.
- 2024 sponsor ACR poster reports 457 randomized/safety participants,
  456 efficacy ITT, and one placebo participant randomized in error
  who failed a safety criterion.
- SAP Section 13 does not document this specific ITT exception.
- These documents alone do not prove when, by whom, or under which
  version of the plan the exclusion was authorized.

## Decision gate — require original documentation
A. Final signed SAP with version history and any amendments, including
   approval timestamps relative to database lock and unblinding.
B. CSR analysis population definition and subject disposition listing.
C. Protocol deviation classification and exclusion rationale.
D. Blinded adjudication record, including date and reviewer.
E. All-randomized N=457 primary endpoint analysis or documented
   reason it was not performed.
F. Evidence of FDA review or agreement, if asserted.

## Adjudication states
- **CONFORMANT** only when contemporaneous governing plan or
  documented authorized exception supports the exclusion.
- **NONCONFORMANT** only when authenticated governing documents
  establish an unauthorized exclusion; do not infer this merely
  from an apparent contradiction.
- **UNRESOLVED** when required evidence is missing (current state).

## Quantitative sensitivity
Do not simulate a subject-level endpoint value or calculate a
revised p-value from aggregate arm means. An excluded placebo
subject's impact depends on baseline, longitudinal observations,
missingness, covariance, and model specification. Only report a
recomputed result from the prespecified statistical model with
traceable data or a source-verified all-randomized analysis.

## Research model behavior
- evidence_readiness: NOT_READY
- population_discrepancy: EXPLAINED_BY_SPONSOR
- sap_conformance: UNRESOLVED
- decision_prediction: ABSTAIN
- calibrated_probabilities: UNAVAILABLE
- prospective_accuracy: UNMEASURED

Sources:
https://cdn.clinicaltrials.gov/large-docs/49/NCT05273749/SAP_001.pdf
https://www.tonixpharma.com/wp-content/uploads/2024/11/ACR-2024-Poster-F307-Trial_vFinal2_10-15-2024_QRcode.pdf

No production modifications, and no trading authorization.
