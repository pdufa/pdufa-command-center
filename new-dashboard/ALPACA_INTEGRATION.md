# Alpaca in the new PDUFA Command Center

This is an **isolated integration foundation**, not a deployed migration.
Intended architecture: **React/Next.js UI → authenticated FastAPI → Alpaca**.
GitHub Actions continues the clinical/SEC/PDUFA surveys and nightly
PIPELINE → GEM JR → GEM scan chain. Alpaca supplies market inputs only.

## What is implemented in this foundation

- Server-side read-only stock quotes and historical daily OHLCV bars.
- Alpaca paper-credential connection test.
- SMA20, SMA50, RSI14, ATR14 and MACD(12,26,9) derived from Alpaca daily bars.
- Per-indicator availability counts, explicit missing values/reasons, as-of date and feed provenance.
- No order submission, live brokerage, auto trading or fabricated entry/exit scores.
- An isolated server-only Next.js adapter (NOT a public Next route).

## Configuration

On the **FastAPI backend**, store these server environment variables securely:

    ALPACA_API_KEY=<paper-key>
    ALPACA_SECRET_KEY=<paper-secret>
    ALPACA_PAPER=true
    ALPACA_FEED=iex
    DASHBOARD_API_TOKEN=<long-random-server-to-server-token>

On the **Next.js server** (never browser-exposed variables):

    ALPACA_BACKEND_URL=https://<python-api-host>
    DASHBOARD_API_TOKEN=<matching-token>

Start FastAPI locally from `new-dashboard/backend` with:
`pip install -r requirements.txt && uvicorn main:app --reload`

The FastAPI token protects only the server-to-server boundary: ensure the
Next.js app's user authentication/authorization guards any user-facing
pages or server actions that invoke `alpacaRequest`. Do **not** build
an unauthenticated public proxy to these endpoints.

## Endpoints

Authenticated with the `x-dashboard-token` HTTP header:

- `GET /api/alpaca/status` — configuration present, **not** proof of connectivity
- `GET /api/alpaca/test` — live SPY market-data diagnostic
- `GET /api/alpaca/quotes?symbols=OCGN,SPY` — up to 30 symbols
- `GET /api/alpaca/bars?symbol=OCGN&days=365` — daily bars
- `GET /api/alpaca/technicals?symbol=OCGN` — indicators and gaps

## Data quality and scoring

Alpaca's free IEX feed is **not** a market-wide consolidated tape. Its
volumes cannot be treated as market-wide RVOL or full-market VWAP, and
low-liquidity biotech symbols may be sparsely represented. Even on SIP,
this foundation does not claim to compute comparable intraday VWAP or
session-adjusted RVOL. Those score components are explicitly missing
until their real calculations are implemented and backtested.

The PIPELINE → GEM JR → GEM progression, clinical evidence, financing,
dilution, SEC and PDUFA decision dates remain from independently
verified data sources. GEM Entry/Exit scoring should consume Alpaca
values only after coverage, feed and as-of checks; the score engine is
not wired to these endpoints in this foundation.

## Deployment blocker

The existing Vercel project `pdufa-new-dashboard` was found, but
access to its project details/deployments returned HTTP 403 during
this work. These migration files are not automatically deployed.
The existing Streamlit app remains unchanged.
