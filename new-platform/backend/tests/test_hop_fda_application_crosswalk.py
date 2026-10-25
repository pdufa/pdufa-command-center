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
    ("NDA 213378/Original 1", "NDA213378"),
    ("BLA 761303/Original 2", "BLA761303"),
    ("NDA 018680/S-074", "NDA018680"),
    ("nda 209531/s-016", "NDA209531"),
    ("BL 125845", None),
    ("NDA 209531/S-016/Extra", None),
    ("NDA 209531/Original 0", None),
    ("NDA 209531/S-016 malicious", None),
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


def test_explicit_submission_suffix_links_application_not_review_cycle():
    linked, audit = crosswalk_public_fda_sources(*sources(
        [letter(["NDA 213378/Original 1", "NDA 213378/Original 2"])],
        [drug("NDA213378")],
    ))
    row = linked["records"][0]
    assert row["canonical_application_candidates"] == ["NDA213378"]
    assert row["qualified_source_references_as_published"] == [
        "NDA 213378/Original 1", "NDA 213378/Original 2",
    ]
    assert row["identity_link_status"] == "PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"
    assert audit["qualified_reference_letter_records"] == 1
    assert row["point_in_time_outcome_verified"] is False
    assert audit["verified_review_cycle_outcomes"] == 0
    assert audit["model_eligible_records"] == 0


def test_multiple_distinct_qualified_application_ids_must_remain_ambiguous():
    linked, audit = crosswalk_public_fda_sources(*sources(
        [letter(["NDA 214410/Original 2", "NDA 210854/S-05"])],
        [drug("NDA214410"), drug("NDA210854", "second")],
    ))
    assert linked["records"][0]["identity_link_status"] == "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS"
    assert audit["verified_review_cycle_outcomes"] == 0


def test_legacy_bl_and_missing_application_never_inferred():
    linked, audit = crosswalk_public_fda_sources(*sources(
        [letter(["BL 125845"]), letter([])], [drug("BLA125845")]
    ))
    assert audit["identity_link_status_counts"]["APPLICATION_ID_UNRESOLVED"] == 2
    assert audit["unresolved_legacy_bl_letter_records"] == 1
    assert audit["letters_without_application_identifiers"] == 1
    assert all(not row["model_eligible"] for row in linked["records"])


def test_mixed_qualified_and_unparseable_source_identifier_abstains():
    linked, audit = crosswalk_public_fda_sources(*sources(
        [letter(["NDA 209531/S-016", "BL 125845"])], [drug("NDA209531")]
    ))
    row = linked["records"][0]
    assert row["canonical_application_candidates"] == ["NDA209531"]
    assert row["unresolved_source_identifiers_as_published"] == ["BL 125845"]
    assert row["identity_link_status"] == "MULTIPLE_OR_AMBIGUOUS_APPLICATION_LINKS"
    assert audit["model_eligible_records"] == 0
