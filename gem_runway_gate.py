"""Conservative SEC cash-only runway assessment for GEM qualification.

A GEM score never overrides this separate research eligibility gate.
Runway comes from saved SEC Step 4 records, never speculative financing.
"""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
from datetime import date

MIN_MONTHS = 12.0
PASS = "PASS — CASH RUNWAY >=12 MONTHS"
HOLD = "HOLD — UNDER 12 MONTHS"
REVIEW = "REVIEW — RUNWAY UNVERIFIED"


def _day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except (TypeError, ValueError):
        return None


def _num(value):
    try:
        if isinstance(value, bool):
            return None
        n = float(value)
        return n if math.isfinite(n) else None
    except (TypeError, ValueError, OverflowError):
        return None


def load_snapshots(root):
    """Read explicit Step 4 export or local Step 4 history; no network calls."""
    root = Path(root)
    published = root / "gem_runway_evidence.json"
    if published.is_file():
        try:
            obj = json.loads(published.read_text(encoding="utf-8"))
            if (not isinstance(obj, dict) or obj.get("schema_version") != 1
                    or obj.get("source") != "SEC_STEP4_COMPANYFACTS"
                    or not isinstance(obj.get("snapshots"), list)):
                return {}
            latest, duplicates = {}, set()
            for snap in obj["snapshots"]:
                if not isinstance(snap, dict):
                    continue
                ticker = str(snap.get("ticker") or "").upper()
                if not re.fullmatch(r"[A-Z0-9]{1,9}(?:[.-][A-Z0-9]{1,4})?", ticker):
                    continue
                if ticker in latest:
                    duplicates.add(ticker)
                latest[ticker] = snap
            return {k: v for k, v in latest.items() if k not in duplicates}
        except (OSError, ValueError, UnicodeError, TypeError):
            return {}
    db = root / "sec_step4_snapshots.sqlite3"
    if not db.is_file():
        return {}
    try:
        from sec_step4 import read_history
        latest = {}
        for record in read_history(db_path=db):  # descending revision
            snap = json.loads(record["payload_json"])
            ticker = str(snap.get("ticker") or "").upper()
            if ticker and ticker not in latest:
                latest[ticker] = snap
        return latest
    except (OSError, ValueError, TypeError, KeyError):
        return {}


def assess_runway(ticker, snapshot, *, as_of, second_close=None):
    """Fail closed on missing, stale, restricted-cash or pre-second-close data."""
    item = {
        "Cash runway (months)": None,
        "Cash runway gate": REVIEW,
        "Cash runway reason": "No current SEC Step 4 cash-only assessment",
        "Cash runway as of": "", "Cash runway source": "",
    }
    if not isinstance(snapshot, dict) or str(snapshot.get("ticker") or "").upper() != str(ticker or "").upper():
        return item
    today, assessed = _day(as_of), _day(snapshot.get("as_of"))
    if not today or not assessed or not 0 <= (today - assessed).days <= 7:
        item["Cash runway reason"] = "SEC runway assessment stale or future dated"
        return item
    item["Cash runway as of"] = assessed.isoformat()
    evidence = snapshot.get("evidence")
    if not isinstance(evidence, dict):
        item["Cash runway reason"] = "SEC fact provenance missing"
        return item
    cik = str(snapshot.get("cik") or "").strip()
    source = evidence.get("companyfacts_url")
    if (not cik.isdigit() or not isinstance(source, str)
            or source != f"https://data.sec.gov/api/xbrl/companyfacts/CIK{int(cik):010d}.json"):
        item["Cash runway reason"] = "Companyfacts SEC CIK/source inconsistent"
        return item
    item["Cash runway source"] = source
    if snapshot.get("cash_includes_restricted") is not False or snapshot.get("review_flags") != []:
        item["Cash runway reason"] = "Restricted cash or unresolved financial-source warning"
        return item
    cash_end = None
    for kind in ("cash", "operating_cash_flow"):
        fact = evidence.get(kind)
        if (not isinstance(fact, dict) or fact.get("form") not in ("10-K", "10-Q", "10-K/A", "10-Q/A")
                or not fact.get("accession")):
            item["Cash runway reason"] = "SEC cash / operating cash flow filing provenance absent"
            return item
        period, filed = _day(fact.get("period_end")), _day(fact.get("filed"))
        if (not period or not filed or period > filed or filed > assessed
                or not 0 <= (today - period).days <= 150):
            item["Cash runway reason"] = "SEC filing date/financial reporting period stale"
            return item
        if kind == "cash":
            cash_end = period
    closing = _day(second_close) if second_close else None
    if second_close and closing is None:
        item["Cash runway reason"] = "Second financing date unparseable"
        return item
    if closing and cash_end < closing:
        item["Cash runway reason"] = "SEC-reported cash predates financing #2 close"
        return item
    cash, flow, months = (_num(snapshot.get(k)) for k in
                          ("cash_usd", "operating_cash_flow_usd", "operating_cash_flow_months"))
    saved = _num(snapshot.get("runway_months_cash_only"))
    if (cash is None or cash < 0 or flow is None or flow >= 0
            or months not in (3, 12) or saved is None):
        item["Cash runway reason"] = "Unrestricted cash and positive burn not documented"
        return item
    runway = cash / (-flow / months)
    if abs(round(runway, 2) - saved) > 0.02:
        item["Cash runway reason"] = "Runway arithmetic does not reconcile with SEC Step 4"
        return item
    item["Cash runway (months)"] = round(runway, 2)
    item["Cash runway gate"] = PASS if runway >= MIN_MONTHS else HOLD
    item["Cash runway reason"] = "SEC cash-only runway measured from historical operating burn"
    return item


def passes(item):
    return item.get("Cash runway gate") == PASS
