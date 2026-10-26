"""Dated exchange listing exclusions; never synthesize a current market cap."""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlparse


def validated_listing_exclusions(ledger, registry, now):
    """Require an exact issuer/CIK and a dated, effective Nasdaq corporate action.

    Historical trials remain in the ledger. An exclusion only removes a retired
    listing from current quote coverage and can never make a trade eligible.
    """
    identities = {}
    for row in registry or []:
        ticker = str(row.get("ticker") or "").strip().upper()
        identities.setdefault(ticker, []).append(row)
    found = {}
    records = ledger.get("records", []) if isinstance(ledger, dict) else []
    for row in records:
        try:
            ticker = row["ticker"]
            issuer = identities.get(ticker, [])
            source = urlparse(row["source_url"])
            published = date.fromisoformat(row["source_date"])
            effective = date.fromisoformat(row["effective_date"])
            checked = datetime.fromisoformat(row["checked_at"].replace("Z", "+00:00"))
            # A completed merger suspends the entire former security; a symbol
            # change retires only the predecessor ticker. Neither can be used
            # to qualify the successor or rewrite historical program identity.
            status = row["status"]
            if status == "SUSPENDED — MERGER CLOSED":
                action_valid = not row.get("replacement_ticker")
            elif status == "SYMBOL CHANGED — OLD TICKER RETIRED":
                successor = row.get("replacement_ticker", "")
                action_valid = (isinstance(successor, str) and
                                bool(re.fullmatch(r"[A-Z0-9.-]{1,15}", successor))
                                and successor != ticker)
            else:
                action_valid = False
            if not (len(issuer) == 1 and re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker)
                    and row["company"].strip().casefold() == issuer[0].get("company", "").strip().casefold()
                    and re.fullmatch(r"\d{10}", row["cik10"])
                    and row["cik10"] == issuer[0].get("cik10")
                    and action_valid
                    and source.scheme == "https" and source.netloc == "www.nasdaqtrader.com"
                    and source.path == "/TraderNews.aspx"
                    and re.fullmatch(r"id=ECA\d{4}-\d+", source.query)
                    and not source.fragment
                    and published <= effective <= now.date()
                    and checked.tzinfo is not None
                    and published <= checked.date() and checked <= now):
                continue
            found[ticker] = None if ticker in found else row
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return {ticker: row for ticker, row in found.items() if row is not None}


def resolved_pipeline_status(state, caps, exclusions):
    """Resolve only a complete collector's fully accounted-for quote warning.

    Preserve its timestamp and original status; no network check is implied.
    Unrelated errors, missing quotes, incomplete scans and ambiguous counts
    always retain the original warning.
    """
    original = state.get("status")
    missing = [r for r in caps if r.get("market_cap_status") not in {"VERIFIED", "NOT_LISTED"}]
    if (original == "COMPLETE WITH WARNINGS" and state.get("complete") is True
            and not state.get("errors") and missing
            and state.get("market_cap_source_unavailable") == len(missing)
            and len({r.get("ticker") for r in missing}) == len(missing)
            and all(r.get("ticker") in exclusions for r in missing)):
        return "COMPLETE", len(missing)
    return original, 0
