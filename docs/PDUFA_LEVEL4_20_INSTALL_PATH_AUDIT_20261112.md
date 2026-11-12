# PDUFA levels 4–20: full installation-path audit (2026-11-12)

Scope: GitHub branch `automation/full-install-path-repair-20261112`, reviewed draft PR #1167. This is **not proof that the owner's Windows host has been inspected or modified**. CI validates scripts and offline engineering tests; only a fresh, observed host heartbeat can confirm runtime deployment.

## Serial installation and level-advancement path

1. GitHub domain code is built in a draft review PR for each approved bounded engineering scope. Levels 4, 5 and the Level 6 clinical-registry *gap inventory* have draft implementations. Level 7 has a preparatory validation-readiness draft, **not approved as current-stage implementation**. Levels 7–20 still require actual, reviewed domain modules, sources and tests; no flag toggles are acceptable shortcuts.
2. GitHub CI checks source/phase provenance, tests, permanent retired-system audit and engineering-versus-independent-science separation.
3. The Windows operator invokes the version-pinned installer `scripts/windows_pdufa_level6_unblock.ps1` with `-Preflight` (read-only) followed by `-Install` only on success.
4. Preflight validates Task Scheduler worker ownership and action; owner STOP suppression; confirmed idle heartbeat and no live engineering task; required Python 3.13, Git and authenticated GitHub CLI; the exact reviewed draft PR #1163; expected repo origin, checkout root and the approved GitHub source branch.
5. On installation, safeguard watchdog from competing with the graceful migration; never terminate in-flight PR work or stale/unknown running processes. Source retrieval is SHA-1-blob pinned for every installed file and is verified again after download.
6. Copy existing installed files to timestamped backups. Replace staged files only after their hashes are verified. Run controller self-tests, Level 4–6 domain and integration tests, strict sequence tests, the serial planner and the permanent retirement audit. Any failure before scheduled-worker restart restores prior files/action without pretending success.
7. Install approved engineering task action only after all tests pass, remove only the installer's own graceful STOP, restart task, require a **fresh post-request heartbeat** from the correct engineering controller and strict sequence ledger. If restart cannot be verified, return nonzero without forcibly terminating potential work.
8. Re-enable/install watchdog. The updated watchdog selects active engineering versus legacy queue ledgers; reports blocked/idle engineering work and refuses duplicate restart loops. It still respects owner STOP, nonowner tasks, stale running heartbeats and safe task state. This is a recovery watchdog **not an autonomous coding agent**.
9. The Level 6 controller may once-only reopen its four known old placeholder blockers and retains exact prior-blocker receipts. It must actually retrieve its source inventory, pass tests and verify draft #1163 before recording its narrowly scoped engineering milestone. Independent scientific approval is not implied. Level 7 follows only when those engineering checks genuinely pass.

## Confirmed recurring blockers addressed

| Potential blocker | Mitigation / verification |
| --- | --- |
| Old intake ledger consulted after engineering migration | Watchdog now selects active controller ledger |
| Idle controller re-launched every two minutes | Watchdog checks actual Level 6+ pending/blocked work before restart |
| Unrelated old pending queue prevents safe engineering upgrade | Engineering idle path checks current engineering state, preserves legacy history |
| Missing Python/Git/gh auth or remote PR/branch | Read-only `-Preflight` checks before any drain |
| Wrong owner, unsafe worker state, owner STOP, stale heartbeat | Fail-closed preflight; no force-kill |
| PR scope or original-source drift | Exact approved PR #1163 and file Git blob map |
| Failure after code tests but before Scheduled Task activation | Roll back copied files and task action if still idle |
| False success from preexisting heartbeat | Require heartbeat newer than restart request |
| Unreviewed scientific signoff / blind historical outcome leakage | Read-only source-inventory and phase-first review safeguards remain active |
| Unknown later-level implementations | Retain `AUDIT_ONLY_UNTIL_DOMAIN_IMPLEMENTATION_REVIEWED`, never fabricate advancement |

## Outstanding — not automatically repaired by this release

- A one-time local invocation on the Windows host is still necessary. GitHub CI cannot claim to install or restart a private Windows PC.
- No authenticated autonomous coder is currently connected to create every Level 7–20 module and its required original-source evidence. The serial planner enumerates next work; it does not write code.
- No opt-in securely reviewed automatic release transport is installed for all future levels. A watchdog is not a software deployer.
- Public original preclinical and regulatory sources are not independently verified merely by a registry gap inventory.
- Canonical current FOCUS membership and independent scientific/statistical approvals are distinct from engineering success.
- Runtime tests of real Windows Task Scheduler owner/state, internet access and ClinicalTrials.gov original-source acquisition must be performed on the host. These are environmental uncertainties until local preflight/install succeeds.

## Host action

Fetch the reviewed installer from the **exact PR head commit**, run `-Preflight`, then `-Install` only if preflight passes. This release does not merge, deploy a public website, publish predictions, trade or independently approve science.
