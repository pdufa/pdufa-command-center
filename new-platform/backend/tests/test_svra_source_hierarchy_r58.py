"""R58 mechanistic arithmetic tests only; never clinical/FDA validation."""
from decimal import Decimal
import pytest
from scripts.audit_svra_source_hierarchy_r58 import (
    GATES, NON_JP_KR_WEEK24, NON_JP_KR_WEEK48,
    hochberg_passed, research_readout,
)


def test_savara_non_japan_korea_hierarchical_family_arithmetic():
    output = research_readout()
    group = output["outsideJapanSouthKorea"]
    assert Decimal(GATES["DLCO_WEEK24"]) < Decimal("0.05")
    assert Decimal(GATES["DLCO_WEEK48"]) < Decimal("0.05")
    assert group["week24DlcoGatePassesPublishedPThreshold"] is True
    assert group["week48DlcoGatePassesPublishedPThreshold"] is True
    assert group["week24HochbergNamesPassingPublishedThresholds"] == ["SGRQ_TOTAL"]
    assert group["week48HochbergNamesPassingPublishedThresholds"] == []
    assert set(NON_JP_KR_WEEK24) == set(NON_JP_KR_WEEK48)


def test_japan_south_korea_family_missing_authenticated_aa_do2():
    output = research_readout()
    region = output["japanSouthKorea"]
    assert region["sourceConfirmedPrespecifiedAaDo2P"] is None
    assert region["confirmedFamilyVerdict"] == "UNDETERMINED"
    # Exploratory arithmetic is not a verified regulator result:
    conditional = dict(NON_JP_KR_WEEK24, AA_DO2="0.1043")
    assert hochberg_passed(conditional, "0.05") == [
        "SGRQ_ACTIVITY", "SGRQ_TOTAL"
    ]
    assert output["independentlyValidatedFdaPredictions"] == 0
    assert output["officialApprovalCrlForecast"] == "ABSTAIN"
    assert output["officialReviewTimingForecast"] == "ABSTAIN"
    assert output["fdaApprovalProbability"] is None
    assert output["clinicalReviewerSignoff"] is False
    assert output["modelTrainingAuthorized"] is False
    assert output["clinicalOrProductionWritesAuthorized"] is False


@pytest.mark.parametrize("values,alpha", [
    ({}, "0.05"), ({"x": "NaN"}, "0.05"),
    ({"x": "1.01"}, "0.05"), ({"x": "-0.01"}, "0.05"),
    ({"x": "0.01"}, "0"), ({"x": "0.01"}, "1"),
])
def test_invalid_source_inputs_are_rejected(values, alpha):
    with pytest.raises(ValueError):
        hochberg_passed(values, alpha)
