# OUTCOME readiness panel: frontend integration boundary (2026-10-26)

## Verified implementation

The repository's `outcome_fda_readiness_panel.py` emits a read-only JSON
presentation contract. CI runs the CLI, parses its JSON, and verifies that
prediction remains disabled. **This does not mean the live site serves it.**

The existing frontend already has
`new-platform/frontend/app/HopReadinessPanel.tsx` which requests
`/api/hop/readiness` and expects a `HopSourceReadiness` shape. The new
research-only OUTCOME panel has **a different schema and denominator**:
17 of 20 **selected action timelines**, not a complete historical FDA cohort.

## Required integration steps (not yet performed)

1. Implement a dedicated authenticated backend route for
   `outcome-readiness-panel-v1` or explicitly version the existing route.
   Do not replace the current `HopSourceReadiness` response with the new
   incompatible JSON structure.
2. Generate the payload from a version-pinned, reviewed source dataset;
   do not hard-code 85% in the frontend or treat GitHub's default branch
   as the live database.
3. Validate `schema_version`, `display_role=research_status_only`,
   `primary.prediction_ready=false`, null prediction probability,
   and the denominator at the route boundary. Fail closed if missing.
4. Render primary evidence coverage and prediction NOT READY in the HOP
   readiness area; put the five blockers inside a native `<details>`
   control. Label the 20 actions as a **selected sample**.
5. Add route and frontend tests, verify auth/cache behavior and mobile
   rendering, deploy through the existing release process, then confirm
   the actual public/private site response.

## Invariants

- Sponsor submission dates are **not** independently verified FDA receipts.
- Retrospective FDA outcome labels are not historical prediction features.
- `85%` is documentation coverage (17/20), **not** model accuracy.
- A zero model-eligible count means **no prediction probability**.
- Existing GEM JR / GEM FS and FA associations must not change.
- Read-only panel integration must not start scans or alter trade decisions.
