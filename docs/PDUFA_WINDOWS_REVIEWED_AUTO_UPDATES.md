# PDUFA reviewed Windows release updater

**Scope:** One-time Windows Scheduled Task bootstrap; after that, poll **every 15 minutes and at sign-in** for approved engineering releases. This does **not** author code, merge PRs, approve science, deploy production, or make FDA predictions. The watchdog remains the separate 2-minute recovery task.

## Trust model (fail closed)

The poller reads `automation/windows-release-channel.json` **only from origin/main**. It does not read PR branches, unmerged drafts, environment variables, unsigned URLs, or chat instructions as authority to update.

A release is eligible only if all conditions hold:
- The remote is precisely `pdufa/pdufa-command-center` and `main` is fetched successfully without modifying the worktree.
- GitHub's branch-protection API confirms that `main` requires **at least one independent approval** and **at least one required status check**. Without verifiable protection, no installation occurs. An organization ruleset alone is **not currently accepted** by this check; add branch protection or formally extend the verifier.
- Manifest schema `1`, channel `pdufa-reviewed-windows`, and explicit `enabled: true`.
- `release_commit` is a 40-digit exact Git commit SHA; `installer_git_blob_sha1` is a 40-digit exact Git blob SHA; the installer path is fixed; `approved_pr` is a positive PR number.
- The specified PR is **merged** into `main`, has an **APPROVED** review decision, is not a draft, and its `mergeCommit.oid` equals `release_commit`.
- All required PR checks pass. The commit must be an ancestor of the fetched `main`; Git itself confirms that the installer file at that commit has the pinned blob SHA.
- Downloaded installer content matches the expected Git blob SHA exactly, or the update is rejected.

**Important:** The protected-main manifest must only be enabled in a *separate reviewed PR* after the release implementation has been merged, so its exact merge commit SHA is known. Do not skip that review, remove branch protection, or enable a draft PR. The example manifest in this branch is disabled and **not** the live channel. There is **no live automatic deployment until this approval configuration exists on main.**

## Windows safeguards

- Registers `PDUFA-Reviewed-Release-Updater` under the current signed-in Windows account; checks every 15 minutes and at logon using Task Scheduler. Setup never installs a release or restarts the worker.
- Respects owner `STOP`, validates worker ownership, exact repository origin/root, GitHub authentication, and acquires a local exclusive updater lock.
- Does not interrupt a running worker. Instead, the pinned existing `windows_pdufa_level6_unblock.ps1` runs its own **read-only `-Preflight`** (idle + queue + task-state + source checks) before `-Install`; that installer retains its guarded drain, rollback, verified heartbeat, and watchdog setup.
- Backs up the original installer. If pre-start checks fail and the worker is safely idle/Ready, the previous installer is restored. If the worker may be running, no forced rollback or termination is attempted; requires manual review.
- Tracks `release_commit` and result in `%USERPROFILE%\PDUFA-Agent-Continuous\reviewed-release-updater-status.json`; a recorded successful release is not installed again.
- Failures are visible in Task Scheduler and through the status command. Schedule runs only while the owner signs in (interactive logon).

## First-time bootstrap (once per PC)

After the updater code is peer-reviewed, validate its exact pinned hash before installation:

```powershell
$root = 'C:\PDUFA\pdufa-ai-agent'
$script = Join-Path $root 'scripts\windows_pdufa_reviewed_release_updater.ps1'
$releaseSha = '4acc2b9a5bc7599e079e1c4fef19f34a19f8d67e'
$expectedBlob = '72e3c0c47d22cc5302b48a4d0f0ecfaa39f87f1d'
$source = "https://raw.githubusercontent.com/pdufa/pdufa-command-center/$releaseSha/scripts/windows_pdufa_reviewed_release_updater.ps1"
Invoke-WebRequest -UseBasicParsing -Uri $source -OutFile $script
$actual = (& git -C $root hash-object $script | Out-String).Trim()
if ($LASTEXITCODE -ne 0 -or $actual -ne $expectedBlob) { throw 'Updater code hash mismatch: stop.' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Install
if ($LASTEXITCODE -ne 0) { throw 'Updater registration failed.' }
powershell.exe -NoProfile -ExecutionPolicy Bypass -File $script -Status
```

Use `-Check` to request a manual poll, `-Status` to inspect progress, or `-Uninstall` to remove only the updater task. **Do not** place secrets, tokens, or account numbers into the release manifest.

## Release approval checklist (per release)

1. Develop and test code in draft PRs; obtain independent code and scientific reviews where applicable.
2. Finalize the **installer** for the released code; validate `-Preflight`, `-Install`, owner STOP, local tests, safe rollback, and actual source file pins.
3. Merge a release implementation PR through protected `main` with required approval/checks; record its exact `mergeCommit.oid` and installer blob SHA.
4. In a **separate protected-main PR**, publish `automation/windows-release-channel.json` following the disabled example but with `enabled: true` and exact release metadata, and merge that PR after approval.
5. Poller installs the new reviewed version during a safe idle window. If approval, CI, source, environmental or runtime validation fails, the worker remains unchanged. Review the local status and report; do not bypass gates.

The currently known Level 7 draft PR #1169 **is not** a merged main release and is **not** automatically eligible. The updater's installation is a transport capability, not evidence that Level 7 scientific work is complete.
