"""Bounded public-source observations for isolated review, without DB/score writes."""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
import hashlib
import json
from math import isfinite
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

from .enrichment_calculations import cash_runway_months

ROOT = Path(__file__).with_name("research_sources")
IR_HOSTS = {"CLDX": "ir.celldex.com", "MLTX": "ir.moonlaketx.com"}


@lru_cache(maxsize=1)
def sources():
    values = [json.loads((ROOT / name).read_text()) for name in ("clinical.json", "financial.json")]
    if any(v.get("schemaVersion") != 1 for v in values):
        raise ValueError("Invalid research source version")
    return values


def day(value):
    try:
        if not isinstance(value, str):
            return None
        if "T" in value:
            stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return stamp.astimezone(ZoneInfo("America/Los_Angeles")).date() if stamp.tzinfo else None
        return date.fromisoformat(value)
    except ValueError:
        return None


def number(value):
    return type(value) in (int, float) and isfinite(value)


def group(status, note=""):
    return {"status": status, "note": note, "facts": []}


def fact(label, value, source, observed, checked, status="OBSERVED"):
    return {"label": label, "value": str(value), "source": source, "sourceDate": observed,
            "checkedAt": checked, "status": status}


def financial_summary(result):
    """Never label exclusively stale or review-only financial facts as observed."""
    statuses = {item["status"] for item in result["facts"]}
    if not statuses:
        result.update(status="MISSING", note="No usable financial measurements in the saved source.")
    elif statuses == {"STALE"}:
        result.update(status="STALE", note="All saved financial measurements are stale and need refreshing.")
    elif not statuses.intersection({"OBSERVED", "CALCULATED"}):
        result.update(status="REVIEW_REQUIRED", note="Financial items need review; no current measurement is verified.")
    return result


