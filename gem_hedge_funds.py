"""SEC 13F biotech-specialist long-holdings signals for GEM ranking.

This module never treats 13F data as real-time trading, beneficial ownership,
a complete hedge-fund universe, or a third GEM eligibility benchmark.
Only exact issuer-name and common-stock/CUSIP matches are used.
"""
from __future__ import annotations

import csv
import json
import math
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

SCHEMA = 1
DATA_FILE = "gem_hedge_fund_13f.json"
STATUS = "SOURCE-VERIFIED QUARTERLY 13F HOLDINGS"
REVIEW = "REVIEW — NO SOURCE-MATCHED RECENT 13F"
MAX_AGE = 200
COMPARABLE_QUARTER_GAP = (85, 98)


def day(raw):
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except (ValueError, TypeError):
        return None


def issuer_name(value):
    """Exact legal-name comparison after punctuation and common *suffixes* only."""
    tokens = re.findall(r"[A-Z0-9]+", str(value or "").upper())
    while tokens and tokens[-1] in {
        "INC", "INCORPORATED", "CORP", "CORPORATION", "LTD", "LIMITED",
        "PLC", "LLC", "CO", "COMPANY",
    }:
        tokens.pop()
    if tokens[:1] == ["THE"]:
        tokens.pop(0)
    return " ".join(tokens)


def tracked_issuers(root):
    """Avoid fuzzy issuer resolution and all ambiguous legal-name collisions."""
    p = Path(root) / "company_registry.csv"
    names, collisions = {}, set()
    try:
        with p.open(newline="", encoding="utf-8-sig") as fp:
            for row in csv.DictReader(fp):
                ticker = str(row.get("ticker") or "").upper().strip()
                cik = str(row.get("cik10") or "").strip()
                key = issuer_name(row.get("company"))
                if (not key or not re.fullmatch(r"[A-Z0-9.\-]{1,15}", ticker)
                        or not cik.isdigit() or len(cik) > 10):
                    continue
                if key in names and names[key] != ticker:
                    collisions.add(key)
                names[key] = ticker
    except (OSError, ValueError, csv.Error, UnicodeError):
        return {}
    return {k: v for k, v in names.items() if k not in collisions}


def load_signal_records(root, *, as_of=None):
    """Read a dated publisher output; never rescore future or corrupted reports."""
    p = Path(root) / DATA_FILE
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if (not isinstance(data, dict) or data.get("schema_version") != SCHEMA
                or data.get("source") != "SEC_13F_XML_INFO_TABLE"
                or not isinstance(data.get("records"), list)):
            return {}
        observed = day(as_of)
        checked = day(data.get("as_of_pacific"))
        if not observed or not checked or checked > observed or (observed - checked).days > 50:
            return {}
        matches, duplicates = {}, set()
        for item in data["records"]:
            if not isinstance(item, dict):
                continue
            ticker = str(item.get("ticker") or "").upper()
            if not re.fullmatch(r"[A-Z0-9.\-]{1,15}", ticker):
                continue
            if ticker in matches:
                duplicates.add(ticker)
            matches[ticker] = item
        return {k: v for k, v in matches.items() if k not in duplicates}
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        return {}


def assess_signal(ticker, record, *, as_of):
    """Manager evidence changes ranking points, NEVER the entry benchmarks."""
    out = {
        "Hedge-fund signal": REVIEW,
        "Hedge-fund accumulation /10": 0,
        "Hedge-fund managers holding": None,
        "Hedge-fund managers adding": None,
        "Hedge-fund managers reducing": None,
        "Hedge-fund managers new": None,
        "Hedge-fund managers no longer reported": None,
        "Hedge-fund quarter end": "",
        "Hedge-fund filed as of": "",
        "Hedge-fund source links": "",
        "Hedge-fund position details": "",
        "Hedge-fund limitation": (
            "No currently matched 13F information table from monitored funds; "
            "absence is not proof of zero institutional ownership"
        ),
    }
    if not isinstance(record, dict) or record.get("ticker") != ticker:
        return out
    today = day(as_of)
    quarter = day(record.get("quarter_end"))
    if not today or not quarter or not 0 <= (today - quarter).days <= MAX_AGE:
        return out
    managers = record.get("managers")
    if not isinstance(managers, list) or not managers:
        return out
    good = []
    for m in managers:
        if not isinstance(m, dict):
            continue
        filing = day(m.get("filed"))
        period = day(m.get("quarter_end"))
        source = m.get("filing_url")
        manager_cik = str(m.get("manager_cik") or "")
        shares = m.get("shares")
        if (not filing or not period or period != quarter or filing > today
                or filing < period or not manager_cik.isdigit()
                or not isinstance(source, str) or not source.startswith(
                    "https://www.sec.gov/Archives/edgar/data/")
                or type(shares) is not int or shares < 0
                or not re.fullmatch(r"[A-Z0-9]{9}", str(m.get("cusip") or ""))):
            continue
        previous = m.get("prior_shares")
        if previous is not None and (type(previous) is not int or previous < 0):
            continue
        good.append(m)
    if not good:
        return out
    if len({m["manager_cik"] for m in good}) != len(good):
        return out

    holding = [m for m in good if m["shares"] > 0]
    added = [m for m in good if m["prior_shares"] is not None
             and m["shares"] > m["prior_shares"]]
    reduced = [m for m in good if m["prior_shares"] is not None
               and 0 < m["shares"] < m["prior_shares"]]
    new = [m for m in added if m["prior_shares"] == 0]
    no_longer = [m for m in good if m["prior_shares"] is not None
                 and m["prior_shares"] > 0 and m["shares"] == 0]
    score = min(4, len(holding)) + min(6, 3 * len(added))
    latest_file = max(day(m["filed"]) for m in good)
    details = [
        f"{m.get('manager_name', 'Investment manager')}: "
        f"{m['shares']:,} shares"
        + (f" vs {m['prior_shares']:,} prior" if m["prior_shares"] is not None else
           " (prior quarter not verified)")
        for m in sorted(good, key=lambda x: str(x.get("manager_name") or ""))
    ]
    links = sorted({m["filing_url"] for m in good})
    out.update({
        "Hedge-fund signal": STATUS,
        "Hedge-fund accumulation /10": score,
        "Hedge-fund managers holding": len(holding),
        "Hedge-fund managers adding": len(added),
        "Hedge-fund managers reducing": len(reduced),
        "Hedge-fund managers new": len(new),
        "Hedge-fund managers no longer reported": len(no_longer),
        "Hedge-fund quarter end": quarter.isoformat(),
        "Hedge-fund filed as of": latest_file.isoformat(),
        "Hedge-fund source links": "; ".join(links),
        "Hedge-fund position details": "; ".join(details),
        "Hedge-fund limitation": (
            "Selected specialist managers only. Form 13F discloses reportable long "
            "holdings as of quarter end, not real-time buying, aggregate beneficial "
            "ownership, complete shorts, or necessarily all economically held shares."
        ),
    })
    return out


