"""A bounded FDA primary-source PDF *observation*, not outcome adjudication.

The documented historical Drugs@FDA/openFDA source discrepancy is
NDA206627 Original 1. Read FDA's 2014 original approval-package cover and
action-letter page as independent *publication evidence*. PDF availability,
source hashes and text consistency cannot establish a complete review-cycle
decision cohort, authenticated human review, or model eligibility.

No trading, database, scanner, or production paths import this module.
"""
from __future__ import annotations

import hashlib
import re
from collections.abc import Mapping

URL = (
    "https://www.accessdata.fda.gov/drugsatfda_docs/nda/2014/"
    "206627Orig1s000Approv.pdf"
)
MAX_PDF_BYTES = 24 * 1024 * 1024
PAGES_TO_OBSERVE = (0, 3)
STATUS = "OFFICIAL_FDA_ORIGINAL_APPROVAL_PDF_TEXT_OBSERVED_NOT_ADJUDICATED"


def _normalized_text(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Extracted FDA page must be text")
    return re.sub(r"\s+", " ", value).strip()


def inspect_nda206627_original_pdf(
    pdf_bytes: bytes,
    page_text: Mapping[int, str],
    *, page_count: int,
    source_url: str = URL,
) -> dict:
    """Evaluate a fixed official-source PDF and exact-page text observations.

    page_text is supplied by an independent PDF text extractor. This function
    checks source consistency, not credibility or identity of any reviewer.
    """
    if (source_url != URL
            or not isinstance(pdf_bytes, bytes)
            or len(pdf_bytes) < 100
            or len(pdf_bytes) > MAX_PDF_BYTES
            or not pdf_bytes.lstrip().startswith(b"%PDF-")
            or type(page_count) is not int or page_count < 4 or page_count > 100
            or not isinstance(page_text, Mapping)
            or set(page_text) != set(PAGES_TO_OBSERVE)):
        raise ValueError("Original FDA document bytes, URL or pages are unsupported")
    cover = _normalized_text(page_text[0]).lower()
    letter = _normalized_text(page_text[3]).lower()

    # All statements below are FDA document observations, not signed
    # independent regulatory action-cycle labels or model ground truth.
    cover_application = bool(re.search(
        r"\b206627\s*orig(?:inal)?\s*1\s*s\s*0{3}\b", cover
    ))
    letter_application = bool(re.search(r"\bnda\s*206627\b", letter))
    cover_date = bool(re.search(
        r"\bapproval\s+date\s*:\s*november\s+20\s*,\s*2014\b", cover
    ))
    cover_drug = "hysingla er" in cover and "hydrocodone bitartrate" in cover
    source_letter_action = (
        "nda approval" in letter
        and bool(re.search(r"\bit\s+is\s+approved\s*,?\s+effective\b", letter))
    )
    # Do not emit an outcome claim unless all basic document signals agree;
    # even when they agree, it is only a provisional published statement.
    checks = {
        "cover_application_206627_original_1": cover_application,
        "action_letter_application_nda206627": letter_application,
        "cover_fda_approval_date_2014_11_20": cover_date,
        "cover_hysingla_hydrocodone_identification": cover_drug,
        "action_letter_contains_approval_wording": source_letter_action,
    }
    consistent = all(checks.values())
    return {
        "status": STATUS,
        "source_url": source_url,
        "retrieved_pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "retrieved_pdf_bytes": len(pdf_bytes),
        "pdf_page_count": page_count,
        "examined_page_indices_zero_based": list(PAGES_TO_OBSERVE),
        "source_text_consistency_flags": checks,
        "all_target_source_text_checks_passed": consistent,
        "application_reference_as_observed": "NDA206627",
        "original_submission_reference_as_observed": "206627Orig1s000",
        "published_drug_name": "Hysingla ER" if cover_drug else None,
        "published_approval_date": "2014-11-20" if cover_date else None,
        "source_document_action_wording": (
            "FDA original approval letter states approved"
            if source_letter_action else None
        ),
        "verified_original_review_cycle": None,
        "independent_regulatory_adjudication_completed": False,
        "source_document_text_not_signed_independent_adjudication": True,
        "complete_original_nda_bla_denominator_verified": False,
        "model_eligible_records": 0,
        "approval_rate": None,
        "prediction_probability": None,
        "predictive_accuracy": None,
        "readiness": "REVIEW_REQUIRED",
        "note": (
            "Actual original FDA publication text was inspected, not signed "
            "by two qualified independent reviewers. Source cover/letter "
            "page observations do not prove a complete historical review "
            "cycle or establish scientific training eligibility."
        ),
    }
