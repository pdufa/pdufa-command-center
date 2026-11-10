"""Synthetic mathematics/security contracts, never actual FDA model accuracy."""
from dataclasses import replace
from datetime import date

import pytest

from app.hop_blinded_phase3_backtest import freeze_predecision_evidence
from app.hop_probability_calibration import (
    TemporalCalibrationPlan, calibration_readiness_status, evaluate_calibration_protocol,
)
from app.medical_fda_validation import (
    CycleIdentity, FrozenTargetForecast, HistoricalReviewCycle,
    ReviewDelayEvidence, SourceReceipt,
)

D = date.fromisoformat


def source(day):
    return SourceReceipt("https://accessdata.fda.gov/drugsatfda_docs/appletter/synthetic-only.pdf",
                         "Synthetic test-only action receipt", D(day), "a" * 64)


def row(index, year, outcome):
    group = ("TRAIN" if year == 2020 else "VAL" if year == 2021 else "TEST") + str(index)
    return HistoricalReviewCycle(CycleIdentity(f"NDA{index:06d}", 1, "SYNTHETIC-NOT-REAL", group),
        "SYNTHETIC-COHORT-NOT-ACTUAL-DATA", True, True, D(f"{year}-01-10"), outcome,
        D(f"{year}-06-01"), source(f"{year}-06-02"))


def packet(r):
    year = r.public_features_as_of.year
    return freeze_predecision_evidence({
        "applicationId": r.identity.application_id, "reviewCycle": r.identity.review_cycle,
        "programFamily": r.identity.program_id, "nctIds": [f"NCT{int(r.identity.application_id[3:]):08d}"],
        "phase3ReadoutPublicOn": f"{year}-01-01", "predictionCutoff": f"{year}-01-10",
        "evidenceSources": [{"id": "synthetic-pivotal", "role": "PIVOTAL_PHASE3_RESULT",
            "source_url": "https://clinicaltrials.gov/study/NCT00000001",
            "first_public_date": f"{year}-01-01", "retrieved_date": "2023-02-01",
            "as_published_version_verified": True, "sha256": "c" * 64,
            "summary": "Synthetic original-version proof used only to test boundary checks."}]})


def fixture(target="APPROVAL"):
    training = [row(1, 2020, "APPROVED"), row(2, 2020, "COMPLETE_RESPONSE")]
    validation = [row(i, 2021, outcome) for i, outcome in enumerate(
        ["COMPLETE_RESPONSE", "APPROVED", "COMPLETE_RESPONSE", "APPROVED"], start=3)]
    test = [row(i, 2022, outcome) for i, outcome in enumerate(
        ["COMPLETE_RESPONSE", "APPROVED", "APPROVED"], start=7)]
    plan = TemporalCalibrationPlan(D("2020-12-01"), D("2021-01-01"), D("2021-09-01"),
        D("2021-10-01"), D("2022-01-01"), D("2023-01-01"), D("2023-02-01"), D("2020-10-01"),
        frozenset(r.identity.program_id for r in training),
        frozenset(r.identity.program_id for r in validation), frozenset(r.identity.program_id for r in test))
    forecasts = [FrozenTargetForecast(r.identity, target, p,
        D(f"{r.public_features_as_of.year}-01-11"), r.public_features_as_of,
        D("2020-07-01"), D("2020-06-02"), D("2020-11-01"), "b" * 64,
        plan.training_programs, frozenset(x.identity.application_id for x in training))
        for r, p in zip(validation + test, [0.1, 0.3, 0.6, 0.9, 0.15, 0.5, 0.85])]
    return training + validation + test, forecasts, [packet(r) for r in validation + test], plan


def evaluate(rows=None, forecasts=None, packets=None, plan=None, target="APPROVAL", **kwargs):
    default = fixture(target)
    return evaluate_calibration_protocol(rows if rows is not None else default[0],
        forecasts if forecasts is not None else default[1],
        packets if packets is not None else default[2], target,
        plan if plan is not None else default[3], min_validation=kwargs.pop("min_validation", 4), **kwargs)


def test_pav_fit_pools_violations_and_retains_sample_uncertainty_without_release():
    result = evaluate()
    assert result["fittedArtifact"]["blocks"] == [
        [0.1, 0.1, 0, 1], [0.3, 0.6, 1, 2], [0.9, 0.9, 1, 1]]
    assert result["calibratedTestResearchMetrics"]["predictedCount"] == 3
    assert result["calibratedTestResearchMetrics"]["brierScore"] == pytest.approx(1 / 6)
    assert result["calibratedTestResearchMetrics"]["accuracyWilson95"] is not None
    assert all("observedEventRateWilson95" in b and "observedApprovalRate" not in b
               for b in result["calibratedTestResearchMetrics"]["calibrationBins"])
    assert result["prediction"] == "ABSTAIN" and result["accuracy"] == "NOT_CALIBRATED"
    assert result["modelValidated"] is False and result["trainingAuthorized"] is False
    assert result["outcomeVaultCustodyVerifiedByThisCode"] is False
    assert result["calibrationConfidenceInterval"] is None


