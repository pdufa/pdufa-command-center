# Scientific adjudication preflight (read-only safety gate)

This module makes the review-platform's outstanding scientific validation work **visible, testable and non-bypassable**. It does not itself perform scientific or regulatory adjudication.

## Where it appears

The isolated `/scientific-assessment/batches` panel now includes **Scientific adjudication blockers** within an exact trial's evidence ledger. The authenticated trial-detail API returns this under `evidenceLedger.adjudicationPreflight`; the 20-stage downloadable dossier also contains it as `adjudicationPreflight`, protected by the review packet's existing SHA-256 integrity checksum.

For the existing KEYNOTE-024 trial, the 8 source reconciliation questions are reviewed separately. Other archived trials start with the 4 independent-source requirements; neither population is assigned scientific pass/fail outcomes by this module.

## How it works

For each source question, the backend:

1. Validates the exact NCT and source worklist identity.
2. Reads the **complete**, checksum-verified revision history from the reviewer-statement ledger. A truncated review history is rejected rather than silently masking contradictory entries.
3. Selects only the **latest revision of each statement thread** to identify active `supports` and `contradicts` pairs. Earlier versions remain in the audit history.
4. Reports how many distinct source URLs and reviewer-claimed labels are on file, the presence of `uncertain` or `not_assessable` statements, and the exact reasons the question cannot be resolved.
5. Leaves `readyToResolve=false`, `criteriaIndependentlySatisfied=0`, `independentlyVerified=false`, and the external readiness gates **unsatisfied**, even if two different reviewer *labels* wrote supportive notes. Merely entering two labels is not evidence of two authenticated independent reviewers.

## Four global prerequisites (all outstanding)

| Required independent safeguard | Status |
| --- | --- |
| Authenticated individual reviewer identity and appropriate qualifications | Not implemented |
| Retrieved, authenticated, dated and hashed full-text source documents | Not independently verified |
| Independently authenticated second reviewer and immutable signed decision | Not implemented |
| Signed reconciliation of protocol/SAP, numerical outcomes, safety and contradictory sources against acceptance criteria | Not completed |

Additional per-question blockers include missing source-anchored observations, conflicting current statements, and unresolved uncertainty.

The preflight is **diagnostic**: there is deliberately **no “Approve evidence” button, review gate write endpoint, grade override or automatic promotion**. The separate review-only write gate for documenting source claims remains disabled unless its own isolated Render settings and independent credential are explicitly configured. The system has no basis to certify a reviewer as a doctor, scientist, statistician, or FDA specialist from a supplied display name.

## Safety and verification

- Archive gzip, SHA-256 and exact NCT identity validation still precede trial review.
- Every reviewer statement is part of a checked, versioned, append-only audit ledger. Tampering with a saved entry blocks ledger/packet readback.
- Any source with a mismatched ClinicalTrials.gov NCT remains rejected.
- Unit/integration tests cover empty worklists, two self-declared reviewers, active contradictory threads, corrected/retracted statements, unrecognized or wrong-NCT notes, missing/truncated history and authorization.
- Chromium acceptance verifies the new blocker details without exposing API keys.
- Isolated PostgreSQL startup logs `SCIENTIFIC_ADJUDICATION_PREFLIGHT` and does not write or finalize any evidence.

**Scientific limitation:** A diagnostic checklist does not replace independent document appraisal or a real evidence-adjudication service. Historical FDA approval is not a prospective PDUFA forecast. Scientific scores, trading orders and existing GEM JR/GEM FS/FA preset memberships remain unchanged.

## Next substantive milestone

Implement trustworthy reviewer identity/role verification and independent document capture with content fingerprints, followed by an explicitly authorized two-reviewer decision record and conflict arbitration. Only when those safeguards are actually operational, tested and human-completed may verified evidence gates be reconsidered. Keep clinical benefit-risk judgment separate from evidence completeness and economic trading signals.
