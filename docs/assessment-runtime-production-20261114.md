# Assessment evidence runtime production release

The owner authorized production release on November 14, 2026 after tests and safeguards. This runtime implements separate Levels 1–6 **evidence engines**; it does not claim complete scientific adjudication, validated clinical-benefit scores or calibrated FDA probabilities. FDA predictions explicitly ABSTAIN.

## Execution

`new-platform/backend/app/assessment_runtime.py` dispatches only the requested function:

| Level | Actual engine | Outputs and remaining evidence limits |
|---|---|---|
| 1 | `level_one` | Exact official registry identity, sponsor, original response digest, publication/capture receipts. These do not authenticate the sponsor's scientific claims. |
| 2 | `level_two` | Official registry phase/status, condition/population checks. FDA application identity/current regulatory status remains unverified. |
| 3 | `level_three` | Actual posted primary-result groups, denominators, measurements, statistical analyses, participant flow and adverse events; earlier-phase future pivotal requirements distinguished. Posting is not success. |
| 4 | `level_four` | Actual registered design, arms and enrollment; bounded retrieval and text extraction of the latest original linked protocol PDF. Amendment completeness and actual execution remain unresolved. |
| 5 | `level_five` | Reported estimates and interval consistency; actual original SAP PDF and source excerpts for estimands, multiplicity, missing data and sensitivity analyses. Prespecification/lock/unblinding and statistical adequacy remain unresolved. |
| 6 | `level_six` | Indication-specific review lenses and endpoint classification with original measures/timeframes. No sourced patient/population-specific meaningful-effect threshold or surrogate validation is installed. |

The score is precisely **100 × available applicable evidence checks / all applicable evidence checks**. This is level-specific evidence coverage, not a fabricated scientific efficacy score or an FDA probability. A result of 100 does not establish trial success. No unsupported medical-effect scoring algorithm or validated FDA model was found; none is invented. Clinical questions use the registry indication rather than matching by ticker; unsupported indications remain unmapped.

## API, storage and historical protection

Authenticated `POST /api/assessment-runtime/runs` creates an exact-NCT job and executes only on the owner's explicit request. Request fields are strictly bounded to NCT, level, mode and optional historical cutoff. PostgreSQL and existing write/storage guards are required on hosted endpoints.

Each execution records real progress transitions, a frozen normalized source snapshot, original response/PDF digests and capture/publication dates, execution timestamp, selected level, engine version and a report hash. The source and result tables enforce database append-only triggers. Job progress changes never overwrite a completed scientific report. Failed or interrupted jobs do not claim completion. Saved report hashes are verified during retrieval.

Additive tables are initialized by the explicitly authenticated execution path: `assessment_v2_jobs`, `assessment_v2_sources`, `assessment_v2_results`. Existing analysis, prediction, archive, identity and membership tables are not altered or copied. There is no new nightly worker, automatic promotion, or reassessment from an unverified news mention.

Blind Historical selects **only** immutable original snapshots with both capture and source-publication dates at or before the cutoff. It never fetches today's registry, protocol or SAP, or reads current model/outcome caches. Scoring inputs exclude FDA outcome and cached/derived prediction fields. A newly fetched old-dated PDF gets today's capture time; it cannot become a historical source by its printed date. Historical fixtures test this boundary without backdating real source records.

No eligible historical snapshot means HTTP 409, before creating a job or prediction. Public registry historical endpoints tested during this task returned HTTP 403. No access restriction is bypassed. Existing outcome-exposed retrospective files are not imported as blind sources. Human outcome exposure remains unknown and all runs remain excluded from calibrated/independently blind accuracy. There is no verified FDA application/outcome comparison provider for these runs; outcome comparison remains unavailable rather than manufacturing an answer.

## Frontend and platform links

The Assessments page provides population search (POOL / FOCUS / historical catalog), exact NCT entry, six-level selection, current/historical mode and cutoff, real persisted progress/error reporting, scores with explicit meaning, prediction abstention/confidence status, evidence/risks/recommendations, saved history and selection of two persisted levels/versions for side-by-side comparison.

POOL/FOCUS trial details, COMPANY, CALENDAR and NEWS exact-NCT links open the workbench and its immutable history. This is read-only navigation: it does not substitute these evidence scores into application forecasts, overwrite old charts, change FOCUS membership or trigger automatic scans. The retained collected-evidence runner remains available separately and explicitly session-only.

## Release targets and validation

- Frontend: existing Vercel project `pdufa-new-dashboard`, production branch `main`, root `new-platform/frontend`.
- Backend: existing Render service `srv-db976hfbtjjs73bb98fg`, deployment branch `new-platform-bootstrap`, automatic deploy disabled.
- Because the storage branch is substantially diverged, backend PR **#1189** contains only the isolated runtime, additive tables, separate identity-only choices, dependency, tests and router registration. It preserves the deployed branch's existing schemas and workers.
- Backend release merge: `3b5e5ec642c19f5c0874dae1ac4be36230efd278`; Render deployment initially requested as `dep-dbs7pptg1s2s73ee9drg`.
- Deployment-branch full backend regression: **427 passed, 2 skipped**.
- Main-branch full backend regression: **1,212 passed, 2 skipped**.
- Full frontend regression: **160 test files passed**; TypeScript passed; production Next.js build passed; mandatory RAAS retirement audit passed.
- All six actual engines processed NCT04576949 sequentially against live ClinicalTrials.gov evidence, persisted their results in isolated local storage, and retrieved matching immutable hashes. Levels 4/5 retrieved the original linked PDFs; this is not a mock document-presence flag.
- New tests exercise each engine separately in both source modes, pre-cutoff capture/publication selection, future-source rejection, no live historical fetch, outcome/derived-feature exclusion, immutable SQL history, authorization, invalid inputs, true frontend progress and saved-result rendering.
- Initial local failures were repaired or resolved: backend module lookup from the legacy deployment root used retired `app.py`; running in the backend package fixed the environment. The first restricted build could not parse TypeScript child-process output; the normal network-enabled build passed without bypassing typechecking. Historical PDF tests now seed actual frozen fixtures directly rather than attempting to backdate new collection.

The authorized browser workflow uses the existing `DASHBOARD_PASSWORD` Actions secret only for normal owner login, then selects and executes each level through the live workbench. It reads back the exact saved run and history hash, verifies abstention and checks refusal of missing old-cutoff evidence. It retains sanitized run/version/hash receipts only. No credential values, cookies, browser state, page text, screenshots, source bodies or traces become artifacts. It does not claim that refusal of missing historical evidence is a successful blind assessment.

**Production completion is pending the actual browser receipt.** Full scientific activation additionally remains blocked by the missing evidence/methods identified in the six-level table and the lack of legitimate pre-cutoff source snapshots. No result is automatically owner-accepted or labelled scientifically ACTIVE.
