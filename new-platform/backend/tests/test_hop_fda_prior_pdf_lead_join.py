"""Synthetic source PDF availability joins; zero historical FDA outcome labels."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.hop_fda_prior_pdf_lead_join import join_prior_pdf_probes_to_research_packets

ARCHIVE_SHA = "a" * 64
PDF_A = "b" * 64
PDF_B = "c" * 64
RUN_URL = "https://github.com/example/example/actions/runs/1"
CRL_ARCHIVE_URL = "https://download.open.fda.gov/transparency/crl/transparency-crl-0001-of-0001.json.zip"


def packet(packet_id, source_ids):
    return {
        "packet_id": packet_id,
        "published_letter_source_hashes": [f"{i:064x}" for i in source_ids],
        "published_letter_references": len(source_ids),
        "model_eligible": False,
        "adjudicator_authenticated": False,
        "fda_action_outcome": None,
        "original_review_cycle": None,
        "evidence_lead_status": "UNVERIFIED_FDA_SOURCE_LEAD_REQUIRES_INDEPENDENT_REVIEW",
        "manual_evidence_lead_url": "",
        "manual_evidence_sha256": "",
    }


def pdf_row(i, name, sha):
    return {
        "source_record_sha256": f"{i:064x}",
        "source_file_name_as_published": name,
        "document_fetch_status": (
            "OFFICIAL_PDF_BYTES_CONFIRMED" if sha else "NO_SAFE_FILENAME_TO_CHECK"
        ),
        "official_fda_pdf_url_if_confirmed": (
            "https://download.open.fda.gov/crl/" + name if sha else None
        ),
        "full_document_sha256_if_confirmed": sha,
        "letter_type_as_published": "COMPLETE RESPONSE",
        "letter_date_as_published": "01/01/2020",
        "document_identity_adjudicated": False,
        "effective_fda_action_date_verified": False,
        "review_cycle_verified": False,
        "model_eligible": False,
    }


def fixture():
    packets = [
        packet("NDA000003", [1, 2]),
        packet("LETTER_" + f"{3:064x}", [3]),
        packet("BLA000004", [4, 5]),
    ]
    probe = {
        "status": "PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION",
        "records": [
            pdf_row(1, "example-a.pdf", PDF_A),
            pdf_row(2, "example-a.pdf", PDF_A),
            pdf_row(3, "example-a.pdf", PDF_A),
            pdf_row(4, "example-b.pdf", PDF_B),
            pdf_row(5, "Under Review for Release", None),
        ],
    }
    audit = {
        "status": probe["status"],
        "model_eligible_records": 0,
        "prediction_probability": None,
        "independently_verified_review_cycles": 0,
        "complete_application_denominator_verified": False,
        "total_identity_review_cases": 5,
        "official_pdf_bytes_confirmed": 4,
        "document_fetch_status_counts": {
            "OFFICIAL_PDF_BYTES_CONFIRMED": 4,
            "NO_SAFE_FILENAME_TO_CHECK": 1,
        },
        "source_letter_archive_sha256": {CRL_ARCHIVE_URL: ARCHIVE_SHA},
    }
    index = {
        "status": "ALL_PUBLISHED_FDA_ACTION_PDFS_QUARANTINED_NOT_VALIDATED_OUTCOMES",
        "model_eligible_records": 0,
        "prediction_probability": None,
        "adjudicated_review_cycle_outcomes": 0,
        "complete_application_denominator_verified": False,
        "published_letter_records": 5,
        "full_official_pdf_bytes_confirmed": 4,
        "source_records_without_safe_pdf_filename": 1,
        "original_fda_archive_sha256": ARCHIVE_SHA,
        "source_collection_run_url": RUN_URL,
    }
    groups = {
        "status": "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION",
        "model_eligible_records": 0,
        "complete_application_denominator_verified": False,
        "independently_verified_review_cycle_outcomes": 0,
        "unique_confirmed_pdf_documents": 2,
        "official_pdf_confirmed_letter_references": 4,
        "original_fda_archive_sha256": ARCHIVE_SHA,
    }
    return packets, probe, audit, index, groups


def join(*args):
    return join_prior_pdf_probes_to_research_packets(
        args[0], args[1], args[2],
        pinned_pdf_index=args[3], pinned_pdf_group_index=args[4],
    )


def test_all_private_source_leads_join_and_no_decisions_promoted():
    private, result = join(*fixture())
    assert result["total_private_original_application_research_packets"] == 3
    assert result["published_letter_references_in_packets"] == 5
    assert result["previously_probed_official_pdf_letter_references"] == 4
    assert result["unavailable_published_pdf_letter_references"] == 1
    assert result["distinct_prior_confirmed_pdf_sha256_in_packet_worklist"] == 2
    assert result["shared_full_pdf_digests_across_multiple_letter_references"] == 1
    assert result["packet_availability_counts"] == {
        "ALL_PUBLISHED_PDF_LEADS_AVAILABLE_FROM_PRIOR_AUDIT": 2,
        "PARTIAL_PUBLISHED_PDF_LEADS": 1,
        "NO_PUBLISHED_PDF_LEAD": 0,
    }
    assert result["original_fda_review_cycles_independently_adjudicated"] == 0
    assert result["model_eligible_records"] == 0
    assert result["prediction_probability"] is None
    assert result["complete_national_nda_bla_decision_denominator_verified"] is False
    assert result["private_pdf_source_link_records_not_exported"] is True
    for p in private:
        assert p["model_eligible"] is False
        assert p["original_review_cycle"] is None
        assert p["fda_action_outcome"] is None
        for lead in p["previously_probed_published_pdf_leads"]:
            assert lead["pdf_bytes_revalidated_in_current_run"] is False
            assert lead["action_page_range_independently_verified"] is False
            assert lead["review_cycle_independently_verified"] is False
            assert lead["model_eligible"] is False
    assert private[-1]["previously_probed_published_pdf_leads"][-1][
        "pdf_lead_status"
    ] == "NO_RELEASED_PDF_SOURCE_LEAD"


@pytest.mark.parametrize("change", [
    "wrong_url", "wrong_source_hash", "duplicate_source_hash",
    "false_model_clearance", "false_pdf_decision", "false_original_cycle",
    "fake_pdf_digest", "missing_pdf_sha", "false_missing_url",
    "contradict_archive_hash", "fake_total", "fake_verified_pdf_count",
    "fake_shared_document_count", "false_pdf_group_model",
    "packet_duplicate_letter", "packet_false_model",
])
def test_false_fda_evidence_identity_and_model_claims_fail_closed(change):
    inputs = list(deepcopy(fixture()))
    packets, probe, audit, index, groups = inputs
    if change == "wrong_url":
        probe["records"][0]["official_fda_pdf_url_if_confirmed"] = (
            "https://download.open.fda.gov.evil.invalid/crl/example-a.pdf"
        )
    elif change == "wrong_source_hash":
        packets[0]["published_letter_source_hashes"][0] = "e" * 64
    elif change == "duplicate_source_hash":
        probe["records"][1]["source_record_sha256"] = probe["records"][0][
            "source_record_sha256"
        ]
    elif change == "false_model_clearance":
        audit["model_eligible_records"] = 1
    elif change == "false_pdf_decision":
        probe["records"][1]["document_identity_adjudicated"] = True
    elif change == "false_original_cycle":
        probe["records"][2]["review_cycle_verified"] = True
    elif change == "fake_pdf_digest":
        probe["records"][2]["full_document_sha256_if_confirmed"] = "BAD_SHA"
    elif change == "missing_pdf_sha":
        probe["records"][3]["full_document_sha256_if_confirmed"] = None
    elif change == "false_missing_url":
        probe["records"][-1]["official_fda_pdf_url_if_confirmed"] = (
            "https://download.open.fda.gov/crl/fake.pdf"
        )
    elif change == "contradict_archive_hash":
        groups["original_fda_archive_sha256"] = "d" * 64
    elif change == "fake_total":
        index["published_letter_records"] = 6
    elif change == "fake_verified_pdf_count":
        audit["official_pdf_bytes_confirmed"] = 5
    elif change == "fake_shared_document_count":
        groups["unique_confirmed_pdf_documents"] = 3
    elif change == "false_pdf_group_model":
        groups["model_eligible_records"] = 1
    elif change == "packet_duplicate_letter":
        packets[1]["published_letter_source_hashes"][0] = packets[0][
            "published_letter_source_hashes"
        ][0]
    elif change == "packet_false_model":
        packets[0]["model_eligible"] = True
    with pytest.raises(ValueError):
        join(*inputs)


def test_all_docs_missing_is_source_failure_not_fda_nonapproval():
    args = list(fixture())
    packets, probe, audit, index, groups = args
    for i, item in enumerate(probe["records"]):
        item["source_file_name_as_published"] = "Under Review for Release"
        item["document_fetch_status"] = "NO_SAFE_FILENAME_TO_CHECK"
        item["full_document_sha256_if_confirmed"] = None
        item["official_fda_pdf_url_if_confirmed"] = None
    audit["official_pdf_bytes_confirmed"] = 0
    audit["document_fetch_status_counts"] = {"NO_SAFE_FILENAME_TO_CHECK": 5}
    index["full_official_pdf_bytes_confirmed"] = 0
    index["source_records_without_safe_pdf_filename"] = 5
    groups["unique_confirmed_pdf_documents"] = 0
    groups["official_pdf_confirmed_letter_references"] = 0
    private, summary = join(*args)
    assert summary["unavailable_published_pdf_letter_references"] == 5
    assert summary["packet_availability_counts"] == {
        "ALL_PUBLISHED_PDF_LEADS_AVAILABLE_FROM_PRIOR_AUDIT": 0,
        "PARTIAL_PUBLISHED_PDF_LEADS": 0,
        "NO_PUBLISHED_PDF_LEAD": 3,
    }
    assert summary["model_eligible_records"] == 0
    assert all(all(l["official_fda_pdf_url"] is None
                   for l in p["previously_probed_published_pdf_leads"])
               for p in private)
