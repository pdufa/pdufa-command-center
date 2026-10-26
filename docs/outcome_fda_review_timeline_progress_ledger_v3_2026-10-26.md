# OUTCOME — FDA review-timeline progress ledger v3 (2026-10-26)

Versioned status update. Supersedes *counts* in v2; does not modify the immutable published FDA source-audit snapshots. The selected research fixture collection is **not** an exhaustive application denominator and cannot support statistical approval rates.

## Current denominators

| Measure | Complete | Total / denominator | Remaining | Interpretation |
|---|---:|---:|---:|---|
| Priority source-record application identity documented | 15 | 17 source records | 2 | DBV and Chiesi still open |
| Sampled FDA action endpoints represented | 20 | 20 selected actions | Unknown outside sample | Added FDA SBRA-supported LANTIDRA August 2021 CRL |
| Distinct BLA identifiers in selected sample | 10 | 10 sampled identifiers | Unknown outside sample | Multiple letters/actions can refer to same BLA |
| Source-supported structured review timelines | **16** | **20 selected endpoints** | **4** | Documentation progress only; not 80% of FDA universe |
| Distinct sampled BLAs with >=1 structured timeline | **8** | **10 sampled BLAs** | **2** | Atara/Pierre Fabre and REGENXBIO lack exact verified receipt boundaries |
| Independently certified complete priority review cycles | **0** | **17 priority source records** | **17** | Source-record denominator is not unique cycle denominator |
| Model-eligible priority source records | **0** | **17 priority source records** | **17** | Complete cohort and timestamped as-of evidence still missing |

### Five new FDA-sourced review timelines

| BLA | Submission received | Final FDA action | Evidence distinction |
|---|---|---|---|
| 125743 ALYGLO | 2021-02-25 | 2022-02-25 CRL | Original signed CRL + FDA SBRA |
| 125743 ALYGLO | 2023-07-14 | 2023-12-15 approval | Signed approval + FDA SBRA |
| 125734 LANTIDRA | 2020-05-19 | 2021-08-18 CRL | **FDA SBRA regulatory history only; signed CRL not directly retrieved** |
| 125734 LANTIDRA | 2022-12-30 | 2023-06-28 approval | FDA SBRA resubmission + signed approval |
| 125842 Capricor | 2024-12-31 | 2025-07-09 CRL | 2026 FDA regulatory-history presentation + signed CRL |

For full source links and visual verification scope see `docs/outcome_fda_alyglo_lantidra_capricor_review_timeline_pass_2026-10-26.md`:
- ALYGLO FDA SBRA https://www.fda.gov/media/175227/download ; CRL https://download.open.fda.gov/crl/CRL_BLA125743_20220225.pdf ; approval https://www.fda.gov/media/174897/download.
- LANTIDRA FDA SBRA https://www.fda.gov/media/170457/download ; signed approval https://www.fda.gov/media/169921/download.
- Capricor FDA history https://www.fda.gov/media/193912/download ; original CRL https://download.open.fda.gov/crl/CRL_BLA125842_20250709.pdf.

### Four sampled endpoints remaining without verified start-to-action records

1. Mesoblast BLA 125706, September 30, 2020 CRL — source FDA review documents attest chronology but original signed action letter still not independently retrieved.
2. Atara/Pierre Fabre BLA 125745, January 15, 2025 CRL — exact FDA original BLA receipt date not independently verified.
3. Same BLA 125745, January 9, 2026 CRL — exact FDA resubmission receipt date is redacted in released action letter; sponsor reports July 2025 but exact FDA day remains unverified.
4. REGENXBIO BLA 125840, February 7, 2026 CRL — original BLA receipt date not established by the released FDA CRL; sponsor May 2025 filing acceptance is not a precise agency submission receipt.

The FDA SBRA for LANTIDRA additionally establishes a previously absent **August 18, 2021** CRL. Thus the sampled denominator changed **19 → 20**. It is incorrect to call that discovery a new independent application.

### Source conflicts and modeling limits

- ALYGLO PDUFA goal date disagreement: FDA SBRA **2024-01-13**, FDA clinical review **2024-01-12**. Both retained with source references. The goal is not the FDA final action.
- Ultragenyx PDUFA goal date disagreement and Mesoblast SBRA application-number conflict remain open from prior ledgers.
- Replimune FDA clinical reviewer recommendation differed from the signed final approval action; preserved as a source-role conflict.
- Capricor's 2026 regulatory-history presentation was **not available before its July 2025 CRL**, and therefore cannot be used as pre-action predictive evidence.
- LANTIDRA original signed 2021 CRL is **not** marked verified; event source role explicitly `fda_regulatory_history_summary` rather than `signed_fda_final_action_letter`.
- Source publication timestamps, cryptographic original-document hashes, complete amendments, comprehensive action inventories, and application-universe denominators have not been independently certified. All research events and structured timelines remain `model_eligible=false` and `prediction_probability=null`.

### New machine-readable research interface

- `outcome_fda_research_action_fixtures.py`: 20 selected FDA action events with explicit `source_document_role`.
- `outcome_fda_review_timeline_evidence.py`: 16 source-supported receipt-to-final-action timelines.
- `outcome_fda_review_timeline_export.py`: JSON export of all 16 timelines with dated sources, explicit FDA conflict flags and fail-closed gates.
- `test_outcome_fda_review_timeline_export.py`: export integrity, provenance distinction and source conflict verification.
- `outcome_fda_research_export.py`: research event JSON with source roles.

### CI proof

GitHub Actions **OUTCOME historical safety tests** run **40370788097** (commit **7ff7dcdb95b2ee056c4ef18e97855d67c7b0083f**) finished successfully:
- Historical/backtest safety: **74 passed**.
- FDA action, research export and timeline tests: **58 passed**.
- Immutable published FDA audit fail-closed check: **passed**.

**Overall:** More historically sourced regulatory timelines are usable for **research inspection**, not training, prediction probability display, or investment decisions. No model readiness percentage should be inferred from sample coverage.
