# Levels 7–20 development checklist

## Baseline at `5c02c3f7`

Each level earns 35 points for its defined method and abstention behavior, 20
for passing level-specific automated tests, 25 for verified integrated
execution (10 for its operational entry point and immutable result handling,
15 for dashboard/history and applicable reassessment or historical flow), and
20 for validating real evidence and limitations for the initial cohort (10 for
exact 32-trial reconciliation, 10 for end-to-end verified evidence readiness).
Points are earned only for demonstrated gates. The overall percentage is the
mean of the fourteen level percentages.

| Level | Baseline verified % | Evidence of progress or acceptance gap |
|---|---:|---|
| 7 | 75 | Provenance and storage, 42 passing local tests, opt-in monitor/report path, and 32 exact roster matches. Persistent real evidence and browser flow pending. |
| 8 | 0 | Readiness criteria exist in a standalone module. Test execution and end-to-end integration pending. |
| 9 | 0 | Verify phase and indication hierarchy with exact-NCT data and phase-appropriate eligibility. |
| 10 | 0 | Validate primary endpoints, populations, comparator and effect reporting. |
| 11 | 0 | Validate adverse-event counts, comparators, follow-up and exposure gaps. |
| 12 | 0 | Validate statistical methods and flag missing or conflicting evidence. |
| 13 | 0 | Evaluate subgroups and unmet need using indication-matched evidence. |
| 14 | 0 | Verify dated regulatory evidence for the exact application and indication. |
| 15 | 0 | Distinguish documented CMC risks from unavailable manufacturing information. |
| 16 | 0 | Verify advisory votes, exceptions and conflicting findings for the exact cycle. |
| 17 | 0 | Separate sourced sponsor capability evidence from unsupported inferences. |
| 18 | 0 | Persist model-versioned forecasts and explanations, with calibrated confidence or abstention. |
| 19 | 0 | Freeze outcome-isolated historical forecasts before joining adjudicated outcomes and computing accuracy/calibration. |
| 20 | 0 | Validate integrated release readiness and display/sort behavior without publishing unverified predictions. |

Overall verified acceptance baseline **5.4%**. Credit is conservative for partial
features and applies to the extended assessment contracts. Existing legacy
runtime levels and the separate Level 16 export do not verify those contracts.
All 13 visible PR-triggered workflows reported success at the baseline SHA.


## Safety and release gates
- Development branch only; no merge, production deployment, or trading action.
- Preserve Levels 1–6 behavior and stored prediction versions.
- Do not fabricate clinical evidence, numerical scores, FDA decisions, confidence, or trends.
- Missing or unverified source material must remain explicitly missing/unverified.
- Gate each level on tests, source provenance, and reproducible evidence before marking complete.

## Level 7 — Evidence collection (first implementation target)
- Inventory existing ingestion, trial identifiers, sources, and database migrations.
- Implement idempotent ingestion keyed by stable trial ID, source URL/document ID, version, and retrieval timestamp.
- Persist source publisher, document date, retrieval time, checksum, verification state, and extraction provenance.
- Distinguish source absent, source inaccessible, conflicting evidence, and not yet reported.
- Provide an audit trail of source revisions and reassessment triggers.
- Test duplicates, corrections, missing data, untrusted sources, and backfills.
- Verify no change to production endpoints or Level 1–6 outputs.

## Subsequent levels
8. Trial identity and normalized data
9. Phase and indication hierarchy
10. Efficacy
11. Safety
12. Statistical validity
13. Subgroups and unmet need
14. FDA regulatory intelligence
15. CMC and manufacturing
16. Advisory committee and exceptions
17. Sponsor/commercial intelligence
18. Versioned predictions, confidence, explanations
19. Blind historical backtesting and calibration
20. Integrated validation and dashboard release readiness

## Definition of done for each level
- Implementation committed to development branch
- Unit/integration tests run and passing
- Source and missing-data audit verified
- Prediction versions retained
- FOCUS, PAST, POOL, ASSESSMENTS regression checked where applicable
- Reviewed without merging or deploying