def clinical_facts(nct, exact_key, records, today):
    if not nct:
        return group("NO_EXACT_TRIAL_LINK", "This application has no source-confirmed NCT link in the review catalog.")
    item = records.get(nct)
    if not isinstance(item, dict):
        return group("MISSING", "The exact trial registry record has not been retrieved.")
    study = item.get("study") or {}
    protocol = study.get("protocolSection") or {}
    source = "https://clinicaltrials.gov/api/v2/studies/" + nct
    digest = hashlib.sha256(json.dumps(study, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if (exact_key != "TRIAL|" + nct or item.get("source") != source
            or (protocol.get("identificationModule") or {}).get("nctId") != nct or item.get("sha256") != digest):
        return group("IDENTITY_MISMATCH", "Registry identity or source receipt could not be reconciled.")
    checked = day(item.get("retrievedAt"))
    observed = day(((protocol.get("statusModule") or {}).get("lastUpdatePostDateStruct") or {}).get("date"))
    if not checked or not observed or not observed <= checked <= today:
        return group("INVALID_SOURCE_REVIEW")
    if (today - checked).days > 7:
        return group("STALE", "The registry source needs a fresh retrieval.")
    url = "https://clinicaltrials.gov/study/" + nct
    make = lambda label, value: fact(label, value, url, observed.isoformat(), checked.isoformat())
    design = protocol.get("designModule") or {}
    info = design.get("designInfo") or {}
    enrollment = design.get("enrollmentInfo") or {}
    result = group("OBSERVED", "Registry design is source evidence. Issuer readouts and clinical interpretation remain separate.")
    result["facts"] = [make("Trial", nct), make("Allocation", info.get("allocation", "Not recorded")),
                       make("Masking", (info.get("maskingInfo") or {}).get("masking", "Not recorded"))]
    if type(enrollment.get("count")) is int and enrollment["count"] >= 0:
        result["facts"].append(make("Enrollment", f"{enrollment['count']:,} ({enrollment.get('type', 'type not recorded')})"))
    for endpoint in (protocol.get("outcomesModule") or {}).get("primaryOutcomes") or []:
        result["facts"].append(make("Registered primary endpoint", str(endpoint.get("measure", "")) + " · " + str(endpoint.get("timeFrame", ""))))
    results = "Posted" if study.get("hasResults") is True else "Not posted; this does not negate a separate issuer readout" if study.get("hasResults") is False else "Not recorded"
    result["facts"].append(make("Registry results", results))
    return result


def financial_facts(ticker, identity, data, today):
    observations = (data.get("issuerObservations") or {}).get(ticker)
    if observations:
        parsed = urlparse(observations.get("source", ""))
        published = day(observations.get("publishedOn"))
        if (observations.get("cik") != identity["cik"] or parsed.scheme != "https" or parsed.hostname != IR_HOSTS.get(ticker)
                or parsed.username or parsed.password or not published or published > today):
            return group("IDENTITY_MISMATCH")
        result = group("OBSERVED", "Issuer-published financial statements; financing clearance is still required.")
        for item in observations.get("facts") or []:
            observed, checked = day(item.get("sourceDate")), day(item.get("checkedAt"))
            if not observed or not checked or not observed <= published <= checked <= today:
                return group("INVALID_SOURCE_REVIEW")
            state = "STALE" if (today - checked).days > 7 or (today - observed).days > 150 else item.get("status", "REVIEW")
            result["facts"].append(fact(item["label"], item["value"], observations["source"], item["sourceDate"], item["checkedAt"], state))
        return financial_summary(result)
    snap = (data.get("issuers") or {}).get(ticker)
    if not isinstance(snap, dict):
        return group("MISSING", "No matching saved SEC financial snapshot.")
    evidence = snap.get("evidence") or {}
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{identity['cik']}.json"
    checked = day(snap.get("as_of"))
    if (snap.get("ticker") != ticker or str(snap.get("cik")).zfill(10) != identity["cik"]
            or evidence.get("companyfacts_url") != url or not checked or checked > today):
        return group("IDENTITY_MISMATCH")
    result = group("OBSERVED", "Saved SEC observations; no completed financing or dilution clearance is inferred.")
    def add(label, value, key):
        proof = evidence.get(key) or {}
        observed, filed = day(proof.get("period_end")), day(proof.get("filed"))
        if (not number(value) or not observed or not filed or not observed <= filed <= checked
                or proof.get("form") not in {"10-Q", "10-K", "10-Q/A", "10-K/A"}
                or not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(proof.get("accession", "")))):
            return False
        state = "STALE" if (today - checked).days > 7 or (today - observed).days > 150 else "OBSERVED"
        result["facts"].append(fact(label, f"{value:,.2f}", url, observed.isoformat(), checked.isoformat(), state))
        return state == "OBSERVED"
    cash, flow, months = snap.get("cash_usd"), snap.get("operating_cash_flow_usd"), snap.get("operating_cash_flow_months")
    cash_ok = snap.get("cash_includes_restricted") is False and number(cash) and cash >= 0 and add("Cash and cash equivalents (USD)", cash, "cash")
    flow_ok = number(months) and months in (3, 12) and add(f"Operating cash flow ({months:g} months, USD)", flow, "operating_cash_flow")
    if (cash_ok and flow_ok and flow < 0 and not snap.get("review_flags")
            and evidence["cash"]["period_end"] == evidence["operating_cash_flow"]["period_end"]):
        value = cash_runway_months(cash, flow * 3 / months)
        result["facts"].append(fact("Cash-only runway (months, calculated)", f"{value:g}", url,
                                    evidence["cash"]["period_end"], checked.isoformat(), "CALCULATED"))
    for note in snap.get("review_flags") or []:
        result["facts"].append(fact("Financial review note", note, url, "", checked.isoformat(), "REVIEW"))
    for filing in snap.get("filing_review_queue") or []:
        link = urlparse(filing.get("source_url", ""))
        filed = day(filing.get("filed"))
        if link.scheme == "https" and link.hostname == "www.sec.gov" and not link.username and not link.password and filed and filed <= checked:
            result["facts"].append(fact("Financing filing — contents need review", filing.get("form", "") + " · " + filing.get("accession", ""),
                                        filing["source_url"], filed.isoformat(), checked.isoformat(), "REVIEW"))
    return financial_summary(result)


def source_evidence(program_id, exact_key, ticker, *, current=True, today=None, data=None):
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    clinical, financial = data if data is not None else sources()
    result = {"programId": program_id, "exactKey": exact_key, "ticker": ticker,
              "clinical": group("MISSING"), "financial": group("MISSING"),
              "researchOnly": True, "ordersEnabled": False, "assessmentScoreChange": False,
              "fsFaChanges": False, "financingRiskReviewed": False}
    identity = (financial.get("programs") or {}).get(exact_key)
    if (not current or not identity or identity.get("ticker") != ticker
            or not re.fullmatch(r"PDUFA-\d{6,}", str(program_id)) or not re.fullmatch(r"\d{10}", identity.get("cik", ""))):
        return result
    result["clinical"] = clinical_facts(identity.get("nctId"), exact_key, clinical.get("records") or {}, today)
    result["financial"] = financial_facts(ticker, identity, financial, today)
    return result
