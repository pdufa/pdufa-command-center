"""Source-separated KEYNOTE-024 pre-interim chronology and registry safety audit.

2015 study-in-progress abstract establishes an earlier PUBLIC description of
trial design and registered endpoint intent. It does NOT establish a signed,
pre-2016 SAP, amendment history, multiplicity boundaries or actual conduct.

The registry adverse-event module may contain treatment-switch groups: never
pool those groups, infer a randomized comparison, or equate affected patients
with treatment-related events from a separate journal publication.
"""
from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

NCT = "NCT02142738"
ASCO_2015 = "https://ascopubs.org/doi/10.1200/jco.2015.33.15_suppl.tps8103"
ORIGINAL_PUBLICATION = "https://pubmed.ncbi.nlm.nih.gov/27718847/"
ORIGINAL_PROTOCOL_LISTING = "https://doi.org/10.1056/NEJMoa1606774"
LATER_PROTOCOL = "https://cdn.clinicaltrials.gov/large-docs/38/NCT02142738/Prot_SAP_000.pdf"
LONG_TERM_PUBLICATION = "https://pubmed.ncbi.nlm.nih.gov/33872070/"
REGISTRY = "https://clinicaltrials.gov/study/NCT02142738"
MAX_EVENT_GROUPS = 24

# Historical descriptions are versioned reports, not amendments authenticated
# to the date they took effect. No entry here proves original SAP chronology.
_MILESTONES = (
    ("2015-05-20", "contemporaneous_trial_design", "2015 ASCO trial-in-progress abstract",
     ASCO_2015, "ASCO 2015 TPS8103; Methods",
     "public_description_before_cutoff",
     "At publication, the study was ongoing; PFS by central RECIST 1.1 review "
     "was described as primary. ORR, OS and safety were identified as secondary.",
     "This is an abstract, not a full signed protocol or SAP."),
    ("2016-05-09", "primary_analysis_cutoff", "Original interim data cutoff",
     ORIGINAL_PUBLICATION, "Original KEYNOTE-024 2016 randomized analysis",
     "cutoff_reported_retrospectively",
     "Data cutoff documented for the original randomized-trial interim report.",
     "Cutoff is not a source-publication or protocol-approval date."),
    ("2016-10-08", "original_results_published", "Original KEYNOTE-024 findings published",
     ORIGINAL_PUBLICATION, "PubMed 27718847; Epub date and original results",
     "published_results",
     "The original publication reported PFS HR 0.50 (95% CI 0.37–0.68).",
     "Reported results are not independently recalculated."),
    ("2016-10-08", "supplementary_protocol_listed", "2016 journal protocol supplement listed",
     ORIGINAL_PROTOCOL_LISTING, "NEJM 2016 online article; Supplementary Material/Protocol",
     "linked_document_not_content_reviewed",
     "NEJM lists a downloadable protocol named nejmoa1606774_protocol.pdf.",
     "Its content, effective versions, signatures and SAP dates are not verified."),
    ("2017-12-20", "later_protocol_date", "Later registry-linked protocol and SAP",
     LATER_PROTOCOL, "Cover; amendment 024-11, Japan-only",
     "document_date_reported",
     "Protocol/SAP version dated 2017-12-20 is linked from the trial registry.",
     "It cannot independently establish the SAP in effect in May 2016."),
    ("2020-06-01", "long_term_followup_cutoff", "Five-year survival follow-up cutoff",
     LONG_TERM_PUBLICATION, "2021 follow-up; data cutoff June 1, 2020",
     "cutoff_reported_retrospectively",
     "The long-term follow-up uses a later cutoff and later crossover exposure.",
     "Cannot combine interim and long-term OS estimates as a single analysis."),
    ("2021-04-19", "long_term_analysis_published", "Five-year survival report published",
     LONG_TERM_PUBLICATION, "PubMed 33872070; online publication date",
     "published_results",
     "Long-term follow-up includes the 66% effective crossover context.",
     "Follow-up is a separate secondary analysis."),
)


def _source_id(record: Mapping[str, Any]) -> str | None:
    p = record.get("protocolSection")
    if not isinstance(p, Mapping):
        return None
    ident = p.get("identificationModule")
    return ident.get("nctId") if isinstance(ident, Mapping) else None


def _plain(value: Any, *, max_len: int = 140) -> str:
    if not isinstance(value, str):
        raise ValueError("Registry treatment-group string must be text")
    clean = " ".join(value.split()).strip()
    if not clean or len(clean) > max_len:
        raise ValueError("Registry treatment-group label missing or excessive")
    return clean


def _count(value: Any, *, allow_none: bool = True) -> int | None:
    if value is None and allow_none:
        return None
    if type(value) is not int or not 0 <= value <= 100000:
        raise ValueError("Registry event count is not a bounded non-negative integer")
    return value


