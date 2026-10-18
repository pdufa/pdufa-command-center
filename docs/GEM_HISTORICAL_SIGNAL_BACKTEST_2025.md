# GEM / GEM JR: 2025 historical trading-signal backtest

**Research only. Neither a validated strategy nor an instruction to buy.**

The isolated module gem_historical_signal_backtest.py does not affect Streamlit,
nightly scans, GEM clinical/funding scores, or brokerage orders.

## How to run

From the repository root:

    python -m unittest discover -s tests -p 'test_gem_historical_signal_backtest.py' -v
    python gem_historical_signal_backtest.py --year 2025 --output-dir output/gem_backtest_2025

The runner accepts --events and --bars to override the existing CSV templates
in data/post_phase3_historical_trade_events.csv and
data/post_phase3_historical_adjusted_ohlcv.csv.

Files generated: per_event_signals.csv, parameter_grid_summary.csv and
readiness.json. No audited event rows or no verified OHLCV -> no claimed win rate.
GitHub Actions GEM Historical Signal Backtest Checks tests synthetic fixtures
and uploads an evidence-readiness artifact; synthetic trades never enter the
production input or summary.

## Data necessary for a real 2025 study

1. Complete 2025 publicly traded PDUFA cohort: exact issuer and SEC CIK,
   ticker at that date, clinical product and indication/NCT, original PDUFA
   date and changes, outcome including CRLs, delays, early actions, approvals,
   and delisted failures. FDA's novel-drug APPROVAL list is insufficient.
2. Primary-source positive Phase 3 results: disclosed efficacy, benefit,
   safety and date information first became public.
3. Two distinct documented *completed* post-readout financings, matched to
   that issuer CIK, with first-public SEC filing dates. Announcements and
   ATM authorizations are not necessarily financing closes.
4. Verified split-adjusted daily Open/High/Low/Close/Volume covering at least
   50 prior sessions plus the entry-to-exit window. Preserve price provenance.
   Alpaca historical bars: timeframe=1Day, adjustment=split, feed=sip,
   paginating with next_page_token. Confirm ticker-asof mapping, entitlement,
   delistings, price gaps and corporate actions. Never manufacture data.
5. Early FDA decision dates, halted markets and source-coverage exceptions.
   Censored observations must not be dropped as though they were losers/winners.

This engine validates date order, event keys, source URL shape, issuer CIK and
price structure; a syntactically valid source URL does NOT prove the dated
document actually verifies an outcome. Human/source audit is still required.

## Model hypotheses, not fitted parameters

Require the two clinical/financing benchmarks. Enter only after 10 observed
post-financing sessions. Test a 10-session base (width <= 2/3/4 ATR), close
above prior-base high + 0.1 ATR, relative volume >= 1.25/1.5/2.0 times prior
20-day volume, and $250,000 minimum prior-20-session daily dollar liquidity.
Test score cutoffs 60/70/80. Signal is end-of-day; entry is the NEXT open.
Reject chases >0.5 ATR and risk outside 0.5-3 ATR or over 8% of entry.

Experimental score: trend 25, relative volume 20, breakout/location 20,
next-open risk/stop 20, PDUFA timing 15. Do not mistake it for the exact
current dashboard's provisional scoring model. The initial stop is 0.25 ATR
below the ten-session low; a 2 ATR trailing stop uses the preceding day's
completed price data. Two closes below SMA20 trigger next-open exit. Compare
mandatory cutoffs 14 days versus 3 days before PDUFA. Model 10 basis points
of slippage on both entry and exit. Daily bars cannot resolve intraday
ordering; gap stop execution is approximated at the opening price if worse.

## Readiness and anti-overfitting

- Parameter combinations with fewer than 30 completed trades are EXPLORATORY.
  30 does not automatically make a backtest statistically valid.
- Run a separate chronological holdout and freeze parameters beforehand.
- Compare against immediate post-benchmark entries and scheduled exits, using
  consistent eligible programs; separately audit the larger PDUFA population
  to reveal selection bias.
- Report events with no signal, invalid evidence and early FDA actions.
- Delistings, missing sessions, corporate actions and realistic fees/fills
  require separate adjudication before a tradeable performance claim.
- Existing live trading signals and scheduler remain entirely unchanged.

## Sources

FDA novel approvals (NOT full PDUFA denominator):
https://www.fda.gov/drugs/novel-drug-approvals-fda/novel-drug-approvals-2025

Alpaca daily historical bar parameters:
https://docs.alpaca.markets/us/reference/stockbars


## Historical starting queue and Alpaca staging

A separate, NONTRADABLE 13-row initial research queue is available at
data/gem_2025_pdufa_research_queue.csv. These are sourced candidates for
verification, not a complete PDUFA population and not eligible GEM trades.
The PDUFA dates and issuer associations require date-by-date original
disclosure review; no rows are auto-promoted to the historical event template.

After the relevant historical ticker is authenticated, authorized users can
stage market bars using environment variables APCA_API_KEY_ID and
APCA_API_SECRET_KEY (or ALPACA_API_KEY and ALPACA_SECRET_KEY):

    python scripts/fetch_gem_2025_alpaca_review.py --symbols LENZ,CAPR --start 2024-07-01 --end 2026-01-01 --asof 2025-12-31 --output output/gem_2025_alpaca_review.csv

The staging CSV is marked PENDING_TICKER_AND_SPLIT_AUDIT deliberately. Only
after individual verification against ticker history, SEC issuer identity,
provider completeness, and corporate actions may the required existing
backtest field be set to SPLIT_ADJUSTED_VERIFIED. The script prints neither
secrets nor raw responses. GitHub Actions unit tests use fake responses and
require no Alpaca credentials.
