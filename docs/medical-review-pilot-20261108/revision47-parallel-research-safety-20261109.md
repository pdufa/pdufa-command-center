# MAIN R47 — two independent research jobs configured to run in parallel

Date: 2026-11-09. Scope: draft PR #965. **This is an implementation of concurrent background evidence research, not a claim that an accurate predictor has been trained.**

## Track A — current 29 FOCUS NCTs

Nightly/manual current public primary endpoint registry, posted adverse-event terms, and protocol/SAP document-index retrieval for all **29 exact NCTs** linked to **23 provisional application groups**. Source bytes retained in immutable per-run GitHub Actions artifacts with SHA-256 receipt checks. A generated per-NCT evidence-readiness table lists missing original SAP lock, regulatory review-cycle verification, and missing registry source areas. It does **not** silently treat missing current registry postings as absent publications.

## Track B — historical FDA original-publication case research

Separately fetches fresh FDA Drugs@FDA published approved-product and FDA published CRL records; constructs research-only candidate union, hashes the original source snapshots, checks its case-selection bias and the independent outcome-blind replay protocol. The current published FDA sources are not a consecutive population of all filing cycles, and historical predictions are **not** allowed until original trial readout public-version clock, complete NDA/BLA cohort, independent review-cycle outcomes, and sealed prediction-before-outcome barriers are documented. Currently 0 independent historical backtests and no numerical accuracy. This work must not import retired scoring or select winners-only history.

## Parallel execution, schedule status and safeguards

- One GitHub Actions workflow `.github/workflows/main-r47-parallel-focus-historical-research.yml` declares **two sibling jobs without `needs` edges**. Each branch works from independent source inputs, source archives, validation tests and artifacts, so one job's evidence gaps cannot block another job.
- On this draft feature branch, both jobs trigger automatically on the R47 code's push, allowing **actual concurrent execution and logs to be verified now**.
- The workflow also declares a daily `10:28 UTC` schedule. **GitHub scheduled workflows execute only from the repository default branch.** Therefore this daily schedule **is not yet operational while R47 remains on the draft feature branch**. It will not become live until separately reviewed and merged to main. This is deliberate to avoid an unapproved production change.
- Schedule triggers on main do not modify production data: `contents:read`, no rating writes or API mutation. Dataset membership hash-locked to FOCUS 29 / 23.
- Jobs do not promote a clinical grade, draw an independent FDA approval/CRL conclusion, claim measured 100% accuracy, or use the retired RAAS/TOP/BOTTOM/GEM/P3 workspace systems. Both publish explicit source/evidence gaps.
- Completion is measured by **two successful independent execution receipts**, not one green scheduler event. Future real backtesting requires an adjudicated historical cohort and holdout calibration stage.

## Follow-up gates

Build consecutive independent NDA/BLA filing cohort with pending/withdrawn cases, original Phase 3 public snapshot version proof, locked blinded predictions, independent action labels and out-of-time calibration. Qualify clinical evidence, safety populations, and nonpublic regulatory/CMC unknowns for the 23 current application groups. Until then official FDA outcome/delay predictions remain ABSTAIN.
