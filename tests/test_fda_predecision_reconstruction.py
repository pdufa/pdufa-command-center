"""Synthetic trust-boundary checks, never independently observed FDA accuracy."""
from copy import deepcopy
from datetime import date, datetime, timedelta

import pytest

from research.fda_predecision_reconstruction import (
    PRIORITY_APPLICATIONS, QUESTION_IDS, audit_reconstructions,
)

AS_OF = date(2026, 10, 28)


def fixture():
    cases = []
    history = []
    actual_dates = {"NVAX": "2025-05-16", "UNCY": "2025-06-27", "BCRX": "2025-12-11"}
    for event, application in PRIORITY_APPLICATIONS.items():
        ticker, goal = event.split("|")
        action = actual_dates.get(ticker, goal)
        cutoff = min(date.fromisoformat(goal), date.fromisoformat(action)) - timedelta(days=1)
        history.append({"event_key": event, "ticker": ticker, "pdufa_date": goal})
        cases.append({
            "event_key": event, "application_id": application,
            "indication": "Fictitious test indication", "program_family": "Fictitious " + ticker,
            "legacy_goal_date": goal, "action_date": action,
            "reconstruction_cutoff": cutoff.isoformat(), "original_prediction_cutoff": None,
            "observations": [{
                "id": ticker + "-synthetic",
                "source_url": "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/synthetic-fixture.htm",
                "availability_source_url": "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/0000000001-25-000001-index.html",
                "available_on": "2024-01-01", "availability_basis": "SEC_FILING_INDEX",
                "source_role": "PREDECISION_RESEARCH", "finding": "Fictitious source assertion",
                "science_question_ids": ["S01", "S29"],
            }],
            "missing_documents": ["Actual independently reviewed original source"],
            "supporting_factors": ["Fictitious supporting assertion"],
            "opposing_factors": ["Fictitious opposing assertion"],
            "related_precedents": [], "prediction_provenance": {},
        })
    return {"schema_version": 1, "research_only": True, "cases": cases}, history


def evaluate(packet, history):
    return audit_reconstructions(packet, history, as_of=AS_OF)


def test_reconstruction_preserves_unknown_freeze_and_never_certifies_sources_or_predictions():
    packet, history = fixture()
    original = deepcopy(packet)
    report = evaluate(packet, history)
    assert packet == original
    assert report["priority_cases_analyzed"] == 6
    assert report["validated_cases"] == report["eligible_for_validation"] == 0
    assert all(value is None for value in report["metrics"].values())
    assert report["coverage_status"] == "NOT_MEASURED_NO_VALIDATED_FORECASTS"
    for case in report["case_reports"]:
        assert case["original_prediction_cutoff"] is None
        assert case["predecision_research_candidate_count"] == 1
        assert len(case["science_worklist"]) == 40
        assert [item["depth_level"] for item in case["depth_worklist"]] == list(range(1, 21))
        assert all(item["status"] == "NOT_CERTIFIED" for item in case["science_worklist"] + case["depth_worklist"])
        assert case["independently_certified_assessments"] == 0
        assert case["outcome"]["status"] == case["main"]["status"] == "INSUFFICIENT_EVIDENCE"
        assert case["outcome"]["pass_probability"] is case["outcome"]["fail_probability"] is None
        assert case["model_eligible"] is case["eligible_for_validation"] is False
        assert "original_prediction_cutoff_unavailable" in case["blockers"]


def test_goal_action_discrepancies_use_the_earlier_window_without_rewriting_history():
    packet, history = fixture()
    before = deepcopy(history)
    report = evaluate(packet, history)
    cutoffs = {case["event_key"].split("|")[0]: case["reconstruction_cutoff"] for case in report["case_reports"]}
    assert cutoffs == {"NVAX":"2025-03-31", "UNCY":"2025-06-26", "TNXP":"2025-08-14",
                       "BCRX":"2025-12-10", "CORT":"2025-12-29", "VNDA":"2025-12-29"}
    assert history == before


@pytest.mark.parametrize("ticker,bad_cutoff", [("UNCY","2025-06-27"),("BCRX","2025-12-11"),
                                               ("NVAX","2025-05-15")])
def test_goal_minus_one_or_eventual_action_minus_one_cannot_create_hindsight_window(ticker,bad_cutoff):
    packet, history = fixture()
    case = next(case for case in packet["cases"] if case["event_key"].startswith(ticker + "|"))
    case["reconstruction_cutoff"] = bad_cutoff
    with pytest.raises(ValueError,match="earlier goal/action"):
        evaluate(packet, history)


def test_late_unknown_and_printed_sources_cannot_enter_research_candidates():
    packet, history = fixture()
    case = packet["cases"][0]
    source = case["observations"][0]
    case["observations"] += [
        dict(source,id="late",available_on="2025-04-01"),
        dict(source,id="unknown",available_on=None,availability_basis="UNKNOWN"),
        dict(source,id="printed",availability_basis="PRINTED_DATE_ONLY"),
    ]
    result = evaluate(packet,history)["case_reports"][0]
    classifications = {item["source_id"]:item["classification"] for item in result["source_classification"]}
    assert classifications["late"] == "EXCLUDED_AFTER_RECONSTRUCTION_CUTOFF"
    assert classifications["unknown"] == "QUARANTINED_UNKNOWN_AVAILABILITY"
    assert classifications["printed"] == "QUARANTINED_PRINTED_DATE_ONLY"
    assert result["predecision_research_candidate_count"] == 1


