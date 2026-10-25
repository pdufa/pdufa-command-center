"""KEYNOTE-024 historical DMC-to-PDUFA audit timeline.

Retrospective NEJM DMC review dates, contemporaneous June 16 sponsor news,
September 7 first-line sBLA Priority Review notice and October 24 FDA action
must remain DISTINCT types of dated evidence. A future PDUFA goal date is
not an action date or proof that an earlier regulatory outcome was predicted.

The 2016 interim original signed protocol/SAP, contemporaneous DMC minutes,
regulatory application review/CMC source package and alpha reanalysis remain
unverified. This is read-only historical study provenance, never an FDA
approval probability or GEM/WT/PIPELINE ranking operation.
"""
from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from datetime import date
from typing import Any

NCT = "NCT02142738"
NEJM = "https://www.nejm.org/doi/abs/10.1056/NEJMoa1606774"
EU = "https://www.clinicaltrialsregister.eu/ctr-search/trial/2014-000323-25/NL"
ASCO = "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103"
MERCK_DMC = (
    "https://www.merck.com/news/"
    "mercks-keytruda-pembrolizumab-demonstrates-superior-progression-free-"
    "and-overall-survival-compared-to-chemotherapy-as-first-line-treatment-"
    "in-patients-with-advanced-non-small-cel/"
)
MERCK_REVIEW = (
    "https://www.merck.com/news/"
    "fda-accepts-supplemental-biologics-license-application-assigns-"
    "priority-review-and-grants-breakthrough-therapy-designation-to-"
    "mercks-keytruda-pembrolizumab-for-first-line-treatment-o/"
)
FDA_STAFF = "https://pmc.ncbi.nlm.nih.gov/articles/PMC5679831/"
NCI_APPROVAL = (
    "https://www.cancer.gov/news-events/cancer-currents-blog/2016/"
    "fda-atezolizumab-pembrolizumab-lung"
)


# Dates are *events or dates announced*; source dates can be LATER.
# Distinguish 2016 paper reporting May/June events from real-time disclosures.
# No milestone implies the exact dated content of the 2014 register has been
# verified against contemporaneous 2014 archived versions.
_SOURCES = (
    ("2014-06-19", "european_registry_first_entry", "Trial registration",
     "EU registry first entered / Dutch authority authorized", EU,
     "A.3/A.4/A.5; Dutch authorization/first record dates",
     "registry_source_version_unverified", "2014-06-19",
     "Fields currently displayed in the register have no individual "
     "2014-effective amendment history verified."),
    ("2015-05-20", "early_public_study_design", "Prospective study description",
     "ASCO trial-in-progress abstract describes PFS/OS endpoints and central review",
     ASCO, "JCO 33, TPS8103; methods and intended trial design",
     "contemporaneous_public_study_description", "2015-05-20",
     "Study-design abstract is not a signed protocol/SAP."),
    ("2016-05-09", "original_interim_data_cutoff", "Data cutoff",
     "Second interim PFS/OS analysis data cutoff", NEJM,
     "Original 2016 trial publication; Statistical Analysis",
     "event_reported_retrospectively", "2016-10-08",
     "Later article reporting the cutoff; no separately verified database lock timestamp."),
    ("2016-06-08", "dmc_review_first", "DMC review",
     "First reported committee review of second interim results", NEJM,
     "Original 2016 article; Statistical Analysis (June 8 and 14)",
     "event_reported_retrospectively", "2016-10-08",
     "Committee minutes, independent meeting record and precise recommendation timing not accessed."),
    ("2016-06-14", "dmc_review_second", "DMC review",
     "Second reported committee review of second interim results", NEJM,
     "Original 2016 article; Statistical Analysis (June 8 and 14)",
     "event_reported_retrospectively", "2016-10-08",
     "Does not by itself establish a precisely dated signed stop recommendation."),
    ("2016-06-16", "sponsor_public_stopping_notice", "Public disclosure",
     "Merck publicly announces committee recommendation to stop early and offer crossover",
     MERCK_DMC, "Merck original June 16 2016 5:45 am EDT press release",
     "contemporaneous_sponsor_news", "2016-06-16",
     "Sponsor says recommendation occurred by this release, not which exact June meeting approved it."),
    ("2016-09-07", "first_line_priority_review_notice", "Regulatory review",
     "Merck announces FDA Priority Review acceptance and December 24 PDUFA target",
     MERCK_REVIEW, "Merck September 7 2016 release, first-line NSCLC sBLA",
     "contemporaneous_sponsor_regulatory_notice", "2016-09-07",
     "Sponsor announcement of agency status, not complete FDA internal correspondence."),
    ("2016-10-08", "original_results_online", "Published results",
     "Original randomized PFS/OS study appears online", NEJM,
     "Original 2016 article; electronic publication and reported second interim",
     "original_journal_publication", "2016-10-08",
     "Publication describes earlier results and monitoring; not a prospective prediction."),
    ("2016-10-24", "fda_first_line_approval", "FDA decision",
     "FDA approves first-line pembrolizumab for PD-L1-high metastatic NSCLC",
     NCI_APPROVAL, "NCI November 17 2016 report; original Oct 24 FDA first-line decision",
     "federal_historical_confirmation", "2016-11-17",
     "This first-line action relied on KEYNOTE-024; a simultaneous conversion "
     "of second-line approval relied separately on KEYNOTE-010."),
    ("2016-12-24", "announced_pdufa_goal", "Superseded target",
     "Previously announced first-line sBLA PDUFA goal; action already taken Oct 24",
     MERCK_REVIEW, "September 7 2016 release; December 24 PDUFA goal date",
     "historical_target_not_decision", "2016-09-07",
     "A goal date, not a second action or a missed deadline."),
)


