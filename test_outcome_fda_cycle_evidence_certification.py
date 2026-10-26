from datetime import date
from outcome_fda_cycle_evidence_certification import CycleEvidence, audit_cycle_evidence


def valid(**changes):
    data = dict(
        application_id="BLA-123", review_cycle=1,
        fda_receipt_date=date(2020, 1, 1), fda_receipt_source="FDA receipt document",
        decision_date=date(2020, 9, 1), decision_source="FDA action letter",
        feature_snapshot_date=date(2020, 6, 1),
        feature_source_published_at=date(2020, 5, 1),
        complete_cohort_source="verified cohort registry",
        independently_reviewed=True,
    )
    data.update(changes)
    return CycleEvidence(**data)


def test_empty_never_certifies():
    assert audit_cycle_evidence([])["status"] == "NOT_CERTIFIED"


def test_missing_receipt_and_review_fail_closed():
    result = audit_cycle_evidence([valid(fda_receipt_date=None, independently_reviewed=False)])
    assert result["certified_count"] == 0
    assert "fda_receipt_date" in result["records"][0]["missing_or_invalid"]
    assert "independent_review" in result["records"][0]["missing_or_invalid"]


def test_publication_after_snapshot_fails():
    result = audit_cycle_evidence([valid(feature_source_published_at=date(2020, 7, 1))])
    assert "source_published_by_snapshot" in result["records"][0]["missing_or_invalid"]


def test_duplicate_cycle_fails():
    result = audit_cycle_evidence([valid(), valid()])
    assert result["status"] == "NOT_CERTIFIED"
    assert "valid_unique_application_review_cycle" in result["records"][1]["missing_or_invalid"]


def test_complete_documentation_is_not_prediction_accuracy():
    result = audit_cycle_evidence([valid()])
    assert result["status"] == "CERTIFIED"
    assert result["prediction_accuracy_estimate"] is None
