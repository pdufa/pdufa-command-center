# Historical FDA evidence continuation — October 29, 2026

## Completed development

Fetched `research/fda-decision-label-gate-20261028` from origin. Its actual tip was
`57748094`, matching the handoff. Continued on that branch, preserving its work.
GitHub PR metadata could not be read: `gh pr view 522` returned `Forbidden`.

Added `research/scientific_historical_verification.py`, a reproducible worklist
joining the existing source-lead registry to exact application identity, reported
action context, trial leads, scientific gaps and point-in-time exclusions. This
extends coverage beyond the existing outcome-only acquisition queue; it does not
replace the registry or any adjudication gate. Every case has nine open tasks:
authenticate original FDA documentation; adjudicate identity and review cycle;
verify outcome; verify decision date; establish publication clock; retain and
hash original bytes; verify pivotal trial identities/history; reconstruct
pre-cutoff evidence; review missing/contradictory evidence.

The worklist binds to a SHA-256 of the local registry. Its hash is explicitly
not an original FDA document hash or proof of publication time. Existing source
artifact hashes retain their original scope. Program access checks and v1's ban
on self-certification run before worklist generation. New audit files cannot
overwrite prior snapshots. `--check` detects drift against current source inputs.
The audit contains outcome context and must never be supplied as model input.

## Files added or modified

- `research/scientific_historical_verification.py`
- `research/evidence/historical_verification_worklist_20261029.json`
- `tests/test_scientific_historical_verification.py`
- `.github/workflows/scientific-historical-comparison-safety.yml`
- `tests/test_predictions_trial_source.py`
- `docs/historical-evidence-continuation-20261029.md`

The existing selector test assumed trial-ID order despite the implemented
label ordering. It now asserts source membership by trial ID. No application,
scanner, membership, preset, authentication or trading behavior changed.

## Historical cases and collected records

No new primary documents or independently verified cases were collected.
The generated artifact organizes existing leads, not new scientific evidence.

| Existing case | Application | Existing reported claim, unverified |
| --- | --- | --- |
| BCRX / Orladeyo pediatric expansion | NDA219776 | PASS |
| CORT / relacorilant | NDA219398 | CRL |
| NVAX / NUVAXOVID | BLA125817 | PASS |
| TNXP / Tonmya | NDA219428 | PASS |
| UNCY / oxylanthanum carbonate | NDA218607 | CRL |
| VNDA / Nereus | NDA220152 | PASS |

Verified structural totals: six registry cases, 26 source observations, 17
cutoff-admitted research observations, nine excluded observations, three linked
trial metadata leads. Cutoff admission does not establish independent review.
There are zero independently verified decision cycles and zero evaluated,
validated predictions. Existing reported claims are not newly verified facts.

## Comparison and scientific validation

The existing ten-criterion comparison engine remains unchanged. The new worklist
makes scientific feature gaps, exact-cycle uncertainty and cutoff exclusions
reviewable for each historical case. No case is promoted into comparison,
training or evaluation eligibility. The catalog validator confirms 650 draft
fields, 40 canonical assessments and 50 investigation levels; independently
validated definitions remain zero. Field IDs and canonical content are preserved.
Structural success does not establish scientific validation.

## Backtesting status

Existing backend code already provides chronological, application-disjoint and
optional program-family-heldout research evaluation, label masking and metric
contracts. Its full test suite passed. This increment does not introduce a new
backtesting engine or certify a frozen three-outcome validation protocol.
Existing binary research metric support does not establish separate validated
PASS/CRL/EXTENSION performance. No accuracy, calibration or probability is
reported. A preregistered versioned three-outcome protocol, representative
independently adjudicated cohort, frozen model and feature manifest, family
separation, horizon policy, abstention handling and uncertainty plan are still
required before evaluation claims.

## Verification

- Research regression selection: **773 passed, 1 skipped; 298 subtests passed**.
- Full backend suite: **1,004 passed, 1 skipped**.
- Four new tests cover cutoff/outcome exclusion, scope/self-certification,
  registry hash binding, CLI reproduction/drift and no-overwrite behavior.
- Worklist regeneration `--check`, catalog structural validator and
  `git diff --check` passed.
- Existing skipped integration tests do not establish successful live source access.
- No new GitHub CI result is claimed. Frontend was not changed or retested.

Research tests initially lacked PyJWT; installed the repository's existing
research requirements. Restricted runs stalled at local HTTP test clients;
runs outside that shell restriction completed. The initial research regression
failure was the selector test ordering assumption described above.

## External blockers and next milestone

Primary FDA and ClinicalTrials.gov HTTPS requests received proxy CONNECT `403`
denials. The managed network policy excludes those destinations. GitHub API
access returned `Forbidden`, blocking PR report/CI inspection and PR comments.
Git transport fetch succeeds; publishing status is recorded in the chat report.
No production merge, deployment or trading activation was attempted.

Next milestone: restore authorized primary-source and GitHub API access;
retain original bytes and publication evidence for the six cases; obtain
independent identity, cycle and outcome review; verify pivotal trial registry
history; then freeze and implement the three-outcome evaluation protocol before
reporting measured performance. Until those dependencies are met, the historical
verification milestone is incomplete and status remains **NOT READY / ABSTAIN**.