def _group(group: Mapping[str, Any], index: int) -> dict:
    gid = _plain(group.get("id"), max_len=32)
    title = _plain(group.get("title"))
    # Aggregates are presented precisely as registered. Distinct treatment
    # courses are NOT considered randomization-arm equivalents.
    pairs: dict[str, dict] = {}
    for category, affected_key, risk_key in (
        ("seriousEvents", "seriousNumAffected", "seriousNumAtRisk"),
        ("otherEvents", "otherNumAffected", "otherNumAtRisk"),
        ("deaths", "deathsNumAffected", "deathsNumAtRisk"),
    ):
        at_risk = _count(group.get(risk_key))
        affected = _count(group.get(affected_key))
        if affected is not None and at_risk is not None and affected > at_risk:
            raise ValueError("Registry event numerator exceeds denominator")
        pairs[category] = {
            "numAffected": affected,
            "numAtRisk": at_risk,
            "population": "registry_event_group_as_reported",
            "sourceFields": [
                f"resultsSection.adverseEventsModule.eventGroups[{index}].{affected_key}",
                f"resultsSection.adverseEventsModule.eventGroups[{index}].{risk_key}",
            ],
        }
    return {
        "groupId": gid,
        "title": title,
        "sourceLocator": f"resultsSection.adverseEventsModule.eventGroups[{index}]",
        "counts": pairs,
        "independentlyVerified": False,
    }


def keynote024_preinterim_evidence_audit(
    record: Mapping[str, Any], research: Mapping[str, Any],
) -> dict:
    """Inspect one already verified archived trial record, without scoring."""
    if not isinstance(record, Mapping) or _source_id(record) != NCT:
        raise ValueError("Archived registry NCT identity mismatch")
    if (not isinstance(research, Mapping)
        or research.get("nct_id") != NCT
        or research.get("overall_score") is not None
        or research.get("fda_approval_probability") is not None):
        raise ValueError("Historical publication analysis is missing or scored")

    analyses = research.get("analysis_snapshots")
    if not isinstance(analyses, list):
        raise ValueError("Published analysis snapshots are missing")
    by_id = {s.get("analysis_id"): s for s in analyses if isinstance(s, Mapping)}
    if (len(by_id) != 3
        or by_id.get("keynote024_initial_2016", {}).get("source_id") != "27718847"
        or by_id.get("keynote024_initial_2016", {}).get("data_cutoff_date") != "2016-05-09"
        or by_id.get("keynote024_five_year_2021", {}).get("source_id") != "33872070"
        or by_id.get("keynote024_five_year_2021", {}).get("data_cutoff_date") != "2020-06-01"):
        raise ValueError("Published historical chronology mismatch")

    ae = record.get("resultsSection", {})
    if not isinstance(ae, Mapping):
        raise ValueError("Archived results structure invalid")
    ae_module = ae.get("adverseEventsModule", {})
    if ae_module is None:
        ae_module = {}
    if not isinstance(ae_module, Mapping):
        raise ValueError("Archived safety module invalid")
    raw_groups = ae_module.get("eventGroups")
    if raw_groups is None:
        raw_groups = []
    if not isinstance(raw_groups, list):
        raise ValueError("Archived event groups invalid")
    if len(raw_groups) > MAX_EVENT_GROUPS:
        # Fail closed, rather than showing a biased subset as complete.
        raise ValueError("Archived safety groups exceed bounded review capacity")
    groups = []
    ids = set()
    for i, group in enumerate(raw_groups):
        if not isinstance(group, Mapping):
            raise ValueError("Archived safety group structure invalid")
        clean = _group(group, i)
        if clean["groupId"] in ids:
            raise ValueError("Duplicated archived event-group identifier")
        ids.add(clean["groupId"])
        groups.append(clean)

    milestones = [
        {
            "date": when, "id": ident, "title": title, "sourceUrl": url,
            "sourceLocator": locator, "evidenceStatus": status,
            "finding": finding, "limitation": limitation,
            "proofOfOriginalSap": False,
        }
        for when, ident, title, url, locator, status, finding, limitation
        in _MILESTONES
    ]
    if (milestones[0]["date"] >= milestones[1]["date"]
        or milestones[4]["date"] <= milestones[1]["date"]
        or any(date.fromisoformat(m["date"]) is None for m in milestones)):
        raise ValueError("Historical evidence chronology invalid")

    return {
        "nctId": NCT,
        "assessmentStatus": "historical_evidence_crosswalk_only",
        "timeline": milestones,
        "earlyDesignEvidence": {
            "status": "public_trial_design_reported_pre_cutoff",
            "sourceUrl": ASCO_2015,
            "publicationDate": "2015-05-20",
            "primaryEndpoint": "progression_free_survival_by_central_RECIST1_1",
            "secondaryEndpoints": ["objective_response_rate", "overall_survival", "safety"],
            "preinterimDocumentVerified": False,
            "signedSapVerified": False,
            "originalMultiplicityVerified": False,
        },
        "registrySafety": {
            "sourceUrl": REGISTRY,
            "sourceType": "checksum_verified_archive_registry_posting",
            "status": "groups_reported" if groups else "no_groups_documented_in_snapshot",
            "groups": groups,
            "groupCount": len(groups),
            "treatmentSwitchGroupsMayExist": True,
            "randomizedArmComparisonValidated": False,
            "publishedTreatmentRelatedAeRatesReconciled": False,
            "missingGroupsDoNotImplyZeroEvents": True,
            "note": "Distinct registry AE groups may contain first-course, switch-over and retreatment courses. Counts are as posted, not a pooled randomized-arm comparison, not treatment-related adverse-event rates and not independently verified.",
        },
        "readOnly": True,
        "scientificScore": None,
        "fdaApprovalProbability": None,
        "inputReadinessGradeChanged": False,
        "reluctanceGradeChanged": False,
        "independentProtocolSapReviewComplete": False,
        "tradingActionsEnabled": False,
    }
