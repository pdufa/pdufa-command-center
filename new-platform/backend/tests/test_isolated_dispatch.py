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


def test_dispatch_rejects_validator_level_identity_mismatch(monkeypatch):
    from assessment_levels_07_20 import isolated_dispatch

    monkeypatch.setitem(isolated_dispatch._VALIDATORS, 7, lambda record: {
        "level": 8, "scientific_status": "NOT_VERIFIED",
        "scientific_score": None, "fda_prediction": "ABSTAIN",
    })
    with pytest.raises(RuntimeError, match="level mismatch"):
        inspect_isolated_level(7, {})


@pytest.mark.parametrize("unsafe_result", [
    {"scientific_status": "VERIFIED", "scientific_score": None, "fda_prediction": "ABSTAIN"},
    {"scientific_status": "NOT_VERIFIED", "scientific_score": 99, "fda_prediction": "ABSTAIN"},
    {"scientific_status": "NOT_VERIFIED", "scientific_score": None, "fda_prediction": "APPROVAL"},
])
def test_dispatch_rejects_unsafe_scoring_or_prediction(monkeypatch, unsafe_result):
    from assessment_levels_07_20 import isolated_dispatch

    monkeypatch.setitem(isolated_dispatch._VALIDATORS, 7, lambda record: {
        "level": 7, **unsafe_result,
    })
    with pytest.raises(RuntimeError, match="fail closed"):
        inspect_isolated_level(7, {})


@pytest.mark.parametrize("malformed", [None, [], "invalid", 42])
def test_dispatch_fails_closed_on_nonmapping_validator_result(monkeypatch, malformed):
    from assessment_levels_07_20 import isolated_dispatch

    monkeypatch.setitem(isolated_dispatch._VALIDATORS, 7, lambda record: malformed)
    with pytest.raises(RuntimeError, match="fail closed"):
        inspect_isolated_level(7, {})
