"""Auditable two-grade scientific-review *evidence readiness* rubric.

Grades answer "can this trial be analyzed confidently with all the inputs?",
NOT "did the treatment work?" or "will the FDA approve it?"

The only available inputs are checksum/identity-verified archived CT.gov records.
External verification must be a separate future audited workflow; no caller can
self-declare independent evidence or bypass missing regulatory documents.
"""
from __future__ import annotations

from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any

from .scientific_investigation_20 import NCT_PATTERN, _lookup
from .scientific_quantitative_results import reported_quantitative_results

RUBRIC_VERSION = "2026-10-review-1"

# Static externally verified gates are NOT satisfied by citations listed in a
# registry record or by a posting's hasResults flag.
EXTERNAL_GATES = (
    ("protocol_sap", "Original protocol and statistical analysis plan independently reconciled",
     "Retrieve dated protocol/SAP, amendment history, endpoint changes and multiplicity plan."),
    ("published_results", "Independent full-results publication or clinical study report reconciled",
     "Reconcile population, endpoint estimates, uncertainty, safety and follow-up to registry."),
    ("independent_replication", "Biological rationale and independent corroboration reviewed",
     "Evaluate mechanistic validation, external replication and contradictory publications."),
    ("official_regulatory", "FDA/agency filing, review and manufacturing evidence independently validated",
     "Verify the relevant indication, application status, FDA record, CMC and PDUFA date."),
)


def _map(obj: Any) -> Mapping[str, Any]:
    return obj if isinstance(obj, Mapping) else {}


def _items(obj: Any) -> list[Any]:
    return obj if isinstance(obj, list) else []


def _exists(obj: Any) -> bool:
    if obj is None:
        return False
    if isinstance(obj, (list, str, Mapping)):
        return bool(obj)
    return isinstance(obj, (int, float, bool))


def _has_measure(obj: Any) -> bool:
    return any(isinstance(item, Mapping) and isinstance(item.get("measure"), str)
               and bool(item["measure"].strip()) for item in _items(obj))


def _positive_count(obj: Any) -> bool:
    return isinstance(obj, int) and not isinstance(obj, bool) and obj > 0


def _has_eligibility(record: Mapping[str, Any]) -> bool:
    criteria = _lookup(record, "protocolSection.eligibilityModule.eligibilityCriteria")
    return isinstance(criteria, str) and bool(criteria.strip())


def _has_arms(record: Mapping[str, Any]) -> bool:
    arms = _items(_lookup(record, "protocolSection.armsInterventionsModule.armGroups"))
    interventions = _items(_lookup(record, "protocolSection.armsInterventionsModule.interventions"))
    return bool(arms and interventions)


def _number(value: Any) -> Decimal | None:
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        parsed = Decimal(value)
    except (InvalidOperation, ValueError):
        return None
    return parsed if parsed.is_finite() else None


