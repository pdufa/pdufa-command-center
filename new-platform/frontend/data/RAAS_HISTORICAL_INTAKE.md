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

## Known gaps as of 2026-11-02

- Genuine, precommitted historical investment-prediction cases: **0 reviewed**. Historic pre-entry RAAS metric score records: **0 reviewed**. Seven separately labeled retrospective observational windows are available for source-intake testing, but are **not** admissible model performance records.
- Historical source-backed pilot observations cover five NCT records but not actionable, verified pre-entry stock valuation/return timelines. Two CLDX records are one underlying barzolvolimab-CSU asset.
- FDA target and full stock-price/financing sources have not been authenticated for BOTTOM pilot investments, so there is no qualified BOTTOM return forecast.
- No 0–100 RAAS metric has completed independent calibration. Only one experimental **readout-window specificity** research score exists, expressly excluded from overall RAAS.

To populate these ledgers, review primary issuer and FDA regulatory records, historical SEC filings, archived price series with corporate actions and event timestamps, and recorded forecasts made before entry. Manual review and source reconciliation remain necessary. Do NOT automate silently importing unreviewed web search snippets into the approved score registry.
