# RAAS historical calibration intake (TOP and BOTTOM)

Updated 2026-11-02. This document is an implementation contract, not a completed historical backtest or validation certificate.

## Canonical files

- `data/raas-historical-cases.json`: real entry-to-exit event windows; schema `RAAS_HISTORICAL_EVENT_BACKTEST`
- `data/raas-historical-metric-snapshots.json`: 0–100 *pre-entry* metric ratings with benchmark version and dated evidence; schema `RAAS_HISTORICAL_METRIC_SNAPSHOTS`
- `data/raas-approved-calibrations.json`: audited metric-specific scoring rules, initially empty
- `data/raas-reviewed-snapshots.json`: trial-specific ENTRY/CURRENT/EXIT approvals, initially empty
- `lib/raas-historical-backtest.ts`: event-window, leakage, market-cap and same-program deduplication checks
- `lib/raas-metric-backtest.ts`: metric-by-metric rank/return diagnostics
- `lib/raas-reviewed-score-ledger.ts`: requires BOTH a manually approved calibration and matching historical metric-return support before admitting a grade

## What a real historical case MUST establish

1. Identity: exact NCT(s), listed ticker, therapy, indication, `stage: "pre" | "post"`. The same company + drug + indication represents one independent opportunity, however many NCTs it has.
2. Company market cap **at historical entry** between $300M and $10B, with a dated source. Never reuse today's cap as yesterday's cap.
3. Feature cutoff and published prediction **no later than trade entry**. Every study/financial/regulatory source contributing to the prediction must have a publication date on/before the feature cutoff.
4. Actual executable historical entry and exit dates, with source-linked USD **split-adjusted** stock prices, and explicit round-trip costs. Confirm exchange open sessions, including holidays, when reviewing records.
5. Actual Phase 3 public release date and source. TOP entry and planned exit must be before the first public readout. A dated historical PRE_AS_OF_CHECK is not itself proof that the event was still unpublished at a later trading date.
6. For BOTTOM, verify the public Phase 3 readout predates entry and that an accepted FDA application and program-specific PDUFA target were **known at entry**. Exit must be on/before PDUFA minus 3 calendar days, not after the FDA decision.
7. Outcome and sources: the trade return must be observable by the ledger date. Forecasts and RAAS ratings must come from historical versions that really existed at entry, not reconstructed using later trial/FDA knowledge.
8. Stage-specific training and test groups: purge the same therapy/indication/issuer from opposite sides of a walk-forward split. Do not treat two CLDX barzolvolimab CSU NCTs as two independent stocks.

## How to build a qualified metric grade

1. Define the metric's disease- or financial-context benchmark and exact 0/25/50/75/100 bands **before** looking at out-of-sample performance.
2. Save the historic rating, methodology, benchmark ID, rule version and primary source URL/date in `raas-historical-metric-snapshots.json`.
3. Join only eligible, complete historical trade windows. Measure metric score vs realized return by **independent program**, not trial count. Report correlation, higher/lower score-group return spread and uncertainty.
4. Evaluate walk-forward holdouts whose test entries postdate the last training exit, with no overlapping underlying programs. Explicitly account for spread, slippage, financing, ticker changes, splits, delistings, sector returns and survivorship.
5. The current code's floor of 30 independent programs is a **minimum screening requirement**, not a sufficient sample size or evidence of predictive power. Audit multiple eras and the full outcome distribution.
6. Approve a calibrated benchmark only with source-supported, independently reviewed historical evidence. Then create exact trial ENTRY/CURRENT/EXIT reviewed scores. Never populate blanks with zero or assume a clinical p-value is an FDA approval probability.
7. Re-evaluate the model periodically for probability calibration and actual forward performance. Report failures, abstentions and changes to source timing.

## Source-backed retrospective research examples, added 2026-11-02

The dedicated page `/raas-history` now audits each registered TOP/BOTTOM example separately. `lib/raas-history-audit.ts` lists documented source claims, price/corporate-action verification, SEC financing reconciliation, peer comparison and the lack of original predictions. The separately reviewed `data/raas-retrospective-asof-evidence.json` adds nine dated, structured clinical/financial observations across four BOTTOM programs. The validator `lib/raas-retrospective-asof-evidence.ts` rejects facts first published after the retrospectively selected entry date and prevents a single-arm rate from becoming a placebo comparison. This research does not establish any RAAS score.


These are *observed* historic closing-price illustrations, not historical RAAS forecasts. Entry and exit windows were selected **after** knowing subsequent outcomes. No case has been moved into the validated ex-ante `raas-historical-cases.json` registry. Market-cap and price vendors are external and corporate-action adjustments and execution costs still need independent auditing.

