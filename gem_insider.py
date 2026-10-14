"""Source-dated Form 4 insider open-market transaction observations for GEM.

Advisory evidence only, never a third entry benchmark. Code P/A is a reported
non-derivative common-stock purchase; code S/D is a reported sale. Excludes
grants, options, derivatives, zero-price exercises and unverified amendments.
"""
from __future__ import annotations
import json
import math
import re
from datetime import date
from pathlib import Path

FILE = "gem_insider_form4.json"
STATUS = "SOURCE-VERIFIED SEC FORM 4 OBSERVATIONS"
REVIEW = "REVIEW — NO VERIFIED RECENT FORM 4"
LOOKBACK_DAYS = 90


def _day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except (TypeError, ValueError):
        return None


def _int(v):
    try:
        n=float(v)
        if n>=0 and n.is_integer() and math.isfinite(n):
            return int(n)
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def _cash(v):
    try:
        n=float(v)
        if math.isfinite(n) and n>0:
            return n
    except (ValueError, TypeError, OverflowError):
        pass
    return None


def load_records(root, *, as_of):
    try:
        j=json.loads((Path(root)/FILE).read_text(encoding="utf-8"))
        today, checked=_day(as_of), _day(j.get("as_of_pacific"))
        if (j.get("schema_version") != 1 or j.get("source") != "SEC_ISSUER_FORM4_XML"
                or not today or not checked
                or not 0 <= (today-checked).days <= 7
                or not isinstance(j.get("records"), list)):
            return {}
        out,dupes={},set()
        for r in j["records"]:
            if not isinstance(r,dict):
                continue
            ticker=str(r.get("ticker") or "").upper()
            if not re.fullmatch(r"[A-Z0-9.\-]{1,15}",ticker):
                continue
            if ticker in out:
                dupes.add(ticker)
            out[ticker]=r
        return {t:r for t,r in out.items() if t not in dupes}
    except (OSError, ValueError, TypeError, UnicodeError, AttributeError):
        return {}


def assess(ticker, record, *, as_of):
    item={
        "Insider Form 4 signal": REVIEW,
        "Insider open-market purchases": None,
        "Insider open-market sales": None,
        "Insider purchase amount USD": None,
        "Insider sale amount USD": None,
        "Insider net reported amount USD": None,
        "Insider buyers": None,
        "Insider lookback days": LOOKBACK_DAYS,
        "Insider last filing date": "",
        "Insider source links": "",
        "Insider filings reviewed": None,
        "Insider risk note": (
            "No source-complete SEC issuer Form 4 audit; missing evidence "
            "is NOT zero insider buying"
        ),
    }
    today=_day(as_of)
    if not today or not isinstance(record,dict) or str(record.get("ticker") or "")!=ticker:
        return item
    if record.get("status")!="COMPLETE" or not isinstance(record.get("transactions"),list):
        return item
    checked=_day(record.get("as_of"))
    if not checked or not 0 <= (today-checked).days <= 7:
        return item
    txns=[]
    for v in record["transactions"]:
        if not isinstance(v,dict) or v.get("code") not in ("P","S"):
            return item
        d=_day(v.get("date"))
        shares,price=_int(v.get("shares")),_cash(v.get("price"))
        uri=v.get("source")
        if (not d or not 0 <= (today-d).days <= LOOKBACK_DAYS
                or shares is None or shares<=0 or price is None
                or not isinstance(uri,str)
                or not uri.startswith("https://www.sec.gov/Archives/edgar/data/")):
            return item
        txns.append(v)
    buys=[t for t in txns if t["code"]=="P"]
    sells=[t for t in txns if t["code"]=="S"]
    buy=sum(int(t["shares"])*float(t["price"]) for t in buys)
    sell=sum(int(t["shares"])*float(t["price"]) for t in sells)
    buyers={str(t.get("owner") or "") for t in buys if str(t.get("owner") or "")}
    links=sorted({t["source"] for t in txns})
    item.update({
        "Insider Form 4 signal": STATUS,
        "Insider open-market purchases": len(buys),
        "Insider open-market sales": len(sells),
        "Insider purchase amount USD": round(buy,2),
        "Insider sale amount USD": round(sell,2),
        "Insider net reported amount USD": round(buy-sell,2),
        "Insider buyers": len(buyers),
        "Insider last filing date": record.get("latest_filing") or "",
        "Insider source links": "; ".join(links),
        "Insider filings reviewed": record.get("filings_reviewed",0),
        "Insider risk note": (
            "Form 4 P/S common-share transactions only, latest 90 days. "
            "A filing may include 10b5-1 planned trades. Does not include "
            "unreported subsequent trades or imply investment performance."
        ),
    })
    return item
