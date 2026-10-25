"""20-stage source-coverage dossier for an exact archived ClinicalTrials.gov study.

All observations are descriptive source presence indicators. They do NOT establish
independent verification, favorable results, statistical significance, FDA review,
approval odds, or a score. This is an inventory for deeper investigation.
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

NCT_PATTERN = re.compile(r"NCT[0-9]{8}\Z")

# id, title, primary areas to inspect, external independent verification needed,
# caution before scientific inference. Keep ordering stable for time-series UI.
STAGES: tuple[tuple[int, str, tuple[tuple[str, str], ...], bool, str], ...] = (
    (1, "Trial identity and protocol",
     (("Study title", "protocolSection.identificationModule.briefTitle"),
      ("Official title", "protocolSection.identificationModule.officialTitle")), False,
     "Study identity does not establish clinical or regulatory success."),
    (2, "Indication and disease context",
     (("Conditions", "protocolSection.conditionsModule.conditions"),
      ("Keywords", "protocolSection.conditionsModule.keywords")), True,
     "Disease biology, unmet need and standard of care require external sources."),
    (3, "Trial phase and development context",
     (("Phases", "protocolSection.designModule.phases"),
      ("Study type", "protocolSection.designModule.studyType"),
      ("Overall status", "protocolSection.statusModule.overallStatus")), False,
     "An announced trial phase is not a verified FDA pathway or decision."),
    (4, "Timeline from trial start to filing",
     (("Start date", "protocolSection.statusModule.startDateStruct.date"),
      ("Primary completion", "protocolSection.statusModule.primaryCompletionDateStruct.date"),
      ("Study completion", "protocolSection.statusModule.completionDateStruct.date"),
      ("First submitted", "protocolSection.statusModule.studyFirstSubmitDate"),
      ("Last update posted", "protocolSection.statusModule.studyLastUpdatePostDateStruct.date")), True,
     "Protocol dates are not PDUFA targets; FDA filing/decision dates need FDA evidence."),
    (5, "Eligibility and trial population",
     (("Eligibility criteria", "protocolSection.eligibilityModule.eligibilityCriteria"),
      ("Sex", "protocolSection.eligibilityModule.sex"),
      ("Minimum age", "protocolSection.eligibilityModule.minimumAge")), False,
     "Presence of criteria does not establish representativeness or generalizability."),
    (6, "Treatment arms and comparators",
     (("Arm groups", "protocolSection.armsInterventionsModule.armGroups"),
      ("Interventions", "protocolSection.armsInterventionsModule.interventions")), False,
     "Intervention listings do not establish active comparator adequacy."),
    (7, "Randomization and masking",
     (("Allocation", "protocolSection.designModule.designInfo.allocation"),
      ("Masking", "protocolSection.designModule.designInfo.maskingInfo.masking"),
      ("Intervention model", "protocolSection.designModule.designInfo.interventionModel")), False,
     "Registry design fields do not verify correct conduct or concealment."),
    (8, "Sample size and statistical power",
     (("Enrollment", "protocolSection.designModule.enrollmentInfo.count"),
      ("Enrollment type", "protocolSection.designModule.enrollmentInfo.type")), True,
     "Enrollment is not a power calculation; retrieve statistical analysis plan."),
    (9, "Prespecified primary endpoints",
     (("Primary outcomes", "protocolSection.outcomesModule.primaryOutcomes"),), False,
     "Outcome registration does not prove endpoint validity or unchanged prespecification."),
    (10, "Secondary and exploratory endpoints",
     (("Secondary outcomes", "protocolSection.outcomesModule.secondaryOutcomes"),
      ("Other outcomes", "protocolSection.outcomesModule.otherOutcomes")), False,
     "Multiple endpoints can introduce multiplicity and selective reporting."),
    (11, "Statistical analysis and multiplicity",
     (("Reported outcome analyses", "resultsSection.outcomeMeasuresModule.outcomeMeasures"),
      ("Linked documents", "documentSection.largeDocumentModule.largeDocs")), True,
     "Reported analyses and linked documents do not establish a fully reviewed SAP."),
    (12, "Observed efficacy results",
     (("Posted outcome measures", "resultsSection.outcomeMeasuresModule.outcomeMeasures"),), True,
     "Posted measures require effect-size, CI, p-value and cross-source evaluation."),
    (13, "Safety and adverse events",
     (("Serious events", "resultsSection.adverseEventsModule.seriousEvents"),
      ("Other events", "resultsSection.adverseEventsModule.otherEvents"),
      ("Safety denominators", "resultsSection.adverseEventsModule.eventGroups")), True,
     "Event tables require exposure-adjusted benefit-risk interpretation."),
    (14, "Participant flow and missing data",
     (("Trial flow", "resultsSection.participantFlowModule.periods"),
      ("Pre-assignment details", "resultsSection.participantFlowModule.preAssignmentDetails")), True,
     "Flow counts alone do not establish unbiased handling of missingness."),
    (15, "Baseline balance and confounding",
     (("Baseline measures", "resultsSection.baselineCharacteristicsModule.baselineMeasures"),
      ("Baseline groups", "resultsSection.baselineCharacteristicsModule.groups")), True,
     "Baseline tables need clinical balance and design-context evaluation."),
    (16, "Mechanism and target validation",
     (("Interventions", "protocolSection.armsInterventionsModule.interventions"),
      ("Trial description", "protocolSection.descriptionModule.detailedDescription")), True,
     "Mechanistic validation requires literature and independent translational evidence."),
    (17, "Biomarkers and subgroup coherence",
     (("Outcome measures", "resultsSection.outcomeMeasuresModule.outcomeMeasures"),
      ("Eligibility criteria", "protocolSection.eligibilityModule.eligibilityCriteria")), True,
     "A registry outcome table is not a validated biomarker or subgroup analysis."),
    (18, "Replication and publication review",
     (("Registry references", "protocolSection.referencesModule.references"),), True,
     "References do not prove independent replication, peer review or agreement."),
    (19, "Regulatory and manufacturing readiness",
     (("FDA-regulated drug", "protocolSection.oversightModule.isFdaRegulatedDrug"),
      ("FDA-regulated device", "protocolSection.oversightModule.isFdaRegulatedDevice")), True,
     "FDA correspondence, CMC, inspections and filing status require official sources."),
    (20, "Integrated benefit-risk and PDUFA synthesis",
     (), True,
     "No automatic regulatory outcome or approval probability. Requires cross-source review."),
)


def _lookup(record: Mapping[str, Any], path: str) -> Any:
    value: Any = record
    for part in path.split("."):
        if not isinstance(value, Mapping):
            return None
        value = value.get(part)
    return value


def _is_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, (str, list, tuple, Mapping)):
        return len(value) > 0
    return isinstance(value, (bool, int, float))


def _observation(label: str, path: str, value: Any) -> dict:
    result = {"label": label, "fieldPath": path, "present": _is_present(value)}
    if isinstance(value, (list, tuple)):
        result["count"] = len(value)
    elif isinstance(value, Mapping):
        result["fieldCount"] = len(value)
    elif _is_present(value):
        # No long clinical prose, undisclosed private values or unconstrained text.
        # Display the data type/presence except for safe structured dates/counts.
        if (isinstance(value, bool) or
                (isinstance(value, (int, float)) and not isinstance(value, bool))):
            result["value"] = value
        elif isinstance(value, str) and len(value) <= 32 and "\n" not in value:
            result["value"] = value
    return result


def investigation_20(nct_id: str, record: Mapping[str, Any],
                     *, retrieved_at: str | None = None) -> dict:
    """Describe exactly which source fields are available at each of 20 levels."""
    if not NCT_PATTERN.fullmatch(nct_id):
        raise ValueError("Exact NCT ID required")
    if not isinstance(record, Mapping):
        raise ValueError("ClinicalTrials.gov record must be an object")
    source_id = _lookup(record, "protocolSection.identificationModule.nctId")
    if source_id != nct_id:
        raise ValueError("Source NCT identity mismatch")
    stages = []
    for number, title, fields, requires_external, caution in STAGES:
        observations = [
            _observation(label, path, _lookup(record, path))
            for label, path in fields
        ]
        available = sum(bool(item["present"]) for item in observations)
        if requires_external:
            status = "external_review_required"
        elif available:
            status = "registry_fields_present"
        else:
            status = "not_documented_in_archive"
        stages.append({
            "level": number,
            "title": title,
            "status": status,
            "sourceEvidenceCount": available,
            "sourceFieldCount": len(fields),
            "observations": observations,
            "requiresExternalReview": requires_external,
            "caution": caution,
            "scientificallyVerified": False,
            "score": None,
        })
    assert len(stages) == 20
    return {
        "nctId": nct_id,
        "sourceType": "archived_clinicaltrials_gov_api_v2",
        "sourceUrl": "https://clinicaltrials.gov/study/" + nct_id,
        "retrievedAt": retrieved_at,
        "recordHasResultsFlag": record.get("hasResults") is True,
        "levelCount": len(stages),
        "sourceFieldsPresent": sum(s["sourceEvidenceCount"] for s in stages),
        "levelsWithSourceFields": sum(s["sourceEvidenceCount"] > 0 for s in stages),
        "levelsRequiringExternalReview": sum(s["requiresExternalReview"] for s in stages),
        "scientificallyVerifiedLevels": 0,
        "overallScore": None,
        "fdaApprovalProbability": None,
        "status": "source_coverage_only",
        "note": ("Twenty investigation stages, not twenty independently completed "
                 "scientific assessments. All observations are from the archived "
                 "registry snapshot and need critical source review; no inference "
                 "of clinical significance or FDA approval."),
        "levels": stages,
    }
