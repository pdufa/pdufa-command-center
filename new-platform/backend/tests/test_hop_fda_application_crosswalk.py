import pytest

from app.hop_fda_application_crosswalk import canonical_application_id, crosswalk_public_fda_sources


def letter(app):
    return {
        "application_numbers": app,
        "source_record_sha256": "letter-hash",
        "letter_type_as_published": "COMPLETE RESPONSE",
        "letter_date_as_published": "10/05/2018",
        "model_eligible": False,
    }


def drug(app, digest="registry-hash"):
    return {"application_number_as_published": app,
            "record_sha256": digest, "model_eligible": False}


def sources(letters, drugs):
    return (
        {"status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
         "source_export_date": "2026-10-21", "records": letters},
        {"status": "APPROVED_REGISTRY_NOT_COMPLETE_DECISION_COHORT",
         "source_export_date": "2026-10-23", "records": drugs},
    )


@pytest.mark.parametrize("raw,expected", [
    ("NDA 209510", "NDA209510"),
    ("NDA209510", "NDA209510"),
    ("BLA-001234", "BLA001234"),
    ("anda:1", "ANDA000001"),
    ("205123", None), (None, None),
    ("FDA 205123", None),
])
def test_application_id_normalization(raw, expected):
    assert canonical_application_id(raw) == expected


def test_match_is_not_a_historical_review_cycle_approval():
    crosswalk, audit = crosswalk_public_fda_sources(
        *sources([letter(["NDA 209510"])], [drug("NDA209510")]))
    assert audit["identity_link_status_counts"] == {
        "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT": 1
    }
    assert audit["verified_review_cycle_outcomes"] == 0
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None
    assert crosswalk["records"][0]["registry_presence_is_not_review_cycle_approval"]
    assert crosswalk["records"][0]["model_eligible"] is False


def test_unmatched_does_not_become_rejected_label():
    crosswalk, audit = crosswalk_public_fda_sources(
        *sources([letter(["NDA 209510"])], []))
    assert crosswalk["records"][0]["identity_link_status"] == (
        "NOT_FOUND_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"
    )
    assert audit["verified_review_cycle_outcomes"] == 0


def test_multiple_applications_and_duplicates_abstain():
    crosswalk, audit = crosswalk_public_fda_sources(
        *sources([letter(["NDA209510", "BLA001234"]), letter(["NDA209510"])],
                 [drug("NDA209510"), drug("NDA209510", "other-hash")]))
    assert audit["identity_link_status_counts"] == {
        "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS": 2
    }
    assert all(not row["model_eligible"] for row in crosswalk["records"])


def test_missing_app_id_abstains():
    crosswalk, audit = crosswalk_public_fda_sources(
        *sources([letter(["209510"])], [drug("NDA209510")]))
    assert audit["identity_link_status_counts"]["APPLICATION_ID_UNRESOLVED"] == 1


def test_source_cannot_self_promote():
    bad_letter = letter(["NDA209510"])
    bad_letter["model_eligible"] = True
    with pytest.raises(ValueError, match="cannot promote"):
        crosswalk_public_fda_sources(*sources([bad_letter], [drug("NDA209510")]))
    with pytest.raises(ValueError, match="quarantined"):
        crosswalk_public_fda_sources({"status": "MODEL_READY", "records": []},
                                     sources([], [])[1])
