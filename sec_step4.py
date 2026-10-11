"""Step 4: conservative SEC/EDGAR financial intake and versioned risk research.

This module does not alter Phase 1-3, financing-stage milestones, or FDA PoA.
Never interpret an offering prospectus or 8-K alone as a CLOSED financing.
Actual SEC requests require an identifiable configured SEC_USER_AGENT.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "data" / "company_registry.csv"
DEFAULT_DB = ROOT / "data" / "sec_step4_snapshots.sqlite3"
SEC_HOST = "https://data.sec.gov"
FORMS = {"10-Q", "10-K", "10-Q/A", "10-K/A"}
WATCH_FORMS = {"8-K", "8-K/A", "424B5", "424B4", "424B2", "S-3", "S-3/A", "S-1", "S-1/A", "FWP"}
CASH_TAGS = ("CashAndCashEquivalentsAtCarryingValue", "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents")
SHORT_INVESTMENTS = ("ShortTermInvestments", "ShortTermMarketableSecurities")
OPERATING_CF = ("NetCashProvidedByUsedInOperatingActivities",)
REVENUE = ("RevenueFromContractWithCustomerExcludingAssessedTax",
           "Revenues", "SalesRevenueNet", "RevenueFromContractWithCustomerIncludingAssessedTax")
DEBT_CURRENT = ("LongTermDebtCurrent", "ShortTermBorrowings")
DEBT_NONCURRENT = ("LongTermDebtNoncurrent",)
SHARES = ("CommonStockSharesOutstanding",)
SEC_FORM_NOTE = {
    "8-K": "Current report; contents require review to identify any actual financing",
    "8-K/A": "Amended current report; contents require review",
    "424B5": "Prospectus supplement: possible offering, NOT proof of closing",
    "424B4": "Final prospectus filing: NOT proof of closing",
    "424B2": "Prospectus supplement: financing terms may require review",
    "S-3": "Registration statement: shelf capacity, NOT financing closure",
    "S-3/A": "Amended registration statement: NOT financing closure",
    "S-1": "Registration statement: NOT financing closure",
    "S-1/A": "Amended registration statement: NOT financing closure",
    "FWP": "Free-writing prospectus: NOT financing closure",
}


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def cik10(value):
    raw = str(value or "").strip()
    if not raw.isdecimal() or int(raw) == 0 or len(raw) > 10:
        raise ValueError("Invalid SEC CIK")
    return f"{int(raw):010d}"


def clean_ticker(value):
    ticker = str(value or "").strip().upper()
    if not re.fullmatch(r"[A-Z0-9.\\-]{1,15}", ticker):
        raise ValueError("Invalid ticker")
    return ticker


def load_registry(path=REGISTRY):
    """Only registered ticker/CIK pairs, never fuzzy ticker matching."""
    with Path(path).open(newline="", encoding="utf-8-sig") as fp:
        rows = list(csv.DictReader(fp))
    out = {}
    for row in rows:
        try:
            t = clean_ticker(row.get("ticker"))
            c = cik10(row.get("cik10"))
        except ValueError:
            continue
        if t in out and out[t]["cik"] != c:
            out[t] = {"ticker": t, "cik": "", "company": "", "conflict": True}
            continue
        if t not in out:
            out[t] = {"ticker": t, "cik": c, "company": str(row.get("company") or "").strip(),
                      "conflict": False}
    return out


def _http_json(url, user_agent, opener=urlopen, attempts=3):
    if not (str(user_agent or "").strip() and "@" in user_agent and
            len(user_agent.strip()) >= 12):
        raise ValueError("Set SEC_USER_AGENT to your application name and a genuine contact email.")
    if not url.startswith(("https://data.sec.gov/", "https://www.sec.gov/")):
        raise ValueError("Unapproved SEC URL")
    req = Request(url, headers={"User-Agent": user_agent, "Accept": "application/json",
                                "Accept-Encoding": "identity"})
    for attempt in range(attempts):
        try:
            with opener(req, timeout=18) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            if exc.code in (403, 401):
                raise RuntimeError(f"SEC access HTTP {exc.code}; check configured contact identity and network. No records updated.") from exc
            if exc.code in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                time.sleep(1.0 * (2 ** attempt))
                continue
            raise RuntimeError(f"SEC HTTP {exc.code} while retrieving {url}; no invented data.") from exc
        except (TimeoutError, URLError, OSError) as exc:
            if attempt < attempts - 1:
                time.sleep(1.0 * (2 ** attempt))
                continue
            raise RuntimeError(f"SEC network failure: {exc}") from exc
        except (ValueError, UnicodeError) as exc:
            raise RuntimeError("SEC responded with invalid JSON; no records updated.") from exc
    raise RuntimeError("SEC request failed without usable data.")


def _date(raw):
    try:
        return date.fromisoformat(str(raw or "")[:10])
    except ValueError:
        return None


def _facts(companyfacts, taxonomy, tags, units, as_of):
    items = []
    for priority, tag in enumerate(tags):
        for unit in units:
            for raw in (companyfacts.get("facts", {}).get(taxonomy, {})
                        .get(tag, {}).get("units", {}).get(unit, []) or []):
                if raw.get("form") not in FORMS:
                    continue
                end, filed, start = _date(raw.get("end")), _date(raw.get("filed")), _date(raw.get("start"))
                if end is None or filed is None or filed > as_of or end > as_of:
                    continue
                val = raw.get("val")
                if isinstance(val, bool) or not isinstance(val, (int, float)):
                    continue
                items.append({
                    "tag": tag, "value": val, "start": start, "end": end, "filed": filed,
                    "form": raw.get("form"), "accn": str(raw.get("accn", "")),
                    "fy": raw.get("fy"), "fp": raw.get("fp"), "priority": priority,
                })
    return items


def _recent_instant(facts, taxonomy, tags, units, as_of):
    items = [x for x in _facts(facts, taxonomy, tags, units, as_of) if x["start"] is None]
    # Choose latest reporting date; prefer most direct concept before cash+restricted variant,
    # then most recently filed same-period amendment.
    if not items:
        return None
    return sorted(items, key=lambda v: (v["end"], -v["priority"], v["filed"]), reverse=True)[0]


def _quarter_duration(facts, tags, as_of):
    """Return direct ~quarterly operating cash flow, else correctly derived YTD delta.

    Reject missing predecessor YTD; a 6/9-month cash flow is not a quarter.
    """
    candidates = _facts(facts, "us-gaap", tags, ("USD",), as_of)
    with_starts = [x for x in candidates if x["start"] and x["start"] <= x["end"]]
    direct = [x for x in with_starts if 60 <= (x["end"] - x["start"]).days <= 124]
    if direct:
        row = max(direct, key=lambda v: (v["end"], v["filed"], -v["priority"]))
        return {**row, "basis": "DIRECT QUARTER", "months": 3}
    recent = sorted(with_starts, key=lambda v: (v["end"], v["filed"]), reverse=True)
    for current in recent:
        span = (current["end"] - current["start"]).days
        if not 125 <= span <= 370:
            continue
        previous = [x for x in with_starts
                    if x["tag"] == current["tag"] and x["start"] == current["start"]
                    and x["end"] < current["end"]
                    and 65 <= (current["end"] - x["end"]).days <= 115]
        if previous:
            prior = max(previous, key=lambda v: (v["end"], v["filed"]))
            return {**current, "value": current["value"] - prior["value"],
                    "basis": "YTD LESS PRIOR YTD", "prior_accn": prior["accn"],
                    "prior_end": prior["end"], "months": 3}
    return None


def _annual_duration(facts, tags, as_of):
    rows = [x for x in _facts(facts, "us-gaap", tags, ("USD",), as_of)
            if x["start"] and 330 <= (x["end"] - x["start"]).days <= 380]
    if not rows:
        return None
    item = max(rows, key=lambda v: (v["end"], v["filed"], -v["priority"]))
    return {**item, "basis": "ANNUAL AVERAGE; NO QUARTER AVAILABLE", "months": 12}


def _usable_source(item):
    if not item:
        return None
    return {
        "tag": item["tag"], "period_end": item["end"].isoformat(),
        "filed": item["filed"].isoformat(), "form": item["form"],
        "accession": item["accn"], "basis": item.get("basis", "INSTANT"),
    }


def _reported_num(item):
    return float(item["value"]) if item else None


def _sec_files(submissions, cik, as_of, limit=50):
    recent = (submissions or {}).get("filings", {}).get("recent", {}) or {}
    forms, dates, accns, docs = [recent.get(k) or [] for k in ("form", "filingDate", "accessionNumber", "primaryDocument")]
    items = []
    for form, filed, accn, document in zip(forms, dates, accns, docs):
        filed_at = _date(filed)
        if form not in WATCH_FORMS or not filed_at or filed_at > as_of:
            continue
        if (as_of - filed_at).days > 540:
            continue
        if not re.fullmatch(r"\\d{10}-\\d{2}-\\d{6}", str(accn)):
            continue
        if "/" in str(document) or "\\" in str(document) or not str(document).strip():
            continue
        link = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accn.replace('-', '')}/{document}"
        items.append({"form": form, "filed": filed, "accession": accn,
                      "source_url": link, "review_note": SEC_FORM_NOTE[form],
                      "close_verified": False})
        if len(items) >= limit:
            break
    return items


def _confidence_note(cash, operating, as_of):
    notes = []
    if cash is None:
        notes.append("SEC instant cash balance missing")
    elif (as_of - cash["end"]).days > 150:
        notes.append("SEC cash balance older than 150 days")
    if operating is None:
        notes.append("Operating cash flow missing for a comparable quarter or annual period")
    elif (as_of - operating["end"]).days > 150:
        notes.append("Operating cash flow older than 150 days")
    if cash and operating and abs((cash["end"] - operating["end"]).days) > 100:
        notes.append("Cash and burn reporting periods differ by more than 100 days")
    return notes


def analyze_companyfacts(ticker, cik, company, companyfacts, submissions, as_of=None):
    """Calculated from as-of eligible SEC data; missing stays None, never zero."""
    today = as_of or datetime.now(timezone.utc).date()
    if isinstance(today, str):
        today = date.fromisoformat(today)
    cik = cik10(cik)
    ticker = clean_ticker(ticker)
    if str(companyfacts.get("cik") or "").strip() not in (str(int(cik)), cik):
        raise ValueError("SEC companyfacts CIK does not match registered company")
    sub_cik = (submissions or {}).get("cik")
    if sub_cik is not None and str(sub_cik).strip() not in (str(int(cik)), cik):
        raise ValueError("SEC submissions CIK does not match registered company")
    cash = _recent_instant(companyfacts, "us-gaap", CASH_TAGS, ("USD",), today)
    investments = _recent_instant(companyfacts, "us-gaap", SHORT_INVESTMENTS, ("USD",), today)
    operating = _quarter_duration(companyfacts, OPERATING_CF, today)
    if operating is None:
        operating = _annual_duration(companyfacts, OPERATING_CF, today)
    revenue = _quarter_duration(companyfacts, REVENUE, today)
    if revenue is None:
        revenue = _annual_duration(companyfacts, REVENUE, today)
    current_debt = _recent_instant(companyfacts, "us-gaap", DEBT_CURRENT, ("USD",), today)
    long_debt = _recent_instant(companyfacts, "us-gaap", DEBT_NONCURRENT, ("USD",), today)
    shares = _recent_instant(companyfacts, "dei", SHARES, ("shares",), today)
    notes = _confidence_note(cash, operating, today)
    burn = None
    burn_basis = operating["basis"] if operating else "UNAVAILABLE"
    if operating:
        months = operating["months"]
        burn = max(0.0, -float(operating["value"]) / months)
    runway = None
    if cash and operating and not notes and burn is not None and burn > 0:
        # Cash only: marketable securities and restricted cash are never presumed liquid.
        if cash["tag"] == "CashAndCashEquivalentsAtCarryingValue":
            runway = round(max(0.0, float(cash["value"])) / burn, 2)
        else:
            notes.append("Only cash+restricted cash reported; spendable balance unverified")
    elif burn == 0 and operating and not notes:
        notes.append("No net operating cash burn in this period; runway cannot be inferred")
    runway_risk = ("REVIEW — MISSING OR STALE INPUTS" if runway is None else
                   "HIGH — UNDER 6 MONTHS" if runway < 6 else
                   "ELEVATED — 6 TO UNDER 12 MONTHS" if runway < 12 else
                   "WATCH — 12 TO UNDER 18 MONTHS" if runway < 18 else
                   "LOWER CASH RUNWAY RISK — 18+ MONTHS")
    if cash and cash["tag"] != CASH_TAGS[0] and "Only cash+restricted cash reported; spendable balance unverified" not in notes:
        notes.append("Cash includes restricted balance; do not assume unrestricted liquidity")
    recent_filings = _sec_files(submissions, cik, today)
    return {
        "ticker": ticker, "company": company, "cik": cik, "as_of": today.isoformat(),
        "cash_usd": _reported_num(cash),
        "cash_includes_restricted": bool(cash and cash["tag"] != CASH_TAGS[0]),
        "short_term_investments_usd": _reported_num(investments),
        "operating_cash_flow_usd": _reported_num(operating),
        "operating_cash_flow_months": operating["months"] if operating else None,
        "monthly_operating_burn_usd": round(burn, 2) if burn is not None else None,
        "runway_months_cash_only": runway,
        "cash_runway_risk": runway_risk,
        "company_revenue_usd": _reported_num(revenue),
        "product_revenue_usd": None,
        "product_revenue_note": "NOT VERIFIED — company revenue does not prove approved product sales",
        "current_debt_usd": _reported_num(current_debt),
        "noncurrent_debt_usd": _reported_num(long_debt),
        "shares_outstanding": _reported_num(shares),
        "financing_closed": "NOT VERIFIED — document-level review required",
        "active_atm": "NOT VERIFIED — 8-K/prospectus metadata cannot prove active sales",
        "filing_review_queue": recent_filings,
        "evidence": {
            "cash": _usable_source(cash), "short_term_investments": _usable_source(investments),
            "operating_cash_flow": _usable_source(operating), "revenue": _usable_source(revenue),
            "current_debt": _usable_source(current_debt),
            "noncurrent_debt": _usable_source(long_debt), "shares": _usable_source(shares),
            "companyfacts_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json",
            "submissions_url": f"https://data.sec.gov/submissions/CIK{cik}.json",
        },
        "review_flags": notes,
        "financial_score_0_100": None,
        "financial_score_note": "NOT SCORED — no independently validated composite weighting or offering-close evidence",
        "method": "Trailing reported operating cash flow / months; cash-only estimate, no financing assumed",
    }


def _db(db_path=DEFAULT_DB):
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA busy_timeout=15000")
    db.execute("""CREATE TABLE IF NOT EXISTS sec_financial_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        observed_at_utc TEXT NOT NULL,
        ticker TEXT NOT NULL,
        cik TEXT NOT NULL,
        as_of TEXT NOT NULL,
        content_sha256 TEXT NOT NULL,
        payload_json TEXT NOT NULL,
        UNIQUE(ticker,cik,as_of,content_sha256)
    )""")
    db.execute("CREATE INDEX IF NOT EXISTS sec_financial_company ON sec_financial_history(ticker,id)")
    return db


def save_snapshot(snapshot, db_path=DEFAULT_DB):
    """Append a new content revision; identical refresh is idempotent."""
    data = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(data.encode("utf-8")).hexdigest()
    with _db(db_path) as db:
        db.execute("""INSERT OR IGNORE INTO sec_financial_history
                      (observed_at_utc,ticker,cik,as_of,content_sha256,payload_json)
                      VALUES(?,?,?,?,?,?)""",
                   (utc_now(), snapshot["ticker"], snapshot["cik"], snapshot["as_of"], digest, data))
        row = db.execute("""SELECT id FROM sec_financial_history
                            WHERE ticker=? AND cik=? AND as_of=? AND content_sha256=?""",
                         (snapshot["ticker"], snapshot["cik"], snapshot["as_of"], digest)).fetchone()
        return int(row["id"])


def read_history(db_path=DEFAULT_DB, ticker=None):
    with _db(db_path) as db:
        if ticker:
            rows = db.execute("SELECT * FROM sec_financial_history WHERE ticker=? ORDER BY id DESC",
                              (clean_ticker(ticker),)).fetchall()
        else:
            rows = db.execute("SELECT * FROM sec_financial_history ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def scan_one(ticker, registry=None, user_agent=None, db_path=DEFAULT_DB, getter=_http_json,
             as_of=None, min_interval=0.25):
    reg = registry if registry is not None else load_registry()
    symbol = clean_ticker(ticker)
    identity = reg.get(symbol)
    if not identity or identity.get("conflict") or not identity.get("cik"):
        raise ValueError(f"{symbol}: no unique validated ticker/CIK mapping; no fetch performed")
    agent = user_agent or os.environ.get("SEC_USER_AGENT", "")
    # Fail before any network request if SEC identity is missing.
    if not agent.strip() or "@" not in agent:
        raise ValueError("Set SEC_USER_AGENT to a descriptive app name and reachable contact email.")
    cik = identity["cik"]
    companyfacts = getter(f"{SEC_HOST}/api/xbrl/companyfacts/CIK{cik}.json", agent)
    if min_interval > 0:
        time.sleep(min_interval)
    submissions = getter(f"{SEC_HOST}/submissions/CIK{cik}.json", agent)
    snapshot = analyze_companyfacts(symbol, cik, identity["company"], companyfacts, submissions, as_of=as_of)
    row_id = save_snapshot(snapshot, db_path)
    return row_id, snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manual Step 4 SEC fundamentals scan; no bulk scan by default")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--ticker", help="One registered company ticker")
    target.add_argument("--all", action="store_true", help="Explicit capped universe scan")
    parser.add_argument("--limit", type=int, default=5, help="Maximum companies in explicit --all mode (1–25)")
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 25:
        parser.error("limit must be between 1 and 25")
    mapping = load_registry(args.registry)
    tickers = [args.ticker] if args.ticker else sorted(mapping)[:args.limit]
    successes, failures = [], []
    for ticker in tickers:
        try:
            row_id, snapshot = scan_one(ticker, mapping, db_path=args.db)
            successes.append({"ticker": ticker, "revision": row_id,
                              "risk": snapshot["cash_runway_risk"],
                              "runway_months": snapshot["runway_months_cash_only"]})
        except (ValueError, RuntimeError, OSError, sqlite3.Error) as exc:
            failures.append({"ticker": ticker, "error": str(exc)})
    print(json.dumps({"processed": len(tickers), "successes": successes, "failures": failures}, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
