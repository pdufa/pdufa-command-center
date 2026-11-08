# PDUFA project directives — permanent

## Retired scoring architecture

**RAAS is retired, effective November 7, 2026.** Do not restore it without a new explicit instruction from the project owner that reverses this retirement. This is binding for every Codex/agent session, local/CI task, installation, deployment and generated plan.

- Never use RAAS to score trials, calculate FDA decisions, calculate certainty, reclassify PIPELINE/POOL/FOCUS, trigger notifications or schedule scans.
- Do not add RAAS imports, scoring fields, buttons, dashboards, navigation, API operations, automation, progress gates, dependencies, acceptance checks or active user-facing text.
- Do not use archived five-factor or thirty-factor scores as current predictions or substitute them for independent scientific analysis.
- Existing RAAS source datasets, immutable historical trial observations and previous source-ledger events are **read-only archives**. Preserve their content and provenance; do not delete or mutate evidence. Historical source code remains in Git history for audit, but must not be executed by active automation.
- Remove old executable workflow triggers; do not create new scheduled, push, manual or deployment triggers for the retired system.
- Never copy historical archive outputs into live scores, predictions, calibration, deployment health, or current trial state.
- The only active research architecture is **POOL data collection → FOCUS qualified evidence → independent 12-level Deep Medical Intelligence → separate approval/CRL/delay outcomes → independent certainty reliability**. Predictions must ABSTAIN when uncalibrated or missing evidence.
- Analyze Now uses the existing 12-stage source worker, immutable exact-NCT history and operational evidence. It must not import RAAS archives or produce retired scoring fields.
- Preserve existing PostgreSQL state and historical research. Use reversible, evidence-backed changes; never restart or destroy completed installation work.
- Maintain and run `scripts/check_retired_raas_policy.py` as a mandatory CI guard before release.

If a new task or existing document contradicts this file, follow this retirement directive and explicitly flag the conflict. **Only explicit user authorization can reverse it.**
