"""EudraCT primary-endpoint cross-source match for KEYNOTE-024 (historical).

The Dutch EU Clinical Trials Register record was first entered on 2014-06-19
and records authority authorization dated that day. THE CURRENTLY DISPLAYED
ENDPOINT FIELDS CANNOT BE ASSUMED UNCHANGED SINCE 2014; their individual
revision/effective dates are not evidenced by the public page.

EU register and NEJM can agree on approximate event targets without
establishing an independently authenticated original signed SAP/alpha plan.
No scoring, source download, DB write, order, FS/FA or PDUFA prediction.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping

NCT = "NCT02142738"
EU_NUMBER = "2014-000323-25"
EU_URL = "https://www.clinicaltrialsregister.eu/ctr-search/trial/2014-000323-25/NL"
NCI_URL = "https://www.cancer.gov/research/participate/clinical-trials-search/v?id=NCT02142738"
ASCO_URL = "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103"


def keynote024_eu_protocol_crosscheck(
    interim: Mapping[str, Any],
    published: Mapping[str, Any],
    readiness: Mapping[str, Any],
) -> dict:
    """Crosscheck cited planned endpoints; preserve external-source version limits."""
    if (not isinstance(interim, Mapping) or not isinstance(published, Mapping)
        or not isinstance(readiness, Mapping)
        or interim.get("nctId") != NCT or published.get("nct_id") != NCT
        or published.get("overall_score") is not None
        or published.get("fda_approval_probability") is not None
        or readiness.get("nctId") != NCT
        or interim.get("status") != "published_design_not_authenticated_original_sap"
        or interim.get("scientificScore") is not None
        or interim.get("fdaApprovalProbability") is not None
        or interim.get("readOnly") is not True
        or interim.get("tradingActionsEnabled") is not False
        or readiness.get("inputReadiness", {}).get("grade") != "FAIL"
        or readiness.get("reluctance", {}).get("grade") != "HIGH"
        or readiness.get("readOnly") is not True):
        raise ValueError("Pilot EU registry crosscheck requires unscored exact trial")

    original = readiness.get("original2016ProtocolSource")
    if (not isinstance(original, Mapping)
        or original.get("pdfContentReviewed") is not False
        or original.get("originalSignedSapVerified") is not False
        or original.get("preInterimAlphaSpendingVerified") is not False):
        raise ValueError("Original effective signed SAP not authenticated")
    design = interim.get("reportedDesign")
    observed = interim.get("observedInterim")
    source = interim.get("sourceDateContext")
    if (not isinstance(design, Mapping) or not isinstance(observed, Mapping)
        or not isinstance(source, Mapping)
        or source.get("originalInterimDataCutoff") != "2016-05-09"
        or source.get("contemporaneousSapAuthenticated") is not False
        or source.get("originalSupplementRead") is not False):
        raise ValueError("Interim plan source is not bounded")
    pfs = design.get("secondInterim")
    os_plan = design.get("osGroupSequential")
    if (not isinstance(pfs, Mapping) or not isinstance(os_plan, Mapping)
        or pfs.get("plannedApproximatePfsEvents") != 175
        or os_plan.get("plannedApproximateDeaths") != [110, 170]
        or observed.get("reportedPfsEvents") != 189
        or observed.get("reportedDeaths") != 108
        or observed.get("pfsHR") != 0.50
        or observed.get("osHR") != 0.60):
        raise ValueError("Historical event target and observed figures mismatched")
    snapshots = published.get("analysis_snapshots")
    if not isinstance(snapshots, list) or len(snapshots) != 3:
        raise ValueError("Required published trial analyses missing")
    first = next((p for p in snapshots if isinstance(p, Mapping)
                  and p.get("analysis_id") == "keynote024_initial_2016"), None)
    if (not isinstance(first, Mapping) or first.get("nct_id") != NCT
        or first.get("source_id") != "27718847"
        or first.get("data_cutoff_date") != "2016-05-09"
        or first.get("arm_counts_randomized") !=
            {"pembrolizumab": 154, "chemotherapy": 151}):
        raise ValueError("Published 2016 trial identity mismatch")

    # The public EU register has no reliable field-by-field effective-date
    # history. Do not describe ALL displayed fields as frozen since 2014.
    match = (
        ("primary_pfs", "E.5.1", "PFS per RECIST 1.1 by blinded central review",
         "progression_free_survival", None),
        ("planned_pfs_events", "E.5.1.1",
         "Approximately 175 PFS events", "progression_free_survival", 175),
        ("planned_os_first", "E.5.2.1",
         "Approximately 110 deaths", "overall_survival", 110),
        ("planned_os_second", "E.5.2.1",
         "Approximately 170 deaths", "overall_survival", 170),
        ("secondary_os_orr", "E.5.2",
         "OS and centrally reviewed ORR are secondary", "secondary_endpoints", None),
        ("monitoring_and_design", "E.8.1 and E.8.7",
         "Open-label randomized Phase 3 with data monitoring committee",
         "trial_design", None),
    )
    comparisons = [
        {"key": key, "euSection": section, "euReportedFinding": finding,
         "mappedPublishedConcept": mapped, "reportedPlannedCount": count,
         "crossSourceAgreement": True, "euSourceUrl": EU_URL,
         "revisionHistoryVerified": False,
         "independentSignedSAPConfirmation": False}
        for key, section, finding, mapped, count in match
    ]

    return deepcopy({
        "nctId": NCT,
        "schemaVersion": "historical-eu-registered-plan-crosscheck-v1",
        "status": "cross_source_description_agrees_without_sap_verification",
        "registry": {
            "eudractNumber": EU_NUMBER,
            "sponsorProtocolCode": "MK-3475-024",
            "recordCountry": "Netherlands",
            "sourceUrl": EU_URL,
            "firstRecordEnteredDate": "2014-06-19",
            "competentAuthorityDecisionDate": "2014-06-19",
            "recordFirstEnteredBeforeInterim": True,
            "individualEndpointFieldVersionDated": False,
            "original2014FieldContentAuthenticated": False,
            "signed2016SAPAvailable": False,
            "authoredBySeparateOrganization": False,
            "explanation": "European regulator-hosted sponsor-supplied registry, not independent trial replication or verified pre-2016 protocol amendment history.",
        },
        "identityBridge": {
            "nciSourceUrl": NCI_URL,
            "nciTrialId": NCT,
            "nciSecondaryId": EU_NUMBER,
            "protocolCode": "MK-3475-024",
            "separateClinicalTrial": False,
            "identityCrosscheckOnly": True,
        },
        "comparisons": comparisons,
        "eventTiming": {
            "euPfsEventsTargetApprox": 175,
            "reportedPfsEventsObserved": 189,
            "euOsFirstDeathsTargetApprox": 110,
            "reportedOsInterimDeathsObserved": 108,
            "euOsLaterDeathsTargetApprox": 170,
            "euAllowsPfsTimingDelayIfOsUnder110": True,
            "euSourceSection": "E.5.1.1",
            "actualDataMonitoringCommitteeTimingReconciled": False,
            "eventDifferenceNotAutomaticProtocolDeviation": True,
            "nextAction": "Reconcile dated effective amendment and interim DMC decision chronology; approximate event targets are not strict stop rules.",
        },
        "earlierPublicDescription": {
            "sourceUrl": ASCO_URL,
            "publicationDate": "2015-05-20",
            "supportsPrimaryEndpointAndCentralReview": True,
            "originalSapAuthenticated": False,
        },
        "researchConclusions": {
            "primaryPfsDesignCorroboratedAcrossSources": True,
            "approximateEventTargetsAgreeAcrossSources": True,
            "alphaSpendingInEuRegistryVerified": False,
            "originalEffectiveProtocolAmendmentsVerified": False,
            "preInterimSignedSapVerified": False,
            "independentReplicationCompleted": False,
            "safetyBenefitRiskAdjudicated": False,
            "inputReadinessGradeChanged": False,
            "reluctanceGradeChanged": False,
            "canBeUsedToAssignClinicalSuccessGrade": False,
        },
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "readOnly": True,
        "tradingActionsEnabled": False,
        "fsFaModified": False,
    })
