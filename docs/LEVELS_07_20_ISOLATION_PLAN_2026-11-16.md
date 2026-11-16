# Levels 7–20 isolated implementation contract (2026-11-16)

## Owner instruction
Develop Levels 7–20 without affecting **any of Levels 1–6**. Levels 1–3 and 4–6 are both protected. This is an implementation plan, **not a claim that Levels 7–20 are complete**.

## Non-negotiable isolation
- Work only on dedicated feature branches and draft pull requests. Never merge, deploy, or trigger production scans from this plan.
- Do not change Levels 1–6 algorithms, prompts, scores, prediction versions, source snapshots, UI displays, test fixtures, configuration, migrations, database rows, or existing membership in POOL/FOCUS.
- Do not change shared runtime imports, global configuration, scheduler wiring, database schemas, frontend routes, or existing APIs until a separate compatibility review proves no impact. Additive code must be unreachable from production by default.
- New Level 7–20 implementations should live under a self-contained namespace (proposed `new-platform/backend/assessment_levels_07_20/`) with independent fixtures, tests, and versioned outputs. Do not silently read mutable Level 1–6 outputs: use explicitly versioned, read-only input contracts and sample fixtures.
- No write path to existing scores, historical records, calibration, or prediction state. No hidden activation. No real API calls, paid services, or external reviewers as prerequisites.
- Honor `AGENTS.md`: sole-owner governance, RAAS retired, exact NCT/application identity, evidence provenance, phase/indication applicability, missing evidence, outcome-exposure controls, no guaranteed or uncalibrated FDA probabilities.

## Delivery gates for each Level 7–20
1. Inventory existing implementation and define the level's scientific/engineering requirements from current project specifications. Do not invent completion criteria.
2. Write an explicit input/output contract with version, provenance, missing-data and leakage markers, and no mutable shared state.
3. Implement isolated logic plus deterministic unit tests, negative tests, and missing-evidence cases.
4. Run compatibility tests showing Levels 1–6 files and outputs are unchanged, plus RAAS retirement audit and relevant regression tests.
5. Produce an independent draft PR with changed-file inventory, test evidence, known limitations, and explicit activation=false.
6. Mark level complete **only** after code, tests, and acceptance evidence exist. A plan or placeholder is not completion.

## Integration policy
Keep all Levels 7–20 disabled and out of active workflows until separate owner-approved integration. Rebase and resolve conflicts only after Levels 4–6 resume and their interfaces are frozen. Protect prospective prediction freezes and historical outcome leakage classifications.

## Current verification
The repository's `infra/assessment/sole-owner-levels1-20.json` states `levels7To20EngineeringComplete: false`. No implementation or tests are asserted by this planning document. Levels 1–6 remain untouched by this branch's intended change.
