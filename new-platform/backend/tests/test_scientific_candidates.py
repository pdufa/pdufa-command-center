"""Evidence facts must remain distinct from scientific or regulatory conclusions."""
import copy
import importlib.util
import json
from pathlib import Path

import pytest

_PATH = Path(__file__).parents[1] / "app" / "scientific_candidates.py"
_SPEC = importlib.util.spec_from_file_location("scientific_candidates", _PATH)
module = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(module)
build_dossier = module.build_dossier
STAMP = "2026-10-30T14:00:00+00:00"


@pytest.fixture
def study():
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT01234567", "briefTitle": "A quantitative Phase3 trial",
                                     "secondaryIdInfos": [{"id": "IND 123456", "type": "OTHER", "domain": "FDA"}]},
            "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Sponsor A", "class": "INDUSTRY"}},
            "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "Investigational Product"}]},
            "conditionsModule": {"conditions": ["Example disease"]}, "designModule": {"phases": ["PHASE3"]},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Overall Survival", "timeFrame": "24 months"}]},
            "statusModule": {"overallStatus": "COMPLETED", "completionDateStruct": {"type": "ACTUAL", "date": "2025-01-01"},
                             "primaryCompletionDateStruct": {"type": "ACTUAL", "date": "2024-12-01"}},
        },
        "resultsSection": {
            "outcomeMeasuresModule": {"outcomeMeasures": [{
                "type": "PRIMARY", "title": "Overall Survival", "unitOfMeasure": "months", "groups": [{"id": "G1", "title": "A"}, {"id": "G2", "title": "B"}],
                "classes": [{"categories": [{"measurements": [{"groupId": "G1", "value": "12.3"}, {"groupId": "G2", "value": "10.0"}]}]}],
                "analyses": [{"groupIds": ["G1", "G2"], "statisticalMethod": "Log rank", "pValue": "<0.05",
                              "paramType": "Hazard Ratio", "paramValue": "0.7", "ciPctValue": "95", "ciLowerLimit": "0.5", "ciUpperLimit": "0.9"}],
            }]},
            "adverseEventsModule": {"eventGroups": [{"id": "G1", "title": "A", "seriousNumAffected": 0, "seriousNumAtRisk": 100}],
                                    "seriousEvents": [{"term": "Hospitalization", "organSystem": "General", "stats": [{"groupId": "G1", "numAffected": 0, "numAtRisk": 100}]}]},
        },
    }


def dossier(study, live=None, **kwargs):
    return build_dossier(study, copy.deepcopy(study) if live is None else live, verified_at=STAMP, **kwargs)


def supported(field, value):
    return {"status": "VERIFIED", "nct_id": "NCT01234567", "source_type": "FDA",
            "source_url": "https://www.fda.gov/example-exact-trial-source", "source_document_sha256": "b" * 64,
            "verified_at": "2026-10-29T12:00:00+00:00", "value": value}


def all_external():
    return {field: supported(field, "2026-12-01" if field == "pdufa_date" else {"finding": "Source-scoped fact"})
            for field in ("fda_regulatory_pathway", "special_designations", "regulatory_submission_evidence", "pdufa_date")}


def test_complete_registry_record_is_reluctant_without_regulatory_sources(study):
    d = dossier(study)
    assert d["independently_checked"] is True
    assert d["readiness"] == "RELUCTANT"
    assert d["critical_missing"] == []
    assert d["additional_external_evidence_required"] is True
    assert d["pdufa_date"]["value"] is None
    assert d["fda_regulatory_pathway"]["status"] == "UNRESOLVED"
    assert len(d["checklist"]) == 20
    assert {x["field"] for x in d["checklist"]} == set(module.CHECKLIST_FIELDS)


