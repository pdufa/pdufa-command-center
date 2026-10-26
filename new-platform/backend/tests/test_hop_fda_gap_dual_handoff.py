"""Synthetic-only tests for private A/B FDA source handoff boundaries."""
from __future__ import annotations

from copy import deepcopy
from datetime import date

import pytest

from app.hop_fda_gap_dual_handoff import (
    STATUS, prepare_gap_source_review_handoffs,
)
from app.hop_fda_prior_pdf_lead_join import PUBLISHED_LEAD_STATUS
from app.hop_fda_gap_research_packets import VERIFICATION


def pdf_lead(n: int, present: bool):
    return {
        "published_letter_source_sha256": f"{n:064x}",
        "official_fda_pdf_url": (
            f"https://download.open.fda.gov/crl/synthetic{n}.pdf" if present else None
        ),
        "historically_observed_full_pdf_sha256": (
            f"{n+10:064x}" if present else None
        ),
        "published_letter_type": "COMPLETE RESPONSE",
        "published_letter_date_not_adjudicated_action_date": "2020-01-03",
        "pdf_lead_status": (
            PUBLISHED_LEAD_STATUS if present else "NO_RELEASED_PDF_SOURCE_LEAD"
        ),
        "pdf_bytes_revalidated_in_current_run": False,
        "action_page_range_independently_verified": False,
        "review_cycle_independently_verified": False,
        "model_eligible": False,
    }


def example_packet(pid, hashes, *, ambiguous=False, observed=True):
    kind = ("AMBIGUOUS_APPLICATION_ID_RESEARCH" if ambiguous
            else "APPLICATION_IDENTITY_RESEARCH")
    return {
        "packet_id": pid,
        "packet_kind": kind,
        "application_id_candidate": None if ambiguous else pid,
        "published_letter_source_hashes": hashes,
        "published_letter_references": len(hashes),
        "source_gap_reason": (
            "AMBIGUOUS_OR_UNPARSEABLE_LETTER_APPLICATION" if ambiguous
            else "APPLICATION_NOT_IN_TABULAR_APPROVAL_CENTRIC_SOURCE"
        ),
        "published_letter_type_counts": {"COMPLETE RESPONSE": len(hashes)},
        "research_query_text": "FDA original action letter",
        "manual_evidence_lead_url": "",
        "manual_evidence_document_type": "",
        "manual_evidence_sha256": "",
        "manual_research_notes": "",
        "evidence_lead_status": VERIFICATION,
        "original_review_cycle": None,
        "fda_action_outcome": None,
        "adjudicator_authenticated": False,
        "model_eligible": False,
        "previously_probed_published_pdf_leads": [
            pdf_lead(int(h, 16), observed and i % 2 == 0)
            for i, h in enumerate(hashes)
        ],
    }


def synthetic():
    packets = [
        example_packet("NDA000003", [f"{1:064x}", f"{2:064x}"]),
        example_packet("LETTER_" + f"{3:064x}", [f"{3:064x}"], ambiguous=True),
    ]
    pinned = {
        "status": "ORIGINAL_FDA_APPLICATION_EVIDENCE_SEARCH_PACKETS_UNVERIFIED",
        "research_cutoff": "2026-10-25",
        "total_evidence_search_packets": 2,
        "source_letter_references": 3,
        "unverified_application_research_packets": 1,
        "ambiguous_letter_identity_packets": 1,
        "independently_adjudicated_original_review_cycles": 0,
        "complete_fda_decision_denominator_verified": False,
        "model_eligible_records": 0,
        "prediction_probability": None,
        "private_grouped_packets_not_exported": True,
    }
    return packets, pinned


def prepare(packets=None, pinned=None):
    default_packets, default_pinned = synthetic()
    return prepare_gap_source_review_handoffs(
        default_packets if packets is None else packets,
        pinned_audit=default_pinned if pinned is None else pinned,
        as_of=date(2026, 10, 25),
    )


