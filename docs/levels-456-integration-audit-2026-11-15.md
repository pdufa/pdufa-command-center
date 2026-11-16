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
