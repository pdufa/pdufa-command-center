"""Synthetic validation contracts, never historical FDA performance evidence."""
from dataclasses import replace
from datetime import date
from math import log

import pytest

from app.medical_fda_validation import (
    CycleIdentity, FrozenTargetForecast, HistoricalReviewCycle, ReviewDelayEvidence,
    SourceReceipt, evaluate_target,
)

D = date.fromisoformat
WINDOW = dict(holdout_start=D("2022-01-01"), holdout_end=D("2023-01-01"),
              evaluation_as_of=D("2023-02-01"), holdout_frozen_on=D("2021-11-01"),
              held_out_program_ids=frozenset(("HELDOUT-A", "HELDOUT-B")))


def source(day="2022-06-02"):
    return SourceReceipt("https://accessdata.fda.gov/drugsatfda_docs/appletter/synthetic.pdf",
        "Synthetic original action receipt for tests only", D(day), "a" * 64)


def case(index=1, *, action="APPROVED"):
    identity = CycleIdentity(f"NDA{index:06d}", 1, "SYNTHETIC-INDICATION", "HELDOUT-A" if index == 1 else "HELDOUT-B")
    return HistoricalReviewCycle(identity, "SYNTHETIC-COMPLETE-COHORT", True, True,
                                 D("2022-01-05"), action, D("2022-06-01"), source())


def forecast(row, target="APPROVAL", p=0.8):
    return FrozenTargetForecast(row.identity, target, p, D("2022-01-10"), row.public_features_as_of,
                                D("2021-11-15"), D("2021-11-01"), D("2021-12-01"),
                                "b" * 64, frozenset(("TRAIN-ONLY",)), frozenset(("NDA900001",)))


def evaluate(rows, forecasts=None, target="APPROVAL", **kwargs):
    return evaluate_target(rows, forecasts or [], target, **{**WINDOW, **kwargs})


def test_approval_and_crl_have_opposite_labels_and_reuse_math_without_release():
    approved, crl = case(), case(2, action="COMPLETE_RESPONSE")
    a = evaluate([approved, crl], [forecast(approved), forecast(crl, p=0.2)])
    c = evaluate([approved, crl], [forecast(approved, "CRL", 0.2), forecast(crl, "CRL", 0.8)], "CRL")
    for result in (a, c):
        assert result["eligibleReviewCycles"] == 2
        assert result["researchMetrics"]["brierScore"] == pytest.approx(0.04)
        assert result["researchMetrics"]["logLoss"] == pytest.approx(-log(0.8))
        assert result["researchMetrics"]["accuracyWilson95"] is not None
        assert result["modelValidated"] is False
        assert result["prediction"] == "ABSTAIN"
        assert result["certainty"] == "NOT_VALIDATED" and result["accuracy"] == "NOT_CALIBRATED"
        assert result["sourceTruthVerifiedByThisCode"] is False
        assert result["calibrationConfidenceInterval"] is None
        assert all("observedEventRate" in b and "observedApprovalRate" not in b
                   for b in result["researchMetrics"]["calibrationBins"])


def test_delay_is_a_separate_documented_target_and_can_exist_without_action():
    first = replace(case(), action="POSTPONED", action_on=None, action_source=None,
                    delay=ReviewDelayEvidence(D("2022-05-01"), D("2021-12-01"),
                        "DOCUMENTED_EXTENSION", source("2022-04-02"),
                        extension_on=D("2022-04-01"), revised_goal_on=D("2022-08-01"),
                        independently_adjudicated=True, original_goal_source=source("2021-12-01")))
    second = replace(case(2, action="COMPLETE_RESPONSE"),
                     delay=ReviewDelayEvidence(D("2022-07-01"), D("2021-12-01"),
                         "NO_EXTENSION_CONFIRMED", source(),
                         complete_event_history_through=D("2022-07-01"),
                         independently_adjudicated=True, original_goal_source=source("2021-12-01")))
    delay = evaluate([first, second], [forecast(first, "REVIEW_DELAY", 0.9),
                                      forecast(second, "REVIEW_DELAY", 0.1)], "REVIEW_DELAY")
    assert delay["eligibleReviewCycles"] == 2
    assert delay["researchMetrics"]["brierScore"] == pytest.approx(0.01)
    action = evaluate([first, second])
    assert action["eligibleReviewCycles"] == 1
    assert action["excluded"]["missing_original_source"] == 1


@pytest.mark.parametrize("delay", [None,
    ReviewDelayEvidence(D("2022-07-01"), D("2021-12-01"), "UNRESOLVED", source(),
                        independently_adjudicated=True),
    ReviewDelayEvidence(D("2022-07-01"), D("2021-12-01"), "NO_EXTENSION_CONFIRMED", source(),
                        independently_adjudicated=True),
])
def test_missing_or_unresolved_extension_evidence_is_never_a_negative_label(delay):
    result = evaluate([replace(case(), delay=delay)], target="REVIEW_DELAY")
    assert result["eligibleReviewCycles"] == 0
    assert result["researchMetrics"]["brierScore"] is None
    assert result["researchMetrics"]["accuracy"] is None


@pytest.mark.parametrize("change", [
    {"cohort_complete_verified": False}, {"independently_adjudicated": False},
    {"action_source": None}, {"action": "WITHDRAWN"}, {"action": "UNRESOLVED"},
    {"action_source": source("2024-01-01")},
])
def test_incomplete_cohorts_unreviewed_labels_and_censoring_are_excluded(change):
    result = evaluate([replace(case(), **change)])
    assert result["eligibleReviewCycles"] == 0
    assert sum(result["excluded"].values()) == 1


