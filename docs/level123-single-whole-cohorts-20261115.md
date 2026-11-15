# Levels 1–3: individual and whole-list execution

The launcher on FOCUS, PAST and ASSESSMENTS now offers Single trial, Selected trials and Whole source list. Each requested trial/level produces a distinct immutable scientific research report. Scientific scores remain null/NOT VALIDATED and FDA forecasts remain ABSTAIN; saved execution does not establish scientific completeness.

## Behavior

- Whole lists are derived by the authenticated server and frozen in an immutable manifest. The client loads every inventory page, verifies one consistent hash and refuses partial or changing inventories. The 50-row search limit no longer limits whole-list execution.
- Request UUIDs make retries of uncertain submissions idempotent. One worker lease prevents concurrent resumes. Finite jobs continue after the popup closes; saved batch selection retrieves checkpoints after a reload. A server restart requires an explicit resume after the expired lease. Failed items have at most two execution attempts.
- Progress counts completion only after retrieving a saved report with the matching report hash, NCT, selected level, evidence mode, cutoff and scientific engine version. A saved status without a report cannot count as completion. Batch polling reads report receipts in one database round trip.
- PAST resolves the actual dated PAST event queue, rather than old completed registry trials. Every unlinked event remains a visible blocked item. Exact application/trial links must match retained source evidence and the correct decision year. Historical jobs require original pre-cutoff captures; no current-source fallback, FDA outcome label or cached prediction is used.
- Shared FOCUS results can use an explicitly dated whole-list manifest without modifying spreadsheet membership or representing the packaged snapshot as a freshly reconciled live sheet. Later individual results remain separate versions.
- Existing authentication, same-origin actions, private backend credentials, hosted PostgreSQL requirements, immutable history and write controls remain in force. No owner acceptance or external reviewer requirement was fabricated.

## Source population and real verification

The checked source inventory contains 32 exact FOCUS NCTs and 20 PAST queue events. These are dated source populations, not a current comprehensive FDA census. The PAST event queue has no exact sourced trial/application mappings in the isolated verification database; all 60 requested level items remain blocked, with zero completed historical research reports.

A fresh run against original live ClinicalTrials.gov sources saved and retrieved all 96 FOCUS research reports in an isolated local database, with 32 complete three-report sets, zero execution failures, zero numerical scientific scores and 96 FDA abstentions. Run IDs, immutable hashes and counts are retained in the verification receipt. This is not a production website run.

Separately, read-only queries of the existing isolated Neon branch `br-aged-poetry-akk9tcj9` confirmed the latest saved scientific records cover the reconciled 32-member FOCUS roster at each of Levels 1–3, with zero numerical scores and 32 abstentions per level. Prior histories were not changed.

## Validation and limits

- Frontend: 953 tests passed; TypeScript and Next.js production build passed.
- Backend: full suite plus new cohort tests passed; exact final totals are recorded in the verification JSON.
- Targeted cases include more than 50 inventory records, stale/partial inventory refusal, duplicate request replay, active worker lease, save/checkpoint interruption recovery, bounded failed retries, identity corruption, no completion without a report, historical source isolation, and authenticated proxy execution.
- Retirement audit passed with zero active dependencies. Existing source and spreadsheet memberships remain unchanged.
- Interactive browser QA could not run: system Chromium failed to open its required socket, and the separate cloud browser could not connect to the local preview port. No screenshot, mobile-layout or production browser verification is claimed.

This is a draft change against the existing integration branch. Automatic Vercel Git deployment is disabled for this branch. No merge, production deployment, production database change, trading action, notification or new scheduled task was performed.
