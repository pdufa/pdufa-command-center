# PDUFA Codex/Copilot mandatory architecture constraint

Read [AGENTS.md](../AGENTS.md) first. **RAAS is permanently retired** unless the project owner explicitly reverses it. Preserve historical data as read-only archive evidence; do not import it in current medical analysis, Analyze Now, approval/CRL/delay prediction, certainty, FOCUS qualification or scheduled scans.

All generated code, issues, PRs, implementation plans, tests and deployments must enforce this constraint. Never add retired routes, menu entries, scheduled jobs, source data lookups for scoring, or installation tasks. Active architecture is POOL → FOCUS → standalone 12-level Deep Medical Intelligence → separate outcome assessment → independently calibrated certainty. Unknown or unvalidated results ABSTAIN.

The repository's enforced audit is `python scripts/check_retired_raas_policy.py`. Do not bypass it by renaming retired files or disabling the guard. Keep existing archived evidence immutable.

**Separate P3 and P3 POST-DATA workspaces are also retired.** Only POOL and
FOCUS are active trial populations; clinical Phase 3 data remains valid input.
Never restore retired pages, tabs, scheduled writes or installation gates.
Preserve the FOCUS source sheet and source-only monitoring, and see AGENTS.md.
