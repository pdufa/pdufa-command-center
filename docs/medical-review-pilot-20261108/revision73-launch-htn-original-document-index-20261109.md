# MAIN Revision 73 — Launch-HTN seven public protocol / SAP research leads

**As of 2026-11-09 Pacific** · **stage-only original publication source discovery**. This is not scientific method signoff, lock-date authentication, FDA regulatory prediction, validated forecast, or a production release.

## Original exact study and source index

- Trial: **Launch-HTN / MLYS / NCT06153693** (no FOCUS roster modification)
- Original main public article: [JAMA online June 30, 2025](https://jamanetwork.com/journals/jama/fullarticle/2835763); [PMC original indexed article](https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/); PMID **40587141**, DOI **10.1001/jama.2025.9413**
- The public JAMA/PMC article's supplements listing explicitly identifies **seven** original linked PDFs: three protocol versions, three SAP documents, and one eMethods/multiplicity/sensitivity supplement.
- This R73 work does **not** claim those PDF files have been downloaded or hashed by the project; publisher index labels do **not** authenticate document content, internal signature dates, first-public availability, original database-lock sequence or pre-unblinding prespecification.

| Supplement | Published file description | Role | Exact public file link |
|---|---|---|---|
| 1 | eMethods, multiplicity and sensitivity tables | METHODS_SUPPLEMENT | [Indexed PDF](https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s001.pdf) |
| 2 | Protocol v3.1 | PROTOCOL_VERSION | [Indexed PDF](https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s002.pdf) |
| 3 | Protocol v3.0 | PROTOCOL_VERSION | [Indexed PDF](https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s003.pdf) |
| 4 | Protocol v2.1 | PROTOCOL_VERSION | [Indexed PDF](https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s004.pdf) |
| 5 | SAP windowing addendum 1 | SAP_ADDENDUM | [Indexed PDF](https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s005.pdf) |
| 6 | SAP amendment 2 | SAP_AMENDMENT | [Indexed PDF](https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s006.pdf) |
| 7 | SAP multiple-imputation addendum 1 | SAP_ADDENDUM | [Indexed PDF](https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/jama-e259413-s007.pdf) |

## Implemented in draft PR #965

- New source-only manifest: `new-platform/frontend/data/focus-r73-launch-htn-original-document-index.json`, containing seven exact links, source dates, evidence-access limits and six unresolved gates.
- Independent Python fail-closed verifier and adversarial tests: `new-platform/backend/scripts/verify_focus_r73_launch_htn_document_index.py`, `new-platform/backend/tests/test_r73_launch_htn_original_document_index.py`.
- Frontend fail-closed crosswalk, tests and responsive research-only panel: `new-platform/frontend/lib/focus-r73-launch-htn-document-index.ts`, `new-platform/frontend/tests/focus-r73-launch-htn-document-index.test.cjs`, `new-platform/frontend/app/predictions/evidence-gaps/LaunchHtnOriginalDocumentsR73.tsx`; displayed only for `NCT06153693` inside the existing five-pivotal-source research queue.
- New isolated CI workflow: `.github/workflows/main-r73-launch-htn-protocol-sap-source-index.yml`. Keeps 29 original NCT and 23 provisional application roster SHA locks and permanent retired-score audit; no production writes.
- Existing R71 Chromium acceptance now also tests all seven link addresses, UI no-grade status and publication-index readback on desktop and 390 px mobile.

## Scientific gates still outstanding

1. Rights-compatible retrieval and archive of the seven actual PDF bytes, exact source URL and SHA-256 proofs.
2. Read and compare internal signed versions/protocol amendments, including 2.1, 3.0, 3.1 and the three SAP documents.
3. Establish independent pre-unblinding signing, trial completion, database lock, actual access, publication and chronology; **publication on June 30, 2025 is not proof the SAP was signed or publicly available before the 2024 study endpoints**.
4. Independently adjudicate Week-6 50 mg randomized estimand, primary H1 and secondary H2–H7 multiplicity graph and region effects.
5. Reconcile 1,000-imputation MAR/MNAR sensitivity, treatment-policy estimand and potassium/sodium/eGFR event rates using exact exposure groups.
6. Obtain independent qualified clinical and regulatory review with immutable source/counterevidence signatures; without such evidence there is no validated FDA application or timing prediction.

**As-built honest scientific status:** source index 7/7 identified; **original PDF byte-authentication 0/7**, signed pre-unblinding SAP chronology 0, signed scientific reviews 0, calibrated FDA forecasts 0/23, FDA outcome **ABSTAIN**, future review timing **UNKNOWN**, grade unavailable. All 29 FOCUS NCTs and 23 application groups preserved. No RAAS/GEM/P3 separate workspace or scores reactivated.

## Release criteria

Do not promote the research panel to an independently graded scientific review, approval/CRL forecast or historical blind backtest until the original PDFs and their chronology are actually checked. Vercel preview readiness and CI PASS are *engineering* checks, not scientific acceptance. PR #965 remains draft until authorized clinical and deployment acceptance.