def summarize_filings(ticker_map, filings_by_manager, *, as_of):
    """Aggregate matching long share classes across selected 13F manager filings.

    A manager with missing/partial data is ignored, not counted as a zero
    holding. Only a *complete* verified previous quarter can support a change.
    """
    groups = defaultdict(list)
    reports = []
    for manager in filings_by_manager:
        cik = manager.get("cik")
        name = manager.get("name")
        reports.append({
            "manager": name, "cik": cik,
            "status": manager.get("status", "ERROR"),
            "latest_period": manager.get("latest_period"),
            "latest_filing": manager.get("latest_filing"),
            "source": manager.get("source", ""),
            "error": manager.get("error", ""),
        })
        if manager.get("status") != "COMPLETE":
            continue
        current = manager.get("current")
        previous = manager.get("previous")
        if not isinstance(current, dict) or not isinstance(previous, dict):
            continue
        report_day = day(manager.get("latest_period"))
        prior_day = day(manager.get("prior_period"))
        if not report_day or not prior_day or not COMPARABLE_QUARTER_GAP[0] <= (
                report_day - prior_day).days <= COMPARABLE_QUARTER_GAP[1]:
            continue

        def matched(table):
            result = {}
            conflicting = set()
            for h in table.get("holdings", []):
                issuer = issuer_name(h.get("issuer"))
                ticker = ticker_map.get(issuer)
                if not ticker:
                    continue
                cusip = str(h.get("cusip") or "")
                shares = h.get("shares")
                if type(shares) is not int or shares < 0 or not re.fullmatch(
                    r"[A-Z0-9]{9}", cusip
                ):
                    continue
                # Only matching one common class CUSIP per tracked issuer.
                if ticker in result and result[ticker][0] != cusip:
                    conflicting.add(ticker)
                else:
                    result[ticker] = (cusip, (result.get(ticker, (cusip, 0))[1] + shares))
            return {t: x for t, x in result.items() if t not in conflicting}, conflicting

        now, conflict_now = matched(current)
        old, conflict_old = matched(previous)
        for ticker in set(now) | set(old):
            if ticker in conflict_now or ticker in conflict_old:
                continue
            now_cusip = now.get(ticker, (None, 0))[0]
            old_cusip = old.get(ticker, (None, 0))[0]
            if now_cusip and old_cusip and now_cusip != old_cusip:
                continue  # CUSIP change cannot be interpreted as buy/sell.
            cusip = now_cusip or old_cusip
            archive = manager.get("current_url")
            if not isinstance(archive, str):
                continue
            groups[ticker].append({
                "manager_name": name, "manager_cik": cik,
                "cusip": cusip, "shares": now.get(ticker, (None, 0))[1],
                "prior_shares": old.get(ticker, (None, 0))[1],
                "quarter_end": report_day.isoformat(),
                "filed": manager.get("latest_filing", ""),
                "filing_url": archive,
                "prior_filing_url": manager.get("previous_url", ""),
                "match": "EXACT_COMPANY_NAME_AND_COMMON_CLASS_CUSIP",
            })
    rows = []
    for ticker in sorted(groups):
        entries = groups[ticker]
        quarters = {x["quarter_end"] for x in entries}
        # No accidental mix of manager reports from different quarters.
        if len(quarters) != 1:
            continue
        rows.append({"ticker": ticker, "quarter_end": next(iter(quarters)),
                     "managers": entries})
    return rows, reports
