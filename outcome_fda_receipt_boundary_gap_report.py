"""Open FDA receipt-boundary queue derived from selected research action fixtures.

The queue exists to prevent guessed review-cycle start dates. FDA agency
publication redactions and sponsor month-only milestones remain documented as
unresolved evidence, not exact submission receipt dates or model features.
"""
from __future__ import annotations
import json
from datetime import date
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
        "known_milestone": "Sponsor completed and submitted BLA March 2025; FDA accepted May 2025. No agency received day",
        "granularity": "month_only_sponsor",
        "corroboration_url": "https://regenxbio.gcs-web.com/news-releases/news-release-details/regenxbio-announces-regulatory-update-rgx-121-bla-mps-ii/",
        "next_evidence": "FDA dated original submission receipt/filing notice or FDA clinical review chronology",
    },
}


# These disclosures narrow sponsor-side chronology only. They NEVER establish
# the FDA's own redacted receipt date or a certified review-cycle start.
SPONSOR_SUBMISSION_EVIDENCE = {
    ("BLA:125745", "2025-01-15"): {
        "sponsor_reported_submission_month": "2024-05",
        "sponsor_submission_publicly_confirmed_by": "2024-05-20",
        "sponsor_confirmation_source_url":
            "https://www.nasdaq.com/press-release/atara-biotherapeutics-submits-tabelecleucel-tab-celr-biologics-license-application",
        "sponsor_reported_exact_submission_date": None,
        "sponsor_exact_day_source_url": None,
        "sponsor_reported_fda_acceptance_date": None,
        "fda_acceptance_announced_on": "2024-07-17",
        "fda_acceptance_announcement_source_url":
            "https://www.sec.gov/Archives/edgar/data/1604464/000119312524180371/d868530d8k.htm",
        "fda_acceptance_effective_date_independently_verified": False,
    },
    ("BLA:125745", "2026-01-09"): {
        "sponsor_reported_submission_month": "2025-07",
        "sponsor_submission_publicly_confirmed_by": "2025-07-14",
        "sponsor_confirmation_source_url":
            "https://www.nasdaq.com/press-release/atara-biotherapeutics-provides-regulatory-and-business-updates-tabelecleucel-tab-celr",
        # Explicit day was disclosed by Pierre Fabre in November 2025.
        # FDA's published CRL still redacts the amendment receipt date.
        "sponsor_reported_exact_submission_date": "2025-07-11",
        "sponsor_exact_day_source_url":
            "https://www.pierrefabrepharmaceuticals.com/sites/default/files/press/20251103_PR_Final_BLA_Transfer_Announcement_0.pdf",
        "sponsor_reported_fda_acceptance_date": "2025-07-23",
        "fda_acceptance_announced_on": None,
        "fda_acceptance_announcement_source_url":
            "https://www.pierrefabrepharmaceuticals.com/sites/default/files/press/20251103_PR_Final_BLA_Transfer_Announcement_0.pdf",
        "fda_acceptance_effective_date_independently_verified": False,
    },
    ("BLA:125840", "2026-02-07"): {
        "sponsor_reported_submission_month": "2025-03",
        "sponsor_submission_publicly_confirmed_by": "2025-03-13",
        "sponsor_confirmation_source_url":
            "https://www.sec.gov/Archives/edgar/data/1590877/000095017025038711/rgnx-ex99_1.htm",
        "sponsor_reported_exact_submission_date": None,
        "sponsor_exact_day_source_url": None,
        "sponsor_reported_fda_acceptance_date": None,
        "fda_acceptance_announced_on": "2025-05-13",
        "fda_acceptance_announcement_source_url":
            "https://ir.regenxbio.com/news-releases/news-release-details/regenxbio-announces-fda-acceptance-and-priority-review-bla-rgx",
        "fda_acceptance_effective_date_independently_verified": False,
    },
}


def _validated_sponsor_evidence(evidence: dict) -> dict:
    """Check disclosure chronology without inventing agency receipt dates.

    A sponsor-confirmed submission date must fall in its reported month.
    A dated announcement can bound *when the sponsor publicly confirmed*
    submission; it does not prove the agency's timestamp.
    """
    month = evidence["sponsor_reported_submission_month"]
    if len(month) != 7 or month[4] != "-":
        raise ValueError("Expected YYYY-MM sponsor reported submission month")
    start = date.fromisoformat(month + "-01")
    by = date.fromisoformat(evidence["sponsor_submission_publicly_confirmed_by"])
    if by.year != start.year or by.month != start.month or by < start:
        raise ValueError("Sponsor confirmation must belong to reported submission month")
    if not evidence["sponsor_confirmation_source_url"].startswith("https://"):
        raise ValueError("Dated sponsor submission confirmation needs provenance")
    submitted = evidence["sponsor_reported_exact_submission_date"]
    if submitted is not None:
        actual = date.fromisoformat(submitted)
        if not start <= actual <= by:
            raise ValueError("Sponsor exact submission day inconsistent with disclosure")
        if not evidence["sponsor_exact_day_source_url"] or not evidence[
            "sponsor_exact_day_source_url"
        ].startswith("https://"):
            raise ValueError("Sponsor exact day needs a specific source")
    elif evidence["sponsor_exact_day_source_url"] is not None:
        raise ValueError("Do not imply an exact sponsor date with absent exact day")
    reported_accepted = evidence["sponsor_reported_fda_acceptance_date"]
    if reported_accepted is not None:
        accepted = date.fromisoformat(reported_accepted)
        if submitted is None or accepted < date.fromisoformat(submitted):
            raise ValueError("Sponsor reported FDA acceptance must follow submission")
    announced = evidence["fda_acceptance_announced_on"]
    if announced is not None:
        if date.fromisoformat(announced) < by:
            raise ValueError("FDA acceptance announcement precedes submission confirmation")
    if not evidence["fda_acceptance_announcement_source_url"].startswith("https://"):
        raise ValueError("Acceptance disclosure requires a source URL")
    if evidence["fda_acceptance_effective_date_independently_verified"]:
        raise ValueError("Sponsor press statements are not independent FDA confirmation")
    return {
        **evidence,
        # Not a validated FDA-receipt window; only the month of sponsor filing.
        "sponsor_submission_month_earliest_calendar_day": start.isoformat(),
        "exact_fda_received_date": None,
        "exact_fda_received_date_independently_verified": False,
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
        sponsor_info = SPONSOR_SUBMISSION_EVIDENCE.get(
            (event.application_key, event.event_date.isoformat())
        )
        if sponsor_info is None:
            raise ValueError("No source-backed sponsor submission chronology for receipt gap")
        sponsor_info = _validated_sponsor_evidence(sponsor_info)
        rows.append({
            "sponsor_submission_provenance": sponsor_info,
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
        "sponsor_exact_submission_days_documented": sum(
            row["sponsor_submission_provenance"]["sponsor_reported_exact_submission_date"]
            is not None for row in rows
        ),
        "sponsor_exact_submission_days_not_documented": sum(
            row["sponsor_submission_provenance"]["sponsor_reported_exact_submission_date"]
            is None for row in rows
        ),
        "fda_exact_receipt_days_independently_verified": 0,
        "complete_application_denominator_verified": False,
        "independently_certified_review_cycles": 0,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "unlinked_actions": rows,
    }


if __name__ == "__main__":
    print(json.dumps(build_receipt_boundary_gap_report(), indent=2, sort_keys=True))
