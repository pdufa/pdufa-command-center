#!/usr/bin/env python3
"""Conservative ORCA-2 statistical chronology: public research, never review signoff.

No network requests, credentials, calculations of significance, file writes,
FDA forecasts or promotion into the active scientific assessment workflow.
Only an exact, dated, source-located evidence matrix may be processed.
"""
from __future__ import annotations

from datetime import date
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "reports/scientific-levels1-6/orca2-statistical-chronology-20261114.json"
TOP_KEYS = frozenset({
    "schemaVersion", "kind", "nct", "studyCode", "evidenceCutoffDate",
    "context", "events", "databaseLockDate", "unblindingDate",
    "finalSapApprovalRelativeToUnblinding", "priorSapVersionsReconciled",
    "protocolAmendmentHistoryReconciled", "sourceIndependentlyAuthenticated",
    "statisticallyAdjudicated", "fdaApplicationCycleVerified",
    "approvalProbability", "fdaOutcomeJudgment",
})
EVENT_KEYS = frozenset({
    "eventId", "kind", "date", "sourceUrl", "locator", "methods",
    "factualObservation", "sourceReviewStatus",
})
# The individual public *document version* and dated research facts here are
# fixed. Revising them requires a new externally sourced, explicitly reviewed
# research version, not an unvalidated override in a submission.
SOURCES = {
    "protocol_v4": {
        "kind": "PROTOCOL_VERSION_DATE",
        "date": "2021-03-08",
        "sourceUrl": "https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/Prot_000.pdf",
        "methods": ("PRIMARY_MULTIPLICITY_HOCHBERG",),
    },
    "registry_primary_completion": {
        "kind": "REGISTRY_PRIMARY_COMPLETION_DATE",
        "date": "2021-12-23",
        "sourceUrl": "https://clinicaltrials.gov/study/NCT04576949",
        "methods": (),
    },
    "sap_v1": {
        "kind": "SAP_VERSION_DATE",
        "date": "2022-03-25",
        "sourceUrl": "https://cdn.clinicaltrials.gov/large-docs/49/NCT04576949/SAP_001.pdf",
        "methods": ("POWER_SIMULATION_BONFERRONI", "PRIMARY_MULTIPLICITY_HOCHBERG"),
    },
    "journal_publication": {
        "kind": "JOURNAL_PUBLICATION_DATE",
        "date": "2023-07-11",
        "sourceUrl": "https://pmc.ncbi.nlm.nih.gov/articles/PMC10336611/",
        "methods": ("PRIMARY_MULTIPLICITY_HOCHBERG",),
    },
}


def _date(raw):
    if not isinstance(raw, str) or len(raw) != 10:
        raise ValueError("Exact source/event date required")
    try:
        value = date.fromisoformat(raw)
    except (ValueError, TypeError) as exc:
        raise ValueError("Malformed source/event date") from exc
    if value.isoformat() != raw:
        raise ValueError("Date must be YYYY-MM-DD")
    return value


