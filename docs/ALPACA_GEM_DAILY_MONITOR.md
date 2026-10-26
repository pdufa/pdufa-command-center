# Alpaca daily GEM / GEM JR monitoring

## Status

This component is a **draft research implementation**, not deployed into
the active Streamlit dashboard or nightly scan. Its GitHub Actions schedule
will be active only **after merging to main** and configuring the GitHub
Actions secrets described below. It cannot monitor a stock until it is added
to the separate paper Alpaca watchlist. Never confuse a backtest with a live
broker account or a paper holding with an external E*Trade position.

## What happens each weekday

After the US regular session, GitHub Actions can read the named Alpaca PAPER
watchlist 'GEM DAILY MONITOR', retrieve split-adjusted daily OHLCV through the
Alpaca market-data API, and read current PAPER positions. The script uses GET
requests only, then writes `output/gem_alpaca_daily.json`, a GitHub Actions
run summary, and a retained report artifact. It never places buy/sell orders.

The automated schedule is `0 1 * * 2-6` UTC (Monday-Friday evening in the
United States, UTC day Tuesday-Saturday), subject to GitHub scheduling delay.
With the default IEX feed, volumes reflect only IEX and cannot establish
reliable market-wide RVOL; ENTRY_SETUP_REVIEW is **not** a green buy signal.
A paid or otherwise accessible SIP feed may be selected explicitly, subject
to actual Alpaca entitlements, and still requires documentary eligibility.

## Initial one-time setup

1. Obtain **paper** Alpaca API credentials. Save the following in the GitHub
   repository's Actions Secrets: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`.
   Existing keys in Streamlit Secrets are **not** shared with GitHub Actions.
2. In a secure local environment with those environment variables plus
   `ALPACA_PAPER=true`, explicitly add a ticker to Alpaca's paper watchlist:

       python scripts/alpaca_gem_watchlist.py --add SRRK

   This is only an example; the operator must supply the desired ticker.
   The command GETs the watchlist, creates the watchlist if absent, or
   explicitly POSTs the selected ticker. Repeating an existing ticker is
   idempotent. It does not open or fund a trade.
3. Review documentary positive Phase 3 evidence and TWO DISTINCT completed
   post-readout financings and PDUFA public dates in the historical exact-
   event CSV. For now, `data/post_phase3_historical_trade_events.csv` has
   no source-verified event rows. No entry setup will pass without them.
4. After merging the draft changes and configuring credentials, inspect
   GitHub Actions > 'GEM Alpaca Daily Entry Exit Monitor' and its latest
   daily run summary/artifact. Paper positions are not actual broker fills.

## Signals

- **ENTRY_BLOCKED**: missing exact event verification (Phase 3, two
  post-readout financing closings, or PDUFA disclosure). Other indicators
  may still be shown for research, never as a green signal.
- **WAIT**: eligibility evidence exists but the base, breakout, volume,
  liquidity, 70-point experimental score, or risk setup is incomplete.
- **ENTRY_SETUP_REVIEW**: close-only setup qualifies on IEX; market-wide
  volume is not confirmed. No order is placed.
- **ENTRY_SETUP_NEXT_OPEN_RECHECK**: EOD setup on SIP requires a NEXT
  session open check (gap/chase and updated risk) before any buy action.
- **PAPER_POSITION_MONITOR**: there is a positive PAPER Alpaca position;
  this is distinct from a separately held real position.
- **EXIT_WARNING**: a PAPER position has two completed closes below SMA20
  or reaches the verified PDUFA minus three-day boundary.
- **HOLD_REVIEW**: no programmed SMA20 or deadline exit warning yet.
- **DATA_BLOCKED**: stale/invalid bars, absent named watchlist or
  unavailable market API. Research scores are not trusted.

Loss prevention: entry setup requires 10 completed sessions after second
financing, base width <=3 ATR over 10 sessions, breakout close at least
0.1 ATR above prior 10-session high, RVOL>=1.5x prior 20-day volume,
prior-20-day dollar liquidity >=$250k, provisional risk <=8% of the close,
and 7-180 days remaining until disclosed PDUFA date. Preview score uses
the experimental trend/volume/breakout/risk/timing 25/20/20/20/15 rubric.

Without an actual position entry date the monitor **does not invent** a
position-specific 2x ATR trailing stop or a realized exit profit. The
backtest's exit logic remains separate. Negative FDA developments require
a current sourced news feed; they are not automatically detected here.
The requested $300M-$10B cap gate remains OFF.

## Manual research run

    python scripts/alpaca_gem_daily_monitor.py --watchlist 'GEM DAILY MONITOR' --feed iex --output output/gem_alpaca_daily.json

Run only with securely provided paper credentials and an existing named
watchlist. A scheduled report is not equivalent to a mobile push alert;
the current implementation publishes GitHub Actions summaries/artifacts.
No notification channel is claimed until one is configured and tested.