def _valid_pvalue(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    raw = value.strip()
    for operator in ("<=", ">=", "<", ">"):
        if raw.startswith(operator):
            raw = raw[len(operator):].strip()
            break
    numeric = _number(raw)
    return numeric is not None and 0 <= numeric <= 1


def _valid_interval(analysis: Mapping[str, Any]) -> bool:
    lower = _number(analysis.get("confidenceIntervalLower"))
    upper = _number(analysis.get("confidenceIntervalUpper"))
    return lower is not None and upper is not None and lower <= upper


def _has_primary_analysis(report: Mapping[str, Any]) -> bool:
    for outcome in _items(report.get("outcomes")):
        o = _map(outcome)
        if str(o.get("outcomeType") or "").upper() != "PRIMARY":
            continue
        for raw in _items(o.get("analyses")):
            analysis = _map(raw)
            if (_number(analysis.get("reportedEstimate")) is not None
                    and (_valid_pvalue(analysis.get("pValueReported"))
                         or _valid_interval(analysis))):
                return True
    return False


def _safety_with_denominators(report: Mapping[str, Any]) -> bool:
    safety = _map(report.get("safety"))
    for bucket in ("seriousEventTermsShown", "otherEventTermsShown"):
        for event in _items(safety.get(bucket)):
            for row in _items(_map(event).get("groupStats")):
                group = _map(row)
                affected = _number(group.get("numAffected"))
                at_risk = _number(group.get("numAtRisk"))
                if (affected is not None and at_risk is not None
                        and 0 <= affected <= at_risk and at_risk > 0
                        and affected == int(affected) and at_risk == int(at_risk)):
                    return True
    return False


def _has_timeline(record: Mapping[str, Any]) -> bool:
    return _exists(_lookup(record, "protocolSection.statusModule.startDateStruct.date")) and (
        _exists(_lookup(record, "protocolSection.statusModule.primaryCompletionDateStruct.date"))
        or _exists(_lookup(record, "protocolSection.statusModule.completionDateStruct.date"))
    )


def _grade(percentage: int) -> str:
    """Grade evidentiary coverage, not clinical quality or outcome direction."""
    if percentage >= 90:
        return "A"
    if percentage >= 75:
        return "B"
    if percentage >= 60:
        return "C"
    if percentage >= 40:
        return "D"
    return "F"


def review_readiness(
    nct_id: str,
    record: Mapping[str, Any],
    *,
    archive_retrieved_at: str | None = None,
) -> dict:
    """Provide source coverage grade and conservative reluctance grade.

    Must only run AFTER archive checksum/decompression/identity verification.
    The archive-integrity criterion represents that caller invariant. A direct
    caller without checksum verification must NOT use this rubric as evidence.
    """
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT ID required")
    if not isinstance(record, Mapping) or _lookup(record, "protocolSection.identificationModule.nctId") != nct_id:
        raise ValueError("Source NCT identity mismatch")

    report = reported_quantitative_results(nct_id, record)
    checks = (
        ("archive_integrity", "Checksum and trial identity validated", True,
         "verified archive SHA-256 + exact NCT identity", "No external source required for storage identity."),
        ("indication", "Disease and indication documented",
         _exists(_lookup(record, "protocolSection.conditionsModule.conditions")),
         "protocolSection.conditionsModule.conditions", "Document indication and intended-use boundaries."),
        ("design", "Trial design and phase documented",
         _exists(_lookup(record, "protocolSection.designModule.studyType"))
         and _exists(_lookup(record, "protocolSection.designModule.phases")),
         "protocolSection.designModule", "Confirm randomized and comparator design separately."),
        ("eligibility", "Analysis population and eligibility documented",
         _has_eligibility(record), "protocolSection.eligibilityModule.eligibilityCriteria",
         "Compare enrollment to the intended clinical population."),
        ("interventions", "Interventions and treatment groups documented",
         _has_arms(record), "protocolSection.armsInterventionsModule",
         "Assess intervention matching and arm comparability separately."),
        ("enrollment", "Enrollment count documented",
         _positive_count(_lookup(record, "protocolSection.designModule.enrollmentInfo.count")),
         "protocolSection.designModule.enrollmentInfo.count",
         "Enrollment alone cannot establish statistical power."),
        ("timeline", "Trial start and completion dates documented",
         _has_timeline(record), "protocolSection.statusModule",
         "Registry milestone dates are not an FDA PDUFA target."),
        ("registered_primary", "Prespecified primary measures listed",
         _has_measure(_lookup(record, "protocolSection.outcomesModule.primaryOutcomes")),
         "protocolSection.outcomesModule.primaryOutcomes",
         "Compare registration history and original SAP."),
        ("primary_analysis", "Reported primary outcome has estimate and uncertainty",
         _has_primary_analysis(report),
         "resultsSection.outcomeMeasuresModule.outcomeMeasures[*].analyses",
         "Reported p-values or intervals are not independently adjudicated."),
        ("safety_denominators", "Safety event counts with at-risk denominators documented",
         _safety_with_denominators(report),
         "resultsSection.adverseEventsModule",
         "Reported affected and at-risk counts are not exposure-adjusted risk."),
        ("participant_flow", "Participant flow reported",
         _exists(_lookup(record, "resultsSection.participantFlowModule.periods")),
         "resultsSection.participantFlowModule.periods",
         "Review missingness, discontinuations and analysis-set definitions."),
        ("baseline", "Baseline demographic and clinical measures reported",
         _exists(_lookup(record, "resultsSection.baselineCharacteristicsModule.baselineMeasures")),
         "resultsSection.baselineCharacteristicsModule.baselineMeasures",
         "Inspect imbalance and adjustment, not merely data presence."),
    )
    criteria = [
        {"id": code, "label": label, "available": bool(ok),
         "evidenceLevel": "archive_verified" if code == "archive_integrity"
                          else ("registry_field_present" if ok else "missing_in_archive"),
         "sourcePath": source, "nextAction": action, "independentlyVerified": False}
        for code, label, ok, source, action in checks
    ]
    criteria.extend({
        "id": code, "label": label, "available": False,
        "evidenceLevel": "independent_review_not_loaded",
        "sourcePath": None, "nextAction": next_action, "independentlyVerified": False,
    } for code, label, next_action in EXTERNAL_GATES)
    covered = sum(item["available"] for item in criteria)
    total = len(criteria)
    percent = round(100 * covered / total)
    missing = [item["id"] for item in criteria if not item["available"]]
    external_missing = [code for code, _, _ in EXTERNAL_GATES]

    # A high-quality registry posting alone is never enough to conclude efficacy.
    # Grade F for RELUCTANCE = maximal reluctance to draw an approval/efficacy call,
    # NOT a failing clinical trial.
    return {
        "nctId": nct_id,
        "rubricVersion": RUBRIC_VERSION,
        "archiveRetrievedAt": archive_retrieved_at,
        "analysisReadiness": {
            "grade": _grade(percent),
            "coveragePercent": percent,
            "requirementsCovered": covered,
            "requirementsTotal": total,
            "preliminarySourceReviewPossible": covered > 1,
            "readyForFullScientificConclusion": False,
            "verdict": "NOT_READY",
            "passFail": "FAIL_INCOMPLETE_INPUTS",
            "note": ("Letter grade measures auditable evidence-input coverage, not "
                     "treatment efficacy. Full readiness requires independent "
                     "protocol/SAP, clinical results, biology and regulator review."),
        },
        "scientificReluctance": {
            "grade": "F",
            "level": "CRITICAL",
            "reluctanceToConclude": "MAXIMUM",
            "verdict": "WITHHOLD_SCIENTIFIC_CONCLUSION",
            "reasons": external_missing
                       + ([code for code in missing if code not in external_missing]),
            "note": ("F means the system must NOT yet declare a scientific success "
                     "or predict FDA approval. It does NOT mean the drug failed."),
        },
        "requirements": criteria,
        "missingRequirementIds": missing,
        "externalEvidenceVerified": False,
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "sourceStatus": "archived_registry_input_audit_only",
        "note": ("These two grades are a conservative input audit. Source coverage "
                 "must never substitute for independent clinical interpretation."),
    }
