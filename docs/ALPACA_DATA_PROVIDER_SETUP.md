# Alpaca GEM / GEM JR market-data provider — activation

This is a **paper-only, read-only technical-data integration**. It does not
place orders, change GEM/JR clinical gates, or turn research scores into
verified investment advice.

## Provider and feed

- Default: official Alpaca daily historical `feed=sip` (consolidated US
  exchanges), `timeframe=1Day`, `adjustment=split`. For after-close
  historical queries, Alpaca documentation says SIP bars older than 15 minutes
  can be requested without a real-time SIP subscription. Account-specific
  entitlements still determine whether the actual request succeeds.
- Manual dashboard alternative: `feed=iex`. This has ONLY IEX exchange
  prices/volume, so its RVOL CANNOT be treated as a consolidated green BUY.
- We request only completed daily bars after 5 PM Eastern, about 260 calendar
  days of history. The last 50+ sessions support SMA20, SMA50, ATR14, RSI14,
  20-session relative volume, 10-session base, $ volume, and preliminary
  stop/risk/entry score. Missing/late bars fail closed.
- Technical scores are **provisional**, and Phase3 + two distinct completed
  post-Phase3 financings + the publicly known PDUFA event are separately
  checked in `data/post_phase3_historical_trade_events.csv` using the
  existing strict `validate_event` function. This CSV currently contains
  headers only, so **verified ENTRY is blocked for every ticker**.
- STAY / EXIT WARNINGS reflect positive **Alpaca paper** positions only.
  Outside-broker positions cannot be inferred. The active 2 ATR trailing stop
  is NOT calculated from a real fill unless a dated position ledger exists;
  the preliminary stop is a current-chart support estimate, not an order.

## To activate manual chart data in the deployed Streamlit dashboard

In **Streamlit Community Cloud > app Settings > Secrets**, add paper-only
credentials (if not already present):

```toml
ALPACA_API_KEY = "YOUR_ALPACA_PAPER_KEY"
ALPACA_SECRET_KEY = "YOUR_ALPACA_PAPER_SECRET"
ALPACA_PAPER = true
```

Never commit secrets or paste them in GitHub source, a chat, or a public issue.
When this feature is deployed, open **GEM** or **GEM JR**, expand
**ALPACA DATA & ENTRY / STAY / EXIT**, select a ticker and click
**REFRESH ALPACA SIGNAL**. It fetches real daily market data on demand.

## To activate scheduled coverage of every active GEM/JR ticker

Separately, add **GitHub repository > Settings > Secrets and variables >
Actions > Repository secrets**:
`ALPACA_API_KEY` and `ALPACA_SECRET_KEY`, both paper keys.

The `Alpaca GEM / GEM JR EOD Signals` workflow runs `01:00 UTC`
Tuesday–Saturday (US Monday–Friday after the close), with optional manual
dispatch. The workflow pulls **all active stage ticker symbols directly from
`data/gem_stage_membership.json`** and writes a JSON report plus GitHub
Actions job summary. No separate Alpaca watchlist is needed.

GitHub Actions secrets and Streamlit Secrets are **two different locations**.
The scheduled scanner intentionally fails rather than reporting operational
success if GitHub secrets are missing or market API calls fail.

The report is stored as a GitHub Actions artifact for 30 days. It does **not**
send phone/email notifications automatically. It is NOT written to a
publicly accessible repository file and contains no brokerage order requests.

## Before treating BUY / SELL labels as recommendations

1. Confirm Alpaca API connection and historical SIP entitlements from both
   the dashboard and scheduled runner.
2. Fill original SEC-funded disclosure dates, dated Phase 3 efficacy/safety
   results, original PDUFA dates and any early FDA action. Fix ambiguity per
   exact clinical program.
3. Load verified long-window historical adjusted OHLCV into the **separate**
   GEM backtest and validate signals on unseen years/stocks.
4. Check trade entry at NEXT opening price, account position history and
   live market fills. Do not equate EOD entry preview with an executed BUY.
5. Only then consider making alerts actionable. No unattended brokerage
   execution is provided here.

Docs: https://docs.alpaca.markets/us/reference/stockbarsingle-1 and
https://docs.alpaca.markets/us/docs/market-data-faq .
