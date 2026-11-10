# MAIN R59 — exact-29-trial/23-application phase-first scientific review queues

**Date:** 2026-11-09, PST. **Branch:** `feature/medical-stage4-verified-method-matrix-20261108`, existing **draft PR #965**. This is research only, not production. Historical Track B remains independent and unmodified.

## Executed and source-verified installation increment

- **[Full R59 source/guard execution #42708088579](https://github.com/pdufa/pdufa-command-center/actions/runs/42708088579): SUCCESS**, on exact commit `98c44af0cdbe4022da166d49efdd476d14a2c4e3`. Source-integrity regression including adversarial original hash mutation, permanent retirement policy, original archive restoration and write-once output generation all passed.
- **[Immutable archived outputs #13715690190](https://github.com/pdufa/pdufa-command-center/actions/runs/42708088579/artifacts/13715690190)**, retained through **2027-02-07T22:02:12Z**:
  - `FOCUS_29_TRIAL_23_APPLICATION_REVIEW_QUEUE_R59.json`: 29 unique trial source task records and 23 provisional application case queues with per-NCT evidence URLs, original registry SHA, linked PDF SHA, current posted-result and AE-arm availability, phase-first tasks and all remaining independent review blockers.
  - `FOCUS_REVIEW_QUEUE_R59.md`: human-readable application table grouped by ticker/application cycle and current-source counts.
- Original R55 source [archived 29/23 evidence #13710081166](https://github.com/pdufa/pdufa-command-center/actions/runs/42696796318/artifacts/13710081166), **plus separately generated R46 registry index** from the same cryptographically pinned original public research bundle, were both checked. Invalid/mismatched current source SHA and NCT/application relationship fail closed. Source packet was not regenerated from uncontrolled input.
- Canonical unique research counts preserved: **29 unique NCT trials**, **23 provisional application groups**, **12** current registry records with posted primary tables, **12** with current posted safety-arm records, **23** currently attached original protocol/SAP PDF documents. Some trials participate in multiple applications, but the trial-source ledger is not double counted.
- No invention of unavailable clinical evidence. When original current ClinicalTrials.gov source lacks current result tables, attached PDFs or AE-arm results, the resulting task is **recover alternate original sponsor/journal/regulator evidence**, not assign failure or probability. Page leads are source discovery only; they do not certify original pre-unblinding SAP agreement.
- Original reported application stage is explicitly **unverified**, and an `APPROVED_ALREADY` label must be independently checked as an observed action, never treated as a future forecast.

## Engineering implementation

- [Queue builder](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/new-platform/backend/scripts/build_focus_scientific_review_queue_r59.py)
- [Adversarial source/identity tests](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/new-platform/backend/tests/test_focus_scientific_review_queue_r59.py)
- [Manual-or-feature-push, read-only original-archive workflow](https://github.com/pdufa/pdufa-command-center/blob/feature/medical-stage4-verified-method-matrix-20261108/.github/workflows/main-r59-focus-review-queue.yml)

All research outputs remain in **GitHub Actions artifacts**, not in production, an application-review ledger, or live UI. The branch remains draft/unmerged, and no production deployment was authorized. This does **not** claim 29 FDA forecasts have been released.

**Release invariants:** `signedIndependentClinicalReviews=0`; `validatedFDAApplicationPredictions=0/23`; numerical probability `null`; historical accuracy `null`; all future FDA approval/CRL outcomes and review timing `ABSTAIN`. RAAS, retired P3/TOP/BOTTOM/GEM workspaces, production source/roster, and historical Track B remain untouched.

## Remaining next tasks

1. For the 12 current posted-result NCT records, assign qualified independent statistical and safety review with exact Phase 3 original protocol/SAP lock, missing-data, multiplicity, estimand, adverse-event denominators and source-date judgments. Savara R56–R58 has *research arithmetic and discrepancies*, no qualified clinical acceptance.
2. For the 17 trials without currently posted registry results sections, locate original sponsor and journal Phase 3 publications/CSR/regulatory sources where available; avoid reading absence of registry data as trial failure.
3. Independently verify current original FDA action/review-cycle identity and date for all 23 provisional applications. Explicitly differentiate prior action from future forecast.
4. Integrate authenticated, read-only R59 output into the preview scientific review queue only after stable source-snapshot contract validation; do not create a shadow forecast endpoint or modify FOCUS/POOL membership.
5. Run signed expert source adjudication, sealed out-of-sample historical validation, and calibration before releasing probabilities or prospective accuracy. No predicted 100% success.
