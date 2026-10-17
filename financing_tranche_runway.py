"""Research-only reconciliation of funded financing tranches with cash runway.

A financing agreement may have MANY tranche releases. Each release is recorded
independently, but all releases sharing a financing_id count as ONE financing.
Current cash is never increased for merely committed, priced, announced,
conditional, or gross-only tranches. This module does not certify GEM entry.
"""
from __future__ import annotations

import csv
import math
import re
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from gem_runway_gate import _day, _num, assess_runway

FIELDS = (
    "event_key", "ticker", "financing_id", "tranche_id", "tranche_status",
    "funded_date", "expected_date", "gross_amount_usd",
    "net_cash_received_usd", "restricted_cash_usd", "source_url",
    "source_sha256", "verification_status", "notes",
)
FUNDED = "FUNDED"
OPEN = {"ANNOUNCED", "COMMITTED_UNFUNDED", "CONDITIONAL", "EXPECTED"}
CLOSED = {"CANCELLED", "NOT_APPLICABLE"}
VALID_STATUSES = {FUNDED} | OPEN | CLOSED


def load_tranches(root):
    """Read user-maintained tranche rows without modifying or promoting them."""
    path = Path(root) / "financing_tranches.csv"
    if not path.is_file():
        return {}
    with path.open(newline="", encoding="utf-8-sig") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not set(FIELDS).issubset(reader.fieldnames):
            raise ValueError("Tranche input columns are incomplete")
        rows = list(reader)
    result = {}
    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        if not ticker or not str(row.get("financing_id") or "").strip():
            raise ValueError("Tranche issuer or financing agreement ID missing")
        result.setdefault(ticker, []).append(row)
    return result


def _sec_issuer_document(url, cik):
    if not cik or not str(cik).isdigit() or not url:
        return False
    parsed = urlsplit(str(url))
    match = re.fullmatch(
        r"/Archives/edgar/data/(\d+)/(\d{18})/[A-Za-z0-9_.-]+",
        parsed.path, re.I,
    )
    return (parsed.scheme == "https"
            and parsed.hostname in {"sec.gov", "www.sec.gov"}
            and not parsed.query and not parsed.fragment
            and match is not None and int(match.group(1)) == int(cik))


