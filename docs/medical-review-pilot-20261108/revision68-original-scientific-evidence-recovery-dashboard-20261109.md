# MAIN Revision 68 — original clinical evidence recovery and independent source availability

**Installed and verified November 9, 2026 PST.** Existing draft development-only [PR #965](https://github.com/pdufa/pdufa-command-center/pull/965) on `feature/medical-stage4-verified-method-matrix-20261108`. No production merge, forecast release, Phase 3 human adjudication, or Track B access.

## Confirmed installation and links

- [**R68 fully successful source-integrity, frontend and Chromium workflow #42725228063**](https://github.com/pdufa/pdufa-command-center/actions/runs/42725228063), exact code commit `210f8ded2c6c0a1bea11e4ce50cc16466f813d5e`: three independent original research audits (R60, R63, R66) passed, **4 focused Node tests passed**, zero failed; Next.js TypeScript checks and optimized build passed; real local Chromium interaction acceptance passed on desktop **1365 × 850** and iPhone-sized emulated **390 × 844**.
- [Browser verification artifact #13721897853](https://github.com/pdufa/pdufa-command-center/actions/runs/42725228063/artifacts/13721897853), retained to **December 10, 2026**, including local viewport screenshots and `R68_BROWSER_RESULTS.json`. Browser emulator checks do **not** mean signed-in physical iPhone Safari or real clinical reviewer acceptance.
- [**Exact-commit READY development Vercel preview**](https://pdufa-new-dashboard-3453avmtt-pdufa.vercel.app/predictions/evidence-gaps), independently fetched HTTP **200** with all **29** unique original NCTs present, the new source recovery coverage counts, **UNASSESSED**, **ABSTAIN**, and **NOT CALIBRATED**.
- Cross-links on `/predictions` and `/predictions/assessment` now open `/predictions/evidence-gaps`. Every trial links to its original exact-NCT scientific assessment, original source PDF page area, and ClinicalTrials.gov source. Real browser searches, category filters and per-trial expand/collapse worked.
- A first local unit-test run failed for **wording of an allocation N/A exception only**; source contents and review safeguards were unchanged. After correcting the label, dedicated R68 workflow and real browser acceptance fully succeeded at the above exact commit.

## Source availability, not FDA prediction or trial failure

The same previously verified source-retained FOCUS universe is preserved: **29 unique NCT trials** and **23 provisional FDA application cycles**. Shared NCTs are counted once; application memberships are preserved.

| Source availability from retained original research | Trials with source coverage | Trials without that source in retained copy |
| --- | ---: | ---: |
| Current public registry primary outcome table | 12 | 17 |
| Current public registry adverse-event arm table | 12 | 17 |
| Current public protocol/SAP PDF page leads | 12 | 17 |

These three **17-trial counts are separate**: no inference is made that they identify the same exact NCTs. The 22 public PDF files with page leads contributed **466 machine-matched original page locations**; 23 public original protocol/SAP documents were attached to 12 trials in the larger original R63 corpus. Original registry method source coverage is not a full original pre-unblinding SAP or CSR audit.

Across all 29 trials, the R68 source worklist displays:
- a repeated, explicit **independent phase verification** task;
- **dated original signed pre-unblinding protocol/SAP chronology** task;
- posted primary-result **independent multiplicity/estimand review** or recovery from sponsor/journal/CSR/regulatory originals;
- currently posted safety-arm denominator **independent exposure/risk review** or other-original safety recovery;
- original PDF page-lead review or recovery of missing current protocol/SAP documents;
- explicitly unverified **combined Phase 2/3** study design (NCT04871282), and **allocation N/A** (NCT06331299), without scoring them as failed trials.

The list is ordered **only by missing original-source categories**, never by clinical risk, probability of FDA approval, financial importance, trial success or calibrated confidence.

## Genuine scientific and regulatory readiness

- 29 dated source-reported phase records, **0 qualified independent phase reviews**.
- **232 unscored eight-domain reviewer positions**; no source keyword match is an independently completed science assessment.
- **0 signed clinical or statistical reviews**, **0 independently validated future FDA approvals/CRLs or review-delay forecasts**, **0 calibrated historical accuracy measurements**.
- Scientific level displayed: `UNASSESSED_SOURCE_ONLY`; future FDA approvals, CRLs and review timings: `ABSTAIN`; future probability: **withheld**.
- Historical Track B outcome records were **not** accessed, no new clinical reviewer write scope was enabled, and no production, FOCUS, RAAS, or model-training writes occurred.

## Installed development files

- `new-platform/frontend/lib/focus-r68-evidence-recovery.ts`
- `new-platform/frontend/app/predictions/evidence-gaps/page.tsx`
- `new-platform/frontend/app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.tsx`
- `new-platform/frontend/app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.module.css`
- `new-platform/frontend/tests/focus-r68-evidence-recovery.test.cjs`
- `new-platform/frontend/scripts/verify-r68-evidence-recovery-browser.cjs`
- `.github/workflows/main-r68-evidence-recovery-dashboard.yml`
- Navigation integrations in `app/predictions/page.tsx` and `app/predictions/assessment/page.tsx`.

## Next prerequisites

1. Recover study-specific missing original clinical trial data and protocol/SAP source versions without interpreting current ClinicalTrials.gov absence as treatment failure.
2. Obtain properly authorized **independent human phase assessments** with documented scientific reasoning, source chronology, conflicting/favorable/unfavorable evidence and second verification. Current source-only worklist does **not** complete this step.
3. Validate 23 real FDA review-cycle memberships against authoritative original submissions, supplement original efficacy/safety assessments, and run genuinely blinded time-frozen historical prediction validation separately from the future prospective forecast ledger.
4. Require signed audit provenance and true calibration before adding scientific grades, prediction probabilities or claimed FDA approval certainty.

**R68 engineering/UI installation is verified and complete in the development preview.** Stage 4 scientific evidence recovery remains ongoing and is not a finished FDA prediction engine.
