# MAIN — Revision 15: independent phase-first reviewer intake (draft only)

**Date:** 2026-11-08. **Exact pilot:** ACACIA-HCM / NCT06081894 / CY 6033.  
**Repository branch:** `feature/medical-stage4-verified-method-matrix-20261108`, PR #965 (DRAFT).  
**Disposition:** code preparation and synthetic regression only; **NO REVIEWER WRITES ENABLED ON LIVE RENDER**.

## The boundary between collection and independent review

The pilot source-classification audit has 800/800 recorded receipts. That is **not** 800 human scientific grades. Across 29 FOCUS NCTs, 29 original source packets have been captured, but the last authenticated live checkpoint recorded 0 independently verified phases, 0 scientific method-grade events, and 0 validated FDA forecasts. Approval, complete response letter (CRL), and review-delay outcomes remain **ABSTAIN**; prediction accuracy **NOT CALIBRATED**.

This change adds a **strictly disabled-by-default, pilot-only POST route** for two independent human reviewer roles, rather than generating fictional method scores. A medical reviewer account is not automatically a verified clinical specialist; credential issuance and reviewer qualifications must be reviewed out of band before activation.

## Technical changes

1. The append-only scientific assessment ledger now requires both (a) the trial's original roster-attached 12-stage source run and (b) the **latest verified phase-event ID**. This prevents a prior or same-label revised phase event from receiving a misleading current grade. PostgreSQL operations lock the roster row when recording phase/review events to serialize same-NCT writes. Earlier events are never deleted or overwritten.
2. The new `medical_reviewer_submission.py` defines two separate credentials bound to named principals: `phase` verifier and `method` reviewer. Both roles require strong, unique secret material. A source-worker API key, dashboard read key, or general internal API key does not confer reviewer authority.
3. Each `SCORED` method review requires an explicit 0–5 grade, authenticated original saved-source stage, precise source location, a substantive *human-examined finding*, favorable/unfavorable/contradictory classification where appropriate, an independently written rationale, and the reviewer attestation. Missing-only evidence cannot be graded. `NOT_APPLICABLE` cannot be inferred merely from missing evidence. Review revision requires explicit supersession.
4. Separate reviewer findings are preserved with original saved source URLs, SHA-256 of the captured stage document and stage-capture time, then displayed in the review matrix and 800-position export.
5. All writes must satisfy `PDUFA_MEDICAL_PREVIEW_ENABLED=true`, `PDUFA_MEDICAL_ASSESSMENT_LEDGER_ENABLED=true`, `PDUFA_MEDICAL_REVIEW_WRITES_ENABLED=true`, initialized isolated PostgreSQL, and migration-write readiness. Only NCT06081894 is accepted. No automated startup grading or frontend reviewer-key proxy exists.
6. New synthetic API/ledger regression exercises denied auth, separate roles, incomplete/missing evidence, real zero-grade semantics, stale-phase refusal, altered source-run attachment, append-only history, and no FDA output. The tests are **not** a substitute for clinical review.

## Explicit opt-in (NOT performed)

Provision externally verified, distinct human reviewer principals; store secrets only as protected Render environment variables. Example of schema only, not deployable credentials:

```json
{
  "phase": {"qualified-phase-reviewer-id": "GENERATE_A_UNIQUE_LONG_SECRET_IN_RENDER"},
  "method": {"different-qualified-method-reviewer-id": "GENERATE_A_DIFFERENT_LONG_SECRET_IN_RENDER"}
}
```

Set that JSON to `PDUFA_MEDICAL_REVIEWER_CREDENTIALS_JSON` in the dedicated isolated preview **only**. Enable `PDUFA_MEDICAL_REVIEW_WRITES_ENABLED` manually after review of identity, privileges and sources; keep it unset or false otherwise. Do not put secrets in GitHub, browser code, screenshots, logs, or this document. A source-evidence URL in the saved worker ledger authenticates capture location, **not** the scientific relevance or truth of its findings.

The backend paths are:
- `POST /api/internal/medical-reviewer-intake/NCT06081894/phase`
- `POST /api/internal/medical-reviewer-intake/NCT06081894/method`

Each needs `X-PDUFA-Reviewer-Id` and `X-PDUFA-Reviewer-Key` with the correct role. Responses explicitly state `RECORDED_PENDING_INDEPENDENT_SIGNOFF`, `clinicalSignoff=false`, FDA `ABSTAIN` and `NOT_CALIBRATED`. A recorded review event is **not** independent consensus, a regulatory assessment, a clinical signoff or a forecast.

## Gates remaining

- Verify reviewer qualifications and controlled independent review protocol (two-party adjudication, medical specialty and conflict-of-interest review).
- Reconcile original final locked CY 6033 SAP, reported efficacy and safety discrepancies, study amendments and indication-specific FDA filing status.
- Authorize reviewer phase verification and individual methods; no sourced research lead or 800-audit receipt may be promoted to a reviewer grade automatically.
- Build dated FDA decision *and negative/delay* historical cohorts, then test frozen forecasts on held-out future outcomes with Brier/log loss and calibration confidence intervals.
- Obtain an authenticated end-to-end signed-in browser/session readback and a separate release approval. **Do not merge PR #965 or promote production as a result of a green build.**
