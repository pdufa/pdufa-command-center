# OUTCOME — FDA review-timeline progress ledger v2 (2026-10-26)

Supersedes the counts (not the underlying immutable source records) in `docs/outcome_fda_review_timeline_progress_ledger_v1_2026-10-26.md`. This ledger records **source-supported research timelines**, *not* fully audited review cycles or a population-wide prediction denominator.

## Counted progress — each measure has its own denominator

| Measure | Completed | Denominator | Remaining | Interpretation |
|---|---:|---:|---:|---|
| Priority FDA identity documentation | 15 | 17 source records | 2 | DBV and Chiesi remain open |
| Selected action endpoints with a structured submission-to-action timeline | **11** | **19 sampled final-action endpoints** | **8** | Sampled actions only; not exhaustive applications |
| Selected BLA identifiers with at least one structured timeline | **5** | **10 sampled BLA identifiers** | **5** | Application distinct from decision or published letter |
| Independently certified complete priority review cycles | **0** | **17 priority source records** | **17** | The denominator is priority source *records*, not unique cycles |
| Model-eligible priority source records | **0** | **17 priority source records** | **17** | Model remains fail-closed |
| New FDA Python automated test cases passing | **43** | **43 discovered new FDA tests** | **0** | Test pass is infrastructure assurance, not cohort validation |

### 11 source-supported review timelines (5 selected BLAs)

| BLA | Submission received | Final FDA action | Type |
|---|---|---|---|
| 125807 Abeona | 2023-09-25 | 2024-04-16 | CRL |
| 125807 Abeona | 2024-10-28 | 2025-04-28 | Approval |
| 125706 Mesoblast | 2023-01-31 | 2023-08-01 | CRL |
| 125706 Mesoblast | 2024-07-08 | 2024-12-18 | Approval |
| 125806 Rocket | 2023-08-01 | 2024-06-14 | CRL |
| 125806 Rocket | 2025-09-26 | 2026-03-26 | Accelerated approval |
| 125845 Ultragenyx | 2024-12-18 | 2025-07-07 | CRL |
| 125845 Ultragenyx | 2026-03-20 | 2026-09-17 | Approval |
| 125827 Replimune | 2024-11-21 | 2025-07-21 | CRL |
| 125827 Replimune | 2025-10-09 | 2026-04-10 | CRL |
| 125827 Replimune | 2026-06-02 | 2026-08-06 | Accelerated approval |

Primary-source crosschecks for the 7 newest structured timelines are in `docs/outcome_fda_rocket_ultragenyx_replimune_review_timeline_crosscheck_2026-10-26.md`. Earlier Abeona and Mesoblast sources are documented in v1.

### Precisely 8 sampled action endpoints still without structured timelines

- Mesoblast BLA 125706 original September 30, 2020 CRL: **1** endpoint; primary original letter retrieval and timestamp checks needed.
- Green Cross/GC Biopharma BLA 125743 (2022 CRL and 2023 approval): **2** endpoints.
- Atara/Pierre Fabre BLA 125745 (2025 and 2026 CRLs): **2** endpoints.
- CellTrans BLA 125734 (2023 approval): **1** endpoint.
- Capricor BLA 125842 (2025 CRL): **1** endpoint.
- REGENXBIO BLA 125840 (2026 CRL): **1** endpoint.

**Remaining with zero structured timelines: 5 of 10 sampled applications**: 125743, 125745, 125734, 125842, 125840. Mesoblast has two structured timelines but one action without a structured timeline.

### Outstanding data-quality flags

1. Ultragenyx FDA PDUFA date disagreement: FDA SBRA **2026-09-19**, clinical review **2026-09-18**. Store both; due date is not FDA action.
2. Replimune clinical reviewer recommends Complete Response, but signed FDA final agency action **2026-08-06 accelerated approval**. Clinical review prints **2026-08-02** goal; signed action is four days later. Clock explanation unverified.
3. Mesoblast FDA SBRA's **127506** cover-page error versus **125706** regulatory table and signed agency letters; retain source-level conflict and canonicalize application to 125706 with corroboration.
4. DBV and Chiesi identity cases remain unresolved. StemCyte FDA approval-date conflict still unresolved.
5. Pre-action features lack verified source-publication timestamps and original-document hashes; cohort denominator, clock histories, correction notices and complete application inventory have not been independently audited.

### CI execution proof

GitHub Actions run **40367896372**, commit **1002b131bf37ab4ec30e00d7107d7a53cec33be6**, overall success; job log reports:
- historical/backtest safety: **74 passed**;
- new FDA action, fixture, JSON export and timeline tests: **43 passed**;
- published historical audit model-clearance check: **passed**; immutable audit `model_eligible_records=0`, `prediction_probability=null`, `complete_application_denominator_verified=false`.

The code dynamically computes `selected_research_action_endpoints=19`, `source_supported_review_timelines=11`, `selected_actions_without_structured_timeline=8`, `selected_research_application_identifiers=10`, and `selected_applications_without_structured_timeline=5`. File: `outcome_fda_review_timeline_evidence.py`.

**No model training, regulatory approval percentage, backtest calibration, or live deployment is authorized by this progress.** All timelines remain research-only and `prediction_probability=null`.
