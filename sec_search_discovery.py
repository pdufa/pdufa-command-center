"""Search-engine SEC-document discovery links for researcher review.

Yahoo, Bing and Google only suggest URLs. Results and snippets are NEVER proof
of financing closure, a second financing, or GEM entry. Verified evidence
must be fetched directly from SEC using the exact issuer CIK and claim date.
"""
from __future__ import annotations

import re
from urllib.parse import quote


FORMS = {"8-K", "10-Q", "10-K", "EX-99.1", "EX-10"}
ENGINES = {
    "Bing SEC": "https://www.bing.com/search?q=",
    "Yahoo SEC": "https://search.yahoo.com/search?p=",
    "Google SEC": "https://www.google.com/search?q=",
    "Yahoo Finance release": "https://search.yahoo.com/search?p=",
}


def financing_discovery_links(ticker, company, cik, form="8-K"):
    """Create external search URLs; does not access results or verify anything.

    Limit sources to a company-matched SEC archive query or an explicitly
    secondary Yahoo Finance press-release query. No search-derived claim or
    SEC evidence state is accepted or generated.
    """
    symbol = str(ticker or "").strip().upper()
    issuer = str(company or "").strip()
    issuer_cik = str(cik or "").strip()
    if not re.fullmatch(r"[A-Z0-9.-]{1,10}", symbol):
        raise ValueError("Enter a valid issuer ticker")
    if (not 3 <= len(issuer) <= 140
            or any(ord(ch) < 32 for ch in issuer)):
        raise ValueError("Enter an issuer name from the company registry")
    if not issuer_cik.isascii() or not issuer_cik.isdecimal() or not 1 <= len(issuer_cik) <= 10 or int(issuer_cik) == 0:
        raise ValueError("A valid exact issuer SEC CIK is required")
    if form not in FORMS:
        raise ValueError("Choose an indexed filing type")
    scoped = "site:sec.gov/Archives/edgar/data/" + str(int(issuer_cik)) + "/"
    sec_query = (
        f'{scoped} "{issuer}" "{form}" '
        '("closed" OR "completed" OR "consummated") '
        '("offering" OR "financing" OR "proceeds")'
    )
    # Yahoo Finance is useful for finding *reported* closing dates to probe
    # in EDGAR; a news release is never passed as an SEC proof document.
    yahoo_news_query = (
        f'site:finance.yahoo.com "{issuer}" "{symbol}" '
        '"announces closing" "offering"'
    )
    return {
        "Bing SEC": ENGINES["Bing SEC"] + quote(sec_query, safe=""),
        "Yahoo SEC": ENGINES["Yahoo SEC"] + quote(sec_query, safe=""),
        "Google SEC": ENGINES["Google SEC"] + quote(sec_query, safe=""),
        "Yahoo Finance release": ENGINES["Yahoo Finance release"] + quote(yahoo_news_query, safe=""),
    }
