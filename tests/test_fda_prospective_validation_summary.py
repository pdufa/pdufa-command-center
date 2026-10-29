from research.fda_prospective_outcome_scoring import Score
from research.fda_prospective_validation_summary import summarize_research_scores


def test_coverage_report_keeps_accuracy_unavailable():
    report = summarize_research_scores([
        Score("A", "SCORED", True),
        Score("B", "SCORED", False),
        Score("C", "ABSTAIN", None),
        Score("D", "PROVENANCE_NOT_VERIFIED", None),
        Score("E", "DOCUMENT_UNAVAILABLE", None),
    ])
    assert report.total == 5
    assert report.scored_unverified == 2
    assert report.abstentions == 1
    assert report.provenance_blocked == 1
    assert report.other_unscored == 1
    assert report.validated_accuracy is None


def test_empty_report_has_no_accuracy():
    report = summarize_research_scores([])
    assert report.total == 0
    assert report.validated_accuracy is None
