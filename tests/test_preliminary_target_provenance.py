from research.preliminary_target_provenance import classify_target_provenance


def test_fda_host_is_not_document_verification():
    row = {"pdufaDate": "2026-12-01", "fdaSource": "https://www.fda.gov/drugs/example", "checkStatus": "FDA_VERIFIED"}
    result = classify_target_provenance(row)
    assert result["category"] == "FDA_HOST_AND_STATUS_CLAIM_REQUIRES_DOCUMENT_REVIEW"
    assert result["document_content_verified"] is False
    assert result["prediction_status"] == "ABSTAIN"


def test_sec_filing_can_be_review_lead_not_fda_confirmation():
    row = {"pdufaDate": "2026-12-01", "fdaSource": "https://www.sec.gov/Archives/example", "checkStatus": "VERIFIED"}
    result = classify_target_provenance(row)
    assert result["category"] == "SEC_FILING_LEAD_REQUIRES_SPONSOR_DATE_REVIEW"
    assert result["fda_host"] is False
    assert result["document_content_verified"] is False


def test_missing_and_invalid_dates_fail_closed():
    for value in (None, "2026-02-30", "2026-12-01T00:00:00"):
        result = classify_target_provenance({"pdufaDate": value, "fdaSource": "https://www.fda.gov/example"})
        assert result["category"] == "INVALID_OR_MISSING_DATE"
        assert result["prediction_status"] == "ABSTAIN"


def test_lookalike_fda_host_is_not_fda():
    result = classify_target_provenance({"pdufaDate": "2026-12-01", "fdaSource": "https://fda.gov.evil.example/"})
    assert result["fda_host"] is False


def test_application_review_requires_exact_date_and_document_fields():
    from research.preliminary_target_provenance import review_target_application_evidence
    row = {"pdufaDate": "2026-12-01", "fdaSource": "https://www.sec.gov/filing"}
    evidence = {"document_url": "https://www.sec.gov/filing",
                "document_date": "2026-10-01", "drug": "ExampleDrug",
                "indication": "Example indication", "application_id": "NDA 123456",
                "target_date": "2026-12-01", "source_excerpt": "PDUFA goal date"}
    result = review_target_application_evidence(row, evidence)
    assert result["review_status"] == "READY_FOR_INDEPENDENT_REVIEW"
    assert result["document_content_verified"] is False
    assert result["prediction_status"] == "ABSTAIN"
    evidence["target_date"] = "2026-12-02"
    assert review_target_application_evidence(row, evidence)["review_status"] == "INCOMPLETE_EVIDENCE"
    evidence.pop("application_id")
    assert "application_id" in review_target_application_evidence(row, evidence)["missing_review_fields"]
