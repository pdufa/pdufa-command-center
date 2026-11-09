# MAIN R47 — two independent research jobs configured to run in parallel

Date: 2026-11-09. Scope: draft PR #965. **This is an implementation of concurrent background evidence research, not a claim that an accurate predictor has been trained.**

## Track A — current 29 FOCUS NCTs

Nightly/manual current public primary endpoint registry, posted adverse-event terms, and protocol/SAP document-index retrieval for all **29 exact NCTs** linked to **23 provisional application groups**. Source bytes retained in immutable per-run GitHub Actions artifacts with SHA-256 receipt checks. A generated per-NCT evidence-readiness table lists missing original SAP lock, regulatory review-cycle verification, and missing registry source areas. It does **not** silently treat missing current registry postings as absent publications.

## Track B — historical FDA original-publication case research

Separately fetches fresh FDA Drugs@FDA published approved-product and FDA published CRL records; constructs research-only candidate union, hashes the original source snapshots, checks its case-selection bias and the independent outcome-blind replay protocol. The current published FDA sources are not a consecutive population of all filing cycles, and historical predictions are **not** allowed until original trial readout public-version clock, complete NDA/BLA cohort, independent review-cycle outcomes, and sealed prediction-before-outcome barriers are documented. Currently 0 independent historical backtests and no numerical accuracy. This work must not import retired scoring or select winners-only history.

## Parallel execution, schedule status and safeguards

- Two **separate** GitHub Actions workflows, `.github/workflows/main-r47-parallel-focus-historical-research.yml` (Track A) and `.github/workflows/main-r47-historical-source-track-b.yml` (Track B), each declare their own job, data inputs, artifacts and concurrency group. Neither waits for the other. A failure in either leaves the other independently runnable and auditable.
- On this draft feature branch, each workflow triggers on the corresponding R47 code/definition push, allowing **actual independent execution** and logs to be verified now. GitHub runners may queue independently, so identical wall-clock start seconds are not guaranteed. Both scheduled triggers use **the same 10:28 UTC cron** after approval.
- The workflow also declares a daily `10:28 UTC` schedule. **GitHub scheduled workflows execute only from the repository default branch.** Therefore this daily schedule **is not yet operational while R47 remains on the draft feature branch**. It will not become live until separately reviewed and merged to main. This is deliberate to avoid an unapproved production change.
- Schedule triggers on main do not modify production data: `contents:read`, no rating writes or API mutation. Dataset membership hash-locked to FOCUS 29 / 23.
- Jobs do not promote a clinical grade, draw an independent FDA approval/CRL conclusion, claim measured 100% accuracy, or use the retired RAAS/TOP/BOTTOM/GEM/P3 workspace systems. Both publish explicit source/evidence gaps.
- Completion is measured by **two successful independent execution receipts**, not one green scheduler event. Future real backtesting requires an adjudicated historical cohort and holdout calibration stage.

## Follow-up gates

Build consecutive independent NDA/BLA filing cohort with pending/withdrawn cases, original Phase 3 public snapshot version proof, locked blinded predictions, independent action labels and out-of-time calibration. Qualify clinical evidence, safety populations, and nonpublic regulatory/CMC unknowns for the 23 current application groups. Until then official FDA outcome/delay predictions remain ABSTAIN.

## Verified first independent execution receipts

- **Track A — FOCUS 29/23**, [GitHub run 42672583926](https://github.com/pdufa/pdufa-command-center/actions/runs/42672583926): SUCCESS, **33 targeted regression tests PASS** plus permanent retirement audit, registry source records 29/29, primary result tables in 12 trial records, SAP metadata attachments in 12, 29/29 evidence-readiness gap rows, **0 validated application predictions**. Immutable per-run raw original source artifact [13698602767](https://github.com/pdufa/pdufa-command-center/actions/runs/42672583926/artifacts/13698602767), expires 2027-02-07.
- **Track B — original FDA historical source candidates**, [GitHub run 42672946999](https://github.com/pdufa/pdufa-command-center/actions/runs/42672946999): SUCCESS, **39 targeted regression tests PASS** plus permanent retirement audit. Fresh source union of **412** source-action candidates from actual 2026-11-09 FDA published-source captures. Quarantined selected published product approvals and selected published CRLs are **not** a complete original NDA/BLA filing/cycle denominator. **0 independent adjudicated historical backtests, calibrated accuracy unavailable**. Read-only source artifact [13699132927](https://github.com/pdufa/pdufa-command-center/actions/runs/42672946999/artifacts/13699132927), expires 2027-02-07.
- Early draft test runs failed due an original-source filename mismatch and an invalid/unstable historical job launch configuration. Track A's filename was corrected and **the historical research track was separated into a distinct valid standalone workflow**. The verified run IDs above are the subsequent successful independent tests. Do not equate those earlier failures with a completed paired run.
- The daily **scheduled trigger is NOT active on the feature branch** because GitHub cron schedules fire from the default branch. Draft PR #965 is still unmerged. No production write or independent prediction release was performed.

### Operational definition of next milestones

1. **Parallel source research operational in development:** YES; each track has an independent successful GitHub execution.
2. **Automatic scheduled daily research operational in production:** NO; requires explicit approved merge of these two read-only workflows to default branch.
3. **Full actual historical FDA prediction, outcome comparison, accuracy calibration and automatic improvement:** NO; 412 are merely selected FDA source leads and never validated cases. No basis for any claimed 100% FDA prediction accuracy.
