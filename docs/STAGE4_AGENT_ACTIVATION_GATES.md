# Stage 4 autonomous development agent — activation gates

Status: **NOT ACTIVATED OR VERIFIED**. This document is a non-executable review checklist. It grants no approval to spend, deploy, merge scientific changes, or call a model.

## Preconditions

1. Confirm exact canonical FOCUS membership (29 distinct NCT identifiers) against a current authoritative roster snapshot; fail closed on missing, duplicate or additional identifiers.
2. Preserve immutable historical outcome-blinding boundaries and prediction versions. Historical known outcomes must not enter prospective model features.
3. Preserve FS/FA preset associations and existing protected prediction rules without reassignment.
4. Require independently authenticated, dated source evidence and authorized reviewers before any clinical adjudication. A source lead, successful fetch, CI pass or AI-generated explanation is not verification.
5. Keep Stage 4 pending adjudications at **29** and review gates at **232** until an authoritative, independently verified ledger establishes a changed count. These are tracked baseline counts, not evidence of completion.
6. Define a hard, provider-enforced monthly spending cap and verify usage metering and stop behavior before adding model credentials. A proposed $10 budget in configuration is **not** a billing limit.
7. Scope GitHub token to the least privilege needed. Generated changes must use separate branches and pull requests, with CI, human review, and no automatic merge of scientific or prediction-rule changes.
8. Verify secrets are masked and inaccessible to pull-request code; reject fork-triggered secret exposure, uncontrolled shell execution and arbitrary task prompt injection.
9. Test rollback, idempotency, retry limits, concurrency locks and failure notifications. Record exact commit SHA and CI run for every accepted change.
10. Require separate explicit approval for production deployment, source adjudication, calibrated FDA probabilities and any broker or trading action.

## Operational interpretation

A five-minute scheduled preflight is **not** proof of a running coding agent. Successful CI is **not** scientific validation. An agent is operational only after a live, metered, bounded task has produced an auditable branch/PR with an exact-run receipt, without crossing protected gates.

## Current development branches

PR #1075 proposes a scoped coding queue but its latest checked head has a failing general CI workflow. PR #1076 proposes a read-only budget preflight; its checks were pending when this document was prepared. Neither proposal should be considered activated on the strength of this document.
