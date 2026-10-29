# iPhone operator workflow for staging reconciliation

Status: **NOT READY / ABSTAIN**. No staging retrieval has been executed by this
workflow yet. Fresh approval for possible staging identity allocation is required
before starting it.

## What is supported

The current ChatGPT execution tools provide no secure human terminal-input
control or secret-binding control. Do not enter a key in chat. The existing
Render staging Free service has no Dashboard Shell/SSH. Neither is proposed as
an iPhone terminal solution.

Use Safari and GitHub Actions instead. The workflow filename
`isolated-readiness-smoke.yml` already exists with `workflow_dispatch` on the
repository's default branch. Selecting the research branch runs that branch's
definition, including the added staging job. No main merge, backend deployment,
Codespace, paid Render upgrade or new credential is required.

The original isolated-review job and its credential remain unchanged. The new
job only runs on manual dispatch of
`research/fda-decision-label-gate-20261028`. It reuses the existing authenticated
Python client and the fixed staging origin. It never automatically runs on
push, PR or schedule.

## Phone steps

1. Open the [Render staging service](https://dashboard.render.com/web/srv-db976hfbtjjs73bb98fg)
   in Safari. Tap **Environment** and check **Environment Variables** (or a
   **Linked Environment Group**) for `PDUFA_INTERNAL_API_KEY`. This is the
   existing server credential's expected location. The agent's connector cannot
   confirm its presence or retrieve it securely. If absent, stop; do not rotate
   or create a replacement without separate authorization.
2. Open [GitHub Actions secrets](https://github.com/pdufa/pdufa-command-center/settings/secrets/actions)
   in Safari. Tap **New repository secret**. Enter the name
   `PDUFA_STAGING_INTERNAL_API_KEY`. Enter the **existing staging value only in
   GitHub's protected Secret field**, then tap **Add secret**. Do not put it in
   chat, workflow inputs, repository files, logs or screenshots. Do not reuse the
   `isolated-alpaca-review` key. This stores the existing key for the approved
   runner; it does not change or rotate Render's key.
3. Obtain fresh explicit approval for one staging reconciliation run. A summary
   or page GET can refresh published-source caches. Page preparation can insert
   missing exact program identities into staging `program_identity`, including
   keys used by Pipeline and GEM history. Existing IDs are read unchanged;
   source-key uniqueness and conflict-safe inserts prevent duplicate stored
   identities. Sequence gaps can occur under concurrent insert attempts. The
   path does not update restrictions, FS/FA associations, scientific assessments
   or trading settings. Staging database state/constraints remain unprobed.
4. **Only after approval**, open [the manual workflow](https://github.com/pdufa/pdufa-command-center/actions/workflows/isolated-readiness-smoke.yml).
   Tap **Run workflow**, select branch
   **research/fda-decision-label-gate-20261028**, then tap **Run workflow**.
   The page retains the registered name **Isolated PDUFA Readiness Smoke**;
   the research-branch job is **Authorized staging Pipeline reconciliation**.
   Do not choose main or the separate isolated-review branch.
5. Open the completed run. A successful **staging-pipeline-reconciliation**
   artifact contains only `pdufa-pipeline-reconciliation.json` and expires after
   one day. The agent can inspect that run/report through GitHub without
   receiving the secret. A missing key, denied authentication, source drift or
   incomplete pagination fails visibly without a successful report.

Repository administration/Actions permissions are needed for these GitHub
buttons. If unavailable, an authorized repository operator must perform the same
steps; granting database access publicly is not an alternative.

## What executes

The manually selected job checks out the research branch without retaining Git
credentials, injects only `secrets.PDUFA_STAGING_INTERNAL_API_KEY` into the
client's process environment, and calls the existing summary/pages/summary
runner with explicit identity-allocation authorization. No secret is printed or
written to an artifact. The job has read-only repository permissions, a bounded
timeout, serialized runs and no deployment command.

The report reconciles counts, page/version/timestamp consistency, duplicates,
source-presence counts and blocked screening records. Raw individual program
records and credentials are not uploaded. Report hashes establish local JSON
integrity, not independent FDA evidence. The previously observed registry and
assessment counts are separate populations; no equality is assumed. No verified
eligibility counts or preliminary outcomes are inferred before actual data and
evidence review.

Local verification: **112 preliminary/workflow tests passed**; combined
research suites **958 passed plus 298 subtests**, one external fixture skipped,
zero failures. Independent workflow/HTTP review passed 50 tests with no material
findings. These are software checks, not a live staging authentication result.
Repeated manual dispatches are serialized, not deduplicated: approve and start
exactly one run.

## Verified interface references

- [GitHub manual workflow and branch selection](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
- [GitHub workflow_dispatch ref/default-branch requirements](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#workflow_dispatch)
- [GitHub Actions secret form](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets)
- [Render Environment settings](https://render.com/docs/configure-environment-variables)
- [Render Free service limitations](https://render.com/docs/free)
