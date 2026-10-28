# PDUFA historical prediction safety integration — 2026-10-28

Combines four independent, already CI-validated research PR changes into a single integration test against current main: #507 (PEAK SCIENCE/OUTCOME/MAIN read-only abstention), #508 (point-in-time label/decision feature chronology), #509 (CSV/JSON exact-cycle evidence intake), #510 (exact cohort roster reconciliation). The source branches all targeted the same baseline commit. There were no code-file overlaps; their one shared historical-safety GitHub workflow was combined to retain all dedicated tests and source triggers.

## Required safety gates

- No FDA historical cycles have yet been independently adjudicated as model eligible; **0 valid independent real historical backtests**.
- No validated PASS/FAIL probability or model predictive accuracy. Do not treat synthetic test success or selected case-study matches as independent predictive evidence.
- The PEAK research register has 40 questions, 27 observational source entries and 10 curated public source leads, but **0/40 independently certified assessments** and **0/20 certified depths**; readiness remains RELUCTANT / ABSTAIN.
- Preserve original Pipeline, GEM JR/GEM/WT FS/FA preset membership, market-cap settings, read-only staging database policies, disabled trading and no new sheet writes or scan schedules.
- Existing case-study historical decisions without exact application/cycle identity, observation chronology, outcome publication and independent verification are research-only and must never enter training.

## Validation

Run full backend/front-end CI and the dedicated OUTCOME historical safety tests on this **combined** branch; the four source branches passing separately does not establish integrated success.

New prediction-ready status requires independently verified original FDA outcomes, dated decision-cycle records, a representative cohort, point-in-time features, blinded out-of-time validation and calibration. Engineering integration alone cannot promote any of those gates.

All four source PRs stay unmerged until combined CI passes. Changes to original draft descriptions or source history are not used as scientific evidence.
