from app.hop_cohort_manifest import audit_cohort_manifest


def manifest():
    return {
        "cohort_id": "nda-bla-2020",
        "population_definition": "All specified NDA/BLA original review cycles",
        "start_date": "2020-01-01", "end_date": "2020-12-31",
        "source_url": "https://www.fda.gov/drugs",
        "expected_review_cycles": 100, "observed_review_cycles": 100,
        "independent_reviewer": "second-reviewer",
        "source_retrieved_on": "2021-01-01",
        "independent_review_complete": True,
        "approval_and_crl_ascertainment_complete": True,
    }


def test_self_declared_complete_cohort_never_unlocks_model():
    result = audit_cohort_manifest(manifest())
    assert result["status"] == "BLOCKED"
    assert "external_source_verification_required" in result["blockers"]
    assert result["model_eligible"] is False


def test_incomplete_denominator_and_outcomes_blocked():
    data = manifest()
    data["observed_review_cycles"] = 50
    data["approval_and_crl_ascertainment_complete"] = False
    result = audit_cohort_manifest(data)
    assert "denominator_not_reconciled" in result["blockers"]
    assert "outcome_ascertainment_not_confirmed" in result["blockers"]


def test_non_fda_source_and_missing_reviewer_blocked():
    data = manifest()
    data["source_url"] = "https://fda.gov.evil.example/approvals"
    data["independent_reviewer"] = ""
    result = audit_cohort_manifest(data)
    assert "missing_independent_reviewer" in result["blockers"]


def test_missing_or_invalid_manifest_fails_closed():
    assert audit_cohort_manifest(None)["model_eligible"] is False
    assert audit_cohort_manifest({})["status"] == "BLOCKED"

def test_non_string_coverage_date_fails_closed():
    data = manifest()
    data["start_date"] = 20200101
    result = audit_cohort_manifest(data)
    assert "invalid_coverage_dates" in result["blockers"]
    assert result["model_eligible"] is False

def test_official_openfda_domain_is_accepted_but_not_self_verified():
    data = manifest()
    data["source_url"] = "https://open.fda.gov/apis/transparency/completeresponseletters/"
    result = audit_cohort_manifest(data)
    assert "source_not_official_fda" not in result["blockers"]
    assert "external_source_verification_required" in result["blockers"]
    assert result["model_eligible"] is False
