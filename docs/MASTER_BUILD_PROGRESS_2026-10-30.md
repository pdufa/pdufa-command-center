# PDUFA MASTER BUILD PROGRESS — 2026-10-30

## Evidence-based baseline
MAIN Core Platform: 1/31 verified (3.23%), 30 open and 0/8 fully accepted sections in recorded October 26 audit. Technical prerequisites: 0/10 accepted. SCIENCE and OUTCOME completion unmeasured. These are NOT overall system percentages.
Production /installation-audit previously returned HTTP 200 with 15 sections. Frontend TypeScript, build and 385 tests passed October 26. Authenticated functionality, runtime scans, database restore and private source health remain unverified.

## Detailed segments
### 01 Infrastructure & deployment
- Scope: GitHub and Vercel projects located; verify live deployment SHA, Render workspace, auth, security, rollback.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 02 Database & ingestion
- Scope: 741-NCT served CSV consistency previously checked; verify database, source provenance, dedupe, backups and restore.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 03 Automated scans
- Scope: Scan workflows present; verify 8 PM Pacific execution, sequential jobs, retries, locks, counts and RESULTS.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 04 Pipeline
- Scope: Audit public, $300M–$10B, US FDA, phase >=3, active, drug/indication, documented evidence filters and per-gate counts.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 05 GEM JR
- Scope: Audit separate scoring, clinical/completeness requirements, source proof and original FS/FA associations.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 06 GEM
- Scope: Audit stricter qualifications, scoring, candidate transitions and original independent FS/FA associations.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 07 Special designations
- Scope: Verify taxonomy, actual grant dates, FDA source citations, icons and timeline coverage.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 08 SCIENCE
- Scope: Freeze investigation depth; verify 8 layers, 40 assessments, evidence, counterevidence, uncertainty and readiness grades.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 09 OUTCOME
- Scope: Verify review-cycle labels, PASS/CRL/EXTENSION, late decisions, historical evidence, calibration and abstention.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 10 MAIN
- Scope: 31-gate core acceptance inventory, 10 technical prerequisites, integration and decision safety.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 11 Predictions page
- Scope: Top input flowchart, separate historical/current/future PDUFA, candidates list, decision header and collapsible metrics.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 12 Historical validation
- Scope: Time-frozen FDA decisions, held-out tests, Brier score, class metrics, uncertainty, model version.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 13 Dashboard & charts
- Scope: Three summary boxes, full-width source health, mobile view, timeline, matrices, chart rendering and audit progress.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 14 Notifications
- Scope: Verify scan start/end email and SMS delivery, retries, provider configuration and logs.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

### 15 Final acceptance
- Scope: Authenticated end-to-end test, data integrity, backup restore, shadow predictions and signed release gates.
- [ ] Confirm requirements and preserve approved version.
- [ ] Locate implementation and record file/commit evidence.
- [ ] Verify deployed runtime behavior with timestamp.
- [ ] Run acceptance and failure-path tests.
- [ ] Record completed/open/blocked counts, owner, priority and next action.

## Priority and controls
P0: authenticated production access, data integrity, scans, backup/restore.
P1: restrictions/presets, SCIENCE → OUTCOME → MAIN, defensible PASS/CRL/EXTENSION output.
P2: historical out-of-sample calibration, visualizations, notifications, mobile and release.
Do not change GEM JR/GEM original FS/FA associations without explicit approval.

## Task schema
ID | Segment | Task | Requirement | Status | Priority | Owner | Dependency | Evidence URL/commit | Last verified Pacific | Acceptance test | Blocker.
Status: requested / code present / deployed / runtime verified / accepted / blocked / unknown.
Only accepted tasks with dated evidence count as completed. Missing evidence is unknown, not failed. Never equate installation percentage with predictive accuracy.

## Dashboard proposal
Add BUILD PROGRESS with 15 expandable segment carets, four separate progress indicators (installation, data, prediction engine, readiness), evidence links, blockers and last verified time. Percentages only when audited denominators exist.