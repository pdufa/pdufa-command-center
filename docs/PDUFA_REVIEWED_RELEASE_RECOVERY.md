# PDUFA reviewed-release preparation and runtime recovery

This repair makes the installed controller's version and Level 7 blockers
inspectable, and connects the existing reviewed-release transport to an exact
reviewed installer version. It is a draft engineering change. It does not install
on the owner's PC, enable the release channel, certify a scientific level, or
complete the autonomous coding system in [issue #1171](https://github.com/pdufa/pdufa-command-center/issues/1171).

The active pipeline remains **POOL → FOCUS → Deep Medical Intelligence → FDA
Decision**. Preserve completed Levels 4–6 engineering evidence, all scientific
review history, source archives, and POOL/FOCUS membership.

## Existing components reused

| Component | Responsibility and limit |
| --- | --- |
| `pdufa_level_completion.py` | Runs the approved source, implementation, regression and review checkpoints. Does not invent missing domain code. |
| `pdufa_engineering_review_lanes.py` | Advances only the approved engineering slice after its evidence passes; independent scientific acceptance remains separate. |
| `windows_pdufa_level6_unblock.ps1` | Existing bounded installer, despite its legacy filename. Reuses owner/idle checks, exact file pins, staging, backups, local tests, guarded task migration and fresh heartbeat verification for the Level 7 readiness slice. |
| `windows_local_agent_watchdog.ps1` | Recovers the existing worker under its owner/STOP/heartbeat safeguards. It does not author or deploy code. |
| `windows_pdufa_reviewed_release_updater.ps1` | Separate owner task that polls protected `origin/main` every 15 minutes and at sign-in for explicitly approved releases. Its setup does not install a worker release. |
| `pdufa_predictive_preflight.py` | Audits shared source/install dependencies and future domain gaps. Static success cannot certify a running Windows host. |
| `pdufa_runtime_status.py` | Read-only local diagnosis of runtime provenance, installed code, heartbeat and checkpoint evidence. It never starts/stops tasks, modifies ledgers, downloads code or submits a review. |

Level 7 currently implements a source and temporal-validation **gap inventory**.
It is not a fitted or calibrated FDA prediction model. The earlier registry
inventory slices likewise do not establish independent statistical, preclinical
or regulatory adjudication.

## One preparation and release path

1. Prepare one coherent release with the runtime reporter, controller, Level 7
   source modules, installer, updater, watchdog and the exact installed test set.
   Keep every installer file pin synchronized with its reviewed source bytes.
   Run the runtime, controller, source, release-policy and partial-install tests
   together; do not bypass a failing suite to advance a level.
2. Review the complete release PR and obtain the required independent approval
   and green required checks on protected `main`. A draft, open PR or successful
   CI run alone is not a release authorization. The updater requires verifiable
   branch protection; inaccessible or missing protection blocks installation.
3. After that release is merged, record its **exact merge commit** and installer
   Git blob SHA. In a separate reviewed protected-main PR, create the live
   `automation/windows-release-channel.json` from the disabled example, with
   the exact release commit, installer blob, approved release PR and explicit
   release intent. Do not use a moving feature branch, an unmerged draft head,
   or guessed hashes. The live channel is intentionally absent in this repair.
4. After owner approval, stage and verify the reviewed updater at the approved
   checkout and perform its one-time `-Install` setup on the actual Windows PC.
   Setup registers only the updater task. A subsequent `-Check`, or the scheduled
   check, uses the same release path for the consolidated worker migration.
   Normal future approved releases use this transport; they do not require a
   new per-level installation command.
5. The updater verifies channel policy, review/checks, commit reachability and
   downloaded installer bytes before using the installer. It passes the exact
   `-ReviewedReleaseCommit` to both `-Preflight` and `-Install`. Reviewed mode
   verifies the corresponding protected-main release authority and resolves all
   pinned files from that commit. The old draft-branch path is a separate legacy
   mode and cannot stand in for reviewed-release authorization.
6. Require a fresh post-restart worker heartbeat from the expected controller
   and matching runtime files before reporting installation success. Preserve
   the previous installer, file/task backups and local release receipt. Review
   the source and engineering evidence separately from installation success.

The updater keeps the last successful installation in
`installed-release-receipt.json`, separately from the latest poll in
`reviewed-release-updater-status.json`, under the agent data directory. A later
disabled channel or failed poll must not erase the successful installation
receipt. The installer removes only its own unique graceful-upgrade STOP marker;
an owner-created replacement stop blocks restart and is preserved.

These steps prepare a transport for reviewed releases; they do not demonstrate an
unattended code-authoring agent. No verified autonomous coder is supplied by this
repair. Code generation, bounded fixes and draft-PR creation still need their own
implementation and proof. Levels 8–20 still require their reviewed domain
modules, primary sources and tests. The repair must not toggle those levels to
complete or fabricate independent scientific acceptance.

## Read-only status on the Windows host

Run from the owner's existing, verified checkout after the reporter is installed:

```powershell
$repoRoot = 'C:\PDUFA\pdufa-ai-agent'
$agentData = Join-Path $env:USERPROFILE 'PDUFA-Agent-Continuous'
py -3.13 -B (Join-Path $repoRoot 'scripts\pdufa_runtime_status.py') `
  --root $repoRoot --data-dir $agentData
powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File `
  (Join-Path $repoRoot 'scripts\windows_pdufa_reviewed_release_updater.ps1') -Status
```

The reporter prints JSON to standard output. `--heartbeat <path>` can inspect a
specific retained heartbeat; it does not make that heartbeat fresh or prove it
describes the current process. The inspecting Python process and a recorded
worker runtime are separate observations. A current checkout alone cannot prove
which code a long-running worker imported.

The worker records startup source blobs and compares them with current disk
files in its heartbeat provenance. Branch/SHA and release information identify
the checkout; they do not confer release approval. Missing runtime provenance is
reported as legacy/unverified. Missing, malformed, stale or inconsistent local
records remain unknown or blocked rather than being repaired by a status query.

## Recovery decisions

| Observation | Action |
| --- | --- |
| Owner `STOP` exists | Preserve it. No installer, updater or watchdog should clear an owner stop to make progress. Resume only through an owner-authorized operation. |
| Worker is busy, task ownership/action is wrong, heartbeat is stale, or lock ownership is uncertain | Preserve the running state and gather status. Do not kill a process, force a task restart or overwrite code that might be active. |
| Runtime provenance is absent or startup blobs differ from disk | Treat the running version as unverified or drifted. Prepare the reviewed repair and verify an idle migration through the release path; copying files alone does not upgrade imported code. |
| Installation/code dependency is missing | Correct the reviewed release payload or environment prerequisite, rerun offline and partial-install tests, then use the reviewed transport. Do not mark a checkpoint complete because its module now exists. |
| Level 7 prior source receipts are missing, invalid or incomplete | Repair or obtain the actual source receipts through the approved source task. Registry receipts and exact-NCT matching must pass; a restart cannot supply missing evidence. |
| A Level 7 regression or retirement check fails | Keep the checkpoint blocked, fix the implementation in a reviewed PR, and rerun the real suite. Do not substitute a test count or success flag. |
| No approved channel, disabled channel, unverified protection/review, failed required checks, wrong commit/blob, or source drift | Keep updates blocked. Prepare the correct independently reviewed release; never weaken the gate. |
| Release is already recorded as installed | Do not install it again just to retry science/source work. Inspect runtime and checkpoint evidence; escalate a stale success receipt or inconsistent runtime for review. |
| A pre-start install failure leaves a verifiably idle worker | Use the installer's recorded backup and bounded rollback path. Retain the failure receipt. |
| Restart was requested but a fresh matching heartbeat cannot be confirmed | Report failed/unverified activation. Preserve backups and investigate the actual host; do not force rollback over potentially active code. |

Only the four recognized **old Level 7 placeholder** blockers may be reopened by
the existing once-per-version integration migration, after its module, roster,
prior receipt and PR checks pass. Their prior evidence is retained. New source,
test, identity, review or unknown errors are not erased. Levels 4–6 acceptance
evidence and the independent scientific ledger remain intact.

## Verification boundaries and remaining owner actions

The PR-only `level7-runtime-release-repair.yml` runs the offline regression and
exact installed-file tests on Linux and Windows. Native Windows PowerShell 5.1
parses the installer, updater and watchdog and exercises read-only updater
status. Synthetic fixture tests simulate policy/failure conditions. CI has
read-only repository permission, does not receive deployment credentials, and
does not schedule an installer, enable a release channel or change owner tasks.

Actual Windows Task Scheduler ownership/action, installed blob versions, Python
3.13/Git/gh authentication, available disk, source connectivity, worker idleness,
backup/restore behavior and a new matching worker heartbeat must be checked on
the owner's PC. GitHub status cannot certify these host facts. Main-branch
protection, review/merge, release-channel enablement and the one-time PC setup
remain externally controlled until separately authorized and observed. Keep
issue #1171 open for its remaining coding-agent, notification, recovery and
Levels 8–20 acceptance work.
