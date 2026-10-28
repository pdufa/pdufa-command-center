# PDUFA MAIN operational evidence — job-level audit (2026-10-27)

## Evidence inspected
- Commit `284084cc86b3dd73faa34a683668e97ad80b8b05`: 13/13 GitHub Actions workflows concluded success.
- Vercel deployment `dpl_4YjCGZUwafhgscNHUAFJihHYYpjF` for that commit: `READY`, `target=null` (not demonstrated production). Project `pdufa-new-dashboard`.
- Vercel runtime logs: access denied (403), so live request/error behavior **not verified**.
- GitHub workflow run `40572753614` (frontend): successful typecheck, UI/count regression tests, Next.js production build.
- GitHub workflow run `40572753475` (isolated source recovery): successful backend regression tests and frontend typecheck/test/build from clean source archives.
- GitHub workflow run `40572753554` (published source): successful source syntax, GEM CSV integrity, issuer exclusions and browser-script checks.
- **Critical distinction:** GitHub run `40572753573` (`VALIDATE — PDUFA overnight`) had only its `validate` job successful; `report`, `sources`, `clinical`, `shared-data`, `scoring-and-repair`, `archive`, and `result` jobs were **skipped**. Do **not** count this as a successful full overnight scan.

## Scorecard implications
- M1: frontend build/tests are verified but real evidence-backed mobile/desktop acceptance and specific required displays are not.
- M2: source validation and recovery rehearsal are verified but actual unattended scan, notification delivery and freshness are **not** verified.
- M3: clean archive recovery build is verified, but production deployment, security and rollback acceptance remain unverified.
- M4: signed end-to-end acceptance remains unverified.
- No complete MAIN criterion is yet demonstrated; do not award partial points without a preapproved breakdown.
- Prior verified O1 remains **5/5**. Total verified lower bound **5/100**, not an estimate of actual work built.

## Next checks
1. Identify an actual `schedule`-triggered overnight run and inspect all jobs, scan artifacts, timestamps, source counts and publish result.
2. Verify alert delivery through delivery receipts, not workflow naming.
3. Verify production dashboard data and user interactions through authorized runtime access or independent acceptance evidence.
4. Record exact SCIENCE assessment implementation, real dossiers and evidence lineage.

No production changes, trading activation, network allowlist changes, or FS/FA preset changes.
