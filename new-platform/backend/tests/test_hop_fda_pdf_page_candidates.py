import hashlib
import io

import pytest

from app.hop_fda_pdf_page_candidates import (
    build_fda_shared_pdf_page_candidates,
    fetch_official_pdf_bytes,
    pdf_page_texts,
    provisional_page_candidates,
)

URL1 = "https://download.open.fda.gov/crl/212887Orig1s000%2C212888Orig1s000OtherActionLtrs.pdf"
URL2 = "https://download.open.fda.gov/crl/other.pdf"
SOURCE_STATUS = "FDA_PDF_SHARED_DOCUMENT_RECONCILIATION_NOT_OUTCOME_ADJUDICATION"


def letter(char, id_, date="12/19/2019", url=URL1):
    return {
        "source_record_sha256": char * 64,
        "source_letter_date_as_published": date,
        "published_letter_type": "COMPLETE RESPONSE",
        "application_ids_as_published": [id_.replace("NDA", "NDA ")],
        "canonical_application_candidates": [id_],
        "official_fda_document_url": url,
    }


def grouped(*letters, url=URL1, digest=None):
    return {
        "official_fda_pdf_sha256": digest or "f" * 64,
        "official_fda_pdf_url": url,
        "source_letter_records": list(letters),
        "published_letter_record_count": len(letters),
        "individual_letter_page_ranges_verified": False,
        "individual_review_cycle_outcomes_verified": False,
        "model_eligible": False,
    }


def original(*groups):
    return {"status": SOURCE_STATUS, "records": list(groups)}


def fake_bytes_and_parser(pages, data=b"%PDF-fake-source-bytes"):
    def fetch(url):
        return data, "OFFICIAL_PDF_BYTES_RETRIEVED"
    def parse(binary):
        assert binary == data
        return pages, "PDF_TEXT_EXTRACTED"
    return fetch, parse, hashlib.sha256(data).hexdigest()


def test_separate_same_day_letters_find_distinct_pages_without_certifying_outcomes():
    two_pages = [
        "Food and Drug Administration\nDecember 19, 2019\nNDA 212887\nComplete Response",
        "Food and Drug Administration\nDecember 19, 2019\nNDA 212888\nComplete Response",
    ]
    fetch, parse, digest = fake_bytes_and_parser(two_pages)
    group = grouped(letter("a", "NDA212887"), letter("b", "NDA212888"), digest=digest)
    output, audit = build_fda_shared_pdf_page_candidates(
        original(group), fetcher=fetch, parser=parse)
    assert audit["shared_pdf_groups_examined"] == 1
    assert audit["source_letter_records_examined"] == 2
    assert audit["letters_with_same_page_id_and_letter_date_candidates"] == 2
    rows = output["records"][0]["letter_page_candidates"]
    assert [x["candidate_pages"][0]["page_number_1_based"] for x in rows] == [1, 2]
    assert all(x["candidate_status"] == "DATE_AND_ID_PAGE_CANDIDATES" for x in rows)
    assert all(x["individual_letter_page_range_independently_verified"] is False for x in rows)
    assert all(x["effective_fda_action_date_independently_verified"] is False for x in rows)
    assert all(x["regulatory_outcome_independently_verified"] is False for x in rows)
    assert audit["independently_verified_review_cycle_outcomes"] == 0
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None


def test_id_only_and_date_only_are_not_equally_strong():
    record = letter("a", "NDA212887")
    result = provisional_page_candidates(record, [
        "December 19, 2019\nNo application number on this page",
        "Application NDA # 212887\nCover document",
    ])
    assert result["candidate_status"] == "ID_ONLY_PAGE_CANDIDATES"
    assert result["candidate_pages"][0]["page_number_1_based"] == 2
    assert result["candidate_pages"][0]["published_letter_date_token_found"] is False
    assert result["proposed_letter_page_range"] is None


def test_numeric_date_and_all_caps_month_are_supported():
    record = letter("b", "NDA212888", date="02/28/2022")
    result = provisional_page_candidates(record, [
        "NDA212888\nFebruary 28, 2022",
        "NDA #212888\n02-28-2022",
        "NDA 212888\nFEB 28 2022",
    ])
    assert result["candidate_status"] == "DATE_AND_ID_PAGE_CANDIDATES"
    assert len(result["candidate_pages"]) == 3


