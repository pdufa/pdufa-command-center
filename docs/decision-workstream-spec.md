# DECISION workstream — implementation contract (draft)

Status: design specification only. No live signals or orders are authorized.

## Scope
Evaluate two separate trading horizons: (1) positive Phase 3 readout through FDA decision; (2) holding after FDA decision through commercialization. Compare entry immediately after a verified Phase 3 release with entry after FDA filing acceptance. For each existing position evaluate exit before PDUFA, partial exit, and holding through the binary event. Preserve independent MAIN, SCIENCE, OUTCOME and all existing Pipeline/GEM JR/GEM/WT restrictions and FS/FA associations.

## Decision states
BUY_CANDIDATE, STAY, WAIT, PARTIAL_EXIT_CANDIDATE, EXIT_CANDIDATE, NOT_READY. Candidate signals are research outputs requiring human review, never orders. Distinguish new-entry AVOID from existing-position EXIT. Do not issue actionable signals when mandatory evidence is missing or stale.

## Required inputs
Verified trial identity, indication, Phase 3 primary/secondary endpoint results, safety, FDA filing acceptance and target date, scientific assessment and provenance, regulatory model probability with calibration version, timestamped price and market capitalization, float/liquidity/spread, cash runway, debt/financing/warrants, expected dilution, upcoming catalysts, portfolio exposure and user-defined risk limits. Each field requires as-of time, source, quality status and missingness marker.

## Independent calculations
- Event horizon: approval/rejection/delay scenarios; conditional price distributions, dilution, transaction costs, uncertainty intervals and probability-weighted outcomes. Compare exit before FDA decision versus hold-through; avoid treating historical returns as guarantees.
- Long-term horizon: label restrictions, launch costs, market access, competition, sales ramp and further financing scenarios.
- Risk: maximum loss, drawdown, concentration, liquidity, slippage, event gap risk and position sizing within user-specified limits.
- Evidence gates: missing critical sources, conflicting results, stale data, uncalibrated model, or inadequate out-of-sample evidence => NOT_READY.

## Validation gates before any recommendation
Chronological, point-in-time backtests with delisted names and transaction costs; holdout and forward validation; Brier score, log loss, calibration plots and subgroup performance; decision strategy benchmark comparisons including risk-adjusted returns, max drawdown, false-positive signals and sensitivity to approval probabilities and price assumptions. No 100% accuracy claims. Independent review of material model changes.

## UI
Show EVENT and LONG-TERM separately. Primary card: decision state, as-of time, evidence readiness, approval probability and uncertainty, expected gain/loss ranges, pre-PDUFA vs through-PDUFA comparison, reason codes and invalidation triggers. Detailed scientific and financial factors in expandable panels. Show installation completion separately from validated recommendation readiness.

## Engineering constraints
Implement on feature branch only; preserve scheduled scans and source verification; do not modify live main or trigger orders. Inspect existing Workspace, TradingDashboard, EntrySignal, wt-entry-stay-exit and backend endpoints before choosing integration boundaries. Add deterministic unit tests, integration tests and fail-closed tests before merge. Explicit operator approval required for deployment.
