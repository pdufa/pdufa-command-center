from dataclasses import replace
from datetime import date
from types import SimpleNamespace

import pytest

from app.assessment_runtime import packed, sha
from app.extended_prediction_assessment import (
    LockedForecast,
    VerifiedOutcome,
    assess_prediction_level,
    evaluate_locked_calibration,
)

NCT = "NCT04576949"


def snapshot(*, captured="2020-01-02T12:00:00+00:00", published="2020-01-01"):
    document = {"protocolSection": {
        "identificationModule": {"nctId": NCT},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Fixture sponsor"}},
        "designModule": {"phases": ["PHASE3"]},
        "statusModule": {"overallStatus": "COMPLETED"},
        "conditionsModule": {"conditions": ["Fixture indication"]},
    }}
    return {
        "snapshot_id": "fixture", "nct_id": NCT, "captured_at": captured,
        "published_at": published, "source_url": f"https://clinicaltrials.gov/api/v2/studies/{NCT}",
        "raw_sha256": "0" * 64, "input_sha256": sha(document), "document_json": packed(document),
    }


@pytest.mark.parametrize("level", [17, 18, 19, 20])
def test_levels_have_independent_missing_evidence_assessments(level):
    request = SimpleNamespace(level=level, nct=NCT, mode="CURRENT_EVIDENCE", cutoffDate=None)
    report = assess_prediction_level(request, snapshot())
    assert report["engineVersion"].endswith(f"/level-{level}")
    assert report["score"] == {"value": None, "kind": "NOT_SCORED"}
    assert report["fdaPrediction"]["outcome"] == "ABSTAIN"
    assert report["fdaPrediction"]["probability"] is None
    assert report["historicalAccuracyEligible"] is False


def test_level17_registry_sponsor_never_supplies_commercial_rights():
    request = SimpleNamespace(level=17, nct=NCT, mode="CURRENT_EVIDENCE", cutoffDate=None)
    original = snapshot()
    report = assess_prediction_level(request, original)
    assert report["observations"][0]["value"] == "Fixture sponsor"
    checks = {check["id"]: check["state"] for check in report["checks"]}
    assert checks["sponsor_attribution"] == "AVAILABLE"
    assert checks["commercial_rights"] == "MISSING"
    copy = assess_prediction_level(request, {**original, "source_url": "https://example.com"})
    assert copy["observations"] == []


@pytest.mark.parametrize("source,reason", [
    ({"captured_at": "2020-01-02T23:59:59-02:00"}, "chronology"),
    ({"published_at": "2020-01-03"}, "chronology"),
    ({"input_sha256": "0" * 64}, "digest"),
    ({"nct_id": "NCT00000001"}, "identity"),
])
def test_extended_historical_evidence_fails_closed(source, reason):
    request = SimpleNamespace(level=19, nct=NCT, mode="BLIND_HISTORICAL", cutoffDate=date(2020, 1, 2))
    with pytest.raises(ValueError, match=reason):
        assess_prediction_level(request, {**snapshot(), **source})


def forecasts_and_outcomes():
    forecast = LockedForecast(
        application_cycle="fixture-a", nct=NCT, model_version="fixture-v1",
        feature_cutoff="2020-01-03T00:00:00Z", captured_at="2020-01-02T00:00:00Z",
        locked_at="2020-01-04T00:00:00Z", outcome_unexposed=True, approval_probability=0.8,
    )
    outcome = VerifiedOutcome("fixture-a", NCT, "APPROVAL", "2020-01-06", "https://example.com/decision", "VERIFIED")
    return forecast, outcome


def evaluate(forecasts, outcomes):
    return evaluate_locked_calibration(forecasts, outcomes, model_version="fixture-v1", holdout_start=date(2020, 1, 4))


def test_locked_binary_calibration_reports_baseline_and_coverage():
    forecast, outcome = forecasts_and_outcomes()
    values = evaluate(
        (forecast, replace(forecast, application_cycle="fixture-b", approval_probability=0.4)),
        (outcome, replace(outcome, application_cycle="fixture-b", outcome="CRL")),
    )
    assert values["scoredCount"] == 2
    assert values["directionalAccuracy"] == 1
    assert values["alwaysApproveAccuracy"] == 0.5
    assert values["brierScore"] == pytest.approx(0.1)
    assert values["expectedCalibrationError"] == pytest.approx(0.3)
    assert values["releasePermitted"] is False


@pytest.mark.parametrize("change,reason", [
    ({"locked_at": "2020-01-06T00:00:00Z"}, "TEMPORAL_LEAKAGE"),
    ({"locked_at": "2020-01-05T23:59:59-02:00"}, "TEMPORAL_LEAKAGE"),
    ({"captured_at": "2020-01-04T00:00:00Z"}, "TEMPORAL_LEAKAGE"),
    ({"captured_at": "2020-01-02T00:00:00"}, "INVALID_PROVENANCE"),
    ({"locked_at": "2020-01-03T00:00:00Z"}, "PRE_HOLDOUT"),
    ({"outcome_unexposed": False}, "BLIND_PROVENANCE_UNAVAILABLE"),
    ({"approval_probability": None}, "ABSTAINED"),
    ({"approval_probability": float("nan")}, "INVALID_PROBABILITY"),
    ({"approval_probability": True}, "INVALID_PROBABILITY"),
])
def test_unscorable_forecasts_stay_out_of_accuracy(change, reason):
    forecast, outcome = forecasts_and_outcomes()
    values = evaluate((replace(forecast, **change),), (outcome,))
    assert values["exclusions"] == {reason: 1}
    assert values["scoredCount"] == 0
    assert values["directionalAccuracy"] is None
    assert values["brierScore"] is None


def test_multi_version_history_needs_explicit_adjudication_before_comparison():
    forecast, outcome = forecasts_and_outcomes()
    values = evaluate((forecast, replace(forecast, approval_probability=0.7)), (outcome,))
    assert values["exclusions"] == {"AMBIGUOUS_CYCLE": 2}
    assert values["scoredCount"] == 0
    assert evaluate((forecast,), (outcome, replace(outcome, outcome="CRL")))["exclusions"] == {"AMBIGUOUS_CYCLE": 1}


def test_exact_trial_link_and_adjudicated_binary_outcome_are_required():
    forecast, outcome = forecasts_and_outcomes()
    for mismatch in (replace(outcome, nct="NCT00000001"), replace(outcome, outcome="WITHDRAWAL")):
        assert evaluate((forecast,), (mismatch,))["exclusions"] == {"NO_VERIFIED_BINARY_OUTCOME": 1}


def test_runtime_retains_each_prediction_version_with_its_original_evidence():
    from sqlalchemy import create_engine
    from app import assessment_runtime as runtime

    request = runtime.RunInput(nct=NCT, level=18, mode="CURRENT_EVIDENCE", contract="EXTENDED_7_20")
    with create_engine("sqlite://").connect() as connection:
        engine = connection.engine
        first = runtime.create(engine, request)
        runtime.execute(engine, first, lambda _: {**snapshot(), "snapshot_id": "fixture-first"})
        second = runtime.create(engine, request)
        runtime.execute(engine, second, lambda _: {**snapshot(), "snapshot_id": "fixture-second"})
        result = runtime.history(engine, NCT, 18)["runs"]
        assert [row["runId"] for row in result] == [second, first]
        assert [row["evidence"]["snapshot_id"] for row in result] == ["fixture-second", "fixture-first"]
        assert all(row["fdaPrediction"]["probability"] is None for row in result)
        assert all(len(row["reportHash"]) == 64 for row in result)
