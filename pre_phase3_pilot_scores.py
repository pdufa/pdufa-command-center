"""Source-attributed *provisional* clinical research ratings for Phase 3 pilots.

These are dated editorial assessments, NOT FDA success probabilities or
independent attestations. They never satisfy the strict verified-score gate.
"""
from __future__ import annotations

from datetime import date, timedelta
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
    "Clinical score as of",
    "Clinical rationale",
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
                    and str(record.get("drug") or "").strip()
                    and str(record.get("registry_drug") or "").strip()
                    and str(record.get("indication") or "").strip()
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


def reviewed_phase2_link(row, review, as_of):
    """Use a dated exact-study source to resolve a recorded dose-name alias.

    This does not change registry drug names, program verification, scores,
    issuer readout status or entry eligibility. Never join by ticker alone.
    """
    cutoff = _day(as_of)
    if not review or not cutoff:
        return "", ""
    for field, target in (("ticker", "ticker"), ("nct_id", "nct_id"),
                          ("drug", "registry_drug"), ("indication", "indication")):
        if str(row.get(field) or "").strip().casefold() != str(review.get(target) or "").strip().casefold():
            return "", ""
    link_source = review.get("phase2_link_source")
    if not _valid_source(link_source, cutoff):
        return "", ""
    p2 = str(review.get("phase2_nct_id") or "")
    if not NCT.fullmatch(p2):
        return "", ""
    return p2, link_source["url"]


def classify_phase3_protocol(protocol, nct):
    """Classify pivotal *design* only; not issuer outcome or registration success."""
    proto = protocol or {}
    source = "https://clinicaltrials.gov/study/" + str(nct or "")
    endpoint = str(proto.get("primary_endpoint") or "").strip().lower()
    status = str(proto.get("registry_overall_status") or "").strip().upper()
    allocation = str(proto.get("allocation") or "").strip().upper()
    comparator = str(proto.get("comparator") or "").strip()
    posted = str(proto.get("registry_results_first_posted") or "").strip()
    if proto.get("source_url") != source:
        return "REVIEW — EXACT NCT PROTOCOL MISSING"
    if posted:
        return "RESULT POSTED — NOT PRE-READOUT"
    if any(term in endpoint for term in BLOCKED_PRIMARY_TERMS) or (
            not comparator and "SINGLE_GROUP" in str(proto.get("intervention_model") or "").upper()):
        return "NON-PIVOTAL EFFICACY — SAFETY / OPEN LABEL"
    if status not in ACTIVE:
        return "REVIEW — PROTOCOL STATUS UNVERIFIED"
    if (allocation == "RANDOMIZED" and comparator and endpoint):
        return "PIVOTAL EFFICACY DESIGN — SOURCE CHECKED"
    return "REVIEW — EFFICACY DESIGN NOT VERIFIED"


def attach_preliminary_scores(trials, protocols, ledger, as_of):
    """Add numbers only to exact prospective pivotal efficacy trials.

    Note: the existing strict verified score and its status are untouched.
    """
    index = review_index(ledger, as_of)
    cutoff = _day(as_of)
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
        status = str(row.get("Registry status") or "").upper()
        design_type = classify_phase3_protocol(protocol, key[1])
        src = str(row.get("NCT source") or "").strip()
        if not (record
                and row.get("Trial phase") == "Phase 3"
                and status in ACTIVE
                and not str(row.get("Registry results posted") or "").strip()
                and src == "https://clinicaltrials.gov/study/" + key[1]
                and str(protocol.get("source_url") or "") == src
                and design_type == "PIVOTAL EFFICACY DESIGN — SOURCE CHECKED"
                and row.get("Registry check") == "RECENT"
                and row.get("Protocol check") == "RECENT"
                and _day(str(protocol.get("checked_at") or "")[:10]) is not None
                and cutoff - timedelta(days=2) <= _day(str(protocol.get("checked_at"))[:10]) <= cutoff
                and _day(protocol.get("source_updated")) is not None
                and _day(protocol.get("source_updated")) <= cutoff
                and str(row.get("Drug") or "").strip().casefold() ==
                    str(record.get("registry_drug") or "").strip().casefold()
                and str(row.get("Indication") or "").strip().casefold() ==
                    str(record.get("indication") or "").strip().casefold()):
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
        row["Clinical score as of"] = record["assessment_cutoff"]
        row["Clinical rationale"] = " | ".join(
            f"{FIELD_MAP[k]}: {points[k]}. {record['domain_sources'][k]['assessment']}"
            for k in RUBRIC
        )
        if str(row.get("Company/program identity") or "") != "VERIFIED":
            row["Clinical Caveats"] += " Program identity remains flagged REVIEW in automated ledger."
        records.append(row)
    return records
