# MAIN continuation after Revision 15 — November 9, 2026

Continues PR #965 (DRAFT) and branch
`feature/medical-stage4-verified-method-matrix-20261108` from
`415debd9e2722a058b5d6b5d6c0a4835e5bdba43`. All prior source receipts,
revision notes and 29 exact FOCUS identities are preserved. The old unfinished
local rollout patch was preserved in `/tmp/pdufa-pending-rollout-before-revision15.patch`
and was not applied over the newer implemented workflow.

## Accepted development work

- Revision 15 baseline: 1,256 backend tests passed, 4 skipped; 138 frontend test
  files passed. Independent-role, phase freshness, roster/source identity,
  supersession and immutable history checks retained.
- Fixed real preactivation reviewer defects: writes now require the fixed
  isolated Render service identity as well as existing flags/storage/migration
  gates; invalid non-ASCII credentials fail with 503/401 rather than 500.
  No reviewer credentials were fabricated and writes were not enabled.
- Added durable research execution, using the existing phase matrix and source
  ledger. Frozen source/phase/catalog context, exact questions, source versions,
  examination findings/limitations, separate optional research recommendations,
  append-only revisions and bounded 1–20-item restartable batches remain separate
  from official grades. Read-only plans support 29 trials; execution is pilot-only.
  Startup and GET routes are separately opt-in and fixed to the isolated service.
  Startup creates no runs or examinations. The feature was not enabled remotely.
- Added a research-only adapter around existing HOP cohort/metric code for
  APPROVAL, CRL and REVIEW_DELAY. Frozen training/feature/forecast/outcome clocks,
  exact application/indication/cycle identities, program/application holdouts and
  explicit delay labels prevent common leakage and mislabeling. Mathematical
  metrics do not certify sources, cohort completeness, calibration uncertainty or
  a model. No real labels, forecasts or probabilities were manufactured.
- Added the dark navy/teal `FINAL FDA PREDICTION | ACCURACY RATING` header,
  retaining three ABSTAIN outcomes, NOT CALIBRATED accuracy and NOT VALIDATED
  certainty. Actual INSTALLATION now includes the live medical observations and
  a locator that opens, focuses and scrolls to the observed current task.
- Added a hosted read-only acceptance job using the existing dashboard test
  secret and normal session authentication. It never forges sessions or submits
  clinical writes. When deployment is requested, acceptance waits for deployment.

## Pilot sources and limits

[Revision 16 original-source packet](medical-review-pilot-20261108/revision16-source-packet/README.md)
contains seven preserved original responses and one blocked jRCT request.
New same-trial HCMS presentations distinguish KCCQ-OSS from pivotal KCCQ-CSS and
show the small paired CMR subset and missingness/multiplicity limitations.
Original FDA obstructive-HCM/SEQUOIA records are excluded as ACACIA approval
proof. All 800 exact method positions are represented: 18 source handoffs,
782 unexamined, nine bounded findings, zero numerical grading recommendations
or clinical grades. A handoff is not a completed independent scientific test.
Final locked CY 6033 SAP, primary appendix, safety-count reconciliation and
qualified independent reviewers remain open.

## Verification

- Final local backend with real temporary PostgreSQL contracts: **1,313 passed,
  3 skipped**, six warnings. New research history guards, idempotent restarts,
  interruption recovery and clinical-ledger separation passed.
- Final frontend: **139 test files passed**, no failures; TypeScript and
  production build passed. Final auth-driver targeted tests: four passed.
- Retirement policy guard and 20 regression tests passed; source packet receipt,
  catalog, all-position coverage and null-grade validation passed.
- Chromium at 390 and 1360 pixels: header visible, no horizontal PREDICTIONS
  overflow or page errors; current-task locator focused the observed task;
  downloaded CSVs each parsed into **800 unique exact-NCT method records**,
  preserving all unreviewed grades as blank. This is isolated fixture testing,
  not live clinical review or end-user device certification.

## Actual deployment dependency discovered

Initial hosted acceptance run
[42537690479](https://github.com/pdufa/pdufa-command-center/actions/runs/42537690479)
passed backend/frontend/retirement checks and successfully performed normal
login, then failed `AUTHENTICATED_MATRIX_UNAVAILABLE`. Render request receipts at
2026-11-09 00:00:27 UTC show matrix GET **404** and phase-matrix GET **401**.
This is a real compatibility/authentication dependency, not a clinical failure.

Before rollout, isolated Render deploy `dep-dbog96e417fc7385rsc0` was LIVE at
`925970ff2a5f55d550f92b1d5dfaa2471227bbe2`; production was not a target.
Existing startup receipts establish one pilot's **800 source-audit receipts**,
not grades. The compatible draft backend must be deployed and authenticated
acceptance must pass before reporting an operational matrix connection.
The manual job uses the fixed service, exact tested commit and existing
`RENDER_API_KEY` Actions secret, failing closed if unavailable. No service branch,
autorun flags, database URL, IP allowlist or secret is changed by the rollout.

## Outstanding task balances

| Item | Actual accepted evidence | Remaining |
| --- | --- | --- |
| Trial source packets | 29 captured at retained checkpoint | New evidence retrieval/reconciliation remains source-specific |
| Scientific source audits | Pilot 800 source-classification receipts | Remaining 28 trial audit runs; no claim of independent grading |
| Phase verifications | 0 independently recorded at retained checkpoint | 29 current-phase reviews; prior phases separately unresolved |
| Scientific assessments | 0 independently completed | 1,160 potential groups |
| Individual method grades | 0 independent grade events | 23,200 potential positions, subject to applicability |
| FDA predictions | 0 validated; 29 ABSTAIN | Real adjudicated cohort, frozen model and outcome-specific validation |
| Accuracy validation | NOT CALIBRATED | Independent temporal holdout and calibration/reliability validation |

Current engineering action: `installation.authenticated-medical-connection` —
roll out the compatible isolated backend, verify health/PostgreSQL/readback,
then repeat normal-session acceptance. Current scientific action remains
`medical.phase-verification`, followed by the pilot's phase-prioritized evidence
examinations. Do not enable reviewer writes, expand clinical grading or promote
production based on passing engineering tests.
