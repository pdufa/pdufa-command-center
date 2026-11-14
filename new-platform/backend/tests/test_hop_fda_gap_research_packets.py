"""Synthetic-only original FDA source-lead packet safety and grouping tests."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from app.hop_fda_gap_research_packets import (
    VERIFICATION, build_source_search_packets, screen_private_evidence_leads,
)

AS_OF = date(2026, 10, 25)


def row(n, app, reason):
    reasons = (
        "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION",
        "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION",
        "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE",
    )
    return {
        "source_record_sha256": f"{n:064x}",
        "application_candidate": app,
        "review_reason": reason,
        "review_priority": str(reasons.index(reason) + 1),
        "published_letter_type": "COMPLETE RESPONSE",
        "repeated_published_letter_references_for_candidate": (
            2 if app == "NDA000003" else 1 if app else None
        ),
        "original_application_review_cycle": None,
        "fda_action_outcome": None,
        "evidence_independently_adjudicated": False,
        "model_eligible": False,
    }


def fixture():
    queue = [
        row(1, None, "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION"),
        row(2, "NDA000003", "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE"),
        row(3, "NDA000003", "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE"),
        row(4, "BLA000005", "APPLICATION_IN_TABLE_BUT_NO_ORIGINAL_SUBMISSION"),
        row(5, None, "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION"),
    ]
    source_audit = {
        "status": "PUBLISHED_FDA_LETTER_IDENTITY_GAPS_UNVERIFIED",
        "research_cutoff": "2026-10-25",
        "review_queue_references": 5,
        "distinct_candidate_applications_needing_source_research": 2,
        "ambiguous_or_unparseable_letter_references": 2,
        "candidate_applications_with_repeated_published_letters": 1,
        "maximum_published_letter_references_for_one_missing_application": 2,
        "nda_bla_no_original_spine_letter_references": 3,
        "fda_original_actions_independently_verified": 0,
        "complete_original_nda_bla_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
    }
    return queue, source_audit


def prepare():
    queue, audit = fixture()
    return build_source_search_packets(queue, as_of=AS_OF, pinned_audit=audit)


def test_repeated_letters_grouped_as_one_research_task_not_decisions():
    packets, stats = prepare()
    assert len(packets) == 4
    assert stats["source_letter_references"] == 5
    assert stats["unverified_application_research_packets"] == 2
    assert stats["ambiguous_letter_identity_packets"] == 2
    assert stats["total_evidence_search_packets"] == 4
    assert stats["applications_with_repeated_letter_references"] == 1
    nda = next(p for p in packets if p["packet_id"] == "NDA000003")
    assert nda["published_letter_references"] == 2
    assert nda["research_query_text"] == "NDA 000003 original FDA action letter"
    assert len(nda["published_letter_source_hashes"]) == 2
    assert nda["evidence_lead_status"] == VERIFICATION
    assert nda["manual_evidence_lead_url"] == ""
    assert nda["original_review_cycle"] is None
    assert nda["fda_action_outcome"] is None
    assert nda["model_eligible"] is False
    assert stats["independently_adjudicated_original_review_cycles"] == 0
    assert stats["prediction_probability"] is None


def test_ambiguous_letter_ids_stay_separate_until_human_source_review():
    packets, audit = prepare()
    unknown = [p for p in packets
               if p["packet_kind"] == "AMBIGUOUS_APPLICATION_ID_RESEARCH"]
    assert len(unknown) == 2
    assert all(p["application_id_candidate"] is None for p in unknown)
    assert all(p["packet_id"].startswith("LETTER_") for p in unknown)
    assert len({p["packet_id"] for p in unknown}) == 2


def test_blank_evidence_packets_and_official_lead_still_unverified():
    packets, audit = prepare()
    report = screen_private_evidence_leads(packets, deepcopy(packets))
    assert report["lead_screening_counts"] == {"NO_OFFICIAL_SOURCE_LEAD": 4}
    assert report["model_eligible_records"] == 0
    candidate = deepcopy(packets)
    candidate[0]["manual_evidence_lead_url"] = (
        "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/fictional.pdf"
    )
    candidate[0]["manual_evidence_document_type"] = "FDA_APPROVAL_LETTER"
    candidate[0]["manual_evidence_sha256"] = "e" * 64
    report = screen_private_evidence_leads(packets, candidate)
    assert report["lead_screening_counts"] == {
        "NO_OFFICIAL_SOURCE_LEAD": 3,
        "OFFICIAL_URL_WITH_UNAUTHENTICATED_SOURCE_DIGEST_CLAIM": 1,
    }
    assert report["original_fda_documents_independently_authenticated"] == 0
    assert report["independently_adjudicated_original_review_cycles"] == 0
    assert report["prediction_probability"] is None


@pytest.mark.parametrize("change", [
    "duplicate_letter_sha", "promote_letter", "promote_audit",
    "missing_source", "break_count", "invalid_app", "false_review_cycle",
    "false_action_label", "tamper_priority", "invent_unique_letter_count",
    "unsafe_source_type", "ambiguous_with_app",
])
def test_changed_source_queue_cannot_become_model_data(change):
    queue, source_audit = fixture()
    if change == "duplicate_letter_sha":
        queue[1]["source_record_sha256"] = queue[0]["source_record_sha256"]
    elif change == "promote_letter":
        queue[1]["model_eligible"] = True
    elif change == "promote_audit":
        source_audit["model_eligible_records"] = 1
    elif change == "missing_source":
        queue.pop()
    elif change == "break_count":
        source_audit["distinct_candidate_applications_needing_source_research"] = 10
    elif change == "invalid_app":
        queue[1]["application_candidate"] = "NDA000003__"
    elif change == "false_review_cycle":
        queue[1]["original_application_review_cycle"] = 1
    elif change == "false_action_label":
        queue[1]["fda_action_outcome"] = "REJECTED"
    elif change == "tamper_priority":
        queue[1]["review_priority"] = "1"
    elif change == "invent_unique_letter_count":
        queue[1]["repeated_published_letter_references_for_candidate"] = 3
    elif change == "unsafe_source_type":
        queue[1]["published_letter_type"] = "=IMPORTXML"
    elif change == "ambiguous_with_app":
        queue[0]["application_candidate"] = "NDA000001"
    with pytest.raises(ValueError):
        build_source_search_packets(queue, as_of=AS_OF, pinned_audit=source_audit)


@pytest.mark.parametrize("field,value", [
    ("model_eligible", True),
    ("fda_action_outcome", "APPROVED"),
    ("original_review_cycle", 2),
    ("application_id_candidate", "NDA999999"),
    ("evidence_lead_status", "VERIFIED"),
    ("published_letter_references", 5),
    ("manual_evidence_lead_url", "https://www.fda.gov.evil.test/letter"),
    ("manual_evidence_lead_url", "http://www.fda.gov/letter"),
    ("manual_evidence_lead_url", "https://www.fda.gov@evil.test/letter"),
    ("manual_evidence_lead_url", "https://www.fda.gov/"),
    ("manual_evidence_document_type", "APPROVED_VALIDATED"),
    ("manual_evidence_sha256", "NOT_SHA"),
    ("manual_research_notes", "=HYPERLINK(1)"),
])
def test_screening_rejects_fake_promotions_or_untrusted_leads(field, value):
    packets, _ = prepare()
    changed = deepcopy(packets)
    changed[0]["manual_evidence_lead_url"] = (
        "https://www.fda.gov/drugs/application-history"
    )
    changed[0]["manual_evidence_document_type"] = "FDA_APPLICATION_HISTORY"
    changed[0]["manual_evidence_sha256"] = "a" * 64
    changed[0][field] = value
    if field == "manual_evidence_lead_url":
        # Do not mistake an allowed doc class for a valid spoofed URL.
        pass
    with pytest.raises(ValueError):
        screen_private_evidence_leads(packets, changed)


def test_real_pinned_84_applications_plus_17_unknown_identity_tickets():
    import json
    from pathlib import Path
    p = (Path(__file__).resolve().parents[1] / "app" / "research_sources"
         / "hop_fda_unmatched_letter_gap_audit_20261025.json")
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["distinct_candidate_applications_needing_source_research"] == 84
    assert data["ambiguous_or_unparseable_letter_references"] == 17
    assert data["review_queue_references"] == 124
    assert data["candidate_applications_with_repeated_published_letters"] == 20
    assert data["maximum_published_letter_references_for_one_missing_application"] == 3
    assert data["fda_original_actions_independently_verified"] == 0
    assert data["model_eligible_records"] == 0



def test_actual_fda_research_packet_audit_reconciles_pinned_124_letters():
    import json
    from pathlib import Path
    directory = Path(__file__).resolve().parents[1] / "app" / "research_sources"
    report = json.loads(
        (directory / "hop_fda_grouped_evidence_search_packets_20261025.json")
        .read_text(encoding="utf-8")
    )
    letters = json.loads(
        (directory / "hop_fda_unmatched_letter_gap_audit_20261025.json")
        .read_text(encoding="utf-8")
    )
    assert report["status"] == "ORIGINAL_FDA_APPLICATION_EVIDENCE_SEARCH_PACKETS_UNVERIFIED"
    assert report["source_letter_references"] == letters["review_queue_references"] == 124
    assert report["unverified_application_research_packets"] == 84
    assert letters["distinct_candidate_applications_needing_source_research"] == 84
    assert report["ambiguous_letter_identity_packets"] == 17
    assert letters["ambiguous_or_unparseable_letter_references"] == 17
    assert report["total_evidence_search_packets"] == 101
    assert report["applications_with_repeated_letter_references"] == 20
    assert report["letter_references_grouped_under_application_research"] == 107
    assert report["pinned_fda_applications_tsv_sha256"] == (
        letters["source_applications_tsv_sha256"]
    )
    assert report["pinned_fda_submissions_tsv_sha256"] == (
        letters["source_submissions_tsv_sha256"]
    )
    assert report["private_grouped_packets_not_exported"] is True
    assert report["independently_adjudicated_original_review_cycles"] == 0
    assert report["model_eligible_records"] == 0
    assert report["approval_rate"] is None
    assert report["prediction_probability"] is None
    assert report["predictive_accuracy"] is None