def keynote024_historical_pdufa_timeline(
    published: Mapping[str, Any], readiness: Mapping[str, Any],
    interim: Mapping[str, Any], european: Mapping[str, Any],
) -> dict[str, Any]:
    """Publish immutable study-specific event/source time distinctions."""
    if not all(isinstance(v, Mapping) for v in (published, readiness, interim, european)):
        raise ValueError("Historical timeline requires validated source evidence objects")
    if (published.get("nct_id") != NCT
        or published.get("randomized_population") != 305
        or published.get("overall_score") is not None
        or published.get("fda_approval_probability") is not None
        or readiness.get("nctId") != NCT
        or readiness.get("inputReadiness", {}).get("grade") != "FAIL"
        or readiness.get("reluctance", {}).get("grade") != "HIGH"
        or readiness.get("scientificScore") is not None
        or readiness.get("fdaApprovalProbability") is not None
        or readiness.get("readOnly") is not True
        or interim.get("nctId") != NCT
        or interim.get("status") != "published_design_not_authenticated_original_sap"
        or interim.get("scientificScore") is not None
        or interim.get("fdaApprovalProbability") is not None
        or interim.get("readOnly") is not True
        or european.get("nctId") != NCT
        or european.get("schemaVersion") != "historical-eu-registered-plan-crosscheck-v1"
        or european.get("scientificScore") is not None
        or european.get("fdaApprovalProbability") is not None
        or european.get("readOnly") is not True):
        raise ValueError("Unverified, scored or mismatched original trial source")
    pre_protocol = readiness.get("original2016ProtocolSource")
    if (not isinstance(pre_protocol, Mapping)
        or pre_protocol.get("originalSignedSapVerified") is not False
        or pre_protocol.get("preInterimAlphaSpendingVerified") is not False
        or pre_protocol.get("pdfContentReviewed") is not False):
        raise ValueError("Original signed protocol/SAP has not been authenticated")
    ready_checks = readiness.get("checks")
    if (not isinstance(ready_checks, list)
        or sum(1 for v in ready_checks if isinstance(v, Mapping)
               and v.get("id") == "pre_cutoff_protocol"
               and v.get("status") == "BLOCKED") != 1):
        raise ValueError("Original pre-interim protocol gate must remain blocked")
    original = published.get("analysis_snapshots")
    if not isinstance(original, list) or len(original) != 3:
        raise ValueError("Original trial analysis snapshots missing")
    baseline = next((x for x in original if isinstance(x, Mapping)
                     and x.get("analysis_id") == "keynote024_initial_2016"), None)
    if (not isinstance(baseline, Mapping)
        or baseline.get("source_id") != "27718847"
        or baseline.get("nct_id") != NCT
        or baseline.get("data_cutoff_date") != "2016-05-09"
        or baseline.get("arm_counts_randomized") != {
            "pembrolizumab": 154, "chemotherapy": 151,
        }):
        raise ValueError("Original 2016 randomized trial identity mismatch")
    observed = interim.get("observedInterim")
    if (not isinstance(observed, Mapping)
        or observed.get("reportedPfsEvents") != 189
        or observed.get("reportedDeaths") != 108
        or observed.get("pfsHR") != 0.50
        or observed.get("osHR") != 0.60
        or observed.get("fdaStaffReportedOsAllocatedAlpha") != 0.0118):
        raise ValueError("Original reported interim events/alpha mismatch")
    eu = european.get("registry")
    events = european.get("eventTiming")
    if (not isinstance(eu, Mapping) or not isinstance(events, Mapping)
        or eu.get("eudractNumber") != "2014-000323-25"
        or eu.get("firstRecordEnteredDate") != "2014-06-19"
        or eu.get("individualEndpointFieldVersionDated") is not False
        or events.get("euPfsEventsTargetApprox") != 175
        or events.get("euOsFirstDeathsTargetApprox") != 110
        or events.get("reportedPfsEventsObserved") != 189
        or events.get("reportedOsInterimDeathsObserved") != 108):
        raise ValueError("Early trial register/2016 interim mismatch")

    history = [
        {"eventDate": when, "key": key, "category": category,
         "title": title, "sourceUrl": url, "sourceLocator": locator,
         "sourceTemporalStatus": status,
         "sourcePublicationOrEntryDate": published_on,
         "caveat": caveat,
         "originalDmcMinutesVerified": False,
         "originalSignedSapVerified": False}
        for (when, key, category, title, url, locator, status,
             published_on, caveat) in _SOURCES
    ]
    if len(history) != 10 or sorted(x["eventDate"] for x in history) != [
        x["eventDate"] for x in history
    ] or len({x["key"] for x in history}) != len(history):
        raise ValueError("Historical trial chronology is corrupt")
    if (date.fromisoformat("2016-05-09")
        >= date.fromisoformat("2016-06-08")
        or date.fromisoformat("2016-06-14") >= date.fromisoformat("2016-06-16")
        or date.fromisoformat("2016-10-24") >= date.fromisoformat("2016-12-24")):
        raise ValueError("Event ordering invalid")

    return deepcopy({
        "nctId": NCT,
        "schemaVersion": "historical-keynote024-dmc-pdufa-timeline-v1",
        "status": "historical_source_timeline_not_outcome_forecast",
        "application": {
            "biologicsLicense": "125514/S-12",
            "indication": "first_line_PDL1_TPS_ge_50_metastatic_NSCLC",
            "targetAnnouncedDate": "2016-09-07",
            "targetPdufaDate": "2016-12-24",
            "actualFdaActionDate": "2016-10-24",
            "actualAction": "approved_first_line_pembrolizumab",
            "firstLineSupportedBy": NCT,
            "sameDaySecondLineConversionDifferentTrial": "KEYNOTE-010",
            "neverTreatTargetAsObservedDecision": True,
            "actualActionKnownOnlyInHindsight": True,
            "observationalHistoryNotForecast": True,
        },
        "eventCount": len(history),
        "events": history,
        "interim": {
            "dataCutoff": "2016-05-09",
            "independentCommitteeReviewDatesReportedByJournal": [
                "2016-06-08", "2016-06-14",
            ],
            "firstPublicStoppingRecommendationDisclosure": "2016-06-16",
            "dmcMinutesAndSignedRecommendationReviewed": False,
            "dmcExactRecommendationDecisionDateProven": False,
            "prospectiveStoppingBoundaryRecalculated": False,
            "observedPfsEvents": 189,
            "observedOsDeaths": 108,
            "journalRetrospectiveReportingSource": NEJM,
            "sponsorContemporaneousReleaseSource": MERCK_DMC,
            "pfsTargetWasApproximate": True,
            "fdaReviewDossierComplete": False,
        },
        "conclusions": {
            "publicStoppingChronologyCorroborated": True,
            "regulatoryTargetAndActualActionIdentified": True,
            "independentDmcMinutesReviewed": False,
            "originalProtocolSapAuthenticated": False,
            "originalSignedAlphaSpendingReconstructed": False,
            "fullIndependentScientificAdjudicationDone": False,
            "inputReadinessGradeChanged": False,
            "reluctanceGradeChanged": False,
            "retrospectiveDataNotProspectivePrediction": True,
        },
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "readOnly": True,
        "tradingActionsEnabled": False,
        "fsFaModified": False,
    })