def assess_tranche_runway(ticker, snapshot, tranches, *, as_of, event_key=None):
    """Estimate cash from independently verified net proceeds and a SEC baseline.

    Exact program scope is respected; a company event may have multiple funding
    installments in one agreement. The historical SEC gate is NEVER upgraded.
    """
    result = {
        "status": "NO_TRANCHE_INPUT",
        "reason": "No tranche input recorded",
        "tranches": [], "agreement_count": 0,
        "funded_net_added_usd": 0.0, "reported_cash_usd": None,
        "estimated_cash_usd": None, "estimated_runway_months": None,
        "monthly_burn_usd": None, "unverified_rows": 0,
        "pending_rows": 0, "gate_unchanged": True,
    }
    tick = str(ticker or "").strip().upper()
    relevant = [r for r in (tranches or [])
                if str(r.get("ticker") or "").strip().upper() == tick
                and (not event_key or not r.get("event_key")
                     or str(r.get("event_key")).strip() == event_key)]
    if not relevant:
        return result
    result["status"] = "RUNWAY_UNVERIFIED"
    result["reason"] = "Tranche input present; primary cash/burn and net receipts require verification"
    as_at = _day(as_of)
    if not as_at:
        result["reason"] = "Invalid assessment date"
        return result
    agreements = set()
    unique_tranches = set()
    details = []
    fundable = []
    duplicate = False
    cik = str((snapshot or {}).get("cik") or "")
    for row in relevant:
        agreement = str(row.get("financing_id") or "").strip()
        tranche = str(row.get("tranche_id") or "").strip()
        key = (agreement, tranche)
        if not agreement or not tranche or key in unique_tranches:
            duplicate = True
        unique_tranches.add(key)
        if agreement:
            agreements.add(agreement)
        status = str(row.get("tranche_status") or "").strip().upper()
        verified = str(row.get("verification_status") or "").strip().upper() == "VERIFIED"
        funded_on = _day(row.get("funded_date"))
        gross = _num(row.get("gross_amount_usd"))
        net = _num(row.get("net_cash_received_usd"))
        restricted = _num(row.get("restricted_cash_usd"))
        unrestricted = restricted is not None and restricted == 0
        source_valid = _sec_issuer_document(row.get("source_url"), cik)
        digest = str(row.get("source_sha256") or "").lower()
        hashed = re.fullmatch(r"[0-9a-f]{64}", digest) is not None
        eligible = (
            status == FUNDED and verified and funded_on is not None
            and funded_on <= as_at and net is not None and net >= 0
            and unrestricted and source_valid and hashed
            and (gross is None or 0 <= net <= gross)
        )
        if status in OPEN:
            result["pending_rows"] += 1
        if status not in VALID_STATUSES or (
            status == FUNDED and not eligible
        ):
            result["unverified_rows"] += 1
        details.append({
            "financing_id": agreement, "tranche_id": tranche,
            "status": status or "UNVERIFIED",
            "funded_date": funded_on.isoformat() if funded_on else "",
            "expected_date": str(row.get("expected_date") or ""),
            "gross_amount_usd": gross if gross is not None and gross >= 0 else None,
            "net_cash_received_usd": net if net is not None and net >= 0 else None,
            "source_url": row.get("source_url") or "",
            "counted": False,
            "reason": ("Verified net cash available for reconciliation" if eligible
                       else "Pending or unverified net funding; excluded"),
        })
        if eligible:
            fundable.append((funded_on, net, details[-1]))
    result["tranches"] = details
    result["agreement_count"] = len(agreements)
    if duplicate:
        result["reason"] = "Duplicate or incomplete financing/tranche IDs; stop to prevent double counting"
        return result

    base = assess_runway(tick, snapshot, as_of=as_at)
    if base["Cash runway (months)"] is None:
        result["reason"] = base["Cash runway reason"]
        return result
    cash = _num(snapshot.get("cash_usd"))
    flow = _num(snapshot.get("operating_cash_flow_usd"))
    months = _num(snapshot.get("operating_cash_flow_months"))
    evidence = snapshot.get("evidence") or {}
    cash_fact = evidence.get("cash") or {}
    period_end = _day(cash_fact.get("period_end"))
    if (cash is None or flow is None or flow >= 0 or months not in (3, 12)
            or not period_end or period_end > as_at):
        result["reason"] = "Inconsistent reported cash or burn period"
        return result

    # Amounts received ON/BEFORE the statement cash date are ALREADY reflected.
    # Never add historic financing a second time.
    added = sum(net for funded_on, net, _ in fundable
                if period_end < funded_on <= as_at)
    for funded_on, _, detail in fundable:
        detail["counted"] = period_end < funded_on <= as_at
        if not detail["counted"]:
            detail["reason"] = "Already included in SEC balance sheet; not added twice"
    monthly_burn = -flow / months
    elapsed_months = (as_at - period_end).days / 30.4375
    cash_estimate = max(0.0, cash + added - monthly_burn * elapsed_months)
    result.update({
        "reported_cash_usd": cash,
        "funded_net_added_usd": round(added, 2),
        "estimated_cash_usd": round(cash_estimate, 2),
        "estimated_runway_months": round(cash_estimate / monthly_burn, 2),
        "monthly_burn_usd": round(monthly_burn, 2),
        "status": ("RESEARCH_ESTIMATE_INCOMPLETE" if result["unverified_rows"]
                   else "RESEARCH_ESTIMATE"),
        "reason": ("Unaudited pro-forma cash estimate from SEC baseline, "
                   "verified post-period net tranches and constant historical burn; "
                   "not a GEM cash gate or forecast"),
    })
    return result