def test_unknown_canonical_app_and_same_day_repeated_letters_abstain():
    record = letter("a", "NDA212887")
    record["canonical_application_candidates"] = []
    result = provisional_page_candidates(record, [
        "NDA 212887\nDecember 19, 2019"
    ])
    assert result["candidate_status"] == "NO_CANONICAL_APPLICATION_FOR_PAGE_MATCH"
    assert result["candidate_pages"] == []
    assert result["model_eligible"] is False


def test_unavailable_documents_remain_review_queue_cases():
    a, b = letter("a", "NDA212887"), letter("b", "NDA212888")
    queue, audit = build_fda_shared_pdf_page_candidates(
        original(grouped(a, b)),
        fetcher=lambda url: (None, "OFFICIAL_PDF_FETCH_UNAVAILABLE"))
    assert audit["pdf_extraction_status_counts"] == {"OFFICIAL_PDF_FETCH_UNAVAILABLE": 1}
    assert all(r["candidate_status"] == "OFFICIAL_PDF_FETCH_UNAVAILABLE"
               for r in queue["records"][0]["letter_page_candidates"])
    assert audit["model_eligible_records"] == 0


def test_pdf_byte_fingerprint_mismatch_fails_closed():
    f, parser, correct = fake_bytes_and_parser(["NDA 212887"])
    bad_group = grouped(letter("a", "NDA212887"), letter("b", "NDA212888"))
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        build_fda_shared_pdf_page_candidates(
            original(bad_group), fetcher=f, parser=parser)


def test_model_promotion_or_tampered_group_fails_closed():
    a, b = letter("a", "NDA212887"), letter("b", "NDA212888")
    bad = grouped(a,b)
    bad["model_eligible"] = True
    with pytest.raises(ValueError, match="model-ineligible"):
        build_fda_shared_pdf_page_candidates(original(bad),
                                            fetcher=lambda url:(None,"OFFICIAL_PDF_FETCH_UNAVAILABLE"))
    bad["model_eligible"] = False
    bad["published_letter_record_count"] = 9
    with pytest.raises(ValueError, match="invalid shared document"):
        build_fda_shared_pdf_page_candidates(original(bad),
                                            fetcher=lambda url:(None,"OFFICIAL_PDF_FETCH_UNAVAILABLE"))


def test_untrusted_url_and_duplicate_hash_are_blocked_before_fetch():
    a,b = letter("a", "NDA212887"), letter("b", "NDA212888")
    bad = grouped(a,b, url="https://download.open.fda.gov.attacker.example/crl/pdf.pdf")
    with pytest.raises(ValueError, match="invalid shared document"):
        build_fda_shared_pdf_page_candidates(original(bad),
            fetcher=lambda url: (_ for _ in ()).throw(AssertionError("must not fetch")))
    first = grouped(a,b)
    second = grouped(letter("c","NDA212887"),letter("d","NDA212888"))
    with pytest.raises(ValueError, match="invalid shared document"):
        build_fda_shared_pdf_page_candidates(original(first,second),
            fetcher=lambda url:(None,"OFFICIAL_PDF_FETCH_UNAVAILABLE"))


def test_blank_pdf_is_not_ocr_or_outcome_adjudication():
    import pypdf
    writer = pypdf.PdfWriter()
    writer.add_blank_page(width=612, height=792)
    stream = io.BytesIO()
    writer.write(stream)
    texts, status = pdf_page_texts(stream.getvalue())
    assert status == "PDF_NO_EXTRACTABLE_TEXT"
    assert len(texts) == 1


def test_oversized_page_matches_require_manual_review():
    record = letter("a", "NDA212887")
    page = "NDA 212887\nDecember 19, 2019"
    result = provisional_page_candidates(record, [page] * 31)
    assert result["candidate_status"] == "TOO_MANY_PAGES_REQUIRE_MANUAL_REVIEW"
    assert result["candidate_pages"] == []