| Phase | Program | Historical entry and exit closes | Gross change | Later event (unknown at entry) |
|---|---|---|---:|---|
| TOP | GERN / imetelstat / MDS | 2022-11-18 $2.26 → 2022-12-30 $2.42 | +7.08% | Phase 3 public data 2023-01-04 |
| TOP | MDGL / resmetirom / NASH | 2022-11-18 $72.80 → 2022-12-16 $63.80 | −12.36% | Phase 3 public data 2022-12-19 |
| BOTTOM | VRNA / ensifentrine / COPD | 2024-05-10 $14.85 → 2024-06-21 $15.00 | +1.01% | FDA action 2024-06-26 |
| BOTTOM | GERN / imetelstat / MDS | 2024-05-03 $3.93 → 2024-05-31 $3.55 | −9.67% | FDA action **2024-06-06**, ahead of 2024-06-16 PDUFA target |
| BOTTOM | URGN / UGN-102 / bladder cancer | 2025-03-14 $11.07 → 2025-06-06 $7.37 | −33.42% | FDA action 2025-06-12, ahead of 2025-06-13 PDUFA target |
| BOTTOM | MDGL / resmetirom / NASH | 2023-11-03 $146.89 → 2024-03-08 $255.32 | +73.82% | FDA action 2024-03-14 |
| BOTTOM | BBIO / acoramidis / ATTR-CM | 2024-05-10 $29.10 → 2024-11-15 $23.72 | −18.49% | FDA action 2024-11-22, ahead of 2024-11-29 PDUFA target |

Primary company announcements and FDA sources, plus market-cap and closing-price vendor URLs, are attached to each record in `data/raas-retrospective-top-cases.json` and `data/raas-retrospective-source-cases.json`.

An observed negative run-up despite subsequent approval demonstrates why scientific benefit alone is insufficient to forecast remaining stock appreciation. The Geron case shows the danger of a solely PDUFA-date-based exit: FDA may act earlier than the published action target.

Research-only intake validators:
- `lib/raas-top-retrospective-intake.ts` enforces TOP sponsor guidance preceding entry, a verified future readout event and exit strictly before release.
- `lib/raas-retrospective-intake.ts` enforces BOTTOM pre-entry Phase 3 and PDUFA sources, market cap between $300M and $10B, exit no later than PDUFA minus three calendar days, and exit before *actual* early FDA decision in recorded examples.
- Neither data source is read by `lib/raas-historical-backtest.ts` or `lib/raas-reviewed-score-ledger.ts`; these records cannot produce validated 0–100 RAAS grades.

## Point-in-time finance and cost-sensitivity implementation

- `data/raas-historical-finance-facts.json`: 7 dated pre-entry financial snapshots with 24 individually labeled issuer/SEC observations. Liquidity, operating losses, financing proceeds, debt, ATM availability, and financing commitments are separate fields; sources and balance dates are retained.
- `lib/raas-finance-reconciliation.ts`: validates that each financial disclosure was **published before the simulated entry**. Distinguishes cash on hand from obligations, equity financing and committed/available funding; prevents duplicate categories from being treated as additive cash. Its returned readiness stays **unqualified** until security prices, shares, debt and transaction costs have been independently reconciled.
- **Critical rejected source:** Madrigal's September 30, 2023 Form 10-Q was filed November 6, 2023, **after** the retrospectively selected November 3, 2023 entry. It must not be used to score or justify that entry. The research record now uses the **August 8, 2023 Form 10-Q for June 30, 2023** instead (cash and marketable securities $298.418M; six-month operating cash used $159.377M). A regression test rejects the later filing at that entry date.
- `app/raas-history/RaasHistoricalWhatIf.tsx`: interactive historical close-to-close cost sensitivity and a **separate independent price-shock calculation**. User-selected round-trip costs and shock are assumptions, not real executions, probabilities, scenario forecasts or RAAS grades. Outputs cannot enter the genuine prediction registry.
- `tests/raas-finance-reconciliation.test.cjs`: rejects wrong case identity, future financial disclosure, negative figures, double-counted cash categories and nonsensical scenario parameters.

The actual historical adjusted closing prices, ADR conversion, holiday session checks, bid/ask and executed slippage, share count, debt waterfall and forward valuation are still not reconciled. No approved historical RAAS score exists. Source evidence collected after a trading date must **never** be backfilled into an earlier decision snapshot.

## Historical share-count / market-cap reconciliation (2026-11-02)

Source-backed point-in-time SEC cover counts are imported into `data/raas-share-bridge-research.json` and validated by `lib/raas-share-bridge.ts`. The research screen under `/raas-history` now expands an independent share-count / capitalization check per case.

