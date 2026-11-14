# Levels 1–6 execution audit and partial activation — November 14, 2026

This branch adds **partial research execution and history**, not full scientific activation. No level is ACTIVE and production functionality has not been independently verified. No merge, migration against hosted storage, or deployment is performed.

## Audit of existing engines

| Level | Actual implementation | Implemented checks | Missing scientific capabilities |
|---|---|---|---|
| 1 | `processLevel(1)` in `new-platform/frontend/lib/level16-assessment-runner.ts` | Exact NCT receipt, digest format, dated registry version | Original-source authentication, generalized document acquisition and reconciliation |
| 2 | `processLevel(2)` | Registry phase/status, indication/population presence, explicit provisional/unmapped application relationship | Verified FDA application/review cycle and current regulatory filing status |
| 3 | `processLevel(3)`, separate `predictLevel3` | Results presence, extracted counts/rounded percentage consistency; retained ORCA-specific clinical lean | General clinical-result extraction, disease-specific coverage beyond retained ORCA reports, validated FDA predictive model |
| 4 | `processLevel(4)` | Protocol collection and design/population presence | General protocol/amendment retrieval and substantive trial execution assessment |
| 5 | `processLevel(5)` | SAP collection, reported interval consistency, known protocol reference conflict, unresolved chronology | General SAP extraction, verified prespecification/multiplicity/estimands and statistical adequacy |
| 6 | `processLevel(6)` | Primary endpoint descriptions and owner review question | General indication-specific clinical-benefit, magnitude, durability and risk/benefit engine |

All six are **partially implemented**, executable research processors; none has a supported general numerical scoring algorithm. Level 3's `level3-clinical-lean-v1` is an uncalibrated conditional efficacy heuristic for two source-extracted smoking cessation reports, not a complete FDA outcome model. Scores remain null; the new FDA output is ABSTAIN with `NO_VALIDATED_FDA_MODEL` for every level. A selected level other than 3 does not invoke the Level 3 predictor.

Other relevant existing infrastructure:

- `scripts/medical/phase_first_levels_1_6.py`: offline phase-first evidence readiness, not a calibrated assessment model.
- `scripts/medical/export_level16_assessment_evidence.py` and `new-platform/frontend/data/level16AssessmentEvidence.json`: retained 32-trial FOCUS worksheets, ORCA publications, protocol/SAP collection information, provenance metadata and original cutoff. No new-source retrieval occurred in the original runner.
- `new-platform/backend/app/data/focus_application_snapshot.json`: provisional cycle crosswalk, not verified FDA application identities.
- `new-platform/backend/app/level16_staging*.py` and review-event infrastructure: legacy isolated staging, not a substitute for owner execution or validated science. No retired outside reviewer gates are activated.
- `new-platform/backend/app/assessment_service.py`: separate candidate model index/history, **not** Level 1–6 engines. Its scores are not substituted for a level result.
- Existing `FullTrialRecord`, candidate histories, source worker histories, historical freezes and frontend charts are preserved. New history uses a separate additive table.

## New execution and persistence path

The Assessments page mounts `TrialLevelAssessment` above the retained collected-research runner. It supports exact NCT entry, a selector for every level, Current Evidence / unavailable Blind Historical selection, execution/error status, phase/status, limitations, recommended evidence collection, explicit score/prediction availability, and saved report versions.

`POST /api/assessments/trial` requires the existing signed owner dashboard session and same origin, rejects extra source/role/score claims, bounds the request to 1 KiB, and checks durable-backend configuration **before retrieval**. It fetches ClinicalTrials.gov's exact `/api/v2/studies/NCT…` endpoint, validates exact identity and registry revision date, hashes the returned bytes and constructs a source-specific input snapshot. It dispatches the selected existing processor. It does not apply old FOCUS interpretations to the new registry revision. Registry posting is not extracted efficacy evidence. FDA filing status stays unverified/unmapped.

Any exact registered NCT can be entered, including records found in POOL, FOCUS or historical inventories. This does not alter membership or establish that a record belongs to any population. **Population browsing and combined search are not implemented** in this slice.

The server sends the report to authenticated `POST /api/assessments/trial/history` on the Python backend using the existing internal API key. A transaction appends a UUID-keyed `level_assessment_runs` row. Duplicate IDs return 409, never overwrite. Read-only migration mode blocks writes. Only an acknowledged save returns a completed result to the UI. The normalized evidence snapshot, byte digest, revision/retrieval dates, execution timestamp, exact NCT, level and engine version travel with each report. Database failure does not produce a fabricated saved result.

Authenticated `GET /api/assessments/trial?nct=NCT…&level=1` retrieves history through the backend; latest versions are shown together for inspection (latest 50, bounded to 3 MB; backend returns `hasMore`). This is not an automated version-difference algorithm. The old collected FOCUS runner remains explicitly session-only.

