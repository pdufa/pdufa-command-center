# Historical cohort milestone — 2026-10-28

## Verified engineering

Main remains `7a88764c6a5d798b917d3b1cdcfe8a07964343e2`. Draft PRs #507–#509
are still open and unmerged. This increment reuses the existing cohort manifest
audit from main and adds exact member reconciliation plus an offline replay CLI.
It detects equal-count substitutions, aliases, repeated/invalid members and
unresolved/nonbinary dispositions without promoting metadata into model labels.
Contract: [hop-exact-cohort-roster.md](hop-exact-cohort-roster.md).

The full backend suite passed **634 tests**, with six existing syntax/dependency/
Pandas warnings and no failures. The **50 roster/CLI tests** are included in that
suite. Separate software review found no material issues. These tests use
fictitious fixtures; they do not measure FDA prediction performance.

The existing PR safety workflow now runs these checks. No production scanner
schedule, database schema/data, list membership, FS/FA association, spreadsheet,
broker or trading setting changes. Test-created SQLite files and logs remain
local ignored artifacts. GitHub CI results are recorded on the PR after push;
this report does not predeclare them.

## Actual research-asset recovery

Two existing GitHub research artifacts were downloaded read-only, their ZIP
digests checked against GitHub metadata, and their members inspected:

| Artifact | Actual ZIP bytes | Recovered PDF members | Verified ZIP SHA-256 |
| --- | --- | --- | --- |
| [12612773759](https://github.com/pdufa/pdufa-command-center/actions/runs/40232393298/artifacts/12612773759) | 88,709 | **0** | `cb56964e1dc785674c7964f10a0d914f24ce5cdab11f45445e275980b9dc683b` |
| [12612494369](https://github.com/pdufa/pdufa-command-center/actions/runs/40230033926/artifacts/12612494369) | 67,897 | **0** | `695bbcbeb7db02d9ac68f3dbfc7b234b90036fc7718f3a8d47531d4c3f5897b9` |

Both contain JSON audit/index/worklist reports only. Their metadata reconcile
with the committed 458 published-letter records and 457 claimed PDF checks.
Abeona 125807 and Rocket 125806 document-hash claims agree across reports, but
the PDF bytes are absent, so those document hashes **could not be recomputed**.
A verified ZIP digest is not a verified digest of an absent FDA PDF. The
original FDA bulk archive was not recovered either.

The recovered archives and full inspection summary remain in ignored local
`work/historical-source-recovery-20261028`; no archive payload is published by
this PR. These GitHub artifacts report expiration on November 24, 2026. Original
document retention and permitted source retrieval are unresolved evidence
requirements, not fulfilled by matching metadata hashes.

## Existing models and actual scientific status

The repository already contains legacy baseline/calibration infrastructure.
Its 146-row prediction history includes six `EXTERNAL_HOLDOUT` labels, with
other rows explicitly marked development, tuning, retrospective repair or
in-sample. Those rows lack exact FDA application/cycle identity, verified
model-training chronology, frozen-model hash and untouched-partition proof.
The 2024 builder references a 2025 model specification not found in tracked
files and labels its 2024 output `TUNING_COHORT`. No legacy builder/model was run,
rewritten or treated as independent FDA validation.

| Required measure | Actual result |
| --- | --- |
| Independently verified model-eligible FDA decision cycles | **0** |
| Independently backtested real cases | **0** |
| Out-of-sample accuracy, calibration/Brier, discrimination and uncertainty | **Not measured** |
| Validated prediction coverage / covered-case accuracy | **Not measured; no validated real forecasts** |
| SCIENCE independently certified assessments / depths | **0/40 / 0/20** |
| PEAK source leads on main | **10**, explicitly unadjudicated |
| OUTCOME | Research-only, unvalidated, probabilities unavailable |
| MAIN | Deployed baseline unchanged; combined PEAK research view remains in PR #507 |

## Deployment, data access and next work

Render still reports `pdufa-hop-readonly-review` deployment
`dep-dbgnvknlk1mc7392bml0` live at `7a88764c`. This is control-plane metadata;
no deployment was triggered. The runtime is online, but has no custom FDA/Render
host grants or internal API-key binding. The read-only PostgreSQL probe was
rejected before connection because the staging database's external IP allowlist
is empty. Current SQL/data contents remain unverified; no access controls changed.

Next evidence work requires retaining/retrieving original FDA documents,
independent action/cycle and original-publication adjudication, source-supported
PDUFA target revisions, an exact representative population roster, frozen
predecision features and program-disjoint untouched evaluation partitions.
Only then can existing or new baselines produce legitimate out-of-sample
accuracy/calibration comparisons. Reviewed offline exports or supported scoped
source access can unblock collection; production deployment/activation remains
separately controlled.
