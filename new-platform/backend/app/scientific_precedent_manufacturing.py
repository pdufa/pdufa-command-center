"""Levels 15–16 source-bound FDA precedent and CMC/inspection context screens.

These records never infer the current application action from historical outcomes
or nonpublic manufacturing information. Source review is not FDA certification.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlparse

VERSION = "scientific-precedent-cmc-screen-v1"
_APP = re.compile(r"[0-9]{6}")
_TYPES = {"BLA", "NDA", "ANDA"}
_ACTIONS = {"APPROVAL", "COMPLETE_RESPONSE", "OTHER", "UNKNOWN"}


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _original_fda(url):
    try:
        p = urlparse(url)
        return p.scheme == "https" and (p.hostname == "fda.gov" or
            (p.hostname or "").lower().endswith(".fda.gov")) and not p.username and not p.password
    except (TypeError, ValueError):
        return False


def _reviewed(level, evidence, key, need_official=True):
    accepted = level.get("acceptedEvidence") if isinstance(level, dict) else None
    rec = accepted.get(key) if isinstance(accepted, dict) else None
    raw = evidence.get(f"{level['level']}.{key}") if isinstance(evidence, dict) and isinstance(level, dict) else None
    if (not isinstance(rec, dict) or rec.get("sourceVerified") is not True
            or rec.get("retrievalProvenance") != "RECORDED"
            or (need_official and not _original_fda(rec.get("source")))
            or not isinstance(raw, dict) or not isinstance(raw.get("measurements"), dict)):
        return None, None
    return raw["measurements"], rec


def _app(value):
    if not isinstance(value, dict):
        return None
    kind, number, cycle = value.get("applicationType"), value.get("applicationNumber"), value.get("reviewCycle")
    if kind not in _TYPES or not isinstance(number, str) or not _APP.fullmatch(number) or type(cycle) is not int or not 1 <= cycle <= 20:
        return None
    return {"applicationType": kind, "applicationNumber": number, "reviewCycle": cycle}


def assess_precedent(level, evidence, *, cutoff, filing_context=None):
    base = {"methodVersion": VERSION, "status": "NOT_ASSESSED",
            "score": None, "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
            "precedentPredictsTargetOutcome": False,
            "limitations": [
                "Prior FDA actions are not a validated comparator for the target application.",
                "Target-app outcome must not enter a prospective source bundle.",
                "Similar indication or modality does not establish matching FDA review standards or causality.",
            ]}
    target = ((filing_context or {}).get("candidateApplicationCycle")
              if isinstance(filing_context, dict) else None)
    target_app = _app(target)
    if target_app is None:
        return {**base, "reason": "Exact target application/cycle mapping must be reconciled before comparing precedents."}
    raw, receipt = _reviewed(level, evidence, "precedentSelection")
    if raw is None:
        return {**base, "reason": "Source-reviewed original FDA precedent record required."}
    prior_app = _app(raw)
    action = raw.get("officialAction")
    decided, asof = _day(raw.get("officialActionDate")), _day(cutoff)
    indication, modality = raw.get("indication"), raw.get("modality")
    if (prior_app is None or prior_app == target_app or
            prior_app["applicationType"] == target_app["applicationType"]
            and prior_app["applicationNumber"] == target_app["applicationNumber"]
            or action not in _ACTIONS or not decided or not asof or decided > asof
            or not isinstance(indication, str) or not 0 < len(indication.strip()) <= 400
            or not isinstance(modality, str) or not 0 < len(modality.strip()) <= 400):
        return {**base, "status": "REJECTED_PRECEDENT",
                "reason": "Different exact FDA application, historical dated official action, indication and modality required."}
    return {**base, "status": "HISTORICAL_PRECEDENT_SOURCE_ONLY",
            "targetApplication": target_app, "precedentApplication": prior_app,
            "officialAction": action, "officialActionDate": decided.isoformat(),
            "indication": indication.strip(), "modality": modality.strip(),
            "officialSource": receipt["source"],
            "clinicalComparability": "NOT_ESTABLISHED",
            "reason": "A prior official action is a historical record, not a target prediction."}


def assess_manufacturing(level, evidence, *, cutoff, filing_context=None):
    base = {"methodVersion": VERSION, "status": "NOT_ASSESSED",
            "score": None, "fdaPrediction": "ABSTAIN", "scientificValidation": "NOT_VERIFIED",
            "manufacturingRiskJudgment": None, "inspectionDeficiencyEstablished": False,
            "limitations": [
                "Missing, private or nonpublic CMC and inspection information remains UNKNOWN, not a failure.",
                "A disclosed facility record does not establish application-specific quality clearance.",
                "No approval, regulatory review timing or trading conclusion is inferred.",
            ]}
    target = ((filing_context or {}).get("candidateApplicationCycle")
              if isinstance(filing_context, dict) else None)
    app = _app(target)
    if app is None:
        return {**base, "reason": "Exact application/cycle mapping unresolved; manufacturing findings cannot be attributed."}
    raw, receipt = _reviewed(level, evidence, "inspectionEvidence")
    if raw is None:
        return {**base, "status": "NO_REVIEWED_PUBLIC_INSPECTION_RECORD",
                "application": app, "informationAvailability": "UNKNOWN",
                "reason": "No source-reviewed application-specific public inspection record."}
    finding = raw.get("publicInformation")
    if finding not in {"PUBLIC_RECORD_EXISTS", "PUBLIC_RECORD_UNAVAILABLE"}:
        return {**base, "status": "REJECTED_MEASUREMENTS",
                "reason": "Public-record availability must be stated explicitly."}
    rawapp = _app(raw)
    if rawapp != app:
        return {**base, "status": "REJECTED_APPLICATION_LINK",
                "reason": "Inspection record must explicitly match target application and review cycle."}
    asof, checked = _day(cutoff), _day(raw.get("checkedAt"))
    if not asof or not checked or checked > asof:
        return {**base, "status": "REJECTED_CHRONOLOGY",
                "reason": "Original public-record check date must precede assessment cutoff."}
    facility = raw.get("facilityIdentifier")
    if finding == "PUBLIC_RECORD_EXISTS" and (
            not isinstance(facility, str) or not 0 < len(facility.strip()) <= 200):
        return {**base, "status": "REJECTED_MEASUREMENTS",
                "reason": "Actual public facility identifier required for claimed public record."}
    return {**base,
            "status": "PUBLIC_RECORD_REVIEW_REQUIRED" if finding == "PUBLIC_RECORD_EXISTS" else "NONPUBLIC_OR_UNAVAILABLE_REMAINS_UNKNOWN",
            "application": app, "facilityIdentifier": facility.strip() if finding == "PUBLIC_RECORD_EXISTS" else None,
            "informationAvailability": finding,
            "publicSource": receipt["source"],
            "checkedAt": checked.isoformat(),
            "reason": "Reviewed public-record availability does not prove presence or absence of actual manufacturing deficiencies."}
