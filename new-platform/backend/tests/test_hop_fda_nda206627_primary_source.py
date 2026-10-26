"""Synthetic-only NDA206627 source-text checks, not human FDA adjudication."""
from __future__ import annotations

from copy import deepcopy

import pytest

from app.hop_fda_nda206627_primary_source import (
    STATUS, URL, inspect_nda206627_original_pdf,
)

FAKE_PDF = b"%PDF-1.7\n" + b"x" * 256
COVER = (
    "CENTER FOR DRUG EVALUATION AND RESEARCH\n"
    "Approval Package for: APPLICATION NUMBER:\n"
    "206627Orig1s000\n"
    "Trade Name: Hysingla ER extended-release tablets\n"
    "Generic Name: hydrocodone bitartrate\n"
    "Sponsor: Purdue Pharma L.P.\n"
    "Approval Date: November 20, 2014\n"
)
LETTER = (
    "Food and Drug Administration\n"
    "NDA 206627\n"
    "NDA APPROVAL\n"
    "We have completed our review of this application, as amended.\n"
    "It is approved, effective on the date of this letter.\n"
)


def audit(pages=None, pdf=FAKE_PDF, url=URL, page_count=16):
    return inspect_nda206627_original_pdf(
        pdf, {0: COVER, 3: LETTER} if pages is None else pages,
        source_url=url, page_count=page_count,
    )


def test_consistent_original_official_pdf_still_not_model_eligible():
    result = audit()
    assert result["status"] == STATUS
    assert result["all_target_source_text_checks_passed"] is True
    assert result["examined_page_indices_zero_based"] == [0, 3]
    assert result["source_text_consistency_flags"] == {
        "cover_application_206627_original_1": True,
        "action_letter_application_nda206627": True,
        "cover_fda_approval_date_2014_11_20": True,
        "cover_hysingla_hydrocodone_identification": True,
        "action_letter_contains_approval_wording": True,
    }
    assert result["application_reference_as_observed"] == "NDA206627"
    assert result["published_approval_date"] == "2014-11-20"
    assert result["published_drug_name"] == "Hysingla ER"
    assert result["verified_original_review_cycle"] is None
    assert result["independent_regulatory_adjudication_completed"] is False
    assert result["complete_original_nda_bla_denominator_verified"] is False
    assert result["model_eligible_records"] == 0
    assert result["approval_rate"] is None
    assert result["prediction_probability"] is None
    assert result["predictive_accuracy"] is None


@pytest.mark.parametrize("mutation,flag", [
    ("wrong_cover_application", "cover_application_206627_original_1"),
    ("wrong_letter_application", "action_letter_application_nda206627"),
    ("wrong_cover_date", "cover_fda_approval_date_2014_11_20"),
    ("wrong_drug", "cover_hysingla_hydrocodone_identification"),
    ("wrong_letter_action", "action_letter_contains_approval_wording"),
])
def test_original_fda_source_discrepancy_keeps_scientific_gate_closed(
    mutation, flag
):
    pages = {0: COVER, 3: LETTER}
    if mutation == "wrong_cover_application":
        pages[0] = pages[0].replace("206627Orig1s000", "206628Orig1s000")
    elif mutation == "wrong_letter_application":
        pages[3] = pages[3].replace("NDA 206627", "NDA 206628")
    elif mutation == "wrong_cover_date":
        pages[0] = pages[0].replace("November 20, 2014", "November 19, 2014")
    elif mutation == "wrong_drug":
        pages[0] = pages[0].replace("Hysingla ER", "Fictitious drug")
    elif mutation == "wrong_letter_action":
        pages[3] = pages[3].replace("It is approved", "It is not approved")
    result = audit(pages)
    assert result["source_text_consistency_flags"][flag] is False
    assert result["all_target_source_text_checks_passed"] is False
    assert result["model_eligible_records"] == 0
    assert result["verified_original_review_cycle"] is None


@pytest.mark.parametrize("mutation", [
    "spoof_fda_domain", "alternate_pdf_path", "empty_pdf",
    "non_pdf_source", "too_many_pages", "too_few_pages",
    "missing_letter", "extra_page", "nontyped_page",
])
def test_unsupported_primary_source_request_is_rejected(mutation):
    pages = {0: COVER, 3: LETTER}
    pdf, url, page_count = FAKE_PDF, URL, 16
    if mutation == "spoof_fda_domain":
        url = "https://www.accessdata.fda.gov.evil.example/drugsatfda_docs/nda/2014/206627Orig1s000Approv.pdf"
    elif mutation == "alternate_pdf_path":
        url = "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/another.pdf"
    elif mutation == "empty_pdf":
        pdf = b""
    elif mutation == "non_pdf_source":
        pdf = b"<!doctype html>" + b"x" * 250
    elif mutation == "too_many_pages":
        page_count = 101
    elif mutation == "too_few_pages":
        page_count = 3
    elif mutation == "missing_letter":
        del pages[3]
    elif mutation == "extra_page":
        pages[4] = "Some unrelated content"
    elif mutation == "nontyped_page":
        pages[0] = None
    with pytest.raises(ValueError):
        audit(pages, pdf=pdf, url=url, page_count=page_count)
