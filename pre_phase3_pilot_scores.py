"""Source-attributed *provisional* clinical research ratings for Phase 3 pilots.

These are dated editorial assessments, NOT FDA success probabilities or
independent attestations. They never satisfy the strict verified-score gate.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlparse
import re

RUBRIC = {
    "phase2_efficacy": 25, "phase3_design": 30,
    "safety": 15, "regulatory_alignment": 15,
    "execution": 10, "evidence_quality": 5,
}
FIELD_MAP = {
    "phase2_efficacy": "Phase 2 Efficacy /25",
    "phase3_design": "Phase 3 Design /30",
    "safety": "Safety /15",
    "regulatory_alignment": "Regulatory Alignment /15",
    "execution": "Execution /10",
    "evidence_quality": "Evidence Quality /5",
}
ACTIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING",
          "ENROLLING_BY_INVITATION"}
NCT = re.compile(r"^NCT\d{8}$")
URL_HOSTS = {
    "clinicaltrials.gov", "jamanetwork.com", "ir.trevitherapeutics.com",
    "ir.lbpharma.us", "www.globenewswire.com", "www.sec.gov",
}
BLOCKED_PRIMARY_TERMS = ("adverse event", "tolerability", "long term safety",
                         "long-term safety", "treatment emergent event")

SCORE_FIELDS = (
    "Preliminary clinical score /100",
    "Preliminary score status",
    *FIELD_MAP.values(),
    "Score Evidence",
    "Clinical Caveats",
)


def _day(value):
    try:
        return date.fromisoformat(str(value or "").strip())
    except (TypeError, ValueError):
        return None


def _valid_source(record, cutoff):
    if not isinstance(record, dict):
        return False
    parsed = urlparse(str(record.get("url") or "").strip())
    pub = _day(record.get("published"))
    return (parsed.scheme == "https"
            and parsed.hostname in URL_HOSTS
            and pub is not None and pub < cutoff
            and bool(str(record.get("assessment") or "").strip()))


def review_index(ledger, as_of):
    """Validate points, source dates, exact studies and provenance, fail closed."""
    cutoff = _day(as_of)
    if not cutoff:
        raise ValueError("Valid as_of day required")
    records = (ledger or {}).get("records", []) if isinstance(ledger, dict) else []
    matched = {}
    for record in records:
        try:
            ticker = str(record["ticker"]).strip().upper()
            nct = str(record["nct_id"]).strip().upper()
            p2_nct = str(record["phase2_nct_id"]).strip().upper()
            day = _day(record["assessment_cutoff"])
            scores = record["domain_points"]
            sources = record["domain_sources"]
            if not (re.fullmatch(r"[A-Z0-9.-]{1,15}", ticker)
                    and NCT.fullmatch(nct) and NCT.fullmatch(p2_nct)
                    and nct != p2_nct and day and day <= cutoff
                    and record.get("trial_type") == "PIVOTAL_EFFICACY"
                    and record.get("review_status") ==
                    "PRELIMINARY SOURCE-BASED ASSESSMENT — NOT INDEPENDENTLY ATTESTED"
                    and isinstance(scores, dict) and isinstance(sources, dict)
                    and set(scores) == set(RUBRIC) == set(sources)):
                continue
            if not all(type(scores[k]) in (int, float) and
                       0 <= scores[k] <= maximum and
                       _valid_source(sources[k], day)
                       for k, maximum in RUBRIC.items()):
                continue
            key = (ticker, nct)
            if key in matched:
                # Duplicate attestation conflict must never silently pick a winner.
                matched[key] = None
                continue
            matched[key] = record
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    return {key:value for key,value in matched.items() if value is not None}


def attach_preliminary_scores(trials, protocols, ledger, as_of):
    """Add numbers only to exact prospective pivotal efficacy trials.

    Note: the existing strict verified score and its status are untouched.
    """
    index = review_index(ledger, as_of)
    by_nct = {str(p.get("nct_id") or "").upper():p
              for p in (protocols or []) if isinstance(p,dict)}
    records = []
    for item in trials or []:
        row = item.copy()
        for field in SCORE_FIELDS:
            row[field] = None if field == "Preliminary clinical score /100" or field in FIELD_MAP.values() else ""
        key = (str(row.get("Ticker") or "").upper(), str(row.get("NCT ID") or "").upper())
        record = index.get(key)
        protocol = by_nct.get(key[1], {})
        primary = str(protocol.get("primary_endpoint") or "").strip().lower()
        comparator = str(protocol.get("comparator") or "").strip()
        status = str(row.get("Registry status") or "").upper()
        src = str(row.get("NCT source") or "").strip()
        if not (record
                and row.get("Trial phase") == "Phase 3"
                and status in ACTIVE
                and not str(row.get("Registry results posted") or "").strip()
                and src == "https://clinicaltrials.gov/study/" + key[1]
                and str(protocol.get("source_url") or "") == src
                and primary and comparator
                and not any(term in primary for term in BLOCKED_PRIMARY_TERMS)
                and str(row.get("Drug") or "").lower().find(
                    str(record.get("drug") or "").lower()) >= 0
                and str(row.get("Indication") or "").lower().find(
                    str(record.get("indication") or "").lower()) >= 0):
            records.append(row)
            continue
        points = record["domain_points"]
        row["Preliminary clinical score /100"] = sum(points.values())
        row["Preliminary score status"] = (
            "PROVISIONAL /100 — SOURCE-CITED ANALYST ASSESSMENT; NOT AUDITED OR CALIBRATED"
        )
        for key_name, field in FIELD_MAP.items():
            row[field] = points[key_name]
        row["Score Evidence"] = " | ".join(
            record["domain_sources"][k]["url"] for k in RUBRIC
        )
        row["Clinical Caveats"] = record.get("clinical_caveats", "")
        if str(row.get("Company/program identity") or "") != "VERIFIED":
            row["Clinical Caveats"] += " Program identity remains flagged REVIEW in automated ledger."
        records.append(row)
    return records
