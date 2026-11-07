#!/usr/bin/env python3
"""Secondary dated market-cap source for P3 POST-DATA's *missing* primary caps.

Read-only Stock Analysis market-cap pages. A quoted as-of date is a *source
observation date*, NOT a timestamp-verified Nasdaq exchange quote. Values are
rounded by the publisher (e.g. $2.41 billion), never treated as penny-exact.
Never silently substitute a fallback for a confirmed out-of-range primary cap.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

SOURCE = "https://stockanalysis.com/stocks/{ticker}/market-cap/"
MAX_AGE = timedelta(days=4)
MAX_BYTES = 500_000
TITLE_TICKER = re.compile(r"\(([A-Z][A-Z0-9.]{0,9})\)\s+Market Cap\s+&\s+Net Worth\Z")
DATED_CAP = re.compile(
    r"\bhas a market cap or net worth of\s+\$\s*([\d,]+(?:\.\d+)?)"
    r"\s+(million|billion)\s+as of\s+([A-Za-z]+\s+\d{1,2},\s+\d{4})\.",
    re.I,
)


class BackupCapError(ValueError):
    pass


def parse_source(html: str, ticker: str, as_of: date, *, url: str | None = None):
    """Exact-symbol, explicit publisher cap + as-of + strict freshness gate."""
    if not re.fullmatch(r"[A-Z][A-Z0-9.]{0,9}", ticker):
        raise BackupCapError("INVALID_TICKER")
    expected = SOURCE.format(ticker=ticker.lower())
    if url is not None and url != expected:
        raise BackupCapError("SOURCE_REDIRECT_OR_TICKER_MISMATCH")
    if not isinstance(html, str) or not html.strip() or len(html.encode("utf-8")) > MAX_BYTES:
        raise BackupCapError("UNBOUNDED_OR_EMPTY_HTML")
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    match = TITLE_TICKER.search(title)
    if not match or match.group(1) != ticker:
        raise BackupCapError("PAGE_TITLE_SYMBOL_MISMATCH")
    h1 = soup.find("h1")
    if not h1 or not h1.get_text(" ", strip=True).endswith(" Market Cap"):
        raise BackupCapError("MARKET_CAP_HEADING_MISSING")
    headline = h1.get_text(" ", strip=True)[:-len(" Market Cap")].strip()
    if not headline or headline.casefold() not in title.casefold():
        raise BackupCapError("ISSUER_NAME_MISMATCH")
    matches = []
    for p in soup.find_all("p"):
        m = DATED_CAP.search(p.get_text(" ", strip=True))
        if m:
            matches.append(m)
    if len(matches) != 1:
        raise BackupCapError("NO_UNIQUE_DATED_MARKET_CAP")
    m = matches[0]
    try:
        amount = Decimal(m.group(1).replace(",", ""))
        factor = Decimal("1000000") if m.group(2).lower()=="million" else Decimal("1000000000")
        value = int((amount*factor).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        observed = datetime.strptime(m.group(3), "%B %d, %Y").date()
    except (InvalidOperation, ValueError) as exc:
        raise BackupCapError("INVALID_DATED_CAP_VALUE") from exc
    if not 300_000_000 <= value <= 10_000_000_000:
        raise BackupCapError("MARKET_CAP_OUTSIDE_300M_TO_10B")
    if observed > as_of or as_of - observed > MAX_AGE:
        raise BackupCapError("SOURCE_CAP_DATE_TOO_OLD_OR_FUTURE")
    return (value, observed.isoformat(), expected)


def fetch_source(ticker: str, cutoff: date, *, fetcher=requests.get):
    url = SOURCE.format(ticker=ticker.lower())
    response = fetcher(url, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                      "Chrome/131.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml",
    }, timeout=18, allow_redirects=False)
    if response.status_code != 200:
        raise BackupCapError("HTTP_NOT_200")
    content_type = response.headers.get("content-type", "").lower()
    if "text/html" not in content_type:
        raise BackupCapError("NOT_HTML")
    if len(response.content) > MAX_BYTES:
        raise BackupCapError("HTML_TOO_LARGE")
    return parse_source(response.text, ticker, cutoff, url=response.url)


def lookup_missing_primary(tickers: set[str], cutoff: date, *, fetch=fetch_source):
    """One request per issuer; one issuer can map to multiple P3 trial rows."""
    resolved, failures = {}, {}
    for ticker in sorted(tickers):
        try:
            resolved[ticker] = fetch(ticker, cutoff)
        except (requests.RequestException, BackupCapError, ValueError,
                OSError, UnicodeError) as exc:
            failures[ticker] = (str(exc) if isinstance(exc, BackupCapError)
                                else "SECONDARY_SOURCE_UNAVAILABLE_" + type(exc).__name__)
    return resolved, failures
