"""Open FDA receipt-boundary queue derived from selected research action fixtures.

The queue exists to prevent guessed review-cycle start dates. FDA agency
publication redactions and sponsor month-only milestones remain documented as
unresolved evidence, not exact submission receipt dates or model features.
"""
from __future__ import annotations
import json
from outcome_fda_action_events import unique_final_actions
from outcome_fda_research_action_fixtures import RESEARCH_ACTIONS
from outcome_fda_review_timeline_evidence import REVIEW_TIMELINES, validate_review_timelines

SCHEMA_VERSION = "outcome-fda-receipt-boundary-gaps-v1"

MISSING_RECEIPT_EVIDENCE = {
    ("BLA:125745", "2025-01-15"): {
        "original_letter_url": "https://download.open.fda.gov/crl/CRL_BLA125745_20250115.pdf",
        "reason": "FDA original Complete Response letter redacts original submission receipt",
        "known_milestone": "Sponsor reports BLA submitted May 2024; FDA accepted July 2024",
        "granularity": "month_only_sponsor",
        "corroboration_url": "https://www.sec.gov/Archives/edgar/data/1604464/000095017025072040/atra-20250331.htm",
        "next_evidence": "FDA original BLA receipt/filing correspondence or unredacted review record",
    },
    ("BLA:125745", "2026-01-09"): {
        "original_letter_url": "https://download.open.fda.gov/crl/CRL_BLA125745_20260109.pdf",
        "reason": "FDA letter redacts the resubmission amendment date while linking prior 2025 CRL",
        "known_milestone": "Sponsor reports FDA-accepted resubmission in July 2025",
        "granularity": "month_only_sponsor",
        "corroboration_url": "https://www.sec.gov/Archives/edgar/data/1604464/000119312525276219/atra-20250930.htm",
        "next_evidence": "FDA dated resubmission acceptance letter or unredacted review chronology",
    },
    ("BLA:125840", "2026-02-07"): {
        "original_letter_url": "https://download.open.fda.gov/crl/CRL_BLA125840_20260207.pdf",
        "reason": "FDA Complete Response letter redacts original BLA submission receipt",
        "known_milestone": "Sponsor reports FDA BLA acceptance May 2025, NOT original receipt day",
        "granularity": "month_only_sponsor",
        "corroboration_url": "https://regenxbio.gcs-web.com/news-releases/news-release-details/regenxbio-announces-regulatory-update-rgx-121-bla-mps-ii/",
        "next_evidence": "FDA dated original submission receipt/filing notice or FDA clinical review chronology",
    },
}


def build_receipt_boundary_gap_report() -> dict:
    validate_review_timelines()
    actions = unique_final_actions(list(RESEARCH_ACTIONS))
    linked = {
        (c.application_key, c.submission_key, c.action_date, c.action_type)
        for c in REVIEW_TIMELINES
    }
    outstanding = sorted(set(actions) - linked)
    rows = []
    for key in outstanding:
        event = actions[key]
        metadata = MISSING_RECEIPT_EVIDENCE.get((event.application_key, event.event_date.isoformat()))
        if metadata is None:
            raise ValueError("Research FDA action missing its explicit receipt-boundary blocker")
        if metadata["original_letter_url"] != event.source_url:
            raise ValueError("Unlinked FDA action and evidence metadata must agree")
        rows.append({
            "application_key": event.application_key,
            "submission_key": event.submission_key,
            "final_fda_action_date": event.event_date.isoformat(),
            "final_fda_action_type": event.event_type,
            "source_document_role": event.source_document_role,
            "final_action_source_url": event.source_url,
            "exact_submission_received_date": None,
            "receipt_date_verified": False,
            "review_cycle_independently_certified": False,
            "model_eligible": False,
            "evidence": metadata.copy(),
        })
    assert len(rows) == len(outstanding)
    return {
        "schema_version": SCHEMA_VERSION,
        "dataset_role": "research_only_nontraining",
        "selected_action_denominator": len(actions),
        "structured_timeline_count": len(linked),
        "unlinked_actions_count": len(rows),
        "unlinked_application_count": len({r["application_key"] for r in rows}),
        "complete_application_denominator_verified": False,
        "independently_certified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "unlinked_actions": rows,
    }


if __name__ == "__main__":
    print(json.dumps(build_receipt_boundary_gap_report(), indent=2, sort_keys=True))
