from copy import deepcopy
from datetime import date

import pytest

from app.archive_readiness import INVENTORY_FLAGS, study_readiness


TODAY = date(2026, 10, 30)


def example():
    return {
        "protocolSection": {
            "designModule": {"phases": ["PHASE2", "PHASE3"]},
            "oversightModule": {"isFdaRegulatedDrug": True},
            "armsInterventionsModule": {"interventions": [{"type": "BIOLOGICAL", "name": "Investigational antibody"}]},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Sponsor"}},
            "statusModule": {
                "primaryCompletionDateStruct": {"type": "ACTUAL", "date": "2026-09-01"},
                "completionDateStruct": {"type": "ACTUAL", "date": "2026-10-01"},
            },
            "identificationModule": {"secondaryIdInfos": [{"id": "IND 123456", "domain": "FDA"}]},
        },
        "resultsSection": {
            "outcomeMeasuresModule": {"outcomeMeasures": [{
                "title": "Overall Survival", "type": "PRIMARY",
                "classes": [{"categories": [{"measurements": [{"groupId": "G1", "value": "12.5"}]}]}],
                "analyses": [{"pValue": "<0.001", "statisticalMethod": "Log-rank"}],
            }]},
            "adverseEventsModule": {"seriousEvents": [{"term": "Infection", "stats": [{"numAffected": 0, "numAtRisk": 100}]}]},
        },
    }


def test_all_screen_fields_present_without_approval_inference():
    source = example()
    original = deepcopy(source)
    flags = study_readiness(source, today=TODAY)
    assert flags["scientific_ready"] is True
    assert flags["regulatory_identifier_candidates"] is True
    assert flags["verifiable_regulatory_identifiers"] is False
    assert flags["regulatory_outcome_evidence"] is False
    assert source == original
    assert set(flags) == set(INVENTORY_FLAGS)
    assert all(isinstance(value, bool) for value in flags.values())


@pytest.mark.parametrize("study", [{}, None, {"protocolSection": None, "resultsSection": []}, {"protocolSection": {"designModule": {"phases": [{}]}}}])
def test_missing_or_malformed_fields_do_not_count(study):
    assert not any(study_readiness(study, today=TODAY).values())


def test_primary_outcome_alone_is_not_efficacy():
    source = example()
    source["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["title"] = "Plasma concentration"
    flags = study_readiness(source, today=TODAY)
    assert not flags["reported_efficacy_results"]
    assert not flags["scientific_ready"]


def test_labels_without_numeric_outcomes_do_not_count():
    source = example()
    outcome = source["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]
    outcome["classes"] = []
    assert not study_readiness(source, today=TODAY)["reported_efficacy_results"]
    source["resultsSection"]["adverseEventsModule"] = {"seriousEvents": [], "otherEvents": []}
    assert not study_readiness(source, today=TODAY)["adverse_event_information"]
    assert not study_readiness(source, today=TODAY)["reported_safety_results"]


@pytest.mark.parametrize("value,expected", [("0", True), (0, True), ("<0.05", True), ("1e-5", True), ("1.1", False), ("N/A", False), (True, False), ("NaN", False)])
def test_p_values_are_numeric_and_bounded(value, expected):
    source = example()
    source["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["analyses"][0]["pValue"] = value
    assert study_readiness(source, today=TODAY)["reported_p_values"] is expected


@pytest.mark.parametrize("date_struct,expected", [
    ({"type": "ESTIMATED", "date": "2020-01-01"}, False),
    ({"type": "ACTUAL", "date": "2026-11-01"}, False),
    ({"type": "ACTUAL", "date": "2026-10"}, False),
    ({"type": "ACTUAL", "date": "2026-09"}, True),
    ({"type": "ACTUAL", "date": "2026"}, False),
    ({"type": "ACTUAL", "date": "2025"}, True),
    ({"type": "ACTUAL", "date": "2026-02-30"}, False),
    ({"type": "ACTUAL", "date": "2026-10-30"}, True),
])
def test_actual_completion_dates(date_struct, expected):
    source = example()
    source["protocolSection"]["statusModule"]["primaryCompletionDateStruct"] = date_struct
    assert study_readiness(source, today=TODAY)["completed_primary_endpoints"] is expected


def test_string_true_and_device_do_not_establish_drug_regulation():
    source = example()
    source["protocolSection"]["oversightModule"]["isFdaRegulatedDrug"] = "true"
    assert not study_readiness(source, today=TODAY)["fda_regulated_drug_or_biological"]
    source["protocolSection"]["oversightModule"]["isFdaRegulatedDrug"] = True
    source["protocolSection"]["armsInterventionsModule"]["interventions"][0]["type"] = "DEVICE"
    assert not study_readiness(source, today=TODAY)["fda_regulated_drug_or_biological"]


def test_completed_phase4_is_not_regulatory_outcome_evidence():
    source = example()
    source["protocolSection"]["designModule"]["phases"] = ["PHASE4"]
    source["protocolSection"]["statusModule"]["overallStatus"] = "COMPLETED"
    assert not study_readiness(source, today=TODAY)["regulatory_outcome_evidence"]
