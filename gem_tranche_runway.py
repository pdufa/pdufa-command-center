"""Source-bounded tranche ledger and pro-forma cash runway research.

A financing PACKAGE can be paid in several tranches. One package is never
several independent financing rounds. Paid debt principal is not necessarily
net cash after fees. Pro-forma runway NEVER clears GEM's SEC cash-only gate.
"""
from __future__ import annotations

import csv
import math
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from gem_runway_gate import assess_runway, REVIEW

FIELDS = (
    "ticker", "event_key", "financing_id", "tranche_id",
    "funding_date", "status", "currency", "gross_usd",
    "net_cash_received_usd", "sec_url", "sec_accession", "notes",
)
DAYS_PER_MONTH = 365.25 / 12


def _day(x):
    try:
        return date.fromisoformat(str(x or "")[:10])
    except (ValueError, TypeError):
        return None


def _amount(x):
    if x is None or str(x).strip() == "":
        return None
    try:
        n = float(x)
        return n if math.isfinite(n) and n >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def load_tranches(root):
    """One company-wide row per unique package/tranche, not per drug program.

    Return per-ticker ledger rows; invalid or duplicated ledger IDs remain
    visible for review rather than being silently selected as valid funding.
    """
    path = Path(root) / "data" / "financing_tranches.csv"
    if not path.is_file():
        return {}
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not set(FIELDS).issubset(reader.fieldnames or []):
                return {}
            rows = list(reader)
    except (OSError, UnicodeError, csv.Error):
        return {}
    by_ticker = {}
    seen = set()
    for record in rows:
        ticker = str(record.get("ticker") or "").strip().upper()
        finance = str(record.get("financing_id") or "").strip()
        tranche = str(record.get("tranche_id") or "").strip()
        if not ticker or not finance or not tranche:
            continue
        item = {key: str(record.get(key) or "").strip() for key in FIELDS}
        item["ticker"] = ticker
        key = ticker, finance, tranche
        item["ledger_error"] = "DUPLICATE_TRANCHE_ID" if key in seen else ""
        seen.add(key)
        by_ticker.setdefault(ticker, []).append(item)
    for rows in by_ticker.values():
        counts = {}
        for row in rows:
            key = row["financing_id"], row["tranche_id"]
            counts[key] = counts.get(key, 0) + 1
        for row in rows:
            if counts[(row["financing_id"], row["tranche_id"])] > 1:
                row["ledger_error"] = "DUPLICATE_TRANCHE_ID"
    return by_ticker


def _sec_provenance(row, cik):
    url = str(row.get("sec_url") or "")
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in {"sec.gov", "www.sec.gov"}:
        return False
    acc = str(row.get("sec_accession") or "")
    parts = parsed.path.split("/")
    if len(parts) < 7 or parts[:4] != ["", "Archives", "edgar", "data"]:
        return False
    if not (cik and str(cik).isdigit() and parts[4].isdigit()
            and int(parts[4]) == int(cik)):
        return False
    return len(parts[5]) == 18 and parts[5].isdigit() and parts[5] == acc.replace("-", "")