def test_holdout_labels_cannot_change_the_fitted_artifact_and_order_is_irrelevant():
    rows, forecasts, packets, plan = fixture()
    first = evaluate(rows, forecasts, packets, plan)
    flipped = [replace(r, action="COMPLETE_RESPONSE" if r.action == "APPROVED" else "APPROVED")
               if r.identity.program_id in plan.test_programs else r for r in rows]
    other = evaluate(list(reversed(flipped)), list(reversed(forecasts)), list(reversed(packets)), plan)
    assert first["fittedArtifact"] == other["fittedArtifact"]
    assert first["fittedArtifactSha256"] == other["fittedArtifactSha256"]
    assert first["calibratedTestResearchMetrics"]["brierScore"] != other["calibratedTestResearchMetrics"]["brierScore"]


def test_tied_scores_pool_before_monotonicity_and_keep_all_validation_rows():
    rows, forecasts, packets, plan = fixture()
    forecasts[0] = replace(forecasts[0], probability=0.3)
    result = evaluate(rows, forecasts, packets, plan)
    assert result["fittedArtifact"]["blocks"] == [[0.3, 0.6, 1, 3], [0.9, 0.9, 1, 1]]
    assert sum(b[3] for b in result["fittedArtifact"]["blocks"]) == 4


def test_insufficient_validation_never_opens_holdout_labels(monkeypatch):
    import app.hop_probability_calibration as calibration
    original = calibration._label
    def no_test_labels(r, *args, **kwargs):
        assert not r.identity.program_id.startswith("TEST"), "Holdout labels opened before fit succeeded"
        return original(r, *args, **kwargs)
    monkeypatch.setattr(calibration, "_label", no_test_labels)
    result = evaluate(min_validation=100)
    assert result["fittedArtifact"] is None
    assert result["untouchedTestEvaluated"] is False
    assert result["calibratedTestResearchMetrics"] is None


def test_abstention_and_unsupported_score_ranges_remain_in_holdout_denominator():
    rows, forecasts, packets, plan = fixture()
    forecasts = [replace(f, probability=None if f.identity.application_id == "NDA000007" else
                         0.99 if f.identity.application_id == "NDA000008" else f.probability) for f in forecasts]
    result = evaluate(rows, forecasts, packets, plan)
    metrics = result["calibratedTestResearchMetrics"]
    assert metrics["eligibleTestCount"] == 3 and metrics["predictedCount"] == 1
    assert metrics["abstainedCount"] == 2 and metrics["coverage"] == pytest.approx(1 / 3)
    assert result["testScoresOutsideValidationSupport"] == 1


@pytest.mark.parametrize("change", [
    {"training_end": D("2021-01-01")},
    {"calibration_frozen_on": D("2022-01-01")},
    {"split_frozen_on": D("2021-02-01")},
    {"validation_end": D("2022-06-01")},
])
def test_invalid_temporal_partitions_fail_before_fitting(change):
    rows, forecasts, packets, plan = fixture()
    with pytest.raises(ValueError, match="Chronological"):
        evaluate(rows, forecasts, packets, replace(plan, **change))


def test_program_overlap_missing_roster_and_training_aliases_fail_closed():
    rows, forecasts, packets, plan = fixture()
    with pytest.raises(ValueError, match="disjoint"):
        evaluate(rows, forecasts, packets, replace(plan, test_programs=plan.validation_programs))
    with pytest.raises(ValueError, match="Complete prespecified"):
        evaluate(rows[:-1], forecasts, packets, plan)
    with pytest.raises(ValueError, match="training roster"):
        evaluate(rows, [replace(f, training_application_ids=frozenset(("NDA000007",))) for f in forecasts], packets, plan)


def test_selected_outcomes_cannot_claim_representative_training_or_reuse_indication():
    rows, forecasts, packets, plan = fixture()
    rows[0] = replace(rows[0], cohort_complete_verified=False)
    with pytest.raises(ValueError, match="reviewed original labels"):
        evaluate(rows, forecasts, packets, plan)
    rows, forecasts, packets, plan = fixture()
    forecasts[0] = replace(forecasts[0], identity=replace(forecasts[0].identity, indication_id="OTHER-INDICATION"))
    with pytest.raises(ValueError, match="different indication"):
        evaluate(rows, forecasts, packets, plan)


def test_changed_base_model_and_changed_blinded_input_cannot_be_calibrated():
    rows, forecasts, packets, plan = fixture()
    forecasts[-1] = replace(forecasts[-1], model_artifact_sha256="e" * 64)
    with pytest.raises(ValueError, match="unchanged frozen"):
        evaluate(rows, forecasts, packets, plan)
    rows, forecasts, packets, plan = fixture()
    packets[0]["frozenEvidence"]["sourceVersions"][0]["summary"] = "Altered document text"
    with pytest.raises(ValueError, match="digest"):
        evaluate(rows, forecasts, packets, plan)


