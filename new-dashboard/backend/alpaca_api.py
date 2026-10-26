"""Server-side, read-only Alpaca integration for the Next.js + FastAPI migration.

Never send Alpaca credentials to the browser. Live order submission is absent.
Daily IEX bars are single-venue observations, NOT consolidated volume.
"""
import os
import re
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Header, HTTPException, Query

router = APIRouter(prefix="/api/alpaca", tags=["alpaca-market-data"])
_SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,9}$")


def _authorize(x_dashboard_token: str | None):
    expected = os.environ.get("DASHBOARD_API_TOKEN", "")
    if not expected:
        raise HTTPException(503, "Backend API authentication is not configured.")
    if not x_dashboard_token or not secrets.compare_digest(x_dashboard_token, expected):
        raise HTTPException(401, "Unauthorized.")


def _config():
    if os.environ.get("ALPACA_PAPER", "true").strip().lower() != "true":
        raise HTTPException(503, "Alpaca access is restricted to paper credentials.")
    key = os.environ.get("ALPACA_API_KEY", "").strip()
    secret = os.environ.get("ALPACA_SECRET_KEY", "").strip()
    if not key or not secret or key.startswith("YOUR_") or secret.startswith("YOUR_"):
        raise HTTPException(503, "Alpaca paper keys are not configured.")
    feed = os.environ.get("ALPACA_FEED", "iex").strip().lower()
    if feed not in ("iex", "sip"):
        raise HTTPException(503, "ALPACA_FEED must be iex or sip.")
    return key, secret, feed


def _client(key, secret):
    from alpaca.data.historical import StockHistoricalDataClient
    return StockHistoricalDataClient(api_key=key, secret_key=secret)


def _feed_enum(feed):
    from alpaca.data.enums import DataFeed
    return DataFeed.SIP if feed == "sip" else DataFeed.IEX


def _safe_error(exc):
    code = str(getattr(exc, "status_code", ""))
    if code in ("401", "403"):
        return HTTPException(502, "Alpaca authentication or market-data entitlement rejected.")
    if code == "429":
        return HTTPException(503, "Alpaca rate limit reached.")
    return HTTPException(502, "Alpaca market-data request failed.")


def _symbol(value):
    symbol = value.strip().upper()
    if not _SYMBOL.fullmatch(symbol):
        raise HTTPException(422, "Invalid equity ticker symbol.")
    return symbol


def _provenance(feed):
    return {
        "provider": "Alpaca",
        "feed": feed.upper(),
        "is_consolidated": feed == "sip",
        "limitations": (
            "IEX-only; not whole-market volume, RVOL, or consolidated VWAP."
            if feed == "iex" else
            "SIP entitlement must be verified; data coverage and session cutoff still apply."
        ),
    }


def _iso(timestamp):
    return timestamp.isoformat() if timestamp else None


def _bar_dict(bar):
    return {
        "time": _iso(bar.timestamp),
        "open": float(bar.open),
        "high": float(bar.high),
        "low": float(bar.low),
        "close": float(bar.close),
        "volume": int(bar.volume),
    }


def _bars_data(client, symbol, feed, lookback_days):
    from alpaca.data.requests import StockBarsRequest
    from alpaca.data.timeframe import TimeFrame
    end = datetime.now(timezone.utc)
    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        timeframe=TimeFrame.Day,
        start=end - timedelta(days=lookback_days),
        end=end,
        limit=1000,
        feed=_feed_enum(feed),
    )
    response = client.get_stock_bars(request)
    rows = (getattr(response, "data", None) or {}).get(symbol, [])
    return sorted((_bar_dict(row) for row in rows), key=lambda row: row["time"])


def _ema(values, period):
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    alpha = 2 / (period + 1)
    for sample in values[period:]:
        value = alpha * sample + (1 - alpha) * value
    return value