def assess_tranches(ticker, snapshot, ledger, *, as_of):
    """Report funded tranches, and a conditional *research-only* runway.

    Cash already included in the SEC reporting date is never added again.
    Future, undrawn, gross-only, and unsupported proceeds never create cash.
    Extrapolated post-report burn is identified as an assumption, not verified
    current cash. No field from here may make a GEM entry gate pass.
    """
    rows = ledger if isinstance(ledger, list) else []
    today = _day(as_of)
    result = {
        "Financing tranches": [],
        "Financing packages (research)": len({x.get("financing_id") for x in rows
                                             if isinstance(x, dict) and x.get("financing_id")}),
        "Tranche-funded runway (months)": None,
        "Tranche runway status": "REVIEW — TRANCHE PRO FORMA UNVERIFIED",
        "Tranche runway reason": "No verified net tranche proceeds and SEC cash/burn reconciliation",
        "Post-statement tranche net cash USD": None,
    }
    cash_date = None
    if isinstance(snapshot, dict) and isinstance(snapshot.get("evidence"), dict):
        cash_date = _day((snapshot["evidence"].get("cash") or {}).get("period_end"))
    included, added, pending, bad = [], [], [], []
    total = 0.0
    for row in rows:
        if not isinstance(row, dict):
            bad.append("Malformed tranche entry")
            continue
        item = dict(row)
        day = _day(row.get("funding_date"))
        status = row.get("status")
        if row.get("ticker") != ticker:
            item["runway_treatment"] = "COMPANY_MISMATCH"
            bad.append("Cross-company funding row")
        elif row.get("ledger_error"):
            item["runway_treatment"] = row["ledger_error"]
            bad.append("Duplicate tranche identity")
        elif status != "FUNDED":
            item["runway_treatment"] = "NOT_FUNDED_EXCLUDED"
        elif not day or not today or day > today:
            item["runway_treatment"] = "FUNDING_DATE_NOT_CONFIRMED"
            pending.append("Funding date")
        elif not cash_date:
            item["runway_treatment"] = "CASH_PERIOD_UNAVAILABLE"
            pending.append("Cash statement date")
        elif day <= cash_date:
            item["runway_treatment"] = "IN_STATEMENT_PERIOD_NOT_ADDED"
            included.append(item["tranche_id"])
        else:
            cash_cik = snapshot.get("cik", "") if isinstance(snapshot, dict) else ""
            gross = _amount(row.get("gross_usd"))
            net = _amount(row.get("net_cash_received_usd"))
            if (row.get("currency") != "USD" or not _sec_provenance(row, cash_cik)
                    or net is None or (gross is not None and net > gross)):
                item["runway_treatment"] = "NET_PROCEEDS_NEED_PRIMARY_VERIFICATION"
                pending.append(item.get("tranche_id") or "Unidentified tranche")
            else:
                item["runway_treatment"] = "POST_REPORT_VERIFIED_NET_PROCEEDS"
                total += net
                added.append(item["tranche_id"])
        result["Financing tranches"].append(item)
    if not rows:
        result["Tranche runway reason"] = "No tranche rows yet; enter each funded and undrawn tranche separately"
        return result
    if bad or pending:
        result["Tranche runway reason"] = ("Source or net cash still needs review: " +
                                           ", ".join((bad + pending)[:8]))
        return result
    if not added:
        result["Tranche runway reason"] = (
            "No separately verified net cash received after SEC balance-sheet date; "
            "prior funded tranches are already represented by statement-period cash"
        )
        return result
    if not isinstance(snapshot, dict) or not cash_date or not today:
        return result
    # Validate the underlying same-company unrestricted SEC cash and historical
    # burn independently. Do not use the stricter post-close date gate here:
    # a pro-forma by definition can bridge a reported balance and later cash.
    baseline = assess_runway(ticker, snapshot, as_of=today, second_close=None)
    if baseline["Cash runway gate"] == REVIEW:
        result["Tranche runway reason"] = "Underlying SEC cash/burn snapshot unverified"
        return result
    months = _amount(snapshot.get("operating_cash_flow_months"))
    cash = _amount(snapshot.get("cash_usd"))
    flow = snapshot.get("operating_cash_flow_usd")
    if months not in (3, 12) or cash is None or not isinstance(flow, (float, int)) or flow >= 0:
        return result
    burn = -float(flow) / months
    elapsed_months = (today - cash_date).days / DAYS_PER_MONTH
    if elapsed_months < 0 or burn <= 0:
        return result
    projected_cash = cash - burn * elapsed_months + total
    result["Post-statement tranche net cash USD"] = round(total, 2)
    result["Tranche-funded runway (months)"] = round(max(projected_cash, 0) / burn, 2)
    result["Tranche runway status"] = "PRO FORMA RESEARCH ONLY — NOT SEC VERIFIED CURRENT CASH"
    result["Tranche runway reason"] = (
        "SEC dated cash less extrapolated cash burn since reporting date, plus "
        "documented net tranche cash received after that date; excludes undrawn "
        "funding and may omit other cash movements. Never overrides GEM runway gate."
    )
    return result
