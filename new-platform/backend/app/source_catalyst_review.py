"""Isolated primary-source date reviews; never assigns an assessment grade."""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

PRIMARY_HOSTS = {
    "www.sec.gov", "sec.gov", "investors.cogentbio.com", "ir.mineralystx.com",
    "ir.intelliatx.com", "investors.savarapharma.com", "investor.bridgebio.com",
    "www.capricor.com", "ir.corcept.com", "ir.cytokinetics.com", "ir.ionis.com",
    "smmttx.com", "ir.celldex.com", "ir.moonlaketx.com",
}


def _day(value):
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


@lru_cache(maxsize=1)
def catalog():
    value = json.loads(Path(__file__).with_name("source_catalyst_reviews.json").read_text())
    if (value.get("schemaVersion") != 1 or value.get("kind") != "isolated-primary-catalyst-reviews"
            or not isinstance(value.get("programs"), dict) or len(value["programs"]) > 1000):
        raise ValueError("Invalid isolated primary-source catalog")
    return value


def primary_catalyst_review(program_id, exact_key, ticker, reported_date, *, current=True, today=None, data=None):
    today = today or datetime.now(ZoneInfo("America/Los_Angeles")).date()
    item = ((data if data is not None else catalog())["programs"]).get(exact_key)
    result = {"programId": program_id, "exactKey": exact_key, "status": "NO_SOURCE_REVIEW",
              "catalystVerified": False, "source": "", "sourceDate": "", "checkedAt": "",
              "eventType": None, "eventDate": None, "note": "No primary-source date review recorded.",
              "researchOnly": True, "ordersEnabled": False, "assessmentScoreChange": False,
              "fsFaChange": False}
    if not isinstance(item, dict):
        return result
    if (not re.fullmatch(r"PDUFA-[0-9]{6,}", str(program_id)) or item.get("exactKey") != exact_key
            or item.get("ticker") != ticker):
        result.update(status="IDENTITY_MISMATCH", note="Primary-source evidence belongs to another exact program.")
        return result
    if not current:
        result.update(status="PROGRAM_NOT_CURRENT", note="Current program identity could not be reconciled.")
        return result
    source = item.get("sourceUrl", "")
    try:
        url = urlparse(source)
        valid_source = (url.scheme == "https" and url.hostname in PRIMARY_HOSTS
                        and not url.username and not url.password and not any(ch.isspace() for ch in source))
    except (ValueError, TypeError):
        valid_source = False
    published, reviewed = _day(item.get("sourcePublishedOn")), _day(item.get("reviewedOn"))
    if (not valid_source or not published or not reviewed or not published <= reviewed <= today
            or not str(item.get("note") or "").strip()):
        result.update(status="INVALID_SOURCE_REVIEW", note="A dated primary-source review is required.")
        return result
    result.update(source=source, sourceDate=published.isoformat(), checkedAt=reviewed.isoformat(),
                  eventType=item.get("eventType"), eventDate=item.get("eventDate"), note=item["note"],
                  sourceKind=item.get("sourceKind"), historicalReadoutDate=item.get("historicalReadoutDate"),
                  issuerFinancingObservations=deepcopy(item.get("issuerFinancingObservations") or []))
    if (today - reviewed).days > 7:
        result.update(status="STALE", note="Primary-source review needs a fresh check after seven days.")
        return result
    if item.get("status") == "READOUT_ALREADY_REPORTED":
        historical = _day(item.get("historicalReadoutDate"))
        if (exact_key == "TRIAL|" + str(item.get("trialId")) and historical and historical <= published
                and item.get("eventDate") is None and item.get("dateConfirmed") is False
                and item.get("eventType") == "PUBLIC_READOUT" and item.get("sourceKind") == "ISSUER_PUBLIC_READOUT"):
            result.update(status="READOUT_ALREADY_REPORTED")
        else:
            result.update(status="INVALID_SOURCE_REVIEW")
        return result
    event_day = _day(item.get("eventDate"))
    if (not exact_key.startswith("APPLICATION|") or item.get("status") != "CONFIRMED_TARGET"
            or item.get("sourceKind") != "ISSUER_FDA_DATE_DISCLOSURE" or item.get("eventType") != "PDUFA"
            or item.get("dateConfirmed") is not True or not event_day):
        result.update(status="INVALID_SOURCE_REVIEW")
    elif event_day < today:
        result.update(status="PAST_EVENT", note="The primary-source target date has passed; outcome review is required.")
    elif reported_date != event_day.isoformat():
        result.update(status="CONFLICTING_DATE", note="Primary-source and currently reported program dates disagree.")
    else:
        result.update(status="CONFIRMED", catalystVerified=True)
    return result


def apply_primary_catalyst(risk_review, primary):
    """Use a confirmed date as a factual input; keep all 21 numeric grades intact."""
    result = deepcopy(risk_review)
    if (primary.get("status") != "CONFIRMED" or primary.get("catalystVerified") is not True
            or result.get("identityStatus") != "EXACT_IDENTITY_MATCH"
            or primary.get("programId") != result.get("programId")
            or primary.get("exactKey") != result.get("exactKey") or result.get("catalystVerified") is True):
        return result
    checks = result.get("checks") or []
    matches = [c for c in checks if c.get("id") == "catalystTiming"]
    if len(matches) != 1:
        return result
    matches[0].update(status="REVIEWED", source=primary["source"], checkedAt=primary["checkedAt"],
                      sourceDate=primary["sourceDate"], value={"eventType": primary["eventType"],
                      "eventDate": primary["eventDate"], "reviewMethod": "PRIMARY_SOURCE_DATE_ONLY"},
                      reason="Primary-source target date confirmed; assessment grades are unchanged.")
    result.update(catalystVerified=True,
                  status="REVIEWED" if result.get("financingRiskReviewed") is True else "REVIEW_REQUIRED",
                  missingEvidence=[c["label"] for c in checks if c["status"] != "REVIEWED"])
    return result
