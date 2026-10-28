"""Fictitious cohort reconciliation fixtures, not verified FDA decisions."""
from datetime import date, datetime

import pytest

from app.hop_cohort_manifest import DISPOSITIONS, audit_cohort_manifest

AS_OF = date(2021, 1, 2)


def manifest(count=2):
    return {
        "cohort_id": "synthetic-cohort", "population_definition": "Fictitious full application universe",
        "start_date": "2020-01-01", "end_date": "2020-12-31",
        "source_url": "https://www.fda.gov/drugs/example",
        "expected_review_cycles": count, "observed_review_cycles": count,
        "independent_reviewer": "test-only-declaration", "source_retrieved_on": "2021-01-01",
        "independent_review_complete": True, "approval_and_crl_ascertainment_complete": True,
    }


def member(number, *, cycle=1, disposition=None, **extra):
    row = {"application_id": f"NDA{number:06d}", "review_cycle": cycle, **extra}
    if disposition is not None:
        row["disposition"] = disposition
    return row


def audit(expected, observed, data=None):
    return audit_cohort_manifest(data or manifest(len(expected)), expected_members=expected,
                                 observed_members=observed, as_of=AS_OF)


def assert_no_clearance(result):
    assert result["status"] == "BLOCKED"
    assert result["independently_verified"] is False
    assert result["model_eligible"] is False
    assert "external_source_verification_required" in result["blockers"]


def test_count_only_manifest_cannot_reconcile_exact_cohort():
    result = audit_cohort_manifest(manifest(), as_of=AS_OF)
    assert "exact_roster_required" in result["blockers"]
    assert result["roster_audit"]["expected_member_rows"] is None
    assert_no_clearance(result)


def test_empty_expected_roster_cannot_look_reconciled():
    result = audit_cohort_manifest(manifest(0), expected_members=[],observed_members=[],as_of=AS_OF)
    assert result["roster_audit"]["status"] == "BLOCKED"
    assert "empty_expected_roster" in result["blockers"]
    assert_no_clearance(result)


def test_equal_counts_cannot_hide_missing_and_substituted_application():
    result = audit([member(1), member(2)], [member(1,disposition="APPROVED"),member(3,disposition="COMPLETE_RESPONSE")])
    roster = result["roster_audit"]
    assert roster["missing_identities"] == [{"application_id":"NDA000002","review_cycle":1}]
    assert roster["extra_identities"] == [{"application_id":"NDA000003","review_cycle":1}]
    assert {"missing_roster_members","unexpected_roster_members"} <= set(result["blockers"])
    assert roster["binary_disposition_cycles"] == 1
    assert_no_clearance(result)


def test_reconciled_metadata_and_flags_never_verify_source_truth():
    result = audit([member(1),member(2)], [member(1,disposition="APPROVED"),member(2,disposition="COMPLETE_RESPONSE")])
    assert result["roster_audit"]["status"] == "RECONCILED_METADATA_ONLY"
    assert result["roster_audit"]["binary_disposition_cycles"] == 2
    assert result["roster_audit"]["metadata_only"] is True
    assert result["roster_audit"]["model_eligible_records"] == 0
    assert result["roster_audit"]["probability"] is None
    assert result["blockers"] == ["external_source_verification_required"]
    assert_no_clearance(result)


def test_application_aliases_are_canonicalized_in_both_rosters():
    expected = [member(1)]
    observed = [dict(member(1,disposition="APPROVED"),application_id=" nda-000001 ")]
    result = audit(expected,observed)
    assert result["roster_audit"]["missing_identities"] == []
    assert result["roster_audit"]["extra_identities"] == []
    assert result["roster_audit"]["binary_disposition_cycles"] == 1


def test_bad_duplicate_claim_cannot_vanish_before_identity_reconciliation():
    first = member(1,disposition="APPROVED")
    bad = dict(first,application_id="nda-000001",disposition="invented")
    result = audit([member(1)], [first,bad])
    roster = result["roster_audit"]
    assert roster["duplicate_observed_identities"] == [{"application_id":"NDA000001","review_cycle":1,"count":2}]
    assert roster["observed_member_rows"] == 2 and roster["observed_unique_identities"] == 1
    assert roster["disposition_row_counts"]["APPROVED"] == 1
    assert roster["binary_disposition_cycles"] == 0
    assert roster["invalid_observed_disposition_rows"] == 1
    assert "invalid_disposition" in roster["observed_issue_counts"]
    assert "duplicate_observed_roster_identity" in result["blockers"]


def test_duplicate_expected_keys_do_not_create_an_extra_denominator_member():
    result = audit([member(1), dict(member(1),application_id="nda-000001")], [member(1,disposition="APPROVED")])
    roster = result["roster_audit"]
    assert roster["expected_member_rows"] == 2 and roster["expected_unique_identities"] == 1
    assert "duplicate_expected_roster_identity" in result["blockers"]
    assert "expected_roster_count_mismatch" in result["blockers"]


@pytest.mark.parametrize("field,value", [("application_id","invalid"),("application_id",None),
                                        ("application_id",123),("review_cycle",True),
                                        ("review_cycle",0),("review_cycle","1")])
