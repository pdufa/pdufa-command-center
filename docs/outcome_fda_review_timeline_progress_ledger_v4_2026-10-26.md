# OUTCOME FDA historical review-timeline progress ledger v4 — 2026-10-26

**Research-only status; supersedes v3 counts, not original immutable FDA audit snapshots.** Selected sample coverage is not the FDA universe denominator, and **no approval probability or model fitness claim is authorized**.

## Audited selected-sample progress

| Measure | Completed | Selected denominator | Remaining |
|---|---:|---:|---:|
| Priority FDA source-record identity documentation | 15 | 17 source records | 2 (DBV and Chiesi) |
| Selected FDA action endpoints entered | 20 | 20 selected | Whole-universe denominator unknown |
| Distinct BLA identifiers in selected action sample | 10 | 10 selected | Whole-universe denominator unknown |
| Source-backed receipt-to-action timelines | **17** | **20 selected action endpoints** | **3** |
| Sampled BLA identifiers with structured timelines | **8** | **10 selected BLA identifiers** | **2** |
| Independently certified complete priority review cycles | **0** | 17 priority source records | 17 |
| Model-eligible priority source records | **0** | 17 priority source records | 17 |

This revision adds the **January 31, 2020 → September 30, 2020** Mesoblast BLA 125706 original submission-to-CRL timeline. FDA official December 2024 clinical review https://www.fda.gov/media/184952/download, executive summary PDF page 8 and review chronology PDF page 14, independently document both dates. The original signed **September 30, 2020** CRL itself was **not** retrieved. The research fixture now correctly points to the FDA retrospective clinical review and classifies `source_document_role=fda_regulatory_history_summary`, not a signed FDA action letter. The FDA 2024 SBRA https://www.fda.gov/media/185192/download corroborates original receipt, while the 2023 original signed FDA CRL https://download.open.fda.gov/crl/CRL_BLA125706_20230801.pdf refers to the 2020 CRL. The FDA SBRA cover **127506** versus FDA other sources **125706** remains flagged, with **125706** used as verified application identity for this record.

**This does not mark the original CRL signed letter verified, and retrospective 2024 evidence is ineligible as a 2020 prediction input.** The source-created-after-action and provenance flags are explicit in the research-only timeline export.

## Exactly three unresolved receipt-boundary cases

The machine-readable `outcome_fda_receipt_boundary_gap_report.py` calculates missing boundaries from the difference between selected final-action keys and validated timeline keys, rather than listing fabricated complete review cycles:

| BLA | FDA final action | Missing precise review start | Corroboration level |
|---|---|---|---|
| 125745 Atara | 2025-01-15 CRL | Original BLA received date | Sponsor says submitted May 2024; FDA accepted July 2024 |
| 125745 Pierre Fabre | 2026-01-09 CRL | Complete-response resubmission received date | Sponsor says FDA accepted July 2025; signed FDA CRL redacts exact amendment date |
| 125840 REGENXBIO | 2026-02-07 CRL | Original BLA received date | Sponsor says FDA accepted in May 2025 |

FDA original CRLs:
- https://download.open.fda.gov/crl/CRL_BLA125745_20250115.pdf
- https://download.open.fda.gov/crl/CRL_BLA125745_20260109.pdf
- https://download.open.fda.gov/crl/CRL_BLA125840_20260207.pdf

Sponsor/SEC corroboration:
- https://www.sec.gov/Archives/edgar/data/1604464/000095017025072040/atra-20250331.htm
- https://www.sec.gov/Archives/edgar/data/1604464/000119312525276219/atra-20250930.htm
- https://regenxbio.gcs-web.com/news-releases/news-release-details/regenxbio-announces-regulatory-update-rgx-121-bla-mps-ii/

**No precise receipt dates are inferred from sponsor month-only reports, PDUFA arithmetic, or redacted FDA correspondence.** These three rows retain `exact_submission_received_date=null`, `receipt_date_verified=false`, `review_cycle_independently_certified=false`, and `model_eligible=false`. A dated FDA original/complete-response filing or submission acceptance letter, or an unredacted FDA primary regulatory history, is required to advance exact date boundaries.

## Reliability / evidence changes

1. The research action fixture for the Mesoblast **2020 CRL** previously pointed to a purported FDA PDF not independently retrievable in that pass; it now points to the available, inspected **FDA clinical review** with the correct document role.
2. The FDA action JSON and review-timeline JSON exports pass the evidence document role and original-action verification gaps forward to consumers; no silently promoted signed-letter provenance.
3. The FDA original action-receipt status for the LANTIDRA **2021 CRL** remains **FDA regulatory-summary only**; the original signed action letter still has not been directly retrieved.
4. Previously identified ALYGLO and FAYUVI PDUFA source conflicts, Replimune review recommendation versus signed action, and Mesoblast 125706/127506 typo remain preserved in research exports. No original source audit index was edited.
5. As-of evidence publication timestamps, full amendments/clock history, unbiased application universe, and historical sampling/selection bias are not independently certified.

## Executable evidence and tests

Code:
- `outcome_fda_research_action_fixtures.py`
- `outcome_fda_review_timeline_evidence.py`
- `outcome_fda_review_timeline_export.py`
- `outcome_fda_receipt_boundary_gap_report.py`

Latest verified GitHub Actions run: **40378786561** on commit **61476d413241fcee112a286878eb927c19dbc466**, successful:
- Historical/backtest safety **74 passed**
- FDA action/event/export/timeline/gap-report checks **64 passed**
- Immutable FDA published-audit non-eligibility check **passed**.

**Fail-closed remains:** `independently_certified_review_cycles=0`, `model_eligible_records=0`, `complete_application_denominator_verified=false`, `prediction_probability=null`.

**Next:** Obtain precise FDA receipt dates for Atara original/re-review and REGENXBIO; separately certify complete review-cycle boundaries across the full approved and unapproved BLA application universe rather than selected CRL publications.
