"""Synthetic FDA published document page-candidate tests (no decision labels)."""
from __future__ import annotations

import hashlib
from copy import deepcopy

import pytest

from app.hop_fda_pdf_page_candidate_sampling import (
    MAX_INSPECT_PAGES, aggregate_sample, inspect_candidate_pages,
    select_pinned_pdf_sample,
)

A = b"%PDF-1.6\n" + b"fake source A" * 30
B = b"%PDF-1.7\n" + b"fake source B" * 30
SHA_A = hashlib.sha256(A).hexdigest()
SHA_B = hashlib.sha256(B).hexdigest()
ROOT = "https://download.open.fda.gov/crl/"


def lead(i, sha, filename):
    return {
        "published_letter_source_sha256": f"{i:064x}",
        "official_fda_pdf_url": ROOT + filename if sha else None,
        "historically_observed_full_pdf_sha256": sha,
        "pdf_lead_status": (
            "PRIOR_FDA_PDF_BYTES_PROBED_ACTION_UNVERIFIED" if sha
            else "NO_RELEASED_PDF_SOURCE_LEAD"
        ),
        "pdf_bytes_revalidated_in_current_run": False,
        "action_page_range_independently_verified": False,
        "review_cycle_independently_verified": False,
        "model_eligible": False,
    }


def packet(app, source_leads):
    return {
        "packet_id": app,
        "application_id_candidate": app if not app.startswith("LETTER_") else None,
        "published_letter_source_hashes": [
            x["published_letter_source_sha256"] for x in source_leads
        ],
        "previously_probed_published_pdf_leads": source_leads,
        "published_letter_references": len(source_leads),
        "model_eligible": False,
        "adjudicator_authenticated": False,
        "fda_action_outcome": None,
        "original_review_cycle": None,
    }


def fixture():
    return [
        packet("NDA123456", [lead(1, SHA_A, "example-a.pdf"),
                             lead(2, SHA_A, "example-a.pdf")]),
        packet("BLA654321", [lead(3, SHA_B, "example-b.pdf")]),
        packet("LETTER_" + f"{4:064x}", [lead(4, None, "")]),
    ]


def test_distinct_pinned_full_pdf_digests_and_selection_deterministic():
    source = fixture()
    first, metadata = select_pinned_pdf_sample(source, limit=8)
    reversed_sample, _ = select_pinned_pdf_sample(list(reversed(source)), limit=8)
    assert first == reversed_sample
    assert len(first) == 2
    assert metadata["all_unique_previous_pdf_digests"] == 2
    assert metadata["selected_published_letter_references"] == 3
    assert metadata["model_eligible_records"] == 0
    assert next(x for x in first if x["historical_pdf_sha256"] == SHA_A)[
        "published_letter_references_sharing_file"
    ] == 2


def test_page_hints_are_only_navigation_not_reviewed_action_pages():
    selected, _ = select_pinned_pdf_sample(fixture())
    source = next(x for x in selected if x["historical_pdf_sha256"] == SHA_A)
    pages = [
        "FDA — NDA 123456",
        "Application 123456; another mention 999999",
        "unrelated",
        "one NDA 123456",
    ]
    observed = inspect_candidate_pages(
        source, A, page_count=4,
        extract_text=lambda idx: pages[idx],
    )
    assert observed["provisional_candidate_app_page_indices_zero_based"] == {
        "NDA123456": [0, 1, 3]
    }
    assert observed["source_full_pdf_hash_confirmed_against_prior_probe"] is True
    assert observed["original_action_page_ranges_independently_verified"] == 0
    assert observed["independently_verified_review_cycles"] == 0
    assert observed["model_eligible_records"] == 0
    assert observed["prediction_probability"] is None


def test_partial_page_scan_and_nontext_pdf_are_explicit_incomplete_evidence():
    selected, _ = select_pinned_pdf_sample(fixture())
    source = next(x for x in selected if x["historical_pdf_sha256"] == SHA_B)
    observed = inspect_candidate_pages(
        source, B, page_count=100, max_pages=3,
        extract_text=lambda idx: "" if idx != 2 else "654321",
    )
    assert observed["pages_inspected"] == 3
    assert observed["remaining_pages_not_inspected"] == 97
    assert observed["pages_with_no_extractable_text"] == 2
    assert observed["provisional_candidate_app_page_indices_zero_based"] == {
        "BLA654321": [2]
    }