def assess(document):
    """Return limited chronology facts without claiming prespecification proof."""
    if not isinstance(document, dict) or set(document) != TOP_KEYS:
        raise ValueError("Unexpected or missing evidence/verification fields")
    if (type(document["schemaVersion"]) is not int or document["schemaVersion"] != 1
            or document["kind"] != "ORCA2_PHASE_FIRST_STATISTICAL_CHRONOLOGY_RESEARCH_ONLY"
            or document["nct"] != "NCT04576949" or document["studyCode"] != "ACH-CYT-03"
            or document["context"] != "CURRENT_SOURCE_OUTCOME_EXPOSED_NOT_BLIND"):
        raise ValueError("Wrong research cohort or accidental outcome-blind promotion")
    cutoff = _date(document["evidenceCutoffDate"])
    if cutoff != date(2026, 11, 14):
        raise ValueError("Research cutoff is frozen for this case version")
    for key in ("databaseLockDate", "unblindingDate", "approvalProbability", "fdaOutcomeJudgment"):
        if document[key] is not None:
            raise ValueError("No real verification supports setting " + key)
    for key in ("priorSapVersionsReconciled", "protocolAmendmentHistoryReconciled",
                "sourceIndependentlyAuthenticated", "statisticallyAdjudicated",
                "fdaApplicationCycleVerified"):
        if document[key] is not False:
            raise ValueError("External review cannot be self-certified by research JSON")
    if document["finalSapApprovalRelativeToUnblinding"] != "UNRESOLVED":
        raise ValueError("Final SAP timing cannot be inferred from document dates")
    events = document["events"]
    if not isinstance(events, list) or len(events) != len(SOURCES):
        raise ValueError("All four fixed research source events are required")
    indexed = {}
    for row in events:
        if not isinstance(row, dict) or set(row) != EVENT_KEYS:
            raise ValueError("Unexpected source event fields")
        event_id = row["eventId"]
        if not isinstance(event_id, str) or event_id not in SOURCES or event_id in indexed:
            raise ValueError("Duplicate or unknown source event")
        known = SOURCES[event_id]
        if any(row[key] != known[key] for key in ("kind", "date", "sourceUrl")):
            raise ValueError("Source/date mismatch for fixed research event")
        if (not isinstance(row["methods"], list)
                or tuple(row["methods"]) != known["methods"]):
            raise ValueError("Statistical-method role was misassigned or altered")
        if (row["sourceReviewStatus"] != "PUBLIC_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED"
                or not isinstance(row["locator"], str) or not 1 <= len(row["locator"]) <= 300
                or not isinstance(row["factualObservation"], str)
                or not 1 <= len(row["factualObservation"]) <= 1200):
            raise ValueError("Unreviewed source locator or observation is invalid")
        if _date(row["date"]) > cutoff:
            raise ValueError("Source dated after research cutoff")
        indexed[event_id] = row
    if set(indexed) != set(SOURCES):
        raise ValueError("Missing required original source event")
    pre = _date(indexed["protocol_v4"]["date"]) < _date(indexed["registry_primary_completion"]["date"])
    later = _date(indexed["sap_v1"]["date"]) > _date(indexed["registry_primary_completion"]["date"])
    if not pre or not later:
        raise ValueError("Unexpected chronology; reverify original documents")
    return {
        "nct": document["nct"], "assessmentLevel": 5,
        "status": "PUBLIC_SOURCE_CHRONOLOGY_ONLY_NOT_SCIENTIFICALLY_ADJUDICATED",
        "currentResearchIsBlind": False,
        "protocolVersionPredatesRegistryPrimaryCompletion": pre,
        "preCompletionProtocolExplicitlyMentionsPrimaryHochberg": True,
        "sapVersionDateAfterRegistryPrimaryCompletion": later,
        "sapExplainsBonferroniForPowerAndHochbergForPrimaryTesting": True,
        "multiplicityInconsistencyEstablished": False,
        "databaseLockDateVerified": False,
        "unblindingDateVerified": False,
        "finalSapPrespecificationRelativeToUnblinding": "UNRESOLVED",
        "earlierSapVersionsReconciled": False,
        "sourceIndependentlyAuthenticated": False,
        "scientificReviewStatus": "NOT_ADJUDICATED",
        "statisticalDeficiencyEstablished": False,
        "fdaPredictionPermitted": False,
        "approvalProbability": None,
        "fdaOutcomeJudgment": None,
        "sourceEventCount": len(indexed),
        "needsIndependentEvidence": [
            "Actual database-lock and treatment-code unblinding timestamps",
            "Final signed SAP effective date and change-control audit trail",
            "Earlier SAP versions, amendments and documented protocol-to-SAP changes",
            "Clinical Study Report and traceable analysis population/estimands",
            "Independent biostatistical review of familywise testing and secondary hierarchy",
            "Authorized original-source authentication and separate reviewer challenge",
        ],
        "interpretation": (
            "Pre-primary-completion protocol text documents Hochberg for the two "
            "primary comparisons. The 2022 SAP distinguishes Bonferroni power "
            "simulations from Hochberg primary multiplicity. This does not prove "
            "when the final SAP was fixed relative to lock or unblinding, "
            "nor that statistical methods or findings were independently validated."
        ),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, default=INPUT)
    args = parser.parse_args()
    print(json.dumps(assess(json.loads(args.case.read_text(encoding="utf-8"))), indent=2))


if __name__ == "__main__":
    main()
