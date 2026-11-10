# MAIN Revision 39 — Independent Phase-3-readout FDA historical backtesting, blinded inputs

**As-of:** November 9, 2026. GitHub issue #980. **No retrospective performance metrics are released** without independent case-level adjudication. Isolated PR #965, no production, legacy RAAS or clinical grade changes.

## Implementation

\`hop_blinded_phase3_backtest.py\` introduces an exact-NDA/BLA, review-cycle, program-family and NCT crosswalk for point-in-time FDA research replays. It has three deliberately segregated operations:

1. **Freeze predecision public evidence only.** Requires a Phase 3 readout public date and a later prediction cutoff; every clinical/source document must have original as-published version proof, a SHA-256 source fingerprint and a first-public date no later than the cutoff. The forecasting packet contains neither the actual FDA result nor later documents. It is hashed and does not claim a clinical grade. A retrospective source retrieved after the decision is admissible only if the original as-published predecision version has independently established provenance; its latest website text is not proof of prior availability.
2. **Record preliminary research predictions.** A separate research call (APPROVAL_LEAN, CRL_LEAN, ABSTAIN) binds to the exact frozen input hash and an honestly dated *retrospective replay timestamp*. It never pretends a replay run in November 2026 was actually performed before a 2024 decision. It cannot have access to the outcome vault while predicting.
3. **Compare to segregated known historical FDA actions.** The evaluator receives action and separate first-publication dates only after the research input is sealed; it refuses an action that precedes the frozen cutoff, prevents a program family appearing in development and holdout at once, and preserves withdrawal, extension and pending outcomes as nonbinary. It can calculate descriptive research call fractions in synthetic tests but **never upgrades these to independent observed prediction accuracy, calibration or training authority** by setting a Boolean flag.

This is code infrastructure, not a verified independence attestation. A legitimate replay still requires a separately verified complete cohort, exact review-cycle and label source, qualified reviewer attestations, original predecision clinical docs, secured separated provenance and a holdout truly untouched during model revision.

## Actual research status at publication

The FDA original-source archive [#42642513960](https://github.com/pdufa/pdufa-command-center/actions/runs/42642513960) has **412 source-selected 2024–25 action leads**; all are quarantined, with zero independently certified eligible cycles. These sources are not the full filing population and cannot be sampled into a supposedly representative set of approved and CRL decisions. As of today:

| Gate | Real-world count |
| --- | ---: |
| Verified consecutive full original NDA/BLA application cohort | 0 |
| Public, frozen, independently verified phase-3 readout cases | 0 |
| Independently confirmed real historic outcomes in a complete cohort | 0 |
| Historically frozen research predictions scored against valid FDA decisions | 0 |
| Independent chronological holdout evaluations | 0 |
| Measured historical accuracy, Brier score or calibrated probability | Unavailable |

The new \`reports/deep-medical-intelligence/backtest-readiness-r39.json\` is versioned status, not results from 412 backtests. It must be revised only when new independent evidence and actual evaluation receipts support more coverage.

## Next ordered work

Begin with actual permitted predecision source captures for selected original-review-cycle leads, identify a complete consecutive original-filing year population rather than only approved products, and verify on-time FDA action and first-publication timestamps independently. Establish outcome-vault custody and program-disjoint temporal holdout before estimating accuracy. Compare research calls to actual decisions only after predictions are sealed; record all abstentions in coverage denominators. Review sources and discrepancies before revising methodology. Do not use retired RAAS records or claim 100% predictive accuracy.
