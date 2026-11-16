# Levels 4–6 integration audit (initial)

Tracking: #1226; development branch: `feature/levels-456-isolated`.

## Confirmed existing contracts

- `new-platform/backend/app/assessment_runtime.py`: `NAMES` defines L04 trial design/protocol, L05 statistical analysis/multiplicity, L06 endpoint clinical relevance. `RunInput` allows L01–L06 for `LEGACY_SOURCE_AUDIT`, but `SCIENTIFIC_1_3` explicitly rejects levels >3. Coverage metrics are **not** clinical efficacy ratings or calibrated FDA probabilities.
- `new-platform/backend/app/scientific_levels_two_to_six.py`: a separate older evidence-readiness taxonomy calls L04 safety/benefit-risk, L05 indication-specific assessment, L06 regulatory readiness. These names conflict with runtime L04–L06; do not silently combine, rename or overwrite them.
- `AGENTS.md`: owner-only review, immutable provenance, historical leakage protection, no RAAS, and no production merge/deploy without permission.
- Existing `assessment-runtime-tests.yml` runs backend and frontend suites for relevant assessment paths; new `levels-456-regression.yml` provides broad branch PR regression checks.

## Required before scoring changes

1. Select the canonical L04–L06 taxonomy by tracing current deployed API, saved data, UI and tests. Preserve existing identifiers and compatibility; document migration/alias strategy if needed.
2. Extend scientific execution beyond 1–3 only after defining explicit evidence contracts, missing/not-yet-expected states, provenance, phase applicability and versioning.
3. Verify exact-NCT and review-cycle identity, prospective cutoff and outcome-leakage constraints; do not claim outcome-aware historical reruns are blind.
4. Keep evidence coverage separate from clinical performance ratings, approval decisions and calibrated probabilities. No invented confidence percentages.
5. Test unchanged L01–L03 outputs against baseline fixtures; add L04–L06 fixtures and UI integration checks before any deployment.

## Status

This is an initial code audit and CI setup, **not** a completed L04–L06 clinical scoring implementation. No production deployment is authorized.

## Additive L04–L06 scientific execution (development branch only)

- New **opt-in** backend request contract: `SCIENTIFIC_1_6`. Its L04–L06 taxonomy is defined explicitly in `new-platform/backend/app/scientific_levels_four_to_six.py`, separate from `LEGACY_SOURCE_AUDIT`.
- The existing `SCIENTIFIC_1_3` request contract still rejects levels above L03 and retains its original scientific implementation/version. Existing L01–L03 reports and frontend selections are not migrated or overwritten.
- Source collection for `SCIENTIFIC_1_6` retains the existing original NCT / publication/capture chronology and optional original protocol/SAP evidence; historical requests still require the verified review-cycle date linkage.
- Each new level reports source observations, missing/not-yet-expected evidence, owner-not-reviewed status and `ABSTAIN` with null approval probability. There are **no validated clinical score percentages**.
- New tests: `new-platform/backend/tests/test_scientific_levels_four_to_six.py`. These test the opt-in contract, separate evidence domains, no invented forecast, historical isolation, 123 compatibility and immutable persistence.
- **Not yet connected to the FOCUS/PAST/POOL/ASSESSMENTS display**, no bulk 456 evidence backfill, no score publication or approval forecasts. No production deployment authorized.
- **Engineering verification pending** after this code change; previous local backend/frontend passes predate the new module and cannot be cited as its validation.

## Owner dashboard integration: opt-in research L04–L06 (development branch)

- A new client workspace is mounted in **FOCUS**, **PAST**, **POOL** and **ASSESSMENTS**. FOCUS exact-NCT rows also link to their trial in ASSESSMENTS. PAST event rows without a verified exact NCT are **not** automatically linked to a trial; the owner must choose one.
- The panel supports individually selected Level 4/5/6 execution, \`CURRENT_EVIDENCE\` or \`BLIND_HISTORICAL\` with a past cutoff, and bounded exact-NCT saved-history inspection. Each displayed report must be \`SCIENTIFIC_1_6\`, one of Levels 4–6, NCT-matched, database-hash-verified, \`NOT_VALIDATED\` and \`ABSTAIN\`. Other records are withheld from this view, not silently relabeled.
- The existing Levels 1–3 workbench, source snapshot, saved history, scores and original \`SCIENTIFIC_1_3\` request contract are not changed.
- The Next.js owner API uses only **dedicated server-side environment variables** \`PDUFA_LEVEL456_API_BASE_URL\` (HTTPS URL) and \`PDUFA_LEVEL456_INTERNAL_API_KEY\` for the new contract. It **never falls back** to \`PDUFA_LEVEL123_*\` or \`PDUFA_API_*\` when Level 456 credentials are absent. Avoid configuring these against production; use an isolated backend with the matching SCIENTIFIC_1_6 code and isolated persistence.
- Read-only GET requests explicitly select \`contract=SCIENTIFIC_1_6\` to reach the same isolated service as POST and poll requests. Existing FOCUS and PAST summary GET calls are unchanged.
- Client-side reports show evidence provenance, checks, risks, recommendations, original citations and multiple immutable saved versions. Missing evidence or uncertain FDA application details remain unknown. No numeric clinical score, directional FDA call or FDA approval percentage is published.
- **This development-branch integration is not live.** No isolated 456 service or credentials have been configured by these changes, and no data has been backfilled. It cannot be declared end-to-end functional until the isolated backend is configured and exact-NCT request, persistence, history, security, historical isolation and fresh frontend tests pass.
- New frontend tests: \`new-platform/frontend/tests/scientific-456-workspace.test.cjs\`. Run \`npm.cmd test\`, \`npm.cmd run typecheck\` and \`npm.cmd run build\` from \`new-platform/frontend\`, plus complete backend tests and retirement audit before any owner deployment decision.