@pytest.mark.parametrize("change", [
    "malicious_url", "wrong_hash", "malformed_sha", "changed_previous_flag",
    "promoted_model", "promoted_cycle", "reused_original_source",
    "conflicting_url_same_hash", "unreleased_digest", "wrong_app",
    "duplicated_source_list",
])
def test_forged_source_or_review_fields_fail_closed(change):
    packets = fixture()
    if change == "malicious_url":
        packets[0]["previously_probed_published_pdf_leads"][0][
            "official_fda_pdf_url"
        ] = "https://download.open.fda.gov.evil.example/crl/example-a.pdf"
    elif change == "wrong_hash":
        packets[0]["previously_probed_published_pdf_leads"][0][
            "historically_observed_full_pdf_sha256"
        ] = "z" * 64
    elif change == "malformed_sha":
        packets[0]["previously_probed_published_pdf_leads"][0][
            "historically_observed_full_pdf_sha256"
        ] = "not_sha256"
    elif change == "changed_previous_flag":
        packets[0]["previously_probed_published_pdf_leads"][0][
            "pdf_bytes_revalidated_in_current_run"
        ] = True
    elif change == "promoted_model":
        packets[0]["model_eligible"] = True
    elif change == "promoted_cycle":
        packets[0]["previously_probed_published_pdf_leads"][0][
            "review_cycle_independently_verified"
        ] = True
    elif change == "reused_original_source":
        packets[1]["previously_probed_published_pdf_leads"][0][
            "published_letter_source_sha256"
        ] = packets[0]["previously_probed_published_pdf_leads"][0][
            "published_letter_source_sha256"
        ]
    elif change == "conflicting_url_same_hash":
        packets[0]["previously_probed_published_pdf_leads"][1][
            "official_fda_pdf_url"
        ] = ROOT + "other.pdf"
    elif change == "unreleased_digest":
        packets[2]["previously_probed_published_pdf_leads"][0][
            "historically_observed_full_pdf_sha256"
        ] = SHA_A
    elif change == "wrong_app":
        packets[0]["application_id_candidate"] = "NDA000000"
    elif change == "duplicated_source_list":
        packets[0]["published_letter_source_hashes"][1] = packets[0][
            "published_letter_source_hashes"
        ][0]
    with pytest.raises(ValueError):
        select_pinned_pdf_sample(packets)


@pytest.mark.parametrize("value,parameter", [
    (b"%PDF-1.3\n" + b"tampered" * 30, "bytes"),
    (b"<html>" * 30, "bytes"),
    (0, "pages"), (301, "pages"),
    (-1, "max_pages"), (41, "max_pages"),
])
def test_tampered_pdf_or_out_of_bounds_pages_cannot_generate_hints(value, parameter):
    selected, _ = select_pinned_pdf_sample(fixture())
    source = next(x for x in selected if x["historical_pdf_sha256"] == SHA_A)
    kwargs = {"pdf_bytes": A, "page_count": 10,
              "extract_text": lambda idx: "NDA 123456", "max_pages": 5}
    if parameter == "bytes":
        kwargs["pdf_bytes"] = value
    elif parameter == "pages":
        kwargs["page_count"] = value
    else:
        kwargs["max_pages"] = value
    with pytest.raises(ValueError):
        inspect_candidate_pages(source, **kwargs)


def test_provisional_same_page_multiple_apps_only_flags_ambiguity():
    selected = {
        "historical_pdf_sha256": SHA_A,
        "official_fda_pdf_url": ROOT + "example-a.pdf",
        "candidate_application_ids": ["NDA123456", "BLA654321"],
        "published_letter_references_sharing_file": 2,
    }
    observed = inspect_candidate_pages(
        selected, A, page_count=2,
        extract_text=lambda idx: "NDA 123456 and BLA 654321" if idx == 0 else "",
    )
    assert observed["pages_containing_multiple_candidate_app_numbers"] == 1
    assert observed["provisional_candidate_app_page_indices_zero_based"] == {
        "NDA123456": [0], "BLA654321": [0]
    }
    assert observed["original_action_page_ranges_independently_verified"] == 0


def test_aggregate_count_only_and_model_blocks():
    selected, plan = select_pinned_pdf_sample(fixture())
    doc = next(x for x in selected if x["historical_pdf_sha256"] == SHA_A)
    item = inspect_candidate_pages(
        doc, A, page_count=1, extract_text=lambda idx: "NDA123456"
    )
    report = aggregate_sample(plan, [item], fetch_failures=1)
    assert report["sampled_unique_pdf_documents_requested"] == 2
    assert report["sampled_pdf_bytes_sha256_reconfirmed"] == 1
    assert report["sampled_pdf_documents_not_retrieved_or_parsed"] == 1
    assert report["pages_examined_for_candidate_app_tokens"] == 1
    assert report["candidate_application_numbers_with_page_hits"] == 1
    assert "provisional_candidate_app_page_indices_zero_based" not in report
    assert report["private_pdf_page_hints_not_exported"] is True
    assert report["review_cycles_independently_verified"] == 0
    assert report["model_eligible_records"] == 0
    assert report["predictive_accuracy"] is None
    with pytest.raises(ValueError):
        aggregate_sample(plan, [item], fetch_failures=0)
