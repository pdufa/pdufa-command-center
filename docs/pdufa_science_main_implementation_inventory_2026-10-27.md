# PDUFA SCIENCE/MAIN audit — implementation inventory supplement (2026-10-27)

## Confirmed source-level implementation (not operational acceptance)
- `new-platform/frontend/app/Workspace.tsx` exists (about 153k characters). It imports `PublishedScansPanel`, `DailyResultsPanel`, `BackupStatusPanel`, `GoalDashboard`, `PipelineData`, `MainPhase3ResearchPanel`, `HopReadinessPanel`, `TradingDashboard` and other modules. This is evidence that UI integration has been coded, not evidence that each panel displays current verified data.
- Workspace source includes a source-health status display with regulatory/clinical row counts and issues, and historical **stage transitions** for GEM. Stage-transition history is not the same as verified FDA historical parallel trials.
- `new-platform/frontend/app/SiteHealthStatus.tsx` explicitly has unverified health-check states, supporting conservative display behavior.
- `new-platform/frontend/package.json` defines build, typecheck and Node test commands; passing repository workflows do not alone certify the deployed dashboard.
- `README.md` identifies Next.js/Vercel, Render backend and GitHub Actions scanners as the active architecture.
- `docs/MASTER_PDUFA_PASS_FAIL_DIRECTIVE.md` specifies 20 depth levels and the scientific assessment requirements, but the inspected Workspace source does not itself demonstrate a complete 20-level scored trial dossier.

## Scorecard impact
No new criterion satisfies **all** of its published acceptance evidence. O1 remains verified at 5 points; M1/M2 and S1/S3 have additional **implementation evidence** but remain **not acceptance-verified**. This avoids confusing an implemented UI panel with a validated FDA decision model.

## Specific next evidence requests
- M1: representative screenshots and acceptance tests for mobile/desktop on real sourced dossiers, including evidence, parallel-trial details, readiness and abstention.
- M2: timestamped unattended production scan receipts, alert delivery tests, recovery drill and data freshness checks.
- S1/S2: versioned 20-level assessment schema and real dossier-to-application evidence lineage.
- S3: source-verified, time-stamped historical parallels with independent review.
- M3/M4: deployment receipt, rollback/security test, and signed end-to-end acceptance.

This audit does not modify production, data stores, permissions, trading flags, or GEM JR/GEM preset associations.
