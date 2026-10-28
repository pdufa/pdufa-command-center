"""All fixtures are SYNTHETIC, not actual FDA-verified cycles or model accuracy."""
from datetime import date
import pytest

from app.hop_backtest import walk_forward_backtest
from app.hop_outcome_cohort import OutcomeObservation

CUTS = [date(2020, 1, 1), date(2021, 1, 1), date(2022, 1, 1)]


def case(app, year, outcome="APPROVED", *, snapshot_year=None,
         source="COMPLETE_APPLICATION_COHORT"):
    # Synthetic metadata and fictional verified labels exclusively exercise
    # the split, never form model-eligible real FDA decision source records.
    return OutcomeObservation(
        application_id=app, review_cycle=1, decision_date=date(year, 6, 1),
        outcome=outcome, ascertainment_source=source, cohort_id="SYNTHETIC",
        public_features_as_of=date(snapshot_year or year, 1, 1),
        cohort_complete_verified=True, outcome_public_as_of=date(year, 6, 1),
    )


def test_all_historical_sibling_program_labels_purged_from_training():
    rows = [
        case("B1", 2018),       # unrelated training family
        case("A1", 2019),       # earlier same family as test: MUST NEVER train
        case("B2", 2019),
        case("A2", 2020, "COMPLETE_RESPONSE"),
    ]
    family = {"A1": "FAMILY_A", "A2": "FAMILY_A",
              "B1": "FAMILY_B", "B2": "FAMILY_B"}
    seen = []

    def score(training, masked_case):
        assert masked_case.outcome == "WITHHELD"
        assert masked_case.application_id == "A2"
        seen.extend(x.application_id for x in training)
        return 0.3

    folds = walk_forward_backtest(
        rows, CUTS, score, min_train=1,
        program_group_by_application=family,
        heldout_program_groups={"FAMILY_A"},
    )
    assert seen == ["B1", "B2"]
    assert folds[0].train_count == 2
    assert folds[0].test_count == 1
    assert folds[0].eligible_test_count == 1
    assert folds[0].brier_score == pytest.approx(0.09)
    assert folds[0].family_holdout_audit["allSelectedProgramGroupsExcludedFromTraining"] is True
    assert folds[0].family_holdout_audit["mappingIndependentlyAdjudicated"] is False
    assert folds[0].independent_fda_validation_complete is False
    assert folds[0].research_metrics["modelHistoricallyValidated"] is False
    assert folds[1].test_count == 0


def test_first_eligible_program_member_only_across_folds_and_abstentions():
    rows = [
        case("C1", 2019),  # unrelated training cohort
        case("A1", 2020, "APPROVED"),
        case("A2", 2020, "COMPLETE_RESPONSE"),  # later sibling same year
        case("A3", 2021, "APPROVED"),  # cannot reuse family in following year
    ]
    families = {"C1": "CONTROL", "A1": "STUDY",
                "A2": "STUDY", "A3": "STUDY"}
    called = []
    result = walk_forward_backtest(
        rows, CUTS, lambda train, case: called.append(case.application_id) or None,
        min_train=1, program_group_by_application=families,
        heldout_program_groups=frozenset({"STUDY"}),
    )
    assert called == ["A1"]
    assert result[0].eligible_test_count == 1
    assert result[0].abstained_test_count == 1
    assert result[0].excluded_test_count == 1
    assert result[1].eligible_test_count == 0
    assert result[1].excluded_test_count == 1
    assert result[0].family_holdout_audit["testProgramGroupsThisFold"] == ["STUDY"]
    assert result[1].family_holdout_audit["testProgramGroupsThisFold"] == []