def test_primary_analyses_preserve_values_without_claiming_significance(study):
    d = dossier(study)
    analysis = d["statistical_significance"]["reported_primary_analyses"][0]
    assert analysis["groupIds"] == ["G1", "G2"]
    assert analysis["parsed_p_value"] == {"qualifier": "<", "value": 0.05}
    assert analysis["ciLowerLimit"] == "0.5"
    assert d["statistical_significance"]["interpretation"] == "NOT_INFERRED"
    assert d["clinical_effect_size"]["clinical_meaningfulness"] == "NOT_ADJUDICATED"
    assert next(r for r in d["checklist"] if r["field"] == "statistical_significance")["status"] == "REPORTED_NOT_ADJUDICATED"


def test_secondary_statistics_do_not_fill_primary_endpoint_gap(study):
    primary = study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]
    secondary = copy.deepcopy(primary)
    secondary["type"] = "SECONDARY"
    primary["analyses"] = []
    study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"].append(secondary)
    d = dossier(study)
    assert d["statistical_significance"]["valid_p_values_reported"] == 0
    assert d["clinical_effect_size"]["reported_comparative_estimates"] == []


@pytest.mark.parametrize("invalid", ["NR", "NaN", "-0.1", "1.5", True, None])
def test_invalid_p_values_never_count_as_statistical_evidence(study, invalid):
    study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["analyses"][0]["pValue"] = invalid
    assert dossier(study)["statistical_significance"]["valid_p_values_reported"] == 0