def _rsi14(closes):
    period = 14
    if len(closes) <= period:
        return None
    deltas = [b - a for a, b in zip(closes, closes[1:])]
    gains = [max(d, 0) for d in deltas]
    losses = [max(-d, 0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    return 100 - 100 / (1 + avg_gain / avg_loss)


def _atr14(rows):
    period = 14
    if len(rows) < period + 1:
        return None
    ranges = [
        max(row["high"] - row["low"],
            abs(row["high"] - prior["close"]),
            abs(row["low"] - prior["close"]))
        for prior, row in zip(rows, rows[1:])
    ]
    atr = sum(ranges[:period]) / period
    for value in ranges[period:]:
        atr = (atr * (period - 1) + value) / period
    return atr


def _macd(closes):
    if len(closes) < 35:
        return None
    ema12 = sum(closes[:12]) / 12
    ema26 = sum(closes[:26]) / 26
    k12, k26 = 2 / 13, 2 / 27
    # Advance the fast EMA through the extra 14 observations first.
    for value in closes[12:26]:
        ema12 = k12 * value + (1 - k12) * ema12
    macd_series = [ema12 - ema26]
    for value in closes[26:]:
        ema12 = k12 * value + (1 - k12) * ema12
        ema26 = k26 * value + (1 - k26) * ema26
        macd_series.append(ema12 - ema26)
    signal = _ema(macd_series, 9)
    if signal is None:
        return None
    return {"line": macd_series[-1], "signal": signal,
            "histogram": macd_series[-1] - signal}


def _indicators(rows, feed):
    closes = [row["close"] for row in rows]
    macd = _macd(closes)
    metrics = {
        "sma20": sum(closes[-20:]) / 20 if len(closes) >= 20 else None,
        "sma50": sum(closes[-50:]) / 50 if len(closes) >= 50 else None,
        "rsi14": _rsi14(closes),
        "atr14": _atr14(rows),
        "macd_12_26_9": macd,
        # Do not fabricate intraday VWAP or comparable RVOL from daily IEX bars.
        "vwap_session": None,
        "rvol20": None,
    }
    complete = {name: value is not None for name, value in metrics.items()}
    return {
        "values": metrics,
        "available": complete,
        "available_count": sum(complete.values()),
        "possible_count": len(complete),
        "blocking_reasons": [
            "Intraday session VWAP is not calculated from daily bars.",
            "Comparable whole-market RVOL20 requires consolidated, completed-session volume and a separate calculation.",
        ],
        "sessions_returned": len(rows),
        "source": _provenance(feed),
        "note": "These are descriptive inputs, not validated GEM entry/exit or trading scores.",
    }


@router.get("/status")
def status(x_dashboard_token: str | None = Header(default=None)):
    _authorize(x_dashboard_token)
    _, _, feed = _config()
    return {"configured": True, "tested_live": False, "paper_only": True,
            "source": _provenance(feed)}


@router.get("/test")
def connection_test(x_dashboard_token: str | None = Header(default=None)):
    _authorize(x_dashboard_token)
    key, secret, feed = _config()
    try:
        from alpaca.data.requests import StockLatestBarRequest
        result = _client(key, secret).get_stock_latest_bar(
            StockLatestBarRequest(symbol_or_symbols="SPY", feed=_feed_enum(feed))
        )
        if not result or not result.get("SPY"):
            raise HTTPException(502, "Alpaca returned no SPY latest-minute bar.")
        return {"connected": True, "symbol": "SPY", "source": _provenance(feed)}
    except HTTPException:
        raise
    except Exception as exc:
        raise _safe_error(exc) from None


@router.get("/quotes")
def quotes(symbols: str = Query(..., min_length=1, max_length=330),
           x_dashboard_token: str | None = Header(default=None)):
    _authorize(x_dashboard_token)
    tickers = [_symbol(s) for s in symbols.split(",")]
    if not 1 <= len(tickers) <= 30 or len(set(tickers)) != len(tickers):
        raise HTTPException(422, "Supply 1–30 unique symbols.")
    key, secret, feed = _config()
    try:
        from alpaca.data.requests import StockLatestQuoteRequest
        result = _client(key, secret).get_stock_latest_quote(
            StockLatestQuoteRequest(symbol_or_symbols=tickers, feed=_feed_enum(feed))
        )
        data = {}
        for symbol in tickers:
            quote = result.get(symbol) if result else None
            if quote:
                data[symbol] = {
                    "bid": float(quote.bid_price) if quote.bid_price is not None else None,
                    "ask": float(quote.ask_price) if quote.ask_price is not None else None,
                    "time": _iso(quote.timestamp),
                }
        return {"quotes": data, "missing": [s for s in tickers if s not in data],
                "source": _provenance(feed)}
    except Exception as exc:
        raise _safe_error(exc) from None


@router.get("/bars")
def bars(symbol: str, days: int = Query(365, ge=30, le=730),
         x_dashboard_token: str | None = Header(default=None)):
    _authorize(x_dashboard_token)
    ticker = _symbol(symbol)
    key, secret, feed = _config()
    try:
        rows = _bars_data(_client(key, secret), ticker, feed, days)
        return {"symbol": ticker, "timeframe": "1Day", "bars": rows,
                "source": _provenance(feed)}
    except Exception as exc:
        raise _safe_error(exc) from None


@router.get("/technicals")
def technicals(symbol: str, x_dashboard_token: str | None = Header(default=None)):
    _authorize(x_dashboard_token)
    ticker = _symbol(symbol)
    key, secret, feed = _config()
    try:
        rows = _bars_data(_client(key, secret), ticker, feed, 365)
        return {"symbol": ticker, "as_of": rows[-1]["time"] if rows else None,
                **_indicators(rows, feed)}
    except Exception as exc:
        raise _safe_error(exc) from None
