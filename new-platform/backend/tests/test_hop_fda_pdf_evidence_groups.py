import pytest

from app.hop_fda_pdf_evidence_groups import reconcile_fda_pdf_evidence_groups


def source(char, date="03/15/2024", kind="COMPLETE RESPONSE", app="NDA123456"):
    return {
        "source_record_sha256": char * 64,
        "application_ids_as_published": ["NDA 123456"],
        "canonical_application_candidates": [app],
        "letter_type_as_published": kind,
        "source_letter_date_as_published": date,
        "letter_date_as_published": date,
        "file_name_as_published": "original_FDA_letters.pdf",
        "effective_fda_action_date_independently_verified": False,
        "fda_review_cycle_outcome": None,
        "model_eligible": False,
    }


def pdf(row, digest="f"):
    return {
        "source_record_sha256": row["source_record_sha256"],
        "source_application_ids_as_published": row["application_ids_as_published"],
        "letter_type_as_published": row["letter_type_as_published"],
        "letter_date_as_published": row["letter_date_as_published"],
        "source_file_name_as_published": row["file_name_as_published"],
        "document_fetch_status": "OFFICIAL_PDF_BYTES_CONFIRMED",
        "official_fda_pdf_url_if_confirmed": "https://download.open.fda.gov/crl/original_FDA_letters.pdf",
        "full_document_sha256_if_confirmed": digest * 64,
        "document_identity_adjudicated": False,
        "effective_fda_action_date_verified": False,
        "review_cycle_verified": False,
        "model_eligible": False,
    }


def archives(sources, documents):
    return (
        {"status": "PUBLISHED_FDA_ACTION_REVIEW_ONLY_NO_VALIDATED_OUTCOMES",
         "records": sources},
        {"status": "PDF_FETCH_CHECK_ONLY_NOT_HISTORICAL_OUTCOME_VERIFICATION",
         "records": documents},
    )


def test_shared_pdf_links_are_not_verified_independent_review_cycles():
    first = source("a", "03/15/2002")
    second = source("b", "06/23/2004")
    third = source("c", "11/02/2007")
    single = source("d", "01/01/2025")
    docs = [pdf(first), pdf(second), pdf(third), pdf(single, "e")]
    audit_rows, audit = reconcile_fda_pdf_evidence_groups(
        *archives([first, second, third, single], docs))
    assert audit["published_letter_source_records"] == 4
    assert audit["official_pdf_confirmed_letter_references"] == 4
    assert audit["unique_confirmed_pdf_documents"] == 2
    assert audit["distinct_shared_pdf_groups"] == 1
    assert audit["letter_records_in_shared_pdf_groups"] == 3
    assert audit["additional_letter_links_beyond_unique_pdfs"] == 2
    assert audit["independently_verified_review_cycle_outcomes"] == 0
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None
    work = audit_rows["records"][0]
    assert work["individual_letter_page_ranges_verified"] is False
    assert work["fda_effective_action_dates_verified"] is False
    assert work["individual_letter_page_ranges"] is None
    assert work["model_eligible"] is False


def test_cross_application_and_same_date_collision_are_review_flags():
    a = source("a", app="NDA123456")
    b = source("b", app="NDA999999")
    result, audit = reconcile_fda_pdf_evidence_groups(
        *archives([a, b], [pdf(a), pdf(b)]))
    assert audit["shared_documents_containing_multiple_applications"] == 1
    assert audit["same_date_and_letter_type_collision_groups"] == 1
    assert result["records"][0]["multiple_application_candidates_in_one_pdf"] is True
    assert result["records"][0]["same_source_date_and_type_collision"] is True


def test_unreleased_pdf_is_not_counted_as_missing_outcome():
    a = source("a")
    b = source("b")
    unseen = pdf(b)
    unseen.update({
        "document_fetch_status": "NO_SAFE_FILENAME_TO_CHECK",
        "official_fda_pdf_url_if_confirmed": None,
        "full_document_sha256_if_confirmed": None,
    })
    result, audit = reconcile_fda_pdf_evidence_groups(
        *archives([a, b], [pdf(a), unseen]))
    assert result["records"] == []
    assert audit["official_pdf_confirmed_letter_references"] == 1
    assert audit["unique_confirmed_pdf_documents"] == 1
    assert audit["source_records_without_confirmed_pdf"] == 1
    assert audit["source_records_without_confirmed_pdf_sha256"] == [b["source_record_sha256"]]
    assert audit["complete_application_denominator_verified"] is False


@pytest.mark.parametrize("tamper", [
    lambda s,p: s.update({"model_eligible": True}),
    lambda s,p: s.update({"fda_review_cycle_outcome": "APPROVED"}),
    lambda s,p: p.update({"model_eligible": True}),
    lambda s,p: p.update({"source_application_ids_as_published": ["BLA 654321"]}),
    lambda s,p: p.update({"letter_date_as_published": "01/01/2020"}),
    lambda s,p: p.update({"official_fda_pdf_url_if_confirmed": "https://evil.example/f.pdf"}),
    lambda s,p: p.update({"full_document_sha256_if_confirmed": None}),
])
def test_mismatched_or_promoted_sources_fail_closed(tamper):
    s = source("a")
    p = pdf(s)
    tamper(s,p)
    with pytest.raises(ValueError):
        reconcile_fda_pdf_evidence_groups(*archives([s],[p]))


def test_same_hash_cannot_have_conflicting_source_urls():
    a = source("a")
    b = source("b")
    x,y = pdf(a),pdf(b)
    y["official_fda_pdf_url_if_confirmed"] = "https://download.open.fda.gov/crl/another.pdf"
    with pytest.raises(ValueError, match="multiple incompatible"):
        reconcile_fda_pdf_evidence_groups(*archives([a,b],[x,y]))


def test_unexpected_or_duplicate_record_fails_closed():
    a = source("a")
    with pytest.raises(ValueError, match="duplicated or invalid"):
        reconcile_fda_pdf_evidence_groups(*archives([a,a],[pdf(a),pdf(a)]))
    with pytest.raises(ValueError, match="must match"):
        reconcile_fda_pdf_evidence_groups(*archives([a],[]))