def test_malformed_identity_remains_in_row_accounting(field,value):
    malformed = dict(member(1),**{field:value})
    result = audit([malformed],[dict(malformed,disposition="APPROVED")])
    roster = result["roster_audit"]
    assert roster["expected_member_rows"] == roster["observed_member_rows"] == 1
    assert roster["expected_unique_identities"] == roster["observed_unique_identities"] == 0
    assert roster["invalid_expected_identity_rows"] == roster["invalid_observed_identity_rows"] == 1
    assert roster["binary_disposition_cycles"] == 0
    assert_no_clearance(result)


@pytest.mark.parametrize("value", [None,{},"NDA000001",iter([])])
def test_rosters_must_be_ordered_sequences(value):
    result = audit_cohort_manifest(manifest(),expected_members=value,observed_members=value,as_of=AS_OF)
    assert result["roster_audit"]["status"] == "BLOCKED"
    assert_no_clearance(result)


def test_nonobject_member_is_reported_without_disappearing():
    result = audit([member(1),None], [member(1,disposition="APPROVED"),None])
    assert result["roster_audit"]["expected_issue_counts"] == {"member_not_object":1}
    assert result["roster_audit"]["observed_issue_counts"] == {"member_not_object":1}


def test_missing_disposition_cannot_remove_an_expected_cycle_from_denominator():
    result = audit([member(1)], [member(1)])
    roster = result["roster_audit"]
    assert roster["missing_identities"] == []
    assert roster["observed_member_rows"] == roster["observed_unique_identities"] == 1
    assert roster["observed_issue_counts"] == {"missing_disposition":1}
    assert roster["binary_disposition_cycles"] == 0
    assert roster["invalid_observed_disposition_rows"] == 1


def test_all_nonbinary_dispositions_remain_counted_without_becoming_failures():
    expected = [member(i) for i in range(1,len(DISPOSITIONS)+1)]
    observed = [member(i,disposition=action,exclusion_reason="Fictitious prespecified scope rule")
                for i,action in enumerate(DISPOSITIONS,1)]
    result = audit(expected,observed)
    roster = result["roster_audit"]
    assert roster["disposition_counts"] == {key:1 for key in DISPOSITIONS}
    assert roster["observed_unique_identities"] == len(DISPOSITIONS)
    assert roster["binary_disposition_cycles"] == 2
    assert "unresolved_roster_members" in result["blockers"]


@pytest.mark.parametrize("reason", [None,"", "  ",True])
def test_out_of_scope_requires_explicit_exclusion_reason(reason):
    result = audit([member(1)],[member(1,disposition="OUT_OF_SCOPE",exclusion_reason=reason)])
    assert result["roster_audit"]["observed_issue_counts"] == {"missing_exclusion_reason":1}
    assert result["roster_audit"]["disposition_row_counts"]["OUT_OF_SCOPE"] == 1
    assert result["roster_audit"]["disposition_counts"]["OUT_OF_SCOPE"] == 0


@pytest.mark.parametrize("disposition", ["WITHDRAWAL", True,[],"approved"])
def test_unknown_disposition_is_not_guessed(disposition):
    result = audit([member(1)],[member(1,disposition=disposition)])
    assert result["roster_audit"]["observed_issue_counts"] == {"invalid_disposition":1}
    assert result["roster_audit"]["binary_disposition_cycles"] == 0


def test_declared_counts_must_equal_actual_rows_and_unique_members():
    result = audit([member(1)],[member(1,disposition="APPROVED")],data=manifest(100))
    assert {"expected_roster_count_mismatch","observed_roster_count_mismatch"} <= set(result["blockers"])
    assert result["roster_audit"]["status"] == "BLOCKED"


def test_reconciliation_is_order_invariant_even_for_invalid_conflicting_rosters():
    expected = [member(1),member(2),None,dict(member(1),application_id="nda-000001")]
    observed = [member(1,disposition="APPROVED"),member(1,disposition="UNRESOLVED"),
                member(3,disposition="WITHDRAWN"),dict(member(2),review_cycle="1")]
    assert audit(expected,observed) == audit(list(reversed(expected)),list(reversed(observed)))


@pytest.mark.parametrize("value", ["2021-01-02",datetime(2021,1,2),True])
def test_snapshot_must_be_an_explicit_date_not_datetime(value):
    with pytest.raises(ValueError,match="as_of must be a date"):
        audit_cohort_manifest(manifest(),as_of=value)


def test_source_retrieval_after_replay_snapshot_is_not_yet_available():
    result = audit_cohort_manifest(manifest(),expected_members=[],observed_members=[],as_of=date(2020,12,31))
    assert "invalid_coverage_dates" in result["blockers"]
    assert result["as_of"] == "2020-12-31"


@pytest.mark.parametrize("url", ["https://user@www.fda.gov/drugs", "https://www.fda.gov:8443/drugs",
                                  "https://www.fda.gov/drugs#claim", "https://www.fda.gov/"])
def test_manifest_reuses_strict_fda_url_rules(url):
    data = dict(manifest(),source_url=url)
    assert "source_not_official_fda" in audit_cohort_manifest(data,as_of=AS_OF)["blockers"]
