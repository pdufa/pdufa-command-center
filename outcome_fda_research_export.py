"""Serialize source-linked FDA research events without authorizing model use.

Run: python outcome_fda_research_export.py
Writes JSON to stdout only; never updates immutable FDA audit indexes or training data.
"""
from __future__ import annotations
import json
from datetime import date
from outcome_fda_action_events import check_asof, unique_final_actions
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS, research_summary

SCHEMA_VERSION = "outcome-fda-research-actions-v1"


def build_research_export() -> dict:
    actions = unique_final_actions(list(RESEARCH_ACTIONS))
    ordered = sorted(actions.values(), key=lambda x: (x.application_key, x.event_date, x.submission_key, x.event_type))
    summary = research_summary()
    assert len(ordered) == summary["sampled_action_endpoints"]
    records = []
    for e in ordered:
        # Explicit source publication date is required for true as-of verification.
        published = e.source_publication_date
        records.append({
            "application_key": e.application_key,
            "submission_key": e.submission_key,
            "action_date": e.event_date.isoformat(),
            "action_type": e.event_type,
            "final_agency_action": e.final_agency_action,
            "primary_fda_source_url": e.source_url,
            "source_document_role": e.source_document_role,
            "source_document_sha256": e.source_document_sha256,
            "source_publication_date": published.isoformat() if published else None,
            "feature_asof_verified": False,  # No validated source-as-of provenance yet
            "review_cycle_certified": False,
            "model_eligible": False,
        })
    # Defense in depth: a research-only export must remain ineligible for feature extraction.
    assert all(not row["model_eligible"] and not row["feature_asof_verified"] for row in records)
    assert all(not check_asof(e, date(2026, 10, 26)) for e in ordered)
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_role": "research_only_nontraining",
        "source_scope": "selected_fda_action_letters_and_regulatory_summaries_not_a_complete_cohort",
        "complete_application_denominator_verified": False,
        "independently_certified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "applications_with_sampled_actions": summary["applications_with_sampled_actions"],
        "sampled_action_endpoints": summary["sampled_action_endpoints"],
        "records": records,
    }


if __name__ == "__main__":
    print(json.dumps(build_research_export(), indent=2, sort_keys=True))
