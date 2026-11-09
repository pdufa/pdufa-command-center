# MAIN Revision 50 — Original FDA PDUFA review-cycle source evidence

Date: 2026-11-09. Stage 4 draft PR #965, independent historical FDA science and backtesting Track B. All data source-side, read-only, no forecast release.

## Verified successful original FDA regulator source

Source: FDA's *Prescription Drug User Fee Act FY 2024 Performance Report to Congress*, official [report PDF](https://www.fda.gov/media/188188/download?attachment=), **Appendix A**, published under FDA PDUFA reports. The PDF is **128 pages**, **1,344,653 bytes**, cryptographic SHA-256 `589f432a7bb34237b247c1c39376ca1a3a9722984856f409e79d81fddf8127c4`.

- [Standalone FDA original PDF extraction run #42688406870](https://github.com/pdufa/pdufa-command-center/actions/runs/42688406870) **SUCCESS**; exact original PDF and page layout [artifact 13706326002](https://github.com/pdufa/pdufa-command-center/actions/runs/42688406870/artifacts/13706326002), retention through 2027-02-07.
- [Integrated simultaneous historical Track B run #42689302249](https://github.com/pdufa/pdufa-command-center/actions/runs/42689302249) **SUCCESS**, **94 targeted checks passed**, retired scoring audit passed and append-only workstream history persisted. Fresh FDA source-approved-only PDF and machine-extracted review-cycle actions [artifact 13705922988](https://github.com/pdufa/pdufa-command-center/actions/runs/42689302249/artifacts/13705922988). Independent Track B history [artifact 13705952530](https://github.com/pdufa/pdufa-command-center/actions/runs/42689302249/artifacts/13705952530). Expire 2027-02-07.

**Extracted 186 page-anchored FDA Appendix A review-cycle action rows** from printed Appendix pages A-2 through A-13 (PDF pages 84–95), each with source page and original PDF word coordinates. Code and counts are checked against the exact original PDF SHA-256, and original review-cycle-label column vs action-code column is aligned one row at a time.

| Published action code | Count |
| --- | ---: |
| AP — Approved | **126** |
| CR — Complete Response | **43** |
| TA — Tentative Approval | **17** |
| **Review-cycle action rows** | **186** |

| Printed FDA review cycle ordinal | Count |
| --- | ---: |
| First | 133 |
| Second | 38 |
| Third | 12 |
| Fourth | 3 |

These are **source action rows, not 186 distinct applications, not 186 eligible prediction outcomes**. FDA's Appendix A explicitly includes only NDA/BLA submissions **approved in FY2024** and their earlier review histories. Thus even the 43 CR rows are drawn from applications that subsequently achieved approval during the FY2024 report scope. This is a **strong survivorship/approval-selection bias**. A real prediction evaluation still requires nonapproved, pending, withdrawn, and censored original filing cycles and independent application+NCT identification.

Code: `new-platform/backend/scripts/probe_fda_pdufa_appendix_r50.py` (original PDF capture), `new-platform/backend/scripts/build_fda_fy2024_cycle_events_r50.py` (page-anchored original source-only extraction), `new-platform/backend/tests/test_fda_fy2024_cycle_events_r50.py` (row alignment, immutability, refusal of unverified sources). Integrated in `.github/workflows/main-r47-historical-source-track-b.yml`.

## Parallel source/research safeguards

- The previously verified **412 source-action records** in the selected published FDA API cohort remain **412/412** individually reconciled under R49 with the original FDA archive snapshots. **376 provisional parent source IDs**, **33 repeated parent IDs**, and **15 with mixed published approval/CRL source records** still require exact original review-cycle adjudication. These are a separate source population from FDA FY2024's Appendix A; do **not** join by counts or percentages.
- The independent FOCUS 29 exact NCTs / 23 provisional FDA application dossiers are unchanged. No POOL or FOCUS membership, retired scoring, production data or reviewer grade was changed.
- The exact date, NDA/BLA application number, submission unit, NCT trial source, original Phase 3 result and sealed evidence-available-before-outcome date are **not present** in our extracted PDF cycle rows. All must be independently sourced.
- Original ClinicalTrials.gov *history* browser endpoint pilot: three priority exact FOCUS NCTs (`NCT04544293`, `NCT05126758`, `NCT05208047`) had **0/6** accessible internal archive requests on the standard host and **0/9** on the www host during actual R50 probe runs [#42686793862](https://github.com/pdufa/pdufa-command-center/actions/runs/42686793862) and [#42687105556](https://github.com/pdufa/pdufa-command-center/actions/runs/42687105556). HTTP unavailable from the GitHub collector is **NOT evidence** that original versions never existed, and current-registry endpoints cannot be misrepresented as original pre-readout frozen text. Human-accessible official history tab remains available for manual source adjudication as appropriate.
- Both independent development workflows can execute separately; **daily cron still requires deployment on the main/default branch to become operational**, and draft PR #965 has not been merged. 
- **Zero independently validated FDA predictions, zero complete historical blinded backtests, no measured/proven 100% accuracy, no training authorization.**

## Next scientific research steps

1. Extract FDA Appendix A product/applicant identity with row grouping and independently crosswalk to original NDA/BLA number, submission number and NCT IDs; the current source PDF cycle rows intentionally do not invent any.
2. Construct an independent real original filing cohort, including nonapprovals and pending/withdrawn applications, from original prospective FDA/SEC/sponsor primary sources; published FDA Appendix A and CRL libraries alone are outcome-selected and inadequate as denominators.
3. Retrieve original public Phase 3 data and verify publicly posted predecision protocol/SAP version dates, then freeze evidence and produce a blinded forecast with outcome labels inaccessible to the forecasting stage.
4. Adjudicate later review-cycle regulatory action and only then run independent holdout, error analysis, calibration and proficiency measurement.
