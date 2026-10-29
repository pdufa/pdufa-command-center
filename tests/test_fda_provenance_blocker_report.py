from research.fda_provenance_blocker_report import report_blockers
from research.fda_provenance_scoring_pipeline import PipelineResult
from research.fda_prospective_outcome_scoring import Score


def test_missing_evidence_reports_actionable_blockers():
    result = PipelineResult(
        prediction_gate="LEDGER_INTEGRITY_FAILED",
        outcome_gate="DOCUMENT_UNAVAILABLE",
        score=Score("EXAMPLE", "PROVENANCE_NOT_VERIFIED", None),
        membership_gate="LEDGER_NOT_VERIFIED",
        chronology_gate="CUTOFF_NOT_BEFORE_DECISION",
    )
    report = report_blockers(result)
    assert not report.ready_for_validated_scoring
    assert "FROZEN_PREDICTION_MEMBERSHIP_REQUIRED" in report.blockers
    assert "CHRONOLOGY_RECONCILIATION_REQUIRED" in report.blockers
    assert "FDA_ORIGINAL_DOCUMENT_AUTHENTICATION_REQUIRED" in report.blockers


def test_even_claimed_success_cannot_self_certify():
    result = PipelineResult(
        prediction_gate="TRUSTED_ANCHOR_VERIFIED",
        outcome_gate="FDA_ORIGIN_AUTHENTICATED",
        score=Score("EXAMPLE", "SCORED", True),
        membership_gate="LEDGER_MEMBERSHIP_VERIFIED_TIME_UNTRUSTED",
        chronology_gate="CHRONOLOGY_CONSISTENT_TIME_UNTRUSTED",
    )
    report = report_blockers(result)
    assert not report.ready_for_validated_scoring
    assert report.blockers == ("INDEPENDENT_VALIDATION_WORKFLOW_NOT_ESTABLISHED",)
