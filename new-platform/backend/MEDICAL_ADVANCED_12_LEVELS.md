# MAIN PDUFA — advanced Deep Medical Intelligence integration (draft)

**Architecture:** POOL (source evidence) → FOCUS (qualifying trials) → independent Deep Medical Intelligence (12 advanced levels) → separate approval/CRL/review-delay research outcomes → independent prediction-certainty gate.

**Isolation:** No retired scoring or survey dependencies, no POOL/FOCUS Google Sheet writes, no production merge, no trading execution. The source roster used for the initial preview is dated 2026-11-07; this is not a continuous Google Sheets synchronization.

## What is implemented in the draft PR

1. `new-platform/frontend/lib/medical-intelligence-advanced.ts`: fixed, universal 12-level definitions, failure question, original-source leads, outstanding evidence, conservative status and source scope. Applies to reconstructed application cycles and has a `NOT_RECONCILED` fallback for FOCUS NCTs without an established filing identity.
2. `new-platform/frontend/lib/medical-intelligence-registry-phase.ts`: exact-NCT ClinicalTrials.gov phase reconciliation, 6-hour caching and identity-mismatch fail-closed behavior. A missing/unavailable phase remains `UNKNOWN`; a lower phase does not fail merely because Phase 3 material is not available.
3. `new-platform/frontend/app/medical-intelligence-preview/advanced/page.tsx`: all 12 levels expandable, separate approval/CRL/delay outcomes with source/gap details, independent certainty display and active application selector.
4. `new-platform/frontend/lib/medical-intelligence-calibration.ts`: historical locked-data validator and chronological holdout metric evaluator (Brier and expected calibration error). **No real eligible historical cohort** is loaded, and this function **never licenses** live probability forecasts.
5. `new-platform/backend/app/medical_advanced_runtime.py`: append-only per-NCT completed-run source revision snapshots with 12 research levels, separate `ABSTAIN` outcomes and no issued certainty rating. Atomic with marking a 12-stage source run complete.
6. Backend exact-NCT ClinicalTrials.gov source digest watcher, 6-hour interval and duplicate/active-run guards, **opt-in only** with `PDUFA_MEDICAL_AUTO_WATCH=true` **and persistent PostgreSQL**. It does **not** yet watch FDA, SEC, sponsor or literature changes. First observation is baseline rather than a fabricated evidence event.
7. Authenticated read-only revision history endpoint and on-demand expandable history panel on the existing medical research page.

## Twelve advanced levels: evidence readiness gates

| # | Investigative level | Current implementation | Missing for a defended outcome |
|---|---|---|---|
| 1 | Historical FDA CRL | Source-linked prior CRLs where documented | Original letters, exact cycle matching, FDA-recognized remediation |
| 2 | FDA-style multidisciplinary reviewers | FDA reviewer finding and source mapping | Independent clinical, statistics, clinical pharmacology, safety and CMC reviews |
| 3 | Advanced statistical forensic | Prespecified vs amended-method conflict leads | Full protocol/SAP/CSR, multiplicity, sensitivity and independent statistical reproduction |
| 4 | CMC / manufacturing | Known facility/quality observations, BLA/NDA-specific gates | Site/facility data, validation, comparability and actual FDA quality disposition |
| 5 | Regulatory precedent | Historically documented FDA actions | Matching algorithms and appropriately comparable approval/CRL cohort with policy chronology |
| 6 | Clinical benefit-risk | Disease-specific subspecialty source questions | Integrated SAEs, durability, magnitude, comparator and independent benefit-risk adjudication |
| 7 | Trial design/data integrity | Missingness, inspection, protocol, design lead mapping | BIMO/site findings, full deviations, exact trial integrity verification |
| 8 | Scientific contradictions | Candidate conflicting signal pointers | Source-to-source standardized estimands and definitive reconciliation |
| 9 | FDA communication | Public FDA/SEC/sponsor feedback classification | Current-cycle full feedback, response/closure evidence |
| 10 | Regulatory pathway | NDA/BLA/supplement type and evidence source | Formal original FDA status, pathway designations, exact indication and label acceptance |
| 11 | Review delay | Previous extensions and current possible timing risks differentiated | Dated current-cycle filing clock, amendments and formal extension evidence; historical time series |
| 12 | Backtest/calibration | Chronological holdout evaluator with leakage guard | Genuine dated out-of-sample predictions and FDA outcomes, cohort completeness, model stability and independent validation |

**A level with source leads is not a completed analytical or clinical review.** Source-missing means `EVIDENCE_GAP`, not evidence of safety or absence of a blocker.

## Prediction and certainty contract

- Approval, CRL and delay are **three different targets**. Delay can precede a later approval or CRL and must not be normalized into a three-class distribution.
- Predictions remain `ABSTAIN` and probabilities null for pending applications until *independently validated* clinical, statistical, CMC and regulatory analysis, current-cycle source chronology, and temporal historical model calibration are established.
- A previously FDA-approved indication has a non-pending research status, not a newly predicted approval.
- Independent certainty remains `NOT_VALIDATED` and rating null; research-source counts cannot masquerade as reliability percentages.
- No guaranteed approval forecast, invented missing data, inferred FDA inspection clearance, or retrospective action used as a future event.

## What must be connected before operational validation

- The new Render preview backend and free PostgreSQL resource exist separately from production; the internal `DATABASE_URL` has **not** been configured because the connected Render API does not expose it. See `new-platform/backend/MEDICAL_PREVIEW_INSTALLATION.md`. Never paste credentials into GitHub or chat.
- After PostgreSQL is connected, confirm `/health` reports `storage_ready: true`, then run one exact-NCT 12-stage job, verify two saved revisions when the source changes, review history and stop/resume, and validate the restart/replay behavior.
- Do not enable `PDUFA_MEDICAL_AUTO_WATCH=true` until the database is persistent and the baseline is inspected. Keep it disabled in production.
- Expand the source change monitor to FDA letters/labels/inspections, SEC issuer filings, ClinicalTrials.gov and PubMed/peer-reviewed publications with per-source revisions and safe issuer-to-NCT mapping.
- Add a properly labeled historical training/out-of-time cohort and independent outcome adjudication. Run issuer-separated temporal backtests, model/threshold calibration, prospective shadow predictions and data-drift monitoring. **Only then** consider allowing probability outputs and a numerical certainty reliability measure.
- Review all legacy CI failures independently: older RAAS/TOOLS tests may be incompatible with the explicitly independent medical preview. Do not delete or suppress legacy checks merely to make the build green.

## Verification gates

A passing isolated medical frontend suite and backend regression suite verifies code/test properties only. It does **not** verify current FDA assessments, production availability, persistent storage or real prediction reliability.

**Release state:** Draft preview only. Do not merge PR #928 into production without explicit release review.
