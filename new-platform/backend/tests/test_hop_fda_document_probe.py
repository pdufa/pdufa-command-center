import hashlib

import pytest

from app.hop_fda_document_probe import (
    official_document_candidate, probe_fda_review_documents, fetch_official_pdf
)

URL = "https://download.open.fda.gov/crl/CRL_BLA125845_20250707.pdf"


def case(filename="CRL_BLA125845_20250707.pdf", char="a"):
    return {
        "source_record_sha256": char * 64,
        "application_ids_as_published": ["BL 125845"],
        "file_name_as_published": filename,
        "letter_date_as_published": "07/07/2025",
        "identity_link_status": "APPLICATION_ID_UNRESOLVED",
        "model_eligible": False,
        "identity_verified": False,
        "review_cycle_verified": False,
        "complete_denominator_verified": False,
    }


def queue(*rows):
    return {"status": "IDENTITY_REVIEW_QUEUE_NOT_OUTCOME_COHORT",
            "records": list(rows)}


@pytest.mark.parametrize("filename", [
    "../secret.pdf", "/etc/passwd", "x/anything.pdf", "..evil.pdf",
    "http://other.org/file.pdf", "x.pdf?x=1", "x.pdf#part", "", None
])
def test_unsafe_filenames_never_become_pdf_probes(filename):
    assert official_document_candidate(filename) is None


def test_safe_filename_only_a_candidate():
    assert official_document_candidate("CRL_BLA125845_20250707.pdf") == URL


def test_only_confirmed_official_pdf_has_working_link_and_digest():
    seen = []
    def checked(url):
        seen.append(url)
        return "OFFICIAL_PDF_BYTES_CONFIRMED", hashlib.sha256(b"%PDF-1.7").hexdigest()
    result, audit = probe_fda_review_documents(queue(case()), fetcher=checked)
    assert seen == [URL]
    row = result["records"][0]
    assert row["official_fda_pdf_url_if_confirmed"] == URL
    assert len(row["full_document_sha256_if_confirmed"]) == 64
    assert row["document_identity_adjudicated"] is False
    assert row["effective_fda_action_date_verified"] is False
    assert row["review_cycle_verified"] is False
    assert row["model_eligible"] is False
    assert audit["official_pdf_bytes_confirmed"] == 1
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None


def test_failed_url_is_not_presented_as_verified():
    result, audit = probe_fda_review_documents(
        queue(case()), fetcher=lambda url: ("FETCH_NOT_CONFIRMED", None))
    row = result["records"][0]
    assert row["official_fda_pdf_url_if_confirmed"] is None
    assert row["full_document_sha256_if_confirmed"] is None
    assert row["document_fetch_status"] == "FETCH_NOT_CONFIRMED"


def test_batch_is_bounded_and_unchecked_is_not_absent():
    rows = [case(char=char) for char in "abcdef"]
    seen = []
    def checked(url):
        seen.append(url)
        return "FETCH_NOT_CONFIRMED", None
    out, audit = probe_fda_review_documents(queue(*rows),
                                           offset=2, limit=2, fetcher=checked)
    assert len(seen) == 2
    assert audit["document_fetch_status_counts"]["NOT_CHECKED"] == 4
    assert audit["document_fetch_status_counts"]["FETCH_NOT_CONFIRMED"] == 2
    assert out["records"][0]["document_fetch_status"] == "NOT_CHECKED"
    assert out["records"][4]["document_fetch_status"] == "NOT_CHECKED"


def test_model_promotion_or_unexpected_confirmation_fails_closed():
    bad = case()
    bad["review_cycle_verified"] = True
    with pytest.raises(ValueError, match="must remain unverified"):
        probe_fda_review_documents(queue(bad), fetcher=lambda url: ("FETCH_NOT_CONFIRMED", None))
    with pytest.raises(ValueError, match="unexpected"):
        probe_fda_review_documents(queue(case()), fetcher=lambda url: ("MODEL_READY", None))
    with pytest.raises(ValueError, match="invalid PDF evidence SHA256"):
        probe_fda_review_documents(queue(case()),
            fetcher=lambda url: ("OFFICIAL_PDF_BYTES_CONFIRMED", None))


@pytest.mark.parametrize("offset,limit", [(-1,2), (0,0), (0,26), (True,1), (0,False)])
def test_invalid_probe_range_fails_closed(offset, limit):
    with pytest.raises(ValueError, match="invalid bounded"):
        probe_fda_review_documents(queue(case()), offset=offset, limit=limit)


def test_no_network_call_for_bad_filename():
    result, audit = probe_fda_review_documents(queue(case("../bad.pdf")),
        fetcher=lambda url: (_ for _ in ()).throw(AssertionError("must not fetch")))
    assert result["records"][0]["document_fetch_status"] == "NO_SAFE_FILENAME_TO_CHECK"


def test_fetch_rejects_unofficial_host_before_http():
    with pytest.raises(ValueError, match="exact official FDA"):
        fetch_official_pdf("https://download.open.fda.gov.attacker.test/crl/letter.pdf")