def test_training_and_test_programs_must_be_preallocated_not_inferred_from_labels():
    rows = [case("CONTROL", 2019), case("HELDOUT", 2020)]
    families = {"CONTROL": "TRAIN_PROGRAM", "HELDOUT": "TEST_PROGRAM"}
    seen = []
    folds = walk_forward_backtest(
        rows, CUTS,
        lambda train, masked: seen.append(
            (tuple(t.application_id for t in train), masked.application_id)
        ) or 0.5,
        min_train=1, program_group_by_application=families,
        heldout_program_groups={"TEST_PROGRAM"},
    )
    assert seen == [(("CONTROL",), "HELDOUT")]
    assert folds[0].family_holdout_audit["prespecifiedGroupHoldoutMode"] is True
    assert folds[0].research_metrics["coverage"] == 1.0


@pytest.mark.parametrize("mapping,holdout,error", [
    (None, {"GROUP_X"}, "Complete"),
    ({"A": "GROUP_X", "B": "GROUP_Y"}, None, "explicit"),
    ({"A": "GROUP_X"}, {"GROUP_X"}, "Every application"),
    ({"A": "GROUP_X", "B": "GROUP_Y", "C": "GROUP_Z"}, {"GROUP_X"}, "Every application"),
    ({"A": "GROUP_X", "B": "GROUP_Y"}, {"UNSEEN"}, "nonempty proper subset"),
    ({"A": "GROUP_X", "B": "GROUP_Y"}, {"GROUP_X", "GROUP_Y"}, "nonempty proper subset"),
    ({"A": "GROUP_X", "B": "GROUP_Y"}, set(), "nonempty proper subset"),
    ({"A": "GROUP_X", "B": "GROUP_Y"}, ["GROUP_X"], "explicit"),
    ({"A": "GROUP_X", "B": "GROUP_Y"}, "GROUP_X", "explicit"),
    ({"A": "GROUP_X", "B": "GROUP_X"}, {"GROUP_X"}, "nonempty proper subset"),
    ({"A": "group x", "B": "GROUP_Y"}, {"GROUP_Y"}, "canonical"),
    ({"A": "", "B": "GROUP_Y"}, {"GROUP_Y"}, "canonical"),
    ({"A": None, "B": "GROUP_Y"}, {"GROUP_Y"}, "canonical"),
    ({"A": 7, "B": "GROUP_Y"}, {"GROUP_Y"}, "canonical"),
    ({"A": "GROUP_X", "B": "Y" * 81}, {"GROUP_X"}, "canonical"),
])
def test_unverified_or_malformed_family_map_rejected_prior_to_scoring(mapping, holdout, error):
    rows = [case("A", 2019), case("B", 2020)]
    def never(_, __):
        pytest.fail("Unvalidated grouping must fail before invoking scorer")
    with pytest.raises(ValueError, match=error):
        walk_forward_backtest(rows, CUTS, never, min_train=1,
                              program_group_by_application=mapping,
                              heldout_program_groups=holdout)


def test_ineligible_crl_publication_archive_does_not_train_or_count_as_test():
    rows = [
        case("R1", 2019, source="FDA_CRL_PUBLICATION"),
        case("TRAIN", 2019),
        case("HOLD", 2020, "COMPLETE_RESPONSE"),
    ]
    family = {"R1": "CRL_SAMPLE", "TRAIN": "TRAINING", "HOLD": "HOLDOUT"}
    seen = []
    folds = walk_forward_backtest(
        rows, CUTS, lambda train, _: seen.extend(x.application_id for x in train) or 0.4,
        min_train=1,
        program_group_by_application=family,
        heldout_program_groups={"HOLDOUT"},
    )
    assert seen == ["TRAIN"]
    assert folds[0].eligible_test_count == 1
    assert folds[0].family_holdout_audit["realFdaOutcomeCohortVerified"] is False


def test_legacy_application_level_mode_still_returns_no_family_validation_claim():
    rows = [case("OLD", 2019), case("NEW", 2020)]
    folds = walk_forward_backtest(rows, CUTS, lambda train, case: 0.5, min_train=1)
    assert folds[0].family_holdout_audit is None
    assert folds[0].independent_fda_validation_complete is False
    assert folds[0].research_metrics["modelHistoricallyValidated"] is False