def test_first_and_second_private_packets_have_same_evidence_but_blank_independent_claims():
    first, second, audit = prepare()
    assert len(first) == len(second) == 2
    assert all(x["packet_role"] == "FIRST" and x["packet_status"] == STATUS
               for x in first)
    assert all(y["packet_role"] == "SECOND" and y["packet_status"] == STATUS
               for y in second)
    for a, b in zip(first, second):
        for key in a:
            if key != "packet_role":
                assert a[key] == b[key]
        assert a["reviewer_identity"] == ""
        assert b["reviewer_observed_original_pdf_sha256"] == ""
        assert a["reviewer_observed_action_date"] == ""
        assert a["reviewer_observed_review_cycle"] == ""
        assert a["fda_decision_independently_adjudicated"] is False
        assert a["model_eligible"] is False
        assert a["prediction_probability"] is None
    first[0]["previously_probed_pdf_leads"][0]["official_fda_pdf_url"] = "edited"
    assert second[0]["previously_probed_pdf_leads"][0]["official_fda_pdf_url"] != "edited"
    assert audit["published_letter_source_references"] == 3
    assert audit["first_blank_review_packets"] == 2
    assert audit["second_blank_review_packets"] == 2
    assert audit["independent_review_pairs_completed"] == 0
    assert audit["fda_review_cycle_outcomes_independently_verified"] == 0
    assert audit["complete_original_nda_bla_decision_denominator_verified"] is False
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None


@pytest.mark.parametrize("tamper", [
    "duplicate_packet", "duplicate_letter", "model_eligible", "invent_action",
    "fake_authenticated", "inject_evidence", "fake_review_cycle", "unknown_field",
    "wrong_pdf_sha", "unsafe_pdf_url", "fake_pdf_review", "fake_pdf_eligible",
    "missing_pdf", "duplicate_pdf", "wrong_kind", "bad_app_id",
    "wrong_type_summary", "mismatched_count",
])
def test_false_outcome_or_corrupt_evidence_fails_closed(tamper):
    packets, pinned = synthetic()
    if tamper == "duplicate_packet":
        packets[1]["packet_id"] = packets[0]["packet_id"]
    elif tamper == "duplicate_letter":
        packets[1]["published_letter_source_hashes"] = [f"{1:064x}"]
        packets[1]["packet_id"] = "LETTER_" + f"{1:064x}"
        packets[1]["previously_probed_published_pdf_leads"] = [pdf_lead(1, True)]
    elif tamper == "model_eligible":
        packets[0]["model_eligible"] = True
    elif tamper == "invent_action":
        packets[0]["fda_action_outcome"] = "NONAPPROVAL"
    elif tamper == "fake_authenticated":
        packets[0]["adjudicator_authenticated"] = True
    elif tamper == "inject_evidence":
        packets[0]["manual_evidence_lead_url"] = "https://www.fda.gov/drugs/example"
    elif tamper == "fake_review_cycle":
        packets[0]["original_review_cycle"] = 1
    elif tamper == "unknown_field":
        packets[0]["verified"] = True
    elif tamper == "wrong_pdf_sha":
        packets[0]["previously_probed_published_pdf_leads"][0]["historically_observed_full_pdf_sha256"] = "fake"
    elif tamper == "unsafe_pdf_url":
        packets[0]["previously_probed_published_pdf_leads"][0]["official_fda_pdf_url"] = "https://download.open.fda.gov.evil.com/crl/abc.pdf"
    elif tamper == "fake_pdf_review":
        packets[0]["previously_probed_published_pdf_leads"][0]["review_cycle_independently_verified"] = True
    elif tamper == "fake_pdf_eligible":
        packets[0]["previously_probed_published_pdf_leads"][0]["model_eligible"] = True
    elif tamper == "missing_pdf":
        packets[0]["previously_probed_published_pdf_leads"].pop()
    elif tamper == "duplicate_pdf":
        packets[0]["previously_probed_published_pdf_leads"][1] = deepcopy(
            packets[0]["previously_probed_published_pdf_leads"][0]
        )
    elif tamper == "wrong_kind":
        packets[1]["packet_kind"] = "APPLICATION_IDENTITY_RESEARCH"
    elif tamper == "bad_app_id":
        packets[0]["application_id_candidate"] = "NDA000004"
    elif tamper == "wrong_type_summary":
        packets[0]["published_letter_type_counts"]["TENTATIVE APPROVAL"] = 1
    elif tamper == "mismatched_count":
        pinned["total_evidence_search_packets"] = 3
    with pytest.raises(ValueError):
        prepare(packets, pinned)


def test_research_audit_is_only_aggregate_and_never_certifies_review():
    first, second, audit = prepare()
    assert "NDA000003" not in str(audit)
    assert "synthetic1.pdf" not in str(audit)
    assert audit["pdf_lead_counts"] == {
        "previously_confirmed_pdf_letter_links": 2,
        "unavailable_pdf_letter_links": 1,
    }
    assert not any("reviewer_identity" in str(audit) for _ in [0])
    assert len(first[0]["previously_probed_pdf_leads"]) == 2
    assert len(second[1]["previously_probed_pdf_leads"]) == 1
    assert audit["private_per_application_records_not_exported"] is True
