"""Read-only Alpaca historical market data for interactive research charts.

Uses ONLY data.alpaca.markets, never brokerage/order endpoints.
No fallback to TradingView, Yahoo or sample candles. Credentials remain on Render.
All source/coverage errors are explicitly returned to the authenticated client.
"""
from __future__ import annotations

import json
import logging
import math
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

LOG = logging.getLogger(__name__)
ALPACA_HOST = "https://data.alpaca.markets"
SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,12}$")
TZ = ZoneInfo("America/New_York")
_CACHE: dict[str, tuple[float, dict]] = {}
_LOCK = threading.RLock()
VALID_RANGES = {"1M": 45, "3M": 115, "6M": 215, "1Y": 410, "ALL": 800}
MAX_BYTES = 1_700_000
MAX_CACHE_ENTRIES = 80  # The free Render worker has a 512 MiB memory ceiling.
SUCCESS_CACHE_SECONDS = 900
RETRY_CACHE_SECONDS = 60
NO_HISTORY_MESSAGE = (
    "Alpaca returned no daily market bars for this ticker in the requested period. "
    "It may have been acquired, delisted, or lack coverage on the selected feed. "
    "No current price or trading signal is available."
)


def _credentials() -> tuple[str, str] | None:
    key = (os.environ.get("ALPACA_API_KEY") or os.environ.get("APCA_API_KEY_ID") or "").strip()
    secret = (os.environ.get("ALPACA_SECRET_KEY") or os.environ.get("APCA_API_SECRET_KEY") or "").strip()
    if not key or not secret or key.startswith("YOUR_") or secret.startswith("YOUR_"):
        return None
    return key, secret


def _feed() -> str:
    option = (os.environ.get("ALPACA_DATA_FEED") or "iex").strip().lower()
    # Do not quietly switch to the unauthorised paid consolidated feed.
    return option if option in ("iex", "sip") else "iex"


def _out(ticker: str, feed: str, status: str, bars=None, message: str = "") -> dict:
    return {
        "provider": "ALPACA", "ticker": ticker, "feed": feed.upper(),
        "coverage": ("IEX ONLY — single exchange, NOT consolidated"
                     if feed == "iex" else "SIP consolidated — requires account entitlement"),
        "timeframe": "1Day", "adjustment": "raw",
        "status": status, "bars": bars if bars is not None else [],
        "asOf": (bars[-1]["date"] if bars else None),
        "message": message, "researchOnly": True, "orderExecutionEnabled": False,
        "source": "https://docs.alpaca.markets/us/reference/stockbarsingle-1",
    }


def _parse_bars(raw: dict, ticker: str, today: datetime) -> list[dict]:
    supplied = raw.get("bars")
    if not isinstance(supplied, list):
        raise ValueError("Alpaca response lacks valid bar array")
    seen: set[str] = set()
    collected = []
    exchange_now = today.astimezone(TZ)
    for b in supplied:
        if not isinstance(b, dict):
            continue
        timestamp = b.get("t")
        if not isinstance(timestamp, str) or not re.match(r"^\d{4}-\d{2}-\d{2}T", timestamp):
            continue
        day = timestamp[:10]  # Alpaca 1Day bar timestamp is in UTC for its exchange session
        if day in seen or day > exchange_now.date().isoformat():
            continue
        if day == exchange_now.date().isoformat() and (
                exchange_now.weekday() > 4 or (exchange_now.hour, exchange_now.minute) < (16, 10)):
            # No incomplete daily bars while US session is open.
            continue
        try:
            o, h, l, c, v = (float(b.get(k)) for k in ("o", "h", "l", "c", "v"))
        except (ValueError, TypeError, OverflowError):
            continue
        if (not all(math.isfinite(x) for x in (o, h, l, c, v))
                or min(o, h, l, c) <= 0 or v < 0
                or h < max(o, l, c) or l > min(o, h, c)):
            continue
        seen.add(day)
        collected.append({"date": day, "open": o, "high": h,
                          "low": l, "close": c, "volume": int(v)})
    collected.sort(key=lambda r: r["date"])
    return collected[-650:]


