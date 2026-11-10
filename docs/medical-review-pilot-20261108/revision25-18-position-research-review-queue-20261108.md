# MAIN — Revision 25: Phase III research review queue (18 source-mapped positions)

**Scope:** ACACIA-HCM, NCT06081894, protocol CY 6033, original research snapshot 2026-11-08. **Status:** Draft medical preview PR #965. **Not** a production clinical change.

## Engineering delivered

A versioned exact-trial, read-only method-review queue is now derived deterministically from the same original ACACIA evidence snapshot and source-map as the prior quantitative science and documentary checklists. All 18 method leads are inspected against exact assessment IDs, method indices, fixed source URL allowlists, captured original protocol digest, and unchanged phase/clinical-ledger flags.

| Research state | Mapped method positions | Meaning |
| --- | ---: | --- |
| Public documentary-readiness checklists | 3 | A 3/5, 3/5 or 2/5 **source availability** checklist exists; no clinical-quality grade |
| Source-pinned numerical research recalculations | 2 | Published primary efficacy CIs and unadjusted safety risk differences have been replicated; no original SAP/AE clinical signoff |
| Source leads only | 13 | Sources and missing-evidence questions identified, but no completed independent clinical analysis or provisional numerical quality grade |
| Not source mapped within the 800-position pilot matrix | 782 | No source-to-method handoff yet; not reviewed or graded |

The queue is ordered for **research follow-up**, not probability of drug success. It covers 11 critical assessment headings and labels the missing original statistical, CONSORT, safety/AE, amendment and regulatory documentation for each mapped position. A reader can search and filter by source status, expand each source list, and open or export the entire research queue.

**Files:**
- `new-platform/frontend/lib/acacia-phase3-review-queue.ts`: exact source- and position-pinned deterministic queue with zero clinical score/signature outputs, explicit evidence snapshot, review-order identity, and CSV formula-injection escaping.
- `new-platform/frontend/app/predictions/assessment/PilotResearchReviewQueue.tsx`: iPhone-friendly expandable 18-item research queue, search, status filter and missing-original-evidence explanations.
- `new-platform/frontend/app/api/predictions/medical-phase3-review-queue/route.ts`: signed-in, GET-only JSON and CSV export for exact `nct=NCT06081894`, no privileged writes.
- `new-platform/frontend/tests/acacia-phase3-review-queue.test.cjs`: 18 unique positions, 3/2/13 counts, 782 not source mapped, source tampering/clinical review tampering fail-closed, CSV accuracy and formula-injection protections, authenticated API and UI assertions.
- `new-platform/backend/scripts/verify_medical_preview.py`: authenticated live-preview acceptance of 18 positions, JSON fields, CSV 19 rows, anonymity blocked, no clinical ledger mutations.

## Scientific and authorization boundary

Original Phase III status is **registry reported**; independent medical phase review has not been signed. A source-lead entry is not proof of evidence completeness or efficacy. The 18 mapped positions are not 18 scored methods. The 5 research-checklist/numerical-recalculation positions are not five independently reviewed methods either. **Official clinical grades remain 0/800 for this pilot**, FDA outcomes remain **ABSTAIN**, and prediction accuracy is **NOT CALIBRATED**.

A bounded research worklist cannot be extrapolated to all 29 FOCUS trials without their own original phase checks and source maps. In particular, the final CY6033 locked SAP, primary sensitivity analyses, original HF SAE events and interruption denominators still require independent adjudication; the conflicting 11/1 versus 12/3 counts are not a valid safety score.

## Next installation milestone

Use the explicit missing-evidence worklist to acquire primary source documents, verify versioned phase-appropriate original data, and define appropriate research methods before proposing clinical ratings. A reviewer-authorized, append-only grade should only be released after review and signoff. Do not substitute an automatic research checklist or claim a calibrated FDA forecast.

**Release boundary:** Draft Vercel PREDICTIONS only, PR #965 unchanged in draft. No Render redeploy, no production medical code change, no manual clinical grading writes.
