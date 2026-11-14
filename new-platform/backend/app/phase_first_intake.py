"""Level 1 phase-first evidence intake, not a validated scientific prediction.

Never infer phase from trial status or the candidate's PDUFA date. Registry
snapshots dated after the assessment cutoff are ineligible for scoring.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlparse


def _date(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _secure_source(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlparse(value)
        return bool(parsed.scheme == "https" and parsed.hostname and not parsed.username
                    and not parsed.password and not any(ch.isspace() for ch in value))
    except ValueError:
        return False


def _source_matches_trial(source, trial_id):
    """Reject ClinicalTrials.gov evidence URLs pointing to another NCT trial."""
    try:
        parsed = urlparse(source)
        host = (parsed.hostname or "").lower()
        if host not in {"clinicaltrials.gov", "www.clinicaltrials.gov"}:
            return True
        path = parsed.path.rstrip("/").split("/")
        return len(path) >= 3 and path[-2] == "study" and path[-1] == trial_id
    except (TypeError, ValueError):
        return False


def phase_first_intake(registry, *, cutoff, registry_checked, endpoint_reviews=None):
    """Return an auditable, non-scoring Level 1 phase intake."""
    cutoff_day = _date(cutoff)
    checked_day = _date(registry_checked)
    updated = _date((registry.get("last_update_posted") or {}).get("date"))
    eligible = bool(cutoff_day and checked_day and updated
                    and updated <= checked_day <= cutoff_day)
    phases = registry.get("phases") or registry.get("phase") or []
    if isinstance(phases, str):
        phases = [phases]
    if not isinstance(phases, (list, tuple)):
        phases = []
    phases = [str(phase).upper().replace(" ", "") for phase in phases]
    known = {"EARLY_PHASE1", "PHASE1", "PHASE2", "PHASE3", "PHASE4"}
    # Multi-phase trials must not depend on the order of registry phase tags.
    order = {"EARLY_PHASE1": 0, "PHASE1": 1, "PHASE2": 2, "PHASE3": 3, "PHASE4": 4}
    status_value = registry.get("status")
    verified = eligible and bool(phases) and all(phase in known for phase in phases) and bool(status_value)
    phase = max(phases, key=order.__getitem__) if verified else None
    status = status_value if verified else None
    expected = []
    not_yet_expected = []
    if verified:
        expected = ["registry phase and status", "trial design", "primary endpoint definition"]
        if phase in {"PHASE2", "PHASE3", "PHASE4"}:
            expected.append("phase-appropriate efficacy and safety evidence")
        else:
            not_yet_expected.append("pivotal efficacy or marketing-application dossier")
        if phase in {"EARLY_PHASE1", "PHASE1", "PHASE2"}:
            not_yet_expected.append("completed Phase 3 results")
    design = registry.get("study_design") or {}
    design_info = design.get("designInfo") or {}
    endpoints = registry.get("primary_outcomes") or []
    evidence_inventory = {
        "registry phase and status": "OBSERVED" if verified else "UNVERIFIED",
        "trial design": ("OBSERVED" if verified and design_info else "MISSING" if verified else "UNVERIFIED"),
        "primary endpoint definition": ("OBSERVED" if verified and endpoints and all(
            isinstance(item, dict) and item.get("measure") and item.get("timeFrame") for item in endpoints
        ) else "MISSING" if verified else "UNVERIFIED"),
    }
    # Registry design metadata cannot establish clinical efficacy, safety, or
    # regulatory dossier completeness. These require separate source review.
    if verified and "phase-appropriate efficacy and safety evidence" in expected:
        evidence_inventory["phase-appropriate efficacy and safety evidence"] = "NOT_ASSESSED"
    # Record whether an endpoint has a definition, not whether the endpoint
    # was prespecified, clinically meaningful, or successfully met.
    endpoint_details = []
    if verified:
        for item in endpoints if isinstance(endpoints, list) else []:
            if isinstance(item, dict):
                endpoint_details.append({
                    "measure": item.get("measure"),
                    "timeFrame": item.get("timeFrame"),
                    "definitionStatus": "OBSERVED" if item.get("measure") and item.get("timeFrame") else "INCOMPLETE",
                    "scientificAdjudication": "NOT_ASSESSED",
                })
    endpoint_quality = {
        "definitionCompleteness": (
            "OBSERVED" if verified and endpoint_details and all(
                item["definitionStatus"] == "OBSERVED" for item in endpoint_details
            ) else "INCOMPLETE" if verified else "UNVERIFIED"
        ),
        "prespecification": "NOT_ASSESSED" if verified else "UNVERIFIED",
        "clinicalRelevance": "NOT_ASSESSED" if verified else "UNVERIFIED",
        "multiplicityControl": "NOT_ASSESSED" if verified else "UNVERIFIED",
        "estimandAndAnalysisPlan": "NOT_ASSESSED" if verified else "UNVERIFIED",
        "outcomeSuccess": "NOT_ASSESSED" if verified else "UNVERIFIED",
        "score": None,
        "reason": "Endpoint definition completeness is registry metadata, not scientific quality adjudication.",
    }
    # Independently reviewed evidence must be exact-trial, dated, sourced and
    # chronologically available. A review records a judgment, never a probability.
    review_criteria = {
        "prespecification", "clinicalRelevance", "multiplicityControl",
        "estimandAndAnalysisPlan", "outcomeSuccess",
    }
    reviewed_evidence = {}
    if verified and isinstance(endpoint_reviews, dict):
        for criterion in review_criteria:
            record = endpoint_reviews.get(criterion)
            if not isinstance(record, dict):
                continue
            evidence_day = _date(record.get("sourceDate"))
            review_day = _date(record.get("reviewedAt"))
            source = record.get("source")
            trial_id = registry.get("nct_id")
            judgment = record.get("judgment")
            if (judgment in {"SUPPORTS", "CONCERNS", "INCONCLUSIVE"}
                    and _secure_source(source)
                    and trial_id and record.get("nctId") == trial_id
                    and _source_matches_trial(source, trial_id)
                    and record.get("rationale") and evidence_day and review_day
                    and evidence_day <= review_day <= cutoff_day):
                endpoint_quality[criterion] = judgment
                reviewed_evidence[criterion] = {
                    "source": source,
                    "sourceDate": evidence_day.isoformat(),
                    "reviewedAt": review_day.isoformat(),
                    "nctId": trial_id,
                    "rationale": record["rationale"],
                }
    # A fully populated dossier is not automatically a scientifically valid
    # score. Separate the observed review consensus from a prediction.
    judgments = [endpoint_quality[name] for name in sorted(review_criteria)
                 if name in reviewed_evidence]
    if not verified:
        consensus = "BLOCKED_UNVERIFIED_PHASE"
    elif len(judgments) != len(review_criteria):
        consensus = "INSUFFICIENT_REVIEW_COVERAGE"
    elif "CONCERNS" in judgments and "SUPPORTS" in judgments:
        consensus = "MIXED_EVIDENCE"
    elif "INCONCLUSIVE" in judgments:
        consensus = "INCONCLUSIVE_EVIDENCE"
    elif all(judgment == "SUPPORTS" for judgment in judgments):
        consensus = "ALL_CRITERIA_SUPPORTIVE"
    elif all(judgment == "CONCERNS" for judgment in judgments):
        consensus = "ALL_CRITERIA_CONCERNING"
    else:
        consensus = "MIXED_EVIDENCE"
    endpoint_quality["reviewConsensus"] = consensus
    endpoint_quality["scientificScoreStatus"] = "NOT_VALIDATED"
    endpoint_quality["reviewedEvidence"] = reviewed_evidence
    endpoint_quality["reviewCoverage"] = {
        "reviewedCriteria": len(reviewed_evidence),
        "totalCriteria": len(review_criteria),
        "status": ("BLOCKED" if not verified else "ALL_REVIEWED" if len(reviewed_evidence) == len(review_criteria)
                   else "PARTIALLY_REVIEWED" if reviewed_evidence else "NOT_REVIEWED"),
        "note": "Coverage counts accepted review records, not independently verified science or predictive accuracy.",
    }
    missing = ([name for name, state in evidence_inventory.items() if state == "MISSING"]
               if verified else ["Verified phase and chronological registry provenance"])
    return {
        "level": 1,
        "name": "Phase-first evidence intake",
        "executionStatus": "INTAKE_ONLY" if verified else "BLOCKED_UNVERIFIED_PHASE",
        "scientificValidation": "NOT_VERIFIED",
        "fdaPrediction": "ABSTAIN",
        "phase": phase,
        "trialStatus": status,
        "registrySourceDate": updated.isoformat() if updated else None,
        "registryCheckedAt": checked_day.isoformat() if checked_day else None,
        "assessmentCutoff": cutoff_day.isoformat() if cutoff_day else None,
        "expectedEvidence": expected,
        "evidenceInventory": evidence_inventory,
        "endpointDefinitions": endpoint_details,
        "endpointQuality": endpoint_quality,
        "notYetExpected": not_yet_expected,
        "missingEvidence": missing,
        "requiresSourceReview": [name for name, state in evidence_inventory.items() if state == "NOT_ASSESSED"],
        "note": "OBSERVED means present in eligible registry metadata, not clinically adjudicated. NOT_ASSESSED requires separate source review; it is not missing evidence or scientific scoring.",
    }
