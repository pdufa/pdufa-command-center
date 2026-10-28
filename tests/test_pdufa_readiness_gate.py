"""Synthetic contract tests for readiness gate; never real trading validation."""
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from pdufa_readiness_gate import readiness


def report(**changes):
    base = {"audit": "historical_fda_decision_ingestion",
            "independently_verified_pass_count": 0,
            "independently_verified_fail_count": 0,
            "model_eligible_records": 0,
            "source_content_verified": False,
            "complete_application_denominator_verified": False,
            "independent_backtest_complete": False,
            "prediction_model_validated": False}
    return {**base, **changes}


def test_empty_data_is_not_ready():
    result = readiness(report())
    assert result["status"] == "DATA_NOT_READY"
    assert not result["paper_trading_ready"]
    assert not result["live_trading_ready"]


def test_candidate_rows_cannot_establish_readiness():
    result = readiness(report(candidate_review_cycles=[{"candidate_label": "PASS"}]))
    assert result["verified_pass"] == 0
    assert result["status"] == "DATA_NOT_READY"


def test_source_links_alone_cannot_establish_readiness():
    result = readiness(report(independently_verified_pass_count=10,
                              independently_verified_fail_count=10,
                              model_eligible_records=20))
    assert result["status"] == "DATA_NOT_READY"


def test_verified_data_does_not_authorize_trading():
    result = readiness(report(independently_verified_pass_count=10,
                              independently_verified_fail_count=10,
                              model_eligible_records=20,
                              source_content_verified=True,
                              complete_application_denominator_verified=True,
                              independent_backtest_complete=True,
                              prediction_model_validated=True))
    assert result["status"] == "DATA_READY_FOR_RESEARCH"
    assert not result["paper_trading_ready"]
    assert not result["live_trading_ready"]


@pytest.mark.parametrize("value", [-1, 1.5, True, None, "10"])
def test_bad_counts_rejected(value):
    with pytest.raises(ValueError):
        readiness(report(independently_verified_pass_count=value))


def test_wrong_report_type_rejected():
    with pytest.raises(ValueError):
        readiness({"audit": "something_else"})