def test_corrected_cort_action_document_is_never_a_predecision_feature_even_with_old_printed_date():
    packet,history = fixture()
    case = next(case for case in packet["cases"] if case["event_key"].startswith("CORT|"))
    case["observations"].append({
        "id":"corrected-fda-outcome", "source_url":"https://download.open.fda.gov/crl/CRL_NDA219398_20260128.pdf",
        "available_on":"2025-01-01", "availability_basis":"PRINTED_DATE_ONLY",
        "source_role":"OUTCOME_ONLY", "finding":"Synthetic corrected-action reference",
        "science_question_ids":["S29"],
    })
    result = next(case for case in evaluate(packet,history)["case_reports"] if case["event_key"].startswith("CORT|"))
    assert result["source_classification"][-1]["classification"] == "EXCLUDED_OUTCOME_ONLY"
    assert "corrected-fda-outcome" not in next(item for item in result["science_worklist"] if item["question_id"] == "S29")["source_ids"]


def test_different_six_case_lock_cannot_match_by_count():
    packet,history = fixture()
    packet["cases"][0]["prediction_provenance"] = {
        "model_hash":"a"*64, "lock_model_hash":"a"*64,
        "lock_event_keys":["BHVN|2025-05-14","FBIO|2025-01-06","NRXP|2025-01-27",
                           "NRXP|2025-08-13","OTLK|2025-11-13","OTLK|2025-12-31"],
    }
    result = evaluate(packet,history)["case_reports"][0]
    assert "prediction_lock_membership_mismatch" in result["blockers"]
    assert result["eligible_for_validation"] is False


def test_correct_membership_still_requires_matching_model_hash_and_independent_proof():
    packet,history = fixture()
    packet["cases"][0]["prediction_provenance"] = {
        "model_hash":"a"*64,"lock_model_hash":"b"*64,
        "lock_event_keys":list(PRIORITY_APPLICATIONS), "feature_snapshot_hash":"c"*64,
        "model_training_end":"2024-01-01", "model_frozen_at":"2024-02-01T00:00:00Z",
        "prediction_generated_at":"2024-03-01T00:00:00Z",
    }
    result = evaluate(packet,history)["case_reports"][0]
    assert "prediction_lock_model_hash_mismatch_or_missing" in result["blockers"]
    assert "original_prediction_freeze_not_independently_proven" in result["blockers"]
    assert result["eligible_for_validation"] is False


def test_larger_lock_may_link_a_case_without_certifying_its_forecast():
    packet,history = fixture()
    packet["cases"][0]["prediction_provenance"] = {
        "model_hash":"a"*64,"lock_model_hash":"a"*64,
        "lock_event_keys":list(PRIORITY_APPLICATIONS)+["SYNTHETIC|2025-01-01"]}
    result=evaluate(packet,history)["case_reports"][0]
    assert "prediction_lock_membership_mismatch" not in result["blockers"]
    assert result["eligible_for_validation"] is False


def test_supplied_2026_training_and_prediction_artifacts_cannot_validate_2025_forecast():
    packet,history = fixture()
    packet["cases"][0]["prediction_provenance"] = {
        "model_training_end":"2026-09-30", "model_frozen_at":"2026-10-04T03:16:07Z",
        "prediction_generated_at":"2026-10-04T05:11:23Z",
    }
    reasons = evaluate(packet,history)["case_reports"][0]["blockers"]
    assert "supplied_model_training_not_before_reconstruction_cutoff" in reasons
    assert "model_frozen_at_after_reconstruction_cutoff" in reasons
    assert "prediction_generated_at_after_reconstruction_cutoff" in reasons


@pytest.mark.parametrize("proof", [False,None])
def test_false_or_unknown_proof_flags_never_clear_validation(proof):
    packet,history = fixture()
    packet["cases"][0]["prediction_provenance"] = {
        "program_family_disjoint_verified":proof, "sampling_denominator_verified":proof,
        "independent_review_complete":proof,
    }
    assert evaluate(packet,history)["validated_cases"] == 0


@pytest.mark.parametrize("proof", [True,"true","false",1,0])
def test_self_certification_and_boolean_aliases_are_rejected(proof):
    packet,history = fixture()
    packet["cases"][0]["prediction_provenance"]["independent_review_complete"] = proof
    with pytest.raises(ValueError,match="self-certify"):
        evaluate(packet,history)


def test_probability_cannot_be_smuggled_through_packet():
    packet,history = fixture()
    packet["cases"][0]["approval_probability"] = .9
    with pytest.raises(ValueError,match="unvalidated probabilities"):
        evaluate(packet,history)


