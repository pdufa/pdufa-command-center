# SEC verification avenue tracker

This is a **research and audit log**, not a list of approved trades. It is maintained in the repository alongside the live SEC scanner. Last baseline: source run `38770659348`, October 15, 2026, when **26 SEC closing claims and 1 BLTE financial cash/runway claim** required further primary evidence.

## Discovery approaches and audit gates

| Avenue | Used for | Proof rule | State |
|---|---|---|---|
| Google company + SEC + document type | Find potential exact SEC links | Search snippets and generated links are **discovery only** | Available |
| SEC CIK submissions inventory | Reconcile actual issuer, forms and dates | Filing index is **not completion proof** | Automated |
| 8-K, 8-K/A and 6-K | Offering-close disclosures and press-release exhibits | Exact closing date, issuer and SEC body are verified | Automated |
| 10-Q, 10-K and 20-F | Later reported completed financings | Closing claim must be in same transaction clause | Automated |
| Registered offering prospectus/424B | Find terms, settlement references, underwriting | Prospectus alone does not establish funding | Follow-up |
| SEC Exhibits 99, 10, 4 and 2 | Underwriting, placement and debt documents | Completed dated funded transaction, not an agreement to fund later | Automated bounded |
| Investor relations and reputable search | Find unindexed disclosures and transaction hints | Cross-check SEC primary source before resolution | Research only |
| Financing stage and subsequent offerings | Distinguish same offering option/tranche vs a second raise | Match program Phase 3 readout date and independent closings | Separate gate |
| Financial runway (BLTE) | Resolve USD cash and runway audit | Signed SEC 6-K/20-F facts, reporting currency, period and cash-flow evidence | Unresolved |

## Exact-event open cases (baseline)

The **state of every row below is REVIEW REQUIRED in the baseline**, not "no financing." New research outputs are kept separately, without overwriting this historical ledger. A newly found company transaction can be relevant to multiple programs without proving the same stage-specific eligibility.

| Event | Issuer | Existing closing date | Next evidence route |
|---|---|---|---|
| `VTRS|PHENTOLAMINE_PRESBYOPIA_20261017` | VTRS | — | 10-Q/10-K; avoid counting routine financing as program-specific |
| `AGIO|MITAPIVAT_SCD_20261101` | AGIO | — | 8-K financing + quarterly subsequent events |
| `SMMT|IVONESCIMAB_20261114` | SMMT | 2025-10-31 | Reconcile saved 2025-10-31 date against distinct 2026-10-05 investment; never substitute |
| `CAPR|DERAMIOCEL_DMD_20261122` | CAPR | — | 10-Q subsequent-event note + dated offering exhibit |
| `VRTX|POVETACICEPT_IGAN_20261130` | VRTX | — | 10-Q/10-K; no offering inferred from cash balances |
| `ZLAB|POVETACICEPT_IGAN_20261130` | ZLAB | — | 6-K/20-F plus offering exhibits |
| `ANAB|IMSIDOLIMAB_GPP_20261212` | ANAB | — | 8-K + 10-Q subsequent events |
| `CORT|RELACORILANT_CUSHINGS_20261217` | CORT | — | 8-K + 10-Q subsequent events |
| `MLYS|LORUNDROSTAT_20261222` | MLYS | 2025-09-04 | Reconcile 2025-09-04 closing against SEC 10-Q and Exhibit 99 |
| `GILD|ANITOCEL_MM_20261223` | GILD | — | 10-Q/10-K; check external licensing versus capital raising |
| `VTRS|MR107A02_ACUTEPAIN_20261227` | VTRS | — | 10-Q/10-K; avoid counting routine financing as program-specific |
| `COGT|BEZUCLASTINIB_NONADVSM_20261230` | COGT | — | Issuer-specific financing exists; adjudicate event identity and Phase 3 timing |
| `IBRX|ANKTIVA_NMIBC_20270106` | IBRX | — | 8-K/10-Q; distinguish related-party loans from equity |
| `DYN|ZROSTUDIRSEN_DMD_20270121` | DYN | — | SEC-filed July 2026 Exhibit 99 close; validate exact date and amount |
| `ARQT|ZORYVE_AD_20270223` | ARQT | — | 10-Q/8-K; historical close might predate trial readout |
| `CGEM|ZIPALERTINIB_NSCLC_20270227` | CGEM | — | 8-K offering exhibits and quarterly subsequent events |
| `APMD|OXNIMBI_OSA_20270228` | APMD | — | IPO 8-K and prospectus 424B4; IPO is not financing #2 |
| `EXEL|ZANZALINTINIB_CRC` | EXEL | — | 10-Q/10-K; do not assume there was a qualifying offering |
| `HRMY|PITOLISANT_GR_20270401` | HRMY | — | 10-Q/10-K funding events |
| `AXSM|AXS12_CATAPLEXY_20270501` | AXSM | 2026-06-30 | Check saved 2026-06-30 close against quarter-end balance-sheet date |
| `BMY|MEZIGDOMIDE_RRMM_20270513` | BMY | — | 10-Q/10-K; verify financing vs acquisition debt |
| `PHAR|JOENJA_LOWER_DOSE_APDS_20270130` | PHAR | — | 6-K/20-F with currency and issuer CIK check |
| `BLTE|TINLAREBANT_STGD1_20270212` | BLTE | — | 6-K/20-F; separate USD cash/runway from financing proof |
| `SRPT|CASIMERSEN_DMD45_20270228` | SRPT | — | 8-K/10-Q; multiple trials share issuer but cannot share program sequence |
| `SRPT|GOLODIRSEN_DMD53_20270228` | SRPT | — | 8-K/10-Q; multiple trials share issuer but cannot share program sequence |
| `INBX|OZEKIBART_CHONDROSARCOMA_20270414` | INBX | — | 8-K/10-Q + investor-relations disclosure |

## Run and reconciliation process

1. GitHub Actions workflow **PDUFA Unresolved SEC Evidence Discovery** loads the **latest** required review queue and verified registry, not this snapshot.
2. It searches issuer-matched SEC 8-K/6-K and periodic filing documents plus bounded indexed exhibits; every result records the source URL, candidate close date, evidence excerpt and a link to a useful Google query. The Google link is for human discovery and never queried as an authority.
3. Only the pre-existing strict source verifier can label an **individual transaction** `VERIFIED_TRANSACTION_ONLY`. The exported CSV always has `trade_entry_authorized=NO` and `second_post_phase3_verified=NO`.
4. The normal five-source canonical reconciliation is separate. Only its fresh published source ledger may reduce the official unresolved count. Do not delete alert emails merely because a research hit appears.
5. Inspect GitHub Actions run artifacts `unresolved-sec-avenues-<run_id>` and compare **newly supported**, **potential**, **source unavailable**, and **no match within bounded search** against this checklist. A no-match search result is **never** evidence that no financing occurred.

## Working priorities

**First:** correct mismatched dates (SMMT, MLYS, AXSM); **second:** company-specific closing evidence for IPOs/convertible notes/tranches and historic financing; **third:** foreign-issuer 6-K/20-F; **fourth:** remaining issuer filings; **fifth:** independently verify cash and operating runway for BLTE. These are research priorities, not ranked trade recommendations.
