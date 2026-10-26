# OUTCOME FDA review-timeline progress ledger v5 — 2026-10-26

**Research-only progress.** This version updates the v4 evidence chronology but does NOT edit immutable published FDA audit snapshots or authorize model training. Each denominator describes its own population; the **selected** 20-action sample does not establish the historical FDA application universe.

## Progress with explicit denominators

| Measure | Complete | Denominator | Remaining / note |
|---|---:|---:|---|
| Priority FDA source-record application identities documented | 15 | 17 source records | 2 (DBV and Chiesi) |
| Selected FDA final-action records entered | 20 | 20 selected endpoints | True all-FDA universe unknown |
| Selected final actions with FDA-source-supported structured receipt-to-action timeline | 17 | 20 selected endpoints | 3 selected endpoints |
| Sampled BLA identifiers with structured timelines | 8 | 10 selected BLA identifiers | 2 |
| **Previously unresolved sponsor precise submission dates now documented** | **1** | **3** selected open receipt cases | **2** sponsor days still month-only |
| **Exact FDA submission receipt dates independently documented for these three** | **0** | **3** open receipt cases | **3** agency receipt days still unresolved |
| Independently certified complete priority review cycles | **0** | 17 priority source records | 17; source records not unique cycles |
| Model-eligible priority records | **0** | 17 priority source records | 17 |

## Stronger dated filing evidence

| Application and final action | Sponsor submission evidence | Published confirmation | FDA exact received day |
|---|---|---|---|
| BLA 125745 Atara original, CRL **2025-01-15** | **May 2024** submitted, exact day unknown | Atara announced already submitted on **2024-05-20** | Unknown/redacted |
| BLA 125745 Atara / Pierre Fabre resubmission, CRL **2026-01-09** | **2025-07-11** precise sponsor-reported submission; **2025-07-23** sponsor-reported FDA acceptance | Already submitted by Atara **2025-07-14**; exact July 11 date stated by Pierre Fabre **2025-11-03** | Unknown/redacted |
| BLA 125840 REGENXBIO original, CRL **2026-02-07** | **March 2025** submitted, exact day unknown | SEC-filed REGENXBIO statement on **2025-03-13** confirms already submitted | Unknown/redacted |

**Sources:**
- FDA 125745 CRLs: https://download.open.fda.gov/crl/CRL_BLA125745_20250115.pdf and https://download.open.fda.gov/crl/CRL_BLA125745_20260109.pdf . The 2026 signed CRL itself explicitly links back to the 2025 signed CRL for **the same** BL 125745.
- FDA 125840 CRL: https://download.open.fda.gov/crl/CRL_BLA125840_20260207.pdf .
- Atara **May 20, 2024** submission confirmation: https://www.nasdaq.com/press-release/atara-biotherapeutics-submits-tabelecleucel-tab-celr-biologics-license-application .
- Atara **July 14, 2025** resubmission confirmation: https://www.nasdaq.com/press-release/atara-biotherapeutics-provides-regulatory-and-business-updates-tabelecleucel-tab-celr .
- Pierre Fabre **November 3, 2025** primary sponsor PDF, p.1: https://www.pierrefabrepharmaceuticals.com/sites/default/files/press/20251103_PR_Final_BLA_Transfer_Announcement_0.pdf . The PDF specifically states **July 11, 2025 submission** and **July 23 FDA acceptance**, *as reported by sponsor*, not as independently certified FDA receipt timestamps.
- REGENXBIO **March 13, 2025** SEC-filed announcement: https://www.sec.gov/Archives/edgar/data/1590877/000095017025038711/rgnx-ex99_1.htm . Confirms **March** completion/submission, **not** May. May 13 sponsor announcement https://ir.regenxbio.com/news-releases/news-release-details/regenxbio-announces-fda-acceptance-and-priority-review-bla-rgx confirms **acceptance** announced in May, **not** original submission then.

### Temporal/provenance rules

1. A release dated **May 20** or **March 13** attesting that a BLA **has been** submitted does not imply the BLA was submitted on the press release's date. Keep submission day null.
2. The exact **July 11** sponsor submission day is supported by a company source published **November 3**, which must not be backdated as if publicly known July 11. The separate July 14 Atara announcement only establishes it had been submitted by then, not the day.
3. The code records the **2025-11-03 public disclosure date** for Pierre Fabre's precise July 11 sponsor filing claim. A historical as-of check before November 3 correctly returns **false** for knowledge of that exact day. This is a guard against backdating later-published historical evidence.
4. The **July 23** FDA *acceptance* day is sponsor reported; neither this nor a PDUFA target establishes the redacted FDA *submission receipt* day. The two event types must remain distinct.
5. FDA agency source provenance still controls final agency actions; no sponsor milestone creates a distinct additional final FDA action.
6. Model eligibility remains blocked because application-cohort denominator, independent complete review-cycle adjudication, archived source availability and feature-as-of audit are not certified. Historical source availability may follow historical event dates.

## Implemented safeguards

- `outcome_fda_receipt_boundary_gap_report.py` now attaches source URLs, sponsor-reported submission months, earliest possible **calendar day within that reported month**, the day by which submission was publicly confirmed, exact sponsor date only where supported, sponsor-reported FDA acceptance, and explicit `exact_fda_received_date=null`/`exact_fda_received_date_independently_verified=false`.
- The validator rejects a precise sponsor filing day inconsistent with month or announcement, accepts no unproven FDA receipt certification, and rejects contradictory reported acceptance ordering. A separate as-of function verifies that any precise sponsor filing date is unavailable before the *source's public release date*; it does not authorize model features.
- `test_outcome_fda_receipt_boundary_gap_report.py` contains tests for three missing FDA receipt cases, July 11 sponsor evidence, March-vs-May filing/acceptance distinction, and fail-closed safeguards.

## Verified automated execution

GitHub Actions run **40380569423** at commit **8cb2984f7cc07a954a1f59fd572f67e422dc99ad**, overall **success**:
- Existing historical/backtest safety: **74 passed**.
- FDA action, event export, review chronology, receipt-boundary and source-provenance: **71 passed; 9 subtests passed**.
- Immutable original FDA published-audit eligibility assertions: **passed**.

**No change to predictor:** `model_eligible_records=0`, `prediction_probability=null`, `complete_application_denominator_verified=false`.

**Next evidence needed:** dated FDA-origin original receipt notices or unredacted FDA review histories for BLA 125745 original, BLA 125745 2025 resubmission and BLA 125840 original; prioritize sources which visibly print day/month/year and confirm the correct original/supplement/resubmission identity. No guessing from goal-minus-six-months.