def test_both_classes_required_and_crl_uses_its_own_target():
    rows, forecasts, packets, plan = fixture()
    one_class = [replace(r, action="APPROVED") if r.identity.program_id in plan.validation_programs else r for r in rows]
    assert evaluate(one_class, forecasts, packets, plan)["untouchedTestEvaluated"] is False
    result = evaluate(target="CRL")
    assert result["fittedArtifact"]["target"] == "CRL"
    assert result["fittedArtifact"]["blocks"] != evaluate()["fittedArtifact"]["blocks"]


def test_review_delay_requires_documented_positive_and_negative_event_history():
    rows, forecasts, packets, plan = fixture("REVIEW_DELAY")
    converted = []
    for r in rows:
        year = r.action_on.year
        extension = r.action == "APPROVED"
        delay = ReviewDelayEvidence(D(f"{year}-07-01"), D(f"{year-1}-12-01"),
            "DOCUMENTED_EXTENSION" if extension else "NO_EXTENSION_CONFIRMED", source(f"{year}-07-02"),
            extension_on=D(f"{year}-06-01") if extension else None,
            revised_goal_on=D(f"{year}-10-01") if extension else None,
            complete_event_history_through=None if extension else D(f"{year}-07-01"),
            independently_adjudicated=True, original_goal_source=source(f"{year-1}-12-01"))
        converted.append(replace(r, delay=delay))
    forecasts = [replace(f, latest_training_label_public_on=D("2020-07-02"),
                         fitted_through=D("2020-08-01")) for f in forecasts]
    result = evaluate(converted, forecasts, packets, plan, target="REVIEW_DELAY")
    assert result["fittedArtifact"]["target"] == "REVIEW_DELAY"
    assert result["calibratedTestResearchMetrics"]["eligibleTestCount"] == 3
    assert result["prediction"] == "ABSTAIN"


def test_real_readiness_preserves_412_source_leads_as_zero_training_cases():
    result = calibration_readiness_status()
    assert result["sourceActionLeads"] == 412
    for key in ("newHistoricalRecordsObtained", "independentlyVerifiedCycles", "modelEligibleCases",
                "realTrainingCases", "realValidationCases", "realUntouchedTestCases", "actualCalibrationFits"):
        assert result[key] == 0
    assert result["accuracyAvailable"] is False
    assert result["measuredAccuracy"] is None and result["prediction"] == "ABSTAIN"
    assert result["perTargetModelEligibleCases"] == {"APPROVAL": 0, "CRL": 0, "REVIEW_DELAY": 0}


def test_current_track_b_checkpoint_count_is_not_replaced_by_old_412_snapshot():
    # Synthetic checkpoint plumbing only, not a newly collected FDA count.
    checkpoint = {
        "schema": "MAIN_R47_HISTORICAL_SOURCE_BUILD_CHECKPOINT",
        "status": "LIVE_HISTORICAL_FDA_CANDIDATE_SOURCE_RESEARCH_NOT_REAL_BACKTEST",
        "researchSourceActionCandidates": 17, "candidateFileSha256": "a" * 64,
        "originalFdaSourceReceiptSha256": "b" * 64,
        "completeConsecutiveOriginalFilingCohort": False, "modelTrainingAuthorized": False,
        "productionWriteAuthorized": False, "automaticAccuracyOrHundredPercentClaimAuthorized": False,
        "exactCycleOutcomesAdjudicated": 0, "pairedIndependentHistory": 0,
        "qualifiedResearchPredictions": 0, "qualifiedClinicalReviewerSignoffs": 0,
        "outOfTimeValidationCases": 0, "prospectiveAccuracy": None,
        "calibration": None, "approvalProbability": None,
        "generatedAtUtc": "2026-11-09T19:00:00Z",
    }
    result = calibration_readiness_status(checkpoint)
    assert result["sourceActionLeads"] == 17
    assert result["sourceCountBasis"] == "CURRENT_VALIDATED_TRACK_B_CANDIDATE_CHECKPOINT"
    assert result["fitStatus"] == "NOT_RUN_NO_MODEL_ELIGIBLE_CASES"
    assert result["realCases"] == 0
    assert result["candidateFileSha256"] == checkpoint["candidateFileSha256"]
    with pytest.raises(ValueError, match="cannot promote"):
        calibration_readiness_status({**checkpoint, "exactCycleOutcomesAdjudicated": 1})
    with pytest.raises(ValueError, match="cannot promote"):
        calibration_readiness_status({**checkpoint, "candidateFileSha256": None})
    with pytest.raises(ValueError, match="cannot promote"):
        calibration_readiness_status({**checkpoint, "calibration": 0.95})
    with pytest.raises(ValueError, match="timestamp"):
        calibration_readiness_status({**checkpoint, "generatedAtUtc": "2026-11-09T19:00:00"})
