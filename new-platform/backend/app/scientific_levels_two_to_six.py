"""Phase-aware scientific assessment contracts for Levels 2–6.

These are executable evidence-readiness checks, NOT validated efficacy scores
or FDA approval probabilities. Missing and not-yet-expected are distinct.
"""
from __future__ import annotations

from datetime import date
from urllib.parse import urlparse

LEVELS = {
    2: ("Trial design and methodology", (
        "protocol", "randomizationAndControl", "blindingAndBias",
        "populationAndEligibility", "sampleSizeRationale")),
    3: ("Statistical analysis and efficacy", (
        "statisticalAnalysisPlan", "primaryEndpointResults", "effectSizeAndPrecision",
        "missingDataHandling", "multiplicityAdjustment")),
    4: ("Safety and benefit-risk", (
        "adverseEvents", "seriousAdverseEvents", "exposureAndFollowup",
        "discontinuations", "benefitRiskInterpretation")),
    5: ("Indication-specific clinical assessment", (
        "indicationDefinition", "standardOfCareComparator", "clinicalMeaningfulness",
        "subgroupGeneralizability", "unmetNeedContext")),
    6: ("FDA regulatory readiness", (
        "regulatoryPathway", "agencyInteractions", "applicationDossier",
        "manufacturingReadiness", "labelingAndRiskMitigation")),
}
# Requirements that are not normally due at early-phase intake. Absence
# must not be treated as an adverse scientific finding.
LATE_PHASE = {
    (3, "primaryEndpointResults"), (3, "effectSizeAndPrecision"),
    (4, "benefitRiskInterpretation"), (6, "applicationDossier"),
    (6, "manufacturingReadiness"), (6, "labelingAndRiskMitigation"),
}


def _day(value):
    try:
        return date.fromisoformat(str(value or "")[:10])
    except ValueError:
        return None


def _valid_url(value):
    if not isinstance(value, str) or any(ch.isspace() for ch in value):
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def _source_matches_trial(url, trial_id):
    """Reject a ClinicalTrials.gov study URL that names another trial."""
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()
        if host not in {"clinicaltrials.gov", "www.clinicaltrials.gov"}:
            return True
        parts = parsed.path.rstrip("/").split("/")
        return len(parts) >= 3 and parts[-2] == "study" and parts[-1] == trial_id
    except (TypeError, ValueError):
        return False


def assess_levels_two_to_six(level_one, *, trial_id, evidence=None):
    """Return independent level inventories; never convert coverage into a score."""
    evidence = evidence if isinstance(evidence, dict) else {}
    phase = level_one.get("phase")
    cutoff = _day(level_one.get("assessmentCutoff"))
    verified = level_one.get("executionStatus") == "INTAKE_ONLY" and bool(trial_id) and bool(cutoff)
    early = phase in {"EARLY_PHASE1", "PHASE1", "PHASE2"}
    results = {}
    for number, (name, criteria) in LEVELS.items():
        states = {}
        accepted = {}
        for criterion in criteria:
            key = f"{number}.{criterion}"
            if not verified:
                states[criterion] = "BLOCKED_UNVERIFIED_PHASE"
                continue
            if early and (number, criterion) in LATE_PHASE:
                states[criterion] = "NOT_YET_EXPECTED"
                continue
            record = evidence.get(key)
            if not isinstance(record, dict):
                states[criterion] = "NOT_ASSESSED"
                continue
            source_day = _day(record.get("sourceDate"))
            review_day = _day(record.get("reviewedAt"))
            url = record.get("source")
            if (record.get("nctId") != trial_id or not _valid_url(url)
                    or not _source_matches_trial(url, trial_id)
                    or not source_day or not review_day
                    or not source_day <= review_day <= cutoff
                    or record.get("judgment") not in {"SUPPORTS", "CONCERNS", "INCONCLUSIVE"}
                    or not isinstance(record.get("rationale"), str)
                    or not record["rationale"].strip()):
                states[criterion] = "REJECTED_EVIDENCE"
                continue
            states[criterion] = record["judgment"]
            accepted[criterion] = {
                "source": url, "sourceDate": source_day.isoformat(),
                "reviewedAt": review_day.isoformat(),
                "nctId": trial_id, "rationale": record["rationale"],
            }
        required = [c for c in criteria if states[c] != "NOT_YET_EXPECTED"]
        results[str(number)] = {
            "level": number, "name": name,
            "status": ("BLOCKED_UNVERIFIED_PHASE" if not verified else
                       "REVIEWED" if required and all(c in accepted for c in required) else
                       "PARTIAL" if accepted else "AWAITING_REVIEW"),
            "criteria": states, "acceptedEvidence": accepted,
            "reviewedCount": len(accepted), "requiredCount": len(required),
            "score": None, "scientificValidation": "NOT_VERIFIED",
            "fdaPrediction": "ABSTAIN",
            "note": "Review coverage and judgments are not validated scientific scores.",
        }
    return results
