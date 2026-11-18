# 2026 unrestricted Level 1 — cohort reconciliation

As-of: 2026-11-18. This is a **worklist**, not a claim of completed assessments.

## Population rules
- All market caps, including privately held sponsors.
- One record per application + review cycle + indication, with distinct supplement identifiers.
- Record original PDUFA goal date and every amendment; do not confuse FDA action date with PDUFA date.
- Include NDA, BLA, and supplemental applications; keep approvals, CRLs, withdrawals, delays and pending actions separately labeled.
- FDA novel-drug approvals are a subset, not the PDUFA denominator.
- Treat 196 as a **provisional external-tracker target**, not an FDA-certified total.

## Evidence requirements for Level 1
For each event collect application number, sponsor, drug, indication, original/current PDUFA date, source URLs and retrieval dates; trial identifiers, phase, primary endpoint, statistical results, safety signals, FDA filing status and prior regulatory actions. Mark missing data explicitly. Do not infer FDA approval from trial results alone.

## Prediction integrity
For past events, use a demonstrably frozen pre-outcome Level 1 prediction to calculate genuine blind accuracy. A new 2026-11-18 historical assessment may be performed, but must be labeled **retrospective/outcome-aware**, and excluded from blind accuracy. For future events, freeze predictions before the FDA action and retain immutable versions.

## Reconciliation gate
Do not mark the cohort complete until every event has an independently traceable application identity and PDUFA date, and duplicates, date amendments, and missing event classes are reconciled. The seed and reference CSVs in this PR are *not* the 196-event cohort.

## Reporting
Report cohort discovered / validated / unverified; historical / future; prediction available / missing; blinded-eligible / outcome-aware; correct / incorrect; accuracy with denominator; evidence gaps. Never report an invented percentage or completion count.