@pytest.mark.parametrize("url", ["https://www.sec.gov.attacker.example/claim", "https://www.sec.gov@attacker.example/x",
                                  "https://person@www.sec.gov/x", "https://www.sec.gov:8443/x",
                                  "http://www.sec.gov/x", "https://www.sec.gov/x#claim"])
def test_source_spoofing_is_rejected(url):
    packet,history = fixture()
    packet["cases"][0]["observations"][0]["source_url"] = url
    with pytest.raises(ValueError,match="official FDA or SEC"):
        evaluate(packet,history)


def test_fda_document_cannot_claim_sec_filing_index_availability():
    packet,history = fixture()
    packet["cases"][0]["observations"][0]["source_url"] = "https://www.fda.gov/media/123/download"
    with pytest.raises(ValueError,match="SEC filing-index"):
        evaluate(packet,history)


@pytest.mark.parametrize("index", [None,
    "https://www.sec.gov/Archives/edgar/data/1/000000000125000002/0000000001-25-000002-index.html",
    "https://www.sec.gov/Archives/edgar/data/2/000000000125000001/0000000001-25-000001-index.html",
    "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/synthetic-fixture.htm",
    "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/wrong-index.html",
    "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/0000000001-25-000001-index.html?claim=1",
    "https://www.sec.gov/Archives/edgar/data/1/000000000125000001/0000000001-25-000001-index.html#claim",
    "https://person@www.sec.gov/Archives/edgar/data/1/000000000125000001/0000000001-25-000001-index.html",
    "https://www.sec.gov:443/Archives/edgar/data/1/000000000125000001/0000000001-25-000001-index.html",
])
def test_sec_availability_requires_the_same_exact_filing_index(index):
    packet,history = fixture()
    observation = packet["cases"][0]["observations"][0]
    if index is None:
        observation.pop("availability_source_url")
    else:
        observation["availability_source_url"] = index
    with pytest.raises(ValueError):
        evaluate(packet,history)


def test_later_research_observation_never_becomes_an_earlier_original_forecast_feature():
    packet,history = fixture()
    case = packet["cases"][0]
    case["original_prediction_cutoff"] = "2024-12-31"
    case["observations"][0]["available_on"] = "2025-01-15"
    report = evaluate(packet,history)["case_reports"][0]
    source = report["source_classification"][0]
    assert source["classification"] == "PREDECISION_RESEARCH_CANDIDATE"
    assert source["supplied_source_date_vs_original_cutoff"] == "AFTER_SUPPLIED_ORIGINAL_CUTOFF"
    assert source["eligible_for_frozen_prediction"] is False
    assert source["scope"] == "RECONSTRUCTED_RESEARCH_ONLY_NOT_A_VERIFIED_FROZEN_FEATURE"
    assert report["frozen_prediction_source_count"] == 0
    assert report["science_worklist_scope"] == "CONSERVATIVE_RESEARCH_WINDOW_NOT_ORIGINAL_FORECAST_FEATURES"
    assert report["outcome"]["status"] == "INSUFFICIENT_EVIDENCE"


@pytest.mark.parametrize("change", ["duplicate_case","wrong_application","wrong_history_date","duplicate_history","missing_history"])
def test_exact_case_and_history_identity_is_mandatory(change):
    packet,history = fixture()
    if change == "duplicate_case": packet["cases"][-1] = deepcopy(packet["cases"][0])
    if change == "wrong_application": packet["cases"][0]["application_id"] = "NDA218607"
    if change == "wrong_history_date": history[0]["pdufa_date"] = "2025-05-16"
    if change == "duplicate_history": history.append(dict(history[0]))
    if change == "missing_history": history.pop(0)
    with pytest.raises(ValueError): evaluate(packet,history)


def test_duplicate_observations_and_unknown_science_questions_reject():
    packet,history = fixture()
    packet["cases"][0]["observations"] *= 2
    with pytest.raises(ValueError,match="duplicate observation"):
        evaluate(packet,history)
    packet,history = fixture()
    packet["cases"][0]["observations"][0]["science_question_ids"] = ["S41"]
    with pytest.raises(ValueError,match="SCIENCE question"):
        evaluate(packet,history)


def test_issuer_overlap_is_reported_without_inventing_program_identity():
    packet,history = fixture()
    history.append({"ticker":"BCRX","event_key":"BCRX|2020-12-03|berotralstat"})
    report = next(case for case in evaluate(packet,history)["case_reports"] if case["event_key"].startswith("BCRX|"))
    assert report["issuer_history_events_for_program_review"] == ["BCRX|2020-12-03|berotralstat"]
    assert report["issuer_overlap_is_not_program_identity"] is True


@pytest.mark.parametrize("value", ["2026-10-28",datetime(2026,10,28),True])
def test_snapshot_requires_a_date(value):
    packet,history = fixture()
    with pytest.raises(ValueError,match="as_of must be a date"):
        audit_reconstructions(packet,history,as_of=value)


def test_existing_science_contract_cannot_be_replaced_with_partial_questions():
    packet,history = fixture()
    with pytest.raises(ValueError,match="40 SCIENCE"):
        audit_reconstructions(packet,history,as_of=AS_OF,question_ids=QUESTION_IDS[:-1])
