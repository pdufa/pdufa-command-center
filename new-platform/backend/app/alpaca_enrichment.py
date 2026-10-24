"""Read-only Alpaca IEX adapter for shared Pipeline/GEM market enrichment.

No trading API endpoint is referenced. Credentials remain in environment variables.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

SYMBOL = re.compile(r"^[A-Z][A-Z0-9.-]{0,14}$")
DATA_HOST = "https://data.alpaca.markets"
MAX_SYMBOLS = 25


class MarketDataError(RuntimeError):
    pass


def _credentials() -> tuple[str, str]:
    key = os.getenv("APCA_API_KEY_ID") or os.getenv("ALPACA_API_KEY")
    secret = os.getenv("APCA_API_SECRET_KEY") or os.getenv("ALPACA_SECRET_KEY")
    if not key or not secret:
        raise MarketDataError("Alpaca market-data credentials are not configured")
    return key, secret


def _get(path: str, params: dict[str, str]) -> dict:
    key, secret = _credentials()
    req = Request(
        DATA_HOST + path + "?" + urlencode({**params, "feed": "iex"}),
        headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret,
                 "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=12) as response:
            return json.load(response)
    except HTTPError as exc:
        raise MarketDataError(f"Alpaca data request failed (HTTP {exc.code})") from None
    except (URLError, TimeoutError, ValueError) as exc:
        raise MarketDataError("Alpaca data request unavailable or malformed") from None


def latest_daily_bars(symbols: list[str]) -> dict:
    """Read-only IEX latest daily bars; missing symbols remain explicitly missing."""
    normalized = list(dict.fromkeys(s.strip().upper() for s in symbols))
    if not normalized or len(normalized) > MAX_SYMBOLS or any(not SYMBOL.fullmatch(s) for s in normalized):
        raise ValueError("Provide 1–25 valid ticker symbols")
    data = _get("/v2/stocks/bars/latest", {"symbols": ",".join(normalized)})
    bars = data.get("bars") or {}
    retrieved_at = datetime.now(timezone.utc).isoformat()
    return {
        symbol: {
            "status": "retrieved" if isinstance(bars.get(symbol), dict) else "missing",
            "bar": bars.get(symbol) if isinstance(bars.get(symbol), dict) else None,
            "feed": "iex",
            "source": "Alpaca Market Data",
            "source_url": "https://docs.alpaca.markets/us/docs/market-data-faq",
            "retrieved_at": retrieved_at,
            "scope": "IEX exchange only; not consolidated US market volume",
        }
        for symbol in normalized
    }


def daily_history(symbol: str, days: int = 120) -> dict:
    symbol = symbol.strip().upper()
    if not SYMBOL.fullmatch(symbol) or not 2 <= days <= 365:
        raise ValueError("Invalid symbol or history window")
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    data = _get(
        f"/v2/stocks/{symbol}/bars",
        {"timeframe": "1Day", "start": start.isoformat(),
         "end": end.isoformat(), "limit": "1000"},
    )
    if data.get("next_page_token"):
        raise MarketDataError("Historical bars were truncated; pagination required")
    return {"symbol": symbol, "bars": data.get("bars", []),
            "feed": "iex", "retrieved_at": end.isoformat(),
            "status": "retrieved" if data.get("bars") else "missing",
            "scope": "IEX exchange only"}
