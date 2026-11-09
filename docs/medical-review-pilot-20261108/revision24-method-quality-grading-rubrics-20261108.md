# MAIN Revision 24 — method-specific Phase III scientific quality rubrics

**Pilot only:** ACACIA-HCM, protocol CY 6033, NCT06081894.
**Date of dated source snapshot:** 2026-11-08.
**Release boundary:** Draft PR #965 on the isolated feature branch; no clinical ledger writes, no isolated Render redeploy, no production software code change.

## Installed method-specific rubrics

The prior revision replicated published efficacy estimates and raw safety-rate arithmetic for scientific research positions 5.1/L12 and 5.3/L19. This revision adds **the 0–5 evidence-quality grading rules** those positions would require after independent clinical review.

| Phase III position | Scope | Current publicly documented inputs | Missing or unresolved original verification |
| --- | --- | --- | --- |
| 5.1/L12 — multi-method adjudication of pivotal efficacy | Prespecified estimands, statistical endpoints, missingness, meaningfulness, sensitivity and independent replication | 1 of 6 research evidence inputs: published paired primary result estimates and CIs | Final locked SAP/multiplicity graph, all sensitivity models, clinical-important-difference review, alternative estimands, independent analysis and phase signoff |
| 5.3/L19 — independent safety reproducibility | Original event numbers, denominators, adverse-event coding, exposure, causality, reversibility and independent replay | 1 of 6 research evidence inputs: published original safety numerators and randomized denominators | HF serious-AE 11/1 vs 12/3, interruption denominators, exposure, time at risk, complete adverse-event line lists, clinical causality and independent reproduction |

**Observed evidence input count is not a grade.** A missing input is **unverified**, not 0/5. A 0/5 scientific grade would require independently verified *positive evidence of a material invalidating flaw*, rather than unknown data.

For each method, six specific 0–5 ordinal interpretation anchors now describe how a future qualified reviewer can distinguish a confirmed invalid analysis (0) from severe deficiencies (1), mixed discrepancies (2), reconciled conditional result (3), robust independent checks (4), and exceptionally corroborated cross-method findings (5). These are methodological anchors, **not a numeric grade applied to ACACIA**. Some anchors require evidence types not yet publicly established.

## Technical components

- `new-platform/frontend/lib/phase3-clinical-quality-rubric.ts`: strict original-pilot-derived, Phase III method rubric definitions and six verification requirements per method; public source link only for actually documented inputs; fail-closed on changed source, phase, method analysis or ledger status.
- `new-platform/frontend/app/predictions/assessment/PilotScientificSignalPanel.tsx`: two expandable rubric cards with six evidence gates, six rating bands, missing and contradictory evidence, explicitly **Unscored**. Positioned after reproducible statistics and before older documentary readiness indices.
- `new-platform/frontend/app/api/predictions/medical-phase3-reviewer-handoff/route.ts`: dashboard-authenticated, read-only JSON export of original trial numerical research, both rubrics, source links and missingness. Exact NCT required. No POST, no reviewer write credentials or back-end grade release. Every position reports `numericGrade=null`, `officialGrade=null`.
- `new-platform/frontend/tests/phase3-clinical-quality-rubric.test.cjs`: hard assertions for both method IDs, correct 0–5 anchors, 6×2 evidence verification rules, zero score issuance, no FDA model outputs, altered data fail-closed, and signed-in-only readback policy.
- `new-platform/backend/scripts/verify_medical_preview.py`: signed-in live HTML and JSON acceptance rejects unapproved clinical grade, missing method band, wrong trial and unsigned reviewer event. This is an engineering test, not clinical reviewer signoff.

## Current totals and non-claims

Across the single pilot, 18/800 method positions have research **source leads**. Five have either a preliminary documentary checklist (three methods) or a reproducible quantitative research calculation (two methods), but no position has an officially reviewed 0–5 clinical grade. The remaining 13 mapped leads and 782 unmapped methods have no claim of completed analysis or numeric grade. A source lead does not imply evidence completeness.

The pilot remains **0/800 authorized clinical method grades**, all 29 FOCUS trials remain **0/29 signed clinical phase reviews**, FDA outcomes **ABSTAIN** and accuracy **NOT CALIBRATED**. Independent clinical scoring will still require original locked SAP and CSR results, event-list safety reconciliation, qualified reviewer signoff and a versioned append-only clinical event. No amount of research-document scores should be summed into FDA approval odds.

## Next installation

1. Obtain/verify final statistical analysis plan and primary sensitivity tables.
2. Reconcile adverse-event definitions and source-specific safety denominators, exposure and follow-up windows.
3. Establish eligible reviewer workflow and versioned signed evidence adjudication for each method, keeping the existing append-only ledger constraints.
4. Extend validated method-specific rubrics to other phase-appropriate assessments before scaling across all 29 FOCUS trials.