| Phase / case | SEC ordinary/common shares available by selected entry | Quoted-unit conversion | Vendor close × shares, $M | Existing market-cap estimate, $M | Independent cap comparison? |
|---|---:|---:|---:|---:|---|
| TOP BBIO 2023-05-12 | 160,500,999 (May 2 cover count, May 4 filing) | 1 share / quote | 2,173.18 | 2,173.18 | **No:** original listed cap was already calculated from these shares and vendor close |
| BOTTOM GERN 2024-05-03 | 593,132,540 (April 26 cover count, May 2 filing) | 1 share / quote | 2,331.01 | 2,331 | **Separate vendor cap estimate**, still unverified prices |
| BOTTOM VRNA 2024-05-10 | 648,654,174 (May 2 cover count, SEC filing May 10 **09:09:53 ET**) | **8 ordinary shares per ADS** | 1,204.06 | 1,204 | **Separate vendor cap estimate**, still unverified prices |

Only **3 of the 8** registered retrospective examples have a source-vetted cover share-count bridge. Two reconcile arithmetically against separately reported vendor market-cap figures, but one (BBIO) is circular. This does **not** establish the historical close, market-cap methodology, corporate-action adjusted series, fully diluted share count or enterprise value.

Same-day share counts need a pre-close SEC acceptance time; a filing after close is barred from the close-date historical reconstruction. No share-bridge match can enter approved RAAS scoring or predictive validation. Tests in `tests/raas-share-bridge.test.cjs` guard source timing, share conversion, arithmetic and nonpromotion.

All 8 case prices still need a second independently date-specific source; 5 cases still need a dated compatible SEC share-count bridge; historical splits, dividends, ADS transformations, options, debt and price execution remain unresolved.

## Historical daily-close second-provider checks (2026-11-02)

The research-only `data/raas-price-crosschecks.json` stores source links and exact dates for **4 of 16** historic ENTRY/EXIT closing-price observations across the 8 TOP/BOTTOM examples. Each price is independently displayed by a second website, but neither a licensed exchange-tape audit nor a verified corporate-action-adjusted price series has yet been obtained. Dated matches:

| Example | Price side | Date | Original vendor close | Second provider close | Second source |
|---|---|---|---:|---:|---|
| BOTTOM VRNA / ensifentrine | Entry | 2024-05-10 | $14.85 | $14.85 | ChartExchange |
| BOTTOM VRNA / ensifentrine | Exit | 2024-06-21 | $15.00 | $15.00 | ChartExchange |
| BOTTOM URGN / UGN-102 | Exit | 2025-06-06 | $7.37 | $7.37 | ChartExchange |
| TOP MDGL / resmetirom | Exit | 2022-12-16 | $63.80 | $63.80 | StatMuse |

Secondary-source URLs and quote-basis warnings are retained per observation. Missing 12 other second-source observations are **not** counted as matches. Only the VRNA sample has both dates corroborated by a second website.

`lib/raas-price-crosschecks.ts` rejects unknown case IDs, wrong trading dates, reuse of the first vendor URL, invalid price values and duplicate quotes. It highlights disagreements instead of averaging or overlooking them. The per-case collapsed section in `/raas-history` exposes each point, comparisons and outstanding blockers. `tests/raas-price-crosschecks.test.cjs` covers these safeguards.

**Important limitations:** These 4 matching nominal closes have not been independently audited for split, dividend or ADS ratio changes, delisting/merger adjustments, exchange-specific session rules or actual executable fills. A second vendor publishing the same number may use the same upstream price feed. No adjusted total return has been certified and no retrospective case can generate a validated historic RAAS forecast. Next: verify remaining 12 closes, cross-check corporate actions and obtain independently sourced fully diluted historical capitalization.

## Known gaps as of 2026-11-02

- Genuine, precommitted historical investment-prediction cases: **0 reviewed**. Historic pre-entry RAAS metric score records: **0 reviewed**. Seven separately labeled retrospective observational windows are available for source-intake testing, but are **not** admissible model performance records.
- Historical source-backed pilot observations cover five NCT records but not actionable, verified pre-entry stock valuation/return timelines. Two CLDX records are one underlying barzolvolimab-CSU asset.
- FDA target and full stock-price/financing sources have not been authenticated for BOTTOM pilot investments, so there is no qualified BOTTOM return forecast.
- No 0–100 RAAS metric has completed independent calibration. Only one experimental **readout-window specificity** research score exists, expressly excluded from overall RAAS.

To populate these ledgers, review primary issuer and FDA regulatory records, historical SEC filings, archived price series with corporate actions and event timestamps, and recorded forecasts made before entry. Manual review and source reconciliation remain necessary. Do NOT automate silently importing unreviewed web search snippets into the approved score registry.
