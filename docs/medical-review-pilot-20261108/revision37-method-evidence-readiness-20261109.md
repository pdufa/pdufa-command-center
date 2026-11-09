# MAIN Revision 37 — evidence-to-reviewer method mapping

**Date:** 2026-11-09. **Scope:** Draft PR #965, exact pilot NCT06081894/CY 6033, read-only frontend evidence handoff; no production change.

Revision 36 recovered four original ClinicalTrials.gov registry version responses, with independently checked source identity, byte hashes and public posting dates. Three preexisting Phase III source positions (4.2:L1, 4.4:L1, 8.2:L1) have corresponding **documentary source references**. These are not qualified or independently graded scientific assessments.

This revision builds an explicit 40 assessment × 20 method research handoff from the existing source lead queue, the exact preserved original history index, and the phase-first ACACIA pilot. It withholds output if original receipt identity, dates, source counts or unscored clinical state changes.

| Disjoint category | Pilot method positions |
| --- | ---: |
| Original registry documentary references on existing mapped positions | 3 |
| Additional source-mapped leads requiring original/reviewer work | 15 |
| No specific source handoff mapped | 782 |
| **Total** | **800** |
| Independent clinical method grades | **0** |

The original historical endpoint transition from one to two primary outcomes is documented, but this does not resolve final locked SAP and amendment timing, CONSORT actual-population counts, or conflicting HF serious-event definitions. Every clinical method stays review-pending. Missing evidence is not scored zero. The frontend shows the 18 mapped positions with the still-needed original questions and links to the preserved exact-identity records.

The parallel HOP/FDA historical outcome pipeline remains **quarantined** from probability release because a complete, independently adjudicated approval/CRL cohort with documented predecision feature clocks, program-disjoint temporal holdout and calibration has not been established. Existing mathematical calibration tests must not be mistaken for observed FDA performance.

Changes: `new-platform/frontend/lib/acacia-method-evidence-readiness.ts`, `PilotMethodEvidenceReadiness.tsx`, existing `PilotResearchReviewQueue.tsx` insertion and `acacia-method-evidence-readiness.test.cjs`. All read-only, no API writes or reviewer credential changes. Next: qualified independent review, original source reconciliation, and a complete FDA outcome cohort verified independently. FDA APPROVAL/CRL/REVIEW_DELAY: **ABSTAIN**; accuracy **NOT_CALIBRATED**.
