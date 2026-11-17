"""Synthetic Level 15 historical precedent and Level 16 manufacturing safeguards."""
from app.scientific_levels_nine_to_twenty import assess_levels_nine_to_twenty
from test_scientific_regulatory_context import app, evidence as filing_evidence, official
from test_scientific_levels_nine_to_twenty import NCT, intake


def precedent():
    return {"applicationType": "BLA", "applicationNumber": "654321", "reviewCycle": 2,
            "indication": "Similar fictional disease", "modality": "Biologic",
            "officialAction": "COMPLETE_RESPONSE", "officialActionDate": "2026-01-02"}


def inspect():
    return {"applicationType": "NDA", "applicationNumber": "123456", "reviewCycle": 1,
            "publicInformation": "PUBLIC_RECORD_EXISTS", "facilityIdentifier": "SYNTHETIC-FACILITY",
            "checkedAt": "2026-01-27"}


def assess(data):
    return assess_levels_nine_to_twenty(intake(), trial_id=NCT, evidence=data)


def test_prior_action_is_not_a_target_prediction():
    data = filing_evidence()
    data["15.precedentSelection"] = official(precedent())
    result = assess(data)["15"]["precedentContext"]
    assert result["status"] == "HISTORICAL_PRECEDENT_SOURCE_ONLY"
    assert result["officialAction"] == "COMPLETE_RESPONSE"
    assert result["precedentPredictsTargetOutcome"] is False
    assert result["clinicalComparability"] == "NOT_ESTABLISHED"
    assert result["fdaPrediction"] == "ABSTAIN"


def test_same_application_different_cycle_cannot_enter_precedents():
    data = filing_evidence()
    data["15.precedentSelection"] = official({
        **precedent(), "applicationType": "NDA", "applicationNumber": "123456"
    })
    assert assess(data)["15"]["precedentContext"]["status"] == "REJECTED_PRECEDENT"


def test_future_action_and_unofficial_prior_source_rejected():
    data = filing_evidence()
    data["15.precedentSelection"] = official({
        **precedent(), "officialActionDate": "2026-04-01"
    })
    assert assess(data)["15"]["precedentContext"]["status"] == "REJECTED_PRECEDENT"
    data["15.precedentSelection"] = official(precedent())
    data["15.precedentSelection"]["source"] = "https://issuer.example/pr"
    assert assess(data)["15"]["precedentContext"]["status"] == "NOT_ASSESSED"


def test_missing_filing_never_maps_precedent_by_company():
    result = assess({"15.precedentSelection": official(precedent())})["15"]["precedentContext"]
    assert result["status"] == "NOT_ASSESSED"


def test_public_inspection_lead_does_not_mean_deficiency():
    data = filing_evidence()
    data["16.inspectionEvidence"] = official(inspect())
    result = assess(data)["16"]["manufacturingContext"]
    assert result["status"] == "PUBLIC_RECORD_REVIEW_REQUIRED"
    assert result["inspectionDeficiencyEstablished"] is False
    assert result["manufacturingRiskJudgment"] is None
    assert result["fdaPrediction"] == "ABSTAIN"


def test_unpublished_inspection_does_not_count_as_deficiency():
    data = filing_evidence()
    value = {**inspect(), "publicInformation": "PUBLIC_RECORD_UNAVAILABLE"}
    data["16.inspectionEvidence"] = official(value)
    result = assess(data)["16"]["manufacturingContext"]
    assert result["status"] == "NONPUBLIC_OR_UNAVAILABLE_REMAINS_UNKNOWN"
    assert result["informationAvailability"] == "PUBLIC_RECORD_UNAVAILABLE"
    assert result["inspectionDeficiencyEstablished"] is False


def test_application_mismatch_or_bad_chronology_rejected():
    for mutation, status in [
        ({"applicationNumber": "654321"}, "REJECTED_APPLICATION_LINK"),
        ({"checkedAt": "2026-04-01"}, "REJECTED_CHRONOLOGY"),
        ({"facilityIdentifier": ""}, "REJECTED_MEASUREMENTS"),
    ]:
        data = filing_evidence()
        data["16.inspectionEvidence"] = official({**inspect(), **mutation})
        assert assess(data)["16"]["manufacturingContext"]["status"] == status


def test_nonpublic_unknown_not_auto_inferred_as_pass():
    data = filing_evidence()
    result = assess(data)["16"]["manufacturingContext"]
    assert result["status"] == "NO_REVIEWED_PUBLIC_INSPECTION_RECORD"
    assert result["inspectionDeficiencyEstablished"] is False
