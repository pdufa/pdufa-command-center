# Levels 7–20 development checklist

Status: planning scaffold only. No level is certified implemented by this document.

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
