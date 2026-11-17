"""Levels 13–14 original-source regulatory identity and designation reconciliation.

Only source-reviewed official FDA records are eligible. Trial NCT and application
cycle must be explicit; no company/ticker inference, predicted FDA decision,
approval probability, designation inference, or fabrication of agency status.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlparse
from .scientific_event_chronology import event_covered_by_review

VERSION = "scientific-regulatory-context-v1"
_TYPES = {"NDA", "BLA", "ANDA"}
_DESIGNATIONS = {"BREAKTHROUGH_THERAPY", "FAST_TRACK", "PRIORITY_REVIEW",
                 "ACCELERATED_APPROVAL", "ORPHAN_DRUG", "RMAT"}
_NCT = re.compile(r"NCT[0-9]{8}")
_APP = re.compile(r"[0-9]{6}")


def _date(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _official_fda(url):
    try:
        p = urlparse(url)
        return (p.scheme == "https" and bool(p.hostname)
                and (p.hostname.lower() == "fda.gov" or p.hostname.lower().endswith(".fda.gov"))
                and not p.username and not p.password)
    except (TypeError, ValueError):
        return False


def _record(level, evidence, criterion, *, official=True):
    review = (level or {}).get("acceptedEvidence") if isinstance(level, dict) else None
    receipt = review.get(criterion) if isinstance(review, dict) else None
    raw = (evidence or {}).get(f"{level['level']}.{criterion}") if isinstance(evidence, dict) and isinstance(level, dict) else None
    if not isinstance(receipt, dict) or receipt.get("sourceVerified") is not True or receipt.get("retrievalProvenance") != "RECORDED":
        return None
    if official and not _official_fda(receipt.get("source")):
        return None
    if not isinstance(raw, dict) or not isinstance(raw.get("measurements"), dict):
        return None
    return raw["measurements"]


def _app_identity(value, trial_id):
    if not isinstance(value, dict):
        return None
    app_type, number, cycle, indication = (
        value.get("applicationType"), value.get("applicationNumber"),
        value.get("reviewCycle"), value.get("indication"))
    nct = value.get("linkedNct")
    if (app_type not in _TYPES or not isinstance(number, str) or not _APP.fullmatch(number)
            or type(cycle) is not int or not 1 <= cycle <= 20
            or not isinstance(indication, str) or not 0 < len(indication.strip()) <= 400
            or nct != trial_id or not isinstance(nct, str) or not _NCT.fullmatch(nct)):
        return None
    return {"applicationType": app_type, "applicationNumber": number,
            "reviewCycle": cycle, "indication": indication.strip(), "linkedNct": trial_id}


def assess_filing(level, evidence, *, trial_id, cutoff):
    base = {
        "methodVersion": VERSION, "status": "NOT_ASSESSED",
        "score": None, "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
        "fdaFilingVerified": False, "approvalStatus": "NOT_INFERRED",
        "limitations": [
            "Reviewed source fields and matching application IDs do not independently authenticate an FDA filing or its status.",
            "A filing acceptance is not a drug approval and does not imply a successful review.",
            "No application may be inferred solely from sponsor, ticker, NCT or proposed commercial indication.",
        ],
    }
    identity = _record(level, evidence, "exactApplicationIdentity")
    filing = _record(level, evidence, "acceptedFiling")
    if identity is None or filing is None:
        return {**base, "reason": "Exact reviewed FDA application identity and filing acceptance sources are required."}
    app = _app_identity(identity, trial_id)
    linked = _app_identity(filing, trial_id)
    if app is None or linked is None or app != linked:
        return {**base, "status": "REJECTED_IDENTITY",
                "reason": "Both original-source records must explicitly agree on exact NCT, indication, application ID and review cycle."}
    received, accepted, asof = (_date(filing.get("receivedDate")),
                                _date(filing.get("acceptanceDate")), _date(cutoff))
    if (not received or not accepted or not asof or not received <= accepted <= asof
            or not event_covered_by_review(level, "acceptedFiling", accepted, cutoff)):
        return {**base, "status": "REJECTED_CHRONOLOGY",
                "reason": "Both receipt and filing-acceptance dates must be exact and no later than the assessment cutoff."}
    return {**base, "status": "DATED_FILING_RECORDS_RECONCILED_NOT_AGENCY_CERTIFICATION",
            "candidateApplicationCycle": app,
            "receivedDate": received.isoformat(), "acceptanceDate": accepted.isoformat(),
            "sourceProvenance": {
                criterion: level["acceptedEvidence"][criterion]["source"]
                for criterion in ("exactApplicationIdentity", "acceptedFiling")
            },
            "nextReview": "Confirm application/indication/cycle correspondence against original agency documents and owner assessment."}


def assess_designation(level, evidence, *, trial_id, cutoff, filing_context=None):
    base = {
        "methodVersion": VERSION, "status": "NOT_ASSESSED", "score": None,
        "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
        "officialDesignationConfirmed": False, "approvalStatus": "NOT_INFERRED",
        "limitations": [
            "FDA designations, pathways and filing status are distinct; designation does not guarantee approval.",
            "A reviewed designation lead requires indication-specific official original document adjudication.",
            "Pre-application designations need not possess an NDA/BLA number; missing filing ID is not a defect.",
        ],
    }
    values = _record(level, evidence, "officialDesignationEvidence")
    if values is None:
        return {**base, "reason": "Source-reviewed original FDA designation evidence required."}
    designation = values.get("designation")
    nct, indication = values.get("linkedNct"), values.get("indication")
    issued, asof = _date(values.get("designationDate")), _date(cutoff)
    if (designation not in _DESIGNATIONS or nct != trial_id
            or not isinstance(indication, str) or not 0 < len(indication.strip()) <= 400
            or not issued or not asof or issued > asof
            or not event_covered_by_review(level, "officialDesignationEvidence", issued, cutoff)):
        return {**base, "status": "REJECTED_MEASUREMENTS",
                "reason": "Designation, exact trial, indication and valid original announcement date must precede cutoff."}
    app = ((filing_context or {}).get("candidateApplicationCycle")
           if isinstance(filing_context, dict) else None)
    if isinstance(app, dict):
        if indication.strip().casefold() != app["indication"].casefold():
            relation = "INDICATION_DISAGREEMENT"
        else:
            relation = "DECLARED_INDICATION_MATCH_REQUIRES_AGENCY_REVIEW"
    else:
        relation = "PRE_APPLICATION_OR_UNMAPPED"
    return {**base,
            "status": "SOURCE_REVIEWED_DESIGNATION_LEAD_ONLY",
            "designation": designation,
            "designationDate": issued.isoformat(),
            "linkedNct": trial_id, "indication": indication.strip(),
            "applicationRelationship": relation,
            "source": level["acceptedEvidence"]["officialDesignationEvidence"]["source"]}
