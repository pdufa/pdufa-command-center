from datetime import date

import pytest

from app.hop_fda_action_review import build_fda_action_review_worklist


def letter(digest, type_, publication, apps):
    return {
        "source_record_sha256": digest * 64,
        "source_partition": "https://download.open.fda.gov/transparency/crl/test.json.zip",
        "source_record_index": 0,
        "company_name_as_published": "Public example",
        "file_name_as_published": "FDA_source_example.pdf",
        "application_numbers": apps,
        "letter_type_as_published": type_,
        "letter_date_as_published": publication,
        "model_eligible": False,
    }


def identity(source, candidates, status="PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"):
    return {
        "letter_record_sha256": source["source_record_sha256"],
        "source_application_identifiers_as_published": source["application_numbers"],
        "canonical_application_candidates": candidates,
        "identity_link_status": status,
        "letter_date_as_published": source["letter_date_as_published"],
        "letter_type_as_published": source["letter_type_as_published"],
        "model_eligible": False,
        "complete_cohort_verified": False,
        "point_in_time_outcome_verified": False,
    }


def archives(letters, links):
    return (
        {"status": "IDENTITY_LINKAGE_ONLY_NOT_A_REVIEW_CYCLE_OUTCOME_COHORT",
         "records": links},
        {"status": "QUARANTINED_NOT_A_COMPLETE_APPLICATION_COHORT",
         "source_export_date": "2026-10-21",
         "records": letters},
    )


def test_published_action_types_are_not_interchangeable_outcomes():
    docs = [
        letter("a", "COMPLETE RESPONSE", "03/01/2025", ["NDA 213378"]),
        letter("b", "RESCIND COMPLETE RESPONSE", "03/28/2019", ["NDA 202408"]),
        letter("c", "CORRECTED PROVISIONAL DETERMINATION", "07/04/2024",
               ["BLA 761373", "BLA 761425"]),
        letter("d", "TENTATIVE APPROVAL", "09/02/2021", ["NDA 211566"]),
        letter("e", "REFUSAL TO FILE", "05/18/2012", ["NDA 202860"]),
        letter("f", "PROVISIONAL DETERMINATION", "12/17/2024", ["BLA 761338"]),
        letter("0", "UNCLASSIFIED", "11/02/2007", ["NDA 021164"]),
    ]
    links = [identity(row, ["NDA000001"]) for row in docs]
    links[2]["canonical_application_candidates"] = ["BLA761373", "BLA761425"]
    result, audit = build_fda_action_review_worklist(
        *archives(docs, links), date(2026, 10, 25))
    assert len(result["records"]) == 7
    assert len(audit["published_letter_type_counts"]) == 7
    assert audit["source_actions_requiring_original_or_prior_action"] == 2
    assert [x["letter_type_as_published"] for x in result["records"][:2]] == [
        "RESCIND COMPLETE RESPONSE", "CORRECTED PROVISIONAL DETERMINATION"
    ]
    assert all(x["effective_fda_action_date_candidate"] is None for x in result["records"])
    assert all(x["fda_review_cycle_outcome"] is None for x in result["records"])
    assert all(x["effective_fda_action_date_independently_verified"] is False
               for x in result["records"])
    assert all(x["model_eligible"] is False for x in result["records"])
    assert audit["independently_adjudicated_review_cycle_outcomes"] == 0
    assert audit["complete_denominator_verified"] is False
    assert audit["prediction_probability"] is None


def test_corrected_letter_source_date_never_assumed_to_be_action_date():
    row = letter("a", "COMPLETE RESPONSE", "04/10/2026", ["BLA 761401"])
    result, audit = build_fda_action_review_worklist(
        *archives([row], [identity(row, ["BLA761401"])]), date(2026, 10, 25))
    event = result["records"][0]
    assert event["normalized_source_letter_date"] == "2026-04-10"
    assert event["effective_fda_action_date_candidate"] is None
    assert event["effective_fda_action_date_independently_verified"] is False
    assert event["review_cycle_number_verified"] is False
    assert event["public_features_as_of"] is None
    assert audit["independently_verified_predecision_features"] == 0


def test_same_application_multiple_source_letters_not_claimed_as_review_cycles():
    old = letter("a", "COMPLETE RESPONSE", "05/07/2020", ["NDA 209510"])
    new = letter("b", "COMPLETE RESPONSE", "08/25/2021", ["NDA 209510"])
    result, audit = build_fda_action_review_worklist(
        *archives([old, new], [identity(old, ["NDA209510"]), identity(new, ["NDA209510"])]),
        date(2026, 10, 25))
    assert audit["same_application_repeated_letter_candidates"] == 2
    assert all(x["same_application_multiple_published_letters"] for x in result["records"])
    assert all(x["review_cycle_verified"] is False for x in result["records"])
    assert audit["independently_adjudicated_review_cycle_outcomes"] == 0


@pytest.mark.parametrize("change", [
    lambda src, link: link.update({"letter_date_as_published": "01/01/2020"}),
    lambda src, link: link.update({"source_application_identifiers_as_published": ["NDA 000999"]}),
    lambda src, link: link.update({"model_eligible": True}),
    lambda src, link: src.update({"model_eligible": True}),
    lambda src, link: link.update({"identity_link_status": "APPROVED"}),
])
def test_tampering_and_promotion_fail_closed(change):
    src = letter("a", "COMPLETE RESPONSE", "07/07/2025", ["NDA 123456"])
    link = identity(src, ["NDA123456"])
    change(src, link)
    with pytest.raises(ValueError):
        build_fda_action_review_worklist(*archives([src], [link]), date(2026, 10, 25))


def test_future_date_or_unknown_letter_type_rejected():
    src = letter("a", "COMPLETE RESPONSE", "01/01/2027", ["NDA 123456"])
    with pytest.raises(ValueError, match="future"):
        build_fda_action_review_worklist(
            *archives([src], [identity(src, ["NDA123456"])]), date(2026, 10, 25))
    src = letter("a", "FDA APPROVED", "06/01/2025", ["NDA 123456"])
    with pytest.raises(ValueError, match="unrecognized"):
        build_fda_action_review_worklist(
            *archives([src], [identity(src, ["NDA123456"])]), date(2026, 10, 25))
