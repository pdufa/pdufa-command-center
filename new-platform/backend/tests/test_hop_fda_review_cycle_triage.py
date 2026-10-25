from datetime import date

import pytest

from app.hop_fda_review_cycle_triage import triage_published_letter_cycles


def row(app="NDA209510", on="10/05/2018", letter_type="COMPLETE RESPONSE",
        digest="a", status="PRESENT_IN_APPROVED_PRODUCT_REGISTRY_AS_OF_EXPORT"):
    return {
        "letter_record_sha256": digest * 64,
        "canonical_application_candidates": [app] if app else [],
        "identity_link_status": status,
        "letter_date_as_published": on,
        "letter_type_as_published": letter_type,
        "qualified_source_references_as_published": [],
        "complete_cohort_verified": False,
        "point_in_time_outcome_verified": False,
        "model_eligible": False,
    }


def source(rows):
    return {"status": "IDENTITY_LINKAGE_ONLY_NOT_A_REVIEW_CYCLE_OUTCOME_COHORT",
            "records": rows}


def test_two_dates_are_review_candidates_not_verified_cycles():
    candidates, audit = triage_published_letter_cycles(source([
        row(digest="a"), row(on="12/10/2019", digest="b"),
    ]), date(2026, 10, 25))
    assert audit["repeated_letter_application_groups"] == 1
    assert audit["letter_records_in_repeated_groups"] == 2
    assert audit["independently_verified_review_cycles"] == 0
    assert audit["model_eligible_records"] == 0
    assert audit["prediction_probability"] is None
    group = candidates["applications_for_review"][0]
    assert group["distinct_letter_dates"] == 2
    assert group["independently_verified_review_cycles"] == 0
    assert all(not x["model_eligible"] for x in group["letters"])


def test_same_date_type_is_flagged_not_automatically_deduplicated():
    candidates, audit = triage_published_letter_cycles(source([
        row(digest="a"), row(digest="b"),
    ]), date(2026, 10, 25))
    assert audit["potential_same_day_type_duplicate_groups"] == 1
    assert audit["grouped_letter_records"] == 2
    assert all(x["potential_same_day_type_duplicate"] for x in
               candidates["applications_for_review"][0]["letters"])


def test_singletons_and_ambiguous_identifiers_reconcile():
    ambiguous = row(app=None, digest="b", status="APPLICATION_ID_UNRESOLVED")
    candidates, audit = triage_published_letter_cycles(source([
        row(digest="a"), ambiguous,
    ]), date(2026, 10, 25))
    assert candidates["applications_for_review"] == []
    assert audit["single_letter_application_groups"] == 1
    assert audit["excluded_letter_records"]["unresolved_or_ambiguous_identity"] == 1
    assert audit["grouped_letter_records"] == 1


def test_invalid_date_is_excluded_without_creating_outcome():
    candidates, audit = triage_published_letter_cycles(source([
        row(on="12/31/2099", digest="a"),
    ]), date(2026, 10, 25))
    assert candidates["applications_for_review"] == []
    assert audit["excluded_letter_records"]["missing_invalid_or_future_date"] == 1


@pytest.mark.parametrize("field,value", [
    ("model_eligible", True), ("complete_cohort_verified", True),
    ("point_in_time_outcome_verified", True),
    ("letter_record_sha256", "fake"),
])
def test_unverified_source_contract_fails_closed(field, value):
    bad = row()
    bad[field] = value
    with pytest.raises(ValueError):
        triage_published_letter_cycles(source([bad]), date(2026, 10, 25))


def test_duplicate_source_digest_rejected_even_across_applications():
    with pytest.raises(ValueError, match="duplicate source record digest"):
        triage_published_letter_cycles(source([
            row(app="NDA209510"), row(app="NDA200123"),
        ]), date(2026, 10, 25))


def test_unquarantined_input_rejected():
    with pytest.raises(ValueError, match="quarantined"):
        triage_published_letter_cycles({"status": "MODEL_READY", "records": []},
                                      date(2026, 10, 25))