@pytest.mark.parametrize("changes", [
    {"predicted_on": D("2022-06-01")},
    {"features_as_of": D("2022-01-11")},
    {"model_frozen_on": D("2022-01-02")},
    {"latest_training_label_public_on": D("2021-11-15")},
    {"fitted_through": D("2022-01-01")},
])
def test_future_label_model_selection_and_feature_leakage_are_rejected(changes):
    row = case()
    with pytest.raises(ValueError, match="chronology|precede"):
        evaluate([row], [replace(forecast(row), **changes)])


def test_program_holdout_prevents_same_family_training_leakage():
    row = case()
    with pytest.raises(ValueError, match="program"):
        evaluate([row], [replace(forecast(row), training_program_ids=frozenset(("HELDOUT-A",)))])
    with pytest.raises(ValueError, match="Freeze"):
        evaluate([row], holdout_frozen_on=D("2022-02-01"))


def test_training_application_cannot_evade_holdout_with_different_program_alias():
    row = case()
    with pytest.raises(ValueError, match="Training applications"):
        evaluate([row], [replace(forecast(row), training_application_ids=frozenset((row.identity.application_id,)))])
    later = replace(row, identity=replace(row.identity, review_cycle=2, program_id="DIFFERENT-PROGRAM"))
    with pytest.raises(ValueError, match="canonical program"):
        evaluate([row, later])


def test_forecast_cannot_borrow_another_indication_or_target_or_duplicate_cycle():
    row = case()
    other = replace(row.identity, indication_id="DIFFERENT-INDICATION")
    with pytest.raises(ValueError, match="identity"):
        evaluate([row], [replace(forecast(row), identity=other)])
    with pytest.raises(ValueError, match="target"):
        evaluate([row], [forecast(row, "CRL")])
    with pytest.raises(ValueError, match="Duplicate"):
        evaluate([row, replace(row, identity=other)])


def test_earliest_program_cycle_retains_abstention_independent_of_input_order():
    early = case()
    later = replace(early, identity=replace(early.identity, review_cycle=2), action_on=D("2022-09-01"),
                    action_source=source("2022-09-02"))
    forecasts = [forecast(early, p=None), forecast(later)]
    a = evaluate([early, later], forecasts)
    b = evaluate([later, early], forecasts)
    assert a == b
    assert a["eligibleReviewCycles"] == 1
    assert a["researchMetrics"]["predictedCount"] == 0
    assert a["researchMetrics"]["abstainedCount"] == 1
    assert a["excluded"]["repeated_application_or_program"] == 1


def test_empty_real_evidence_yields_no_performance_measurement():
    result = evaluate([], held_out_program_ids=frozenset())
    assert result["eligibleReviewCycles"] == 0
    assert result["researchMetrics"]["coverage"] is None
    assert result["researchMetrics"]["logLoss"] is None
    assert result["prediction"] == "ABSTAIN"


def test_delay_forecast_must_precede_extension_and_use_known_original_goal():
    row = replace(case(), delay=ReviewDelayEvidence(D("2022-05-01"), D("2022-01-07"),
        "DOCUMENTED_EXTENSION", source("2022-04-02"), extension_on=D("2022-04-01"),
        revised_goal_on=D("2022-08-01"), independently_adjudicated=True,
        original_goal_source=source("2022-01-07")))
    with pytest.raises(ValueError, match="publicly known"):
        evaluate([row], [forecast(row, "REVIEW_DELAY")], "REVIEW_DELAY")
    with pytest.raises(ValueError, match="precede"):
        evaluate([row], [replace(forecast(row, "REVIEW_DELAY"), predicted_on=D("2022-04-01"))], "REVIEW_DELAY")


@pytest.mark.parametrize("probability", [True, float("nan"), float("inf"), -0.1, 1.1])
def test_invalid_or_fabricated_probability_values_fail_closed(probability):
    row = case()
    with pytest.raises(ValueError, match="finite"):
        evaluate([row], [forecast(row, p=probability)])


def test_delay_original_target_needs_its_own_public_source_receipt():
    delay = ReviewDelayEvidence(D("2022-05-01"), D("2021-12-01"),
        "DOCUMENTED_EXTENSION", source("2022-04-02"), extension_on=D("2022-04-01"),
        revised_goal_on=D("2022-08-01"), independently_adjudicated=True)
    result = evaluate([replace(case(), delay=delay)], target="REVIEW_DELAY")
    assert result["eligibleReviewCycles"] == 0
    assert result["excluded"] == {"original_goal_source_missing_or_inconsistent": 1}


def test_source_origin_and_application_identity_fail_closed():
    row = case()
    with pytest.raises(ValueError, match="Canonical application"):
        evaluate([replace(row, identity=replace(row.identity, application_id=None))])
    for url in ("https://accessdata.fda.gov:0/fake.pdf", "https://@accessdata.fda.gov/fake.pdf",
                "https://accessdata.fda.gov.attacker.example/fake.pdf"):
        result = evaluate([replace(row, action_source=replace(source(), url=url))])
        assert result["eligibleReviewCycles"] == 0
        assert result["excluded"] == {"invalid_original_source_receipt": 1}
