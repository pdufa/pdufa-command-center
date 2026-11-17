"""Level 12 conservative cross-study registry identity and cohort screen.

An official registry URL/dated retrieval is a source lead, never proof of a
replicated efficacy result or scientifically independent patient cohort.
"""
from __future__ import annotations
from datetime import date
import re
from urllib.parse import urlparse

VERSION = "scientific-replication-candidate-screen-v1"
_NCT = re.compile(r"NCT[0-9]{8}")
_CONTEXT = ("population", "endpoint", "timeFrame")


def _day(value):
    if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _official_registry(record, nct):
    if not isinstance(record, str):
        return False
    try:
        parsed = urlparse(record)
        return (parsed.scheme == "https" and
                parsed.hostname in {"clinicaltrials.gov", "www.clinicaltrials.gov"}
                and not parsed.username and not parsed.password and
                not parsed.query and not parsed.fragment and
                parsed.path.rstrip("/") in {
                    "/study/" + nct, "/api/v2/studies/" + nct
                })
    except ValueError:
        return False


def _context(value):
    if not isinstance(value, dict):
        return None
    fields = {}
    for field in _CONTEXT:
        entry = value.get(field)
        if not isinstance(entry, str) or not 0 < len(entry.strip()) <= 400:
            return None
        fields[field] = entry.strip()
    return fields


def screen_replication_candidates(level_twelve, evidence, *, trial_id, cutoff):
    base = {
        "methodVersion": VERSION,
        "status": "NOT_ASSESSED",
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "score": None,
        "replicationEstablished": False,
        "independentCohortsEstablished": False,
        "limitations": [
            "Distinct registry IDs do not establish independent patient cohorts or replicated effects.",
            "Endpoint and population name matching is structural only, not clinical comparability.",
            "No outcome comparison, meta-analysis, confidence interval, clinical conclusion or FDA probability is calculated.",
        ],
    }
    if not isinstance(level_twelve, dict) or not isinstance(evidence, dict):
        return {**base, "reason": "Reviewed candidate-study source contract required."}
    accepted = level_twelve.get("acceptedEvidence")
    parent = accepted.get("independentStudyIdentity") if isinstance(accepted, dict) else None
    if (not isinstance(parent, dict) or parent.get("sourceVerified") is not True
            or parent.get("retrievalProvenance") != "RECORDED"
            or parent.get("nctId") != trial_id):
        return {**base, "reason": "Reviewed target-trial evidence and retrieval receipt required."}
    record = evidence.get("12.independentStudyIdentity") or {}
    data = record.get("measurements") if isinstance(record, dict) else None
    if not isinstance(data, dict):
        return {**base, "status": "REJECTED_MEASUREMENTS",
                "reason": "Explicit target context and candidate registry references required."}
    target = _context(data.get("target"))
    studies = data.get("studies")
    cutoff_day = _day(cutoff)
    if not target or not isinstance(studies, list) or len(studies) > 100 or not cutoff_day:
        return {**base, "status": "REJECTED_MEASUREMENTS",
                "reason": "Valid target population, endpoint, timeframe, cutoff and bounded studies list required."}
    if not studies:
        return {**base, "status": "NO_REVIEWED_CANDIDATE_STUDIES",
                "reason": "The submitted source record lists no comparator studies; this does not establish none exist."}
    observed_ncts = set()
    cohorts = {}
    rows = []
    for study in studies:
        if not isinstance(study, dict):
            return {**base, "status": "REJECTED_MEASUREMENTS", "reason": "Invalid study record."}
        nct = study.get("nctId")
        source = study.get("registryUrl")
        cohort = study.get("cohortKey")
        study_context = _context(study)
        published = _day(study.get("registryRecordDate"))
        retrieved = _day(study.get("sourceRetrievedAt"))
        if (not isinstance(nct, str) or _NCT.fullmatch(nct) is None
                or nct == trial_id or nct in observed_ncts
                or not _official_registry(source, nct)
                or not isinstance(cohort, str) or not 0 < len(cohort.strip()) <= 200
                or study_context is None
                or not published or not retrieved or not published <= retrieved <= cutoff_day):
            return {**base, "status": "REJECTED_MEASUREMENTS",
                    "reason": "Missing/duplicate/wrong exact NCT, official source, bounded cohort, clinical context or chronology."}
        observed_ncts.add(nct)
        cohorts.setdefault(cohort.strip().casefold(), []).append(nct)
        mismatch = [key for key in _CONTEXT
                    if target[key].casefold() != study_context[key].casefold()]
        rows.append({
            "nctId": nct, "registryUrl": source,
            "registryRecordDate": study["registryRecordDate"],
            "sourceRetrievedAt": study["sourceRetrievedAt"],
            "cohortKey": cohort.strip(),
            "contextDifferences": mismatch,
            "structuralContextMatch": not mismatch,
            "independenceVerified": False,
        })
    overlaps = sorted([group for group in cohorts.values() if len(group) > 1],
                      key=lambda row: row[0])
    return {
        **base,
        "status": "COHORT_OVERLAP_REQUIRES_REVIEW" if overlaps else "SOURCE_CANDIDATE_INVENTORY_ONLY",
        "targetNct": trial_id,
        "targetContext": target,
        "candidateStudies": rows,
        "declaredCohortCollisions": overlaps,
        "note": "Even when no overlap is declared, trial independence and replication remain unverified.",
    }
