import pytest

from assessment_levels_07_20.isolated_dispatch import inspect_isolated_level


def test_all_fourteen_levels_are_addressable_and_abstain():
    for level in range(7, 21):
        result = inspect_isolated_level(level, {})
        assert result["level"] == level
        assert result["scientific_status"] == "NOT_VERIFIED"
        assert result["scientific_score"] is None
        assert result["fda_prediction"] == "ABSTAIN"


@pytest.mark.parametrize("level", [0, 1, 4, 6, 21, True, "7"])
def test_other_levels_rejected(level):
    with pytest.raises(ValueError):
        inspect_isolated_level(level, {})


def test_nonmapping_payload_rejected():
    with pytest.raises(TypeError):
        inspect_isolated_level(7, None)


def test_does_not_mutate_input():
    record = {"nct_id": "NCT04576949", "population": "Example", "cutoff_on": "2026-01-01"}
    before = dict(record)
    inspect_isolated_level(7, record)
    assert record == before