Storage uses the existing database configuration and storage readiness guard, with an additional PostgreSQL requirement for these endpoints even when general development storage permits SQLite. Local tests explicitly override that dependency. The additive migration is `new-platform/backend/migrations/20261114_trial_level_assessment_history.sql`; local bootstrap also knows the new SQLAlchemy model. Hosted migration/application, PostgreSQL verification, release checks and deployment remain outstanding. An internal key is a service credential; public clients never receive it.

## Historical isolation

Blind Historical requires a valid past calendar cutoff. **No eligible immutable outcome-isolated source provider exists in this repository for arbitrary trial/cutoff pairs.** The UI identifies that mode as unavailable and disables execution. The API independently rejects it with 409 **before any source retrieval, scoring, prediction or persistence**. Current evidence cannot be relabeled historical by submitting a cutoff. The backend also rejects historical report writes. Tests assert zero source calls when this mode is requested.

This is a tested refusal boundary, **not a functioning blind backtest**. Point-in-time source version selection, publication/availability cutoff filtering, outcome-isolated model inputs, prediction freeze followed by separately authorized outcome comparison, and blinding/exposure accounting remain unimplemented. No existing outcome-exposed historical file is rewritten or promoted into calibration.

## Validation receipt

- Backend regression: **1,193 passed, 3 skipped**, 6 warnings on the final backend changes.
- Frontend regression: **159 test files passed**, zero failures. Direct execution of the new test file reports seven individual behavioral tests; the configured Node test runner summarizes at file level in this environment.
- TypeScript `npm run typecheck`: passed.
- Mandatory `python scripts/audit_raas_retirement.py --check`: passed, zero active dependencies/violations; archived records retained.
- New backend tests: all six levels append/retrieve, duplicate UUID refusal, exact-NCT history isolation, authorization, invalid level/model/score/history rejection and read-only mode.
- New frontend/API tests: selected dispatch through all six actual processors, exact identity/version validation, current source isolation, FDA abstention, historical cutoff/refusal-before-source-access, session/origin/body bounds, missing backend, save failure, history retrieval and UI behavior.
- Live ClinicalTrials.gov retrieval and processing succeeded for **NCT04576949 individually at Levels 1–6**, registry revision **2026-01-15**, response SHA-256 `cfa130cf267e194e5919aa705086e766f5beda55a9c59714e46bae3879d2e210`. Each returned its own `phase-first-level-N-v1` and FDA ABSTAIN.
- Those six actual-source reports were sent to the real Python API using an isolated local SQLite database; each was saved and retrieved unchanged. This does not verify hosted PostgreSQL or production.
- No remaining failures in the executed checks. Hosted PostgreSQL and browser end-to-end production verification have not run.
- Initial failures repaired: the old Level 3 test rejected the newly supported Level 2 selection; the COMPANY test expected an obsolete 29-record source cohort although its current source file contains 32 retrieved records. Neither repair changes source records.
- Environment issues: npm initially could not write its default cache; retry with `/tmp` cache succeeded. Restricted-network Python TestClient runs stalled on its local event loop; identical tests with local network access passed. Direct Node retrieval initially failed because it ignored the environment proxy; the live check passed with `NODE_USE_ENV_PROXY=1`. Production proxy requirements remain environment-specific.

## Completion status

“Yes” below means verified in development, not production. “Results saved” means isolated local database tests, not hosted records.

| Level | Engine implemented | Executable | Tested | Results saved | Status |
|---|---|---|---|---|---|
| 1 | Partial | Yes | Yes | Yes, local | PARTIAL — not ACTIVE |
| 2 | Partial | Yes | Yes | Yes, local | PARTIAL — not ACTIVE |
| 3 | Partial; narrow clinical heuristic | Yes | Yes | Yes, local | PARTIAL — not ACTIVE |
| 4 | Partial | Yes | Yes | Yes, local | PARTIAL — not ACTIVE |
| 5 | Partial | Yes | Yes | Yes, local | PARTIAL — not ACTIVE |
| 6 | Partial | Yes | Yes | Yes, local | PARTIAL — not ACTIVE |

Full activation remains incomplete: verified regulatory evidence, source-specific original-document extraction, indication-specific scientific engines, actual supported scoring methods, point-in-time blind execution, combined population selection, automatic version diffs, existing-history aggregation and downstream FOCUS/CALENDAR/COMPANY integration are outstanding. There is no supported automatic mapping from these unreviewed registry research reports into those views' scientific scores or FDA forecasts; none is invented. No validated numerical FDA predictor or calibration dataset was found. No level can be called live without independent production execution/persistence/retrieval verification after an authorized release.
