"""Synthetic Level 19 prospective freeze and Level 20 decision chronology tests."""
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_levels_nine_to_twenty import NCT, intake, reviewed_record
from test_scientific_regulatory_context import app, official, evidence as filing_evidence

S = "a" * 64
M = "b" * 64


def reviewed(m):
    x = reviewed_record()
    x["measurements"] = m
    return x


def assess(data):
    return assess_levels_nine_to_twenty(intake(), trial_id=NCT, evidence=data)


def forecast_data():
    return {
        "19.outcomeUnexposedSourceFreeze": reviewed({
            "nctId": NCT, "sourceFreezeSha256": S,
            "frozenAt": "2026-01-15T12:00:00+00:00"
        }),
        "19.predictionModelArtifact": reviewed({
            "nctId": NCT, "modelArtifactSha256": M,
            "modelFrozenAt": "2026-01-16T12:00:00Z"
        }),
        "19.prospectivePredictionTimestamp": reviewed({
            "nctId": NCT, "sourceFreezeSha256": S,
            "modelArtifactSha256": M, "predictionId": "SYNTHETIC-PREDICTION-1",
            "predictionAt": "2026-01-17T12:00:00+00:00",
        }),
    }


def decision_data():
    data = filing_evidence()
    data["20.originalGoalDate"] = official({
        **app(), "linkedNct": NCT, "originalGoalDate": "2026-01-30"
    })
    data["20.officialActionAndDate"] = official({
        **app(), "linkedNct": NCT, "officialActionDate": "2026-01-25",
        "officialAction": "APPROVED"
    })
    return data


def test_freeze_digests_are_metadata_only_not_blind_certification():
    result = assess(forecast_data())["19"]["prospectiveIntegrity"]
    assert result["status"] == "FROZEN_METADATA_RECONCILED_NOT_PROSPECTIVE_CERTIFICATION"
    assert result["genuinelyBlindVerified"] is False
    assert result["prospectiveAccuracyEligible"] is False
    assert result["modelCalibrated"] is False
    assert result["approvalProbability"] is None


def test_invalid_digest_wrong_trial_future_or_naive_timestamp_rejected():
    for key, change in [
        ("19.outcomeUnexposedSourceFreeze", {"sourceFreezeSha256": "not-a-sha"}),
        ("19.predictionModelArtifact", {"nctId": "NCT00000002"}),
        ("19.prospectivePredictionTimestamp", {"predictionAt": "2026-03-01T12:00:00Z"}),
        ("19.prospectivePredictionTimestamp", {"predictionAt": "2026-01-17T12:00:00"}),
        ("19.prospectivePredictionTimestamp", {"modelArtifactSha256": "c" * 64}),
        ("19.predictionModelArtifact", {"modelFrozenAt": "2026-01-18T12:00:00Z"}),
    ]:
        data = forecast_data()
        data[key]["measurements"].update(change)
        assert assess(data)["19"]["prospectiveIntegrity"]["status"] == "REJECTED_FREEZE_METADATA"


def test_official_action_date_is_separate_from_goal_date_and_not_accuracy():
    result = assess(decision_data())["20"]["outcomeChronology"]
    assert result["status"] == "POSTDECISION_ACTION_CHRONOLOGY_ONLY"
    assert result["originalGoalDate"] == "2026-01-30"
    assert result["officialActionDate"] == "2026-01-25"
    assert result["actionDaysRelativeToOriginalGoal"] == -5
    assert result["binaryActionCategory"] == "APPROVED"
    assert result["predictionAccuracy"] is None
    assert result["outcomeComparisonStatus"] == "NO_TRUSTED_PERSISTED_PREDICTION_REFERENCE"


def test_withdrawal_is_not_binary_action_accuracy():
    data = decision_data()
    data["20.officialActionAndDate"]["measurements"]["officialAction"] = "WITHDRAWN"
    result = assess(data)["20"]["outcomeChronology"]
    assert result["binaryActionCategory"] is None
    assert result["binaryDecisionAccuracyEligible"] is False


def test_app_mismatch_source_cutoff_and_unofficial_action_rejected():
    data = decision_data()
    data["20.officialActionAndDate"]["measurements"]["applicationNumber"] = "765432"
    assert assess(data)["20"]["outcomeChronology"]["status"] == "REJECTED_ACTION_RECORD"
    data = decision_data()
    data["20.officialActionAndDate"]["measurements"]["officialActionDate"] = "2026-02-25"
    assert assess(data)["20"]["outcomeChronology"]["status"] == "REJECTED_ACTION_RECORD"
    data = decision_data()
    data["20.officialActionAndDate"]["source"] = "https://issuer.example/press"
    assert assess(data)["20"]["outcomeChronology"]["status"] == "NOT_ASSESSED"


def test_outcome_only_never_creates_forecast_metadata_or_accuracy():
    result = assess(decision_data())
    assert result["19"]["prospectiveIntegrity"]["status"] == "NOT_ASSESSED"
    assert result["20"]["outcomeChronology"]["predictionAccuracy"] is None
    assert result["20"]["score"] is None
    assert result["19"]["fdaPrediction"] == "ABSTAIN"