def test_missing_primary_quantitative_results_is_not_ready(study):
    study["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["classes"] = []
    d = dossier(study)
    assert d["readiness"] == "NOT READY"
    assert "primary_endpoint_results" in d["critical_missing"]


def test_missing_serious_adverse_events_is_not_favorable(study):
    study["resultsSection"]["adverseEventsModule"] = {}
    d = dossier(study)
    assert d["readiness"] == "NOT READY"
    assert "serious_adverse_events" in d["critical_missing"]
    assert d["serious_adverse_events"]["reported"] is False


def test_reported_zero_serious_events_are_retained_with_denominator(study):
    d = dossier(study)
    assert d["serious_adverse_events"]["reported"] is True
    assert d["serious_adverse_events"]["positive_denominator_reported"] is True
    assert d["serious_adverse_events"]["group_totals"][0]["seriousNumAffected"] == 0


def test_live_identity_mismatch_is_not_ready_and_not_independently_checked(study):
    live = copy.deepcopy(study)
    live["protocolSection"]["identificationModule"]["nctId"] = "NCT99999999"
    d = dossier(study, live)
    assert d["readiness"] == "NOT READY"
    assert d["independently_checked"] is False
    assert d["conflicts"][0]["severity"] == "CRITICAL"


def test_archive_only_is_not_independent_verification(study):
    d = build_dossier(study, verified_at=STAMP, source_status="UNAVAILABLE")
    assert d["independently_checked"] is False
    assert d["readiness"] == "RELUCTANT"
    assert d["provenance"][1]["status"] == "UNAVAILABLE"
    assert d["scientific_assessment_eligibility"]["existing_science40_gate_satisfied"] is False


def test_changed_sponsor_is_documented_without_assuming_transfer(study):
    live = copy.deepcopy(study)
    live["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"] = "Sponsor B"
    d = dossier(study, live)
    assert d["sponsor"]["name"] == "Sponsor B"
    assert d["conflicts"][0]["field"] == "sponsor"
    assert d["readiness"] == "RELUCTANT"


def test_supported_sources_can_prepare_ready_intake_but_complete_zero_investigations(study):
    d = dossier(study, external_evidence=all_external())
    assert d["readiness"] == "READY"
    assert d["scientific_assessment_eligibility"]["existing_science40_gate_satisfied"] is True
    assert d["scientific_assessment_eligibility"]["science40_execution_authorized"] is False
    assert d["framework_handoff"]["assessments_completed"] == 0
    assert d["framework_handoff"]["investigation_depths_completed"] == 0
    assert len(d["framework_handoff"]["layers"]) == 8
    assert len(d["framework_handoff"]["assessment_ids"]) == 40
    assert len(d["framework_handoff"]["investigation_depth_levels"]) == 20
    assert d["approval_probability"] is None
    assert d["regulatory_outcome_prediction"] is None
    assert d["trade_authorized"] is False


@pytest.mark.parametrize("change", [
    {"nct_id": "NCT99999999"}, {"source_url": "https://not-fda.example/document"},
    {"source_document_sha256": None}, {"verified_at": "2030-01-01T00:00:00+00:00"},
    {"verified_at": "2026-10-29"}, {"status": "SOURCE_LEAD"}, {"value": "not-a-date"},
])
def test_unscoped_unread_future_or_invalid_pdufa_sources_are_rejected(study, change):
    evidence = all_external()
    evidence["pdufa_date"].update(change)
    d = dossier(study, external_evidence=evidence)
    assert d["pdufa_date"]["status"] == "UNRESOLVED"
    assert d["pdufa_date"]["value"] is None
    assert d["readiness"] == "RELUCTANT"


def test_fda_product_lookup_is_not_trial_specific_regulatory_evidence(study):
    lookup = {"status": "FETCHED", "source_url": "https://api.fda.gov/drug/drugsfda.json", "checked_at": STAMP,
              "applications": [{"application_number": "NDA123456", "sponsor_name": "Sponsor A"}]}
    d = dossier(study, external_evidence={"fda_lookup": lookup})
    assert d["fda_product_lookup"]["applications"][0]["application_number"] == "NDA123456"
    assert d["fda_regulatory_pathway"]["status"] == "UNRESOLVED"
    assert d["pdufa_date"]["value"] is None
    assert any(r["source_type"] == "FDA_PRODUCT_LOOKUP" for r in d["provenance"])


def test_regulatory_candidate_preserves_exact_raw_id_without_verifying_it(study):
    found = module.extract_regulatory_identifiers(study)
    assert found == [{"nct_id": "NCT01234567", "identifier": "IND 123456", "identifier_type": "IND",
                      "identifier_number": "123456", "raw_secondary_id": {"id": "IND 123456", "type": "OTHER", "domain": "FDA"},
                      "source_field": "protocolSection.identificationModule.secondaryIdInfos[0]", "classification": "UNRESOLVED"}]


def test_pdufa_date_is_never_inferred_from_fda_flag_or_phase(study):
    study["protocolSection"]["oversightModule"] = {"isFdaRegulatedDrug": True}
    d = dossier(study)
    assert d["pdufa_date"]["value"] is None
    assert d["special_designations"]["value"] is None
    assert d["regulatory_submission_evidence"]["value"] is None


@pytest.mark.parametrize("date_value", [{"type": "ESTIMATED", "date": "2025-01-01"}, {"type": "ACTUAL", "date": "2028-01-01"}, {}])
def test_planned_future_or_missing_completion_never_makes_ready(study, date_value):
    study["protocolSection"]["statusModule"]["completionDateStruct"] = date_value
    d = dossier(study, external_evidence=all_external())
    assert d["readiness"] == "RELUCTANT"
    assert d["study_completion_status"]["study_completion_actual_elapsed"] is False


@pytest.mark.parametrize("invalid", [None, {}, {"protocolSection": []}, {"protocolSection": {"identificationModule": {"nctId": 1}}}])
def test_malformed_records_have_no_invented_evidence(invalid):
    d = build_dossier(invalid, verified_at=STAMP)
    assert d["readiness"] == "NOT READY"
    assert not d["independently_checked"]
    assert d["products"] == []
    assert d["pdufa_date"]["value"] is None


def test_dossier_serializes_and_does_not_mutate_sources(study):
    original = copy.deepcopy(study)
    d = dossier(study, archived_sha256="a" * 64, live_sha256="c" * 64)
    json.dumps(d, allow_nan=False)
    assert study == original
    assert d["provenance"][0]["stored_payload_sha256"] == "a" * 64
    assert d["provenance"][1]["document_sha256"] == "c" * 64


def test_naive_or_invalid_verification_timestamp_is_rejected(study):
    with pytest.raises(ValueError):
        build_dossier(study, verified_at="2026-10-30")
