# GEM / GEM JR entry signal v1

The entry panel appears above each expanded Alpaca chart in GEM, GEM JR and WT.
It is independent of existing weighted research scores. No orders are submitted.
These starting thresholds have not been backtested or calibrated as probabilities.

## Conditions

- Exact source-linked positive Phase 3 and two independently verified funded post-readout closes.
- Current complete source evidence, a verified unresolved PDUFA date, no flagged new dilution, and more than 14 calendar days until PDUFA.
- At least 60 preceding completed exchange sessions plus the signal session, with split-adjusted consolidated SIP OHLC, volume and bar VWAP, extending before the second-financing anchor.
- The preceding 10-session high-low range is at most 3 times ATR14.
- The latest five-session low is at least the preceding five-session low.
- The completed signal close exceeds base high + 0.1 ATR, rounded up to the displayed price increment.
- Signal volume is at least 1.5 times the preceding 20-session mean.
- The close exceeds the financing-date bar-based anchored VWAP estimate.

ATR uses Wilder smoothing and excludes the signal session, as do base boundaries
and average volume. AVWAP is an estimate from bar VWAP weighted by bar volume;
it is not an exact reconstruction of every eligible underlying trade.

The next-session entry band is trigger through trigger + 0.5 ATR, rounded inward.
The initial stop is base low - 0.25 ATR, rounded down. Stops are not guaranteed fills.

## Light states

- **Green BUY:** all conditions pass, the next regular exchange session is open,
  a quote no older than 60 seconds holds the trigger at the bid, and its ask is
  inside the entry band. This is a rules-based signal, not guaranteed profit.
- **Amber READY NEXT SESSION:** the completed setup passes but the next session
  has not opened. There is no actionable green light outside regular hours.
- **Amber WAIT:** an eligibility or technical condition fails, or price is outside
  the band. A later price in the band is re-evaluated; no order is placed.
- **Gray UNAVAILABLE:** required evidence, credentials, calendar, history, or live
  quote cannot be verified. Failed requests remove a previously displayed green.

Historical calculations always request SIP explicitly, with the query end at
least 16 minutes in the past to support free historical access. The live quote
uses the already configured Alpaca feed (IEX by default), clearly labeled. IEX
volume is never compared with consolidated SIP volume. The exchange calendar
handles holidays and early closes. The browser refreshes every 30 seconds and
independently expires a green light with its quote or session.

API credentials remain on the backend. The authenticated endpoint resolves the
permanent Program ID on the server; another trial cannot borrow eligibility by
ticker. Existing Streamlit code, source data, scanners and schedules are untouched.
