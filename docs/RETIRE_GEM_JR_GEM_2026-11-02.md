# PDUFA active-tier retirement — 2026-11-02

## Governing instruction
The user explicitly directed complete removal of GEM JR and GEM as active system tiers. This supersedes older requirements to maintain them as active lists, original FS/FA preset associations, transitions, score-gates, scans or PREDICTION prerequisites. Do not activate any new 15-minute intelligence monitor: that remains conceptual only.

## New operating sequence
Master POOL → evidence-eligible PIPELINE → SCIENCE → OUTCOME → MAIN → PASS / CRL / EXTENSION / ABSTAIN.
The Phase 3 posted-results collector, FDA special-designation checks and existing 8 PM Pacific scan are separate research processes, not GEM tiers. WT and RAAS remain distinct, provided their logic is independently justified and does not rely on GEM stage membership or score thresholds.

## Implemented in this review branch
- SCANS published-report endpoint no longer fetches or returns archived GEM scan or membership artifacts.
- NEW FROM SCAN distinguishes genuine Pipeline additions from Phase 3 results, with strict same-execution and identity checks and no GEM stage/member fields.
- Backend checklist and isolated research-stage endpoints reject retired stage requests.
- Live workspace source payload, ID numbering, versioned deltas and summary are Pipeline-only, without active retired stage membership objects.
- Readiness and risk-review adapters accept Pipeline stages only; missing Pipeline evidence remains unscored.
- Regression tests updated for the retired stage contract.

## Additional work required before declaring full retirement
- Remove the still-present tier scoring models, obsolete components and original Streamlit GEM menus from executable code without deleting shared trial records.
- Review legacy scanner scripts for any active workflow or manual dispatch entry points; ensure no stage-specific notifications or scan reporting remains.
- Replace stale GEM JR/GEM segments and requirement text in installation-audit manifest using a dated ID migration map, protecting historical accepted task records.
- Update the current Master Directive and open Benchmark 1/flowchart implementation issues to reflect the new Pipeline-only design.
- Run full frontend/backend/worker CI, source scans, staging checks, deployed route acceptance and actual production verification.
- Archive old tier configurations/ledger data as historical evidence; do not erase exact trial identities, source citations, existing FDA decision records or scientific evidence.

## Honesty and acceptance
A branch or draft PR is not deployed, and removing references in a few modules does not prove system-wide retirement. The end state is accepted only when active UI, API, workflow, scheduled triggers, scoring, prediction, tests and production checks contain no operational GEM JR or GEM dependency. Existing data and models must not silently gain alternative unvalidated scores.
