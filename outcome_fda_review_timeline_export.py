"""Export selected FDA review timelines as research-only, provenance-linked JSON.

This is an auditable research export, NOT a certified review-cycle cohort.
Run: python outcome_fda_review_timeline_export.py
"""
from __future__ import annotations

import json
from datetime import date

from outcome_fda_action_events import unique_final_actions
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS
from outcome_fda_review_timeline_evidence import (
    REVIEW_TIMELINES, validate_review_timelines, review_timeline_summary,
    ALYGLO_PDUFA_GOAL_SOURCE_CONFLICT,
    ULTRAGENYX_PDUFA_GOAL_SOURCE_CONFLICT,
    MESOBLAST_SBRA_IDENTIFIER_CONFLICT,
    REPLIMUNE_FINAL_ACTION_VS_REVIEW_RECOMMENDATION,
    LANTIDRA_2021_CRL_EVIDENCE_STATUS,
    MESOBLAST_2020_CRL_EVIDENCE_STATUS,
)

SCHEMA_VERSION = "outcome-fda-research-review-timelines-v1"

# Conflicts are retained as explicit source-specific values rather than
# normalized to a fabricated universal PDUFA date or action classification.
DATA_QUALITY_FINDINGS = {
    "BLA:125706:ORIGINAL": {
        "code": "SIGNED_ORIGINAL_2020_CRL_NOT_DIRECTLY_VERIFIED",
        "detail": MESOBLAST_2020_CRL_EVIDENCE_STATUS,
    },
    "BLA:125743:RESUBMISSION-1": {
        "code": "FDA_SOURCE_PDUFA_GOAL_CONFLICT",
        "detail": ALYGLO_PDUFA_GOAL_SOURCE_CONFLICT,
    },
    "BLA:125845:RESUBMISSION-1": {
        "code": "FDA_SOURCE_PDUFA_GOAL_CONFLICT",
        "detail": ULTRAGENYX_PDUFA_GOAL_SOURCE_CONFLICT,
    },
    "BLA:125706:RESUBMISSION-1": {
        "code": "FDA_PRIMARY_SOURCE_APPLICATION_IDENTIFIER_CONFLICT",
        "detail": MESOBLAST_SBRA_IDENTIFIER_CONFLICT,
    },
    "BLA:125706:RESUBMISSION-2": {
        "code": "FDA_PRIMARY_SOURCE_APPLICATION_IDENTIFIER_CONFLICT",
        "detail": MESOBLAST_SBRA_IDENTIFIER_CONFLICT,
    },
    "BLA:125827:RESUBMISSION-2": {
        "code": "FDA_REVIEW_RECOMMENDATION_VS_FINAL_ACTION",
        "detail": REPLIMUNE_FINAL_ACTION_VS_REVIEW_RECOMMENDATION,
    },
    "BLA:125734:ORIGINAL": {
        "code": "SIGNED_ORIGINAL_CRL_NOT_DIRECTLY_VERIFIED",
        "detail": LANTIDRA_2021_CRL_EVIDENCE_STATUS,
    },
}


def build_timeline_export() -> dict:
    validate_review_timelines()
    summary = review_timeline_summary()
    observed = unique_final_actions(list(RESEARCH_ACTIONS))
    rows = []
    for cycle in sorted(REVIEW_TIMELINES, key=lambda c: (
        c.application_key, c.received_date, c.action_date, c.submission_key,
    )):
        key = (cycle.application_key, cycle.submission_key, cycle.action_date, cycle.action_type)
        event = observed[key]
        rows.append({
            "application_key": cycle.application_key,
            "submission_key": cycle.submission_key,
            "submission_received_date": cycle.received_date.isoformat(),
            "final_fda_action_date": cycle.action_date.isoformat(),
            "final_fda_action_type": cycle.action_type,
            "pdufa_goal_date_from_regulatory_history": (
                cycle.pdufa_goal_date.isoformat() if cycle.pdufa_goal_date else None
            ),
            "receipt_evidence_url": cycle.receipt_source_url,
            "final_action_evidence_url": cycle.final_action_source_url,
            "action_evidence_role": event.source_document_role,
            "regulatory_history_source_url": cycle.regulatory_history_source_url,
            "source_document_sha256": event.source_document_sha256,
            "source_publication_date": (
                event.source_publication_date.isoformat()
                if event.source_publication_date else None
            ),
            "data_quality_finding": DATA_QUALITY_FINDINGS.get(cycle.submission_key),
            "source_publication_asof_verified": False,
            "review_cycle_independently_certified": False,
            "model_eligible": False,
        })
    assert len(rows) == summary["source_supported_review_timelines"]
    assert all(row["model_eligible"] is False
               and row["source_publication_asof_verified"] is False
               and row["review_cycle_independently_certified"] is False
               for row in rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_role": "research_only_nontraining",
        "sampled_fda_actions": summary["selected_research_action_endpoints"],
        "sampled_application_identifiers": summary["selected_research_application_identifiers"],
        "source_supported_timelines": summary["source_supported_review_timelines"],
        "sampled_actions_without_structured_timeline": (
            summary["selected_actions_without_structured_timeline"]
        ),
        "sampled_applications_without_structured_timeline": (
            summary["selected_applications_without_structured_timeline"]
        ),
        "complete_application_denominator_verified": False,
        "independently_certified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "timelines": rows,
    }


if __name__ == "__main__":
    print(json.dumps(build_timeline_export(), sort_keys=True, indent=2))
