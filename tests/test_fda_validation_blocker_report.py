from research.fda_prospective_outcome_scoring import Score
from research.fda_provenance_scoring_pipeline import PipelineResult
from research.fda_validation_blocker_report import explain_validation_blockers


def test_even_clean_local_checks_cannot_certify_readiness():
    result = PipelineResult(
        prediction_gate="SIGNED_PRE_CUTOFF_UNTRUSTED_TIME",
        outcome_gate="BYTES_MATCH_ORIGIN_UNVERIFIED",
        score=Score("EXAMPLE", "PROVENANCE_NOT_VERIFIED", None),
        membership_gate="LEDGER_MEMBERSHIP_VERIFIED_TIME_UNTRUSTED",
        chronology_gate="CHRONOLOGY_CONSISTENT_TIME_UNTRUSTED",
    )
    report = explain_validation_blockers(result)
    assert not report.ready_for_validated_scoring
    assert len(report.blockers) == 3
    assert any("timestamp" in item for item in report.blockers)


def test_failed_local_checks_produce_specific_remediation():
    result = PipelineResult(
        prediction_gate="LEDGER_INTEGRITY_FAILED",
        outcome_gate="DOCUMENT_UNAVAILABLE",
        score=Score("EXAMPLE", "PROVENANCE_NOT_VERIFIED", None),
        membership_gate="LEDGER_NOT_VERIFIED",
        chronology_gate="INVALID_TIME",
    )
    report = explain_validation_blockers(result)
    assert not report.ready_for_validated_scoring
    assert len(report.blockers) == 7