def get_alpaca_bars(ticker: str, range_label: str = "1Y") -> dict:
    ticker = ticker.strip().upper()
    if not SYMBOL.fullmatch(ticker):
        return _out(ticker, "iex", "INVALID_SYMBOL", message="Invalid stock ticker")
    if range_label not in VALID_RANGES:
        return _out(ticker, _feed(), "INVALID_RANGE", message="Unsupported chart range")
    feed = _feed()
    credentials = _credentials()
    if credentials is None:
        return _out(ticker, feed, "NOT_CONFIGURED",
                    message="Set ALPACA_API_KEY and ALPACA_SECRET_KEY in Render backend environment variables. Do not paste API keys into chat.")
    now = datetime.now(timezone.utc)
    session_day = now.astimezone(TZ).date()
    # Use additional sessions to permit SMA50 and other warm-up indicators.
    start = session_day - timedelta(days=VALID_RANGES[range_label] + 95)
    cache_key = ticker + "|" + range_label + "|" + feed
    with _LOCK:
        cached = _CACHE.get(cache_key)
        if cached:
            ttl = (SUCCESS_CACHE_SECONDS if cached[1]["status"] in
                   {"OK", "NO_MARKET_HISTORY", "INSUFFICIENT_BARS"}
                   else RETRY_CACHE_SECONDS)
            if time.monotonic() - cached[0] < ttl:
                return cached[1]
    query = urlencode({
        "timeframe": "1Day", "start": start.isoformat(),
        "end": (session_day + timedelta(days=1)).isoformat(),
        "limit": 1000, "adjustment": "raw", "feed": feed,
        "sort": "asc",
    })
    url = ALPACA_HOST + "/v2/stocks/" + quote(ticker, safe="") + "/bars?" + query
    request = Request(url, headers={
        "APCA-API-KEY-ID": credentials[0],
        "APCA-API-SECRET-KEY": credentials[1],
        "Accept": "application/json",
        "User-Agent": "PDUFA-ReadOnly-Alpaca-Charts/1.0"
    })
    try:
        with urlopen(request, timeout=9) as response:
            blob = response.read(MAX_BYTES+1)
            if len(blob) > MAX_BYTES:
                return _out(ticker, feed, "SOURCE_TOO_LARGE", message="Alpaca response exceeded safe size limit")
        parsed = json.loads(blob)
        if not isinstance(parsed, dict) or "bars" not in parsed:
            result = _out(ticker, feed, "INVALID_SOURCE_RESPONSE",
                          message="Alpaca returned an unexpected market-data response; chart withheld.")
        elif parsed.get("next_page_token"):
            result = _out(ticker, feed, "INCOMPLETE_HISTORY",
                          message="Alpaca returned paged data; chart withheld to prevent truncation")
        elif parsed["bars"] is None or parsed["bars"] == []:
            # Alpaca may legitimately return bars:null for inactive or acquired tickers.
            # This does not mean the entire Alpaca feed is offline.
            result = _out(ticker, feed, "NO_MARKET_HISTORY", message=NO_HISTORY_MESSAGE)
        elif not isinstance(parsed["bars"], list):
            result = _out(ticker, feed, "INVALID_SOURCE_RESPONSE",
                          message="Alpaca returned invalid market-data bars; chart withheld.")
        else:
            candles = _parse_bars(parsed, ticker, now)
            if len(candles) < 21:
                result = _out(ticker, feed, "INSUFFICIENT_BARS",
                              message="Alpaca returned fewer than 21 verified daily sessions")
            else:
                result = _out(ticker, feed, "OK", candles)
    except HTTPError as exc:
        status = "ALPACA_AUTH_FAILED" if exc.code in (401, 403) else "RATE_LIMITED" if exc.code == 429 else "ALPACA_HTTP_ERROR"
        LOG.warning("ALPACA_CHART_UNAVAILABLE ticker=%s status=%s code=%d", ticker, status, exc.code)
        result = _out(ticker, feed, status, message="Alpaca denied or could not supply this chart. Verify backend credentials, market-data plan, and feed.")
    except (OSError, URLError, ValueError, TypeError, UnicodeError) as exc:
        LOG.warning("ALPACA_CHART_UNAVAILABLE ticker=%s error_type=%s", ticker, type(exc).__name__)
        result = _out(ticker, feed, "ALPACA_UNAVAILABLE",
                      message="Alpaca market-data source unavailable. No alternate-provider data displayed.")
    with _LOCK:
        _CACHE[cache_key] = (time.monotonic(), result)
        if len(_CACHE) > MAX_CACHE_ENTRIES:
            oldest = min(_CACHE, key=lambda key: _CACHE[key][0])
            _CACHE.pop(oldest, None)
    return result
