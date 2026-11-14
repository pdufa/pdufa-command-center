from datetime import date
import copy
import json
import pytest
from app.candidate_assessments import DOMAINS, compact, fingerprint, score_candidate

TODAY = date(2026, 10, 20)

def fixture():
    row = {"id": "TRIAL|NCT00000001", "programId": "PDUFA-000001", "ticker": "SAME",
           "phase3Source": "https://clinicaltrials.gov/study/NCT00000001", "lastChecked": "2026-10-20",
           "trialFilters": {"primaryOutcome": "SUCCESS", "resultsDate": "2026-10-01", "lists": ["PIPELINE"]},
           "technical": {"runwayMonths": 24, "runwayGate": "PASS", "runwaySource": "https://www.sec.gov/Archives/edgar/data/123/filing.htm",
                         "runwayAsOf": "2026-10-20", "avgDollarVolume20": 6000000, "eodFresh": True,
                         "marketDate": "2026-10-19", "marketSource": "https://data.alpaca.markets"}}
    registry = {"nct_id": "NCT00000001", "status": "COMPLETED", "study_design": {"designInfo": {"allocation": "RANDOMIZED", "maskingInfo": {"masking": "DOUBLE"}}},
                "treatment_groups": [{"type": "EXPERIMENTAL"}, {"type": "PLACEBO_COMPARATOR"}],
                "primary_outcomes": [{"measure": "Prespecified change", "timeFrame": "12 weeks"}], "last_update_posted": {"date": "2026-10-01"}}
    initial = score_candidate(row, registry, today=TODAY, registry_checked="2026-10-20")
    keys = {m["id"] for model in initial["models"].values() for c in model["categories"] for m in c["metrics"] if "." not in m["id"]}
    reviews = {key: {"grade": 4, "source": "https://example.org/exact-trial-report", "sourceDate": "2026-10-19", "reviewedAt": "2026-10-20", "measurements": {"actual": "Evidence retained"}, "rationale": "Exact program reviewed"} for key in keys}
    return row, registry, reviews

def score(row, registry=None, reviews=None, analyses=None):
    return score_candidate(row, registry, analyses, reviews, today=TODAY, registry_checked="2026-10-20")

def test_weights_reconcile_all_21_and_full_evidence_can_reach_100():
    row, registry, reviews = fixture()
    result = score(row, registry, reviews)
    for stage, model in result["models"].items():
        assert len(model["categories"]) == 7
        assert sum(d[2] for d in DOMAINS[stage]) == 100
        assert model["score"] == model["coverage"] == 100
        assert model["status"] == "COMPLETE"
        for category in model["categories"]:
            assert sum(m["maximum"] for m in category["metrics"]) == pytest.approx(category["maximum"])

def test_no_data_not_zero_and_partial_is_not_scaled_up():
    unknown = score({"id": "TRIAL|NCT00000001", "ticker": "SAME"})
    assert all(m["score"] is None and m["coverage"] == 0 for m in unknown["models"].values())
    row, registry, _ = fixture()
    result = score(row, registry)
    assert result["models"]["PIPELINE"]["score"] is None
    assert result["models"]["PIPELINE"]["observedPoints"] == 33
    assert result["models"]["PIPELINE"]["coverage"] == 33
    assert result["models"]["GEM_JR"]["categories"][0]["observedPoints"] == pytest.approx(6.6)
    assert result["models"]["GEM_JR"]["categories"][0]["coverage"] == pytest.approx(6.6)

def test_reviewed_zero_retains_coverage_and_stale_conflict_future_are_unscored():
    row, registry, reviews = fixture()
    reviews["effectSize"]["grade"] = 0
    result = score(row, registry, reviews)
    item = result["models"]["PIPELINE"]["categories"][0]["metrics"][1]
    assert item["points"] == 0 and item["coverage"] == 10
    for values, state in [({"reviewedAt": "2025-01-01", "sourceDate": "2024-12-01"}, "STALE"), ({"conflict": True}, "CONFLICTING"), ({"sourceDate": "2026-10-21"}, "MISSING"), ({"source": ""}, "MISSING"), ({"grade": float("nan")}, "MISSING")]:
        variant = copy.deepcopy(reviews)
        variant["effectSize"].update(values)
        item = score(row, registry, variant)["models"]["PIPELINE"]["categories"][0]["metrics"][1]
        assert item["points"] is None and item["coverage"] == 0 and item["status"] == state

def test_p_values_and_protocol_thresholds_never_establish_clinical_success():
    row, registry, _ = fixture()
    row["trialFilters"]["primaryOutcome"] = "UNKNOWN"
    registry["primary_outcomes"] = [{"measure": "Use p < 0.05", "timeFrame": "12 weeks"}]
    statistics = [{"endpoint": "secondary", "endpoint_type": "SECONDARY", "p_value": "<0.00001"}, {"endpoint": "primary", "p_value": 0}]
    result = score(row, registry, analyses=statistics)
    assert result["reportedStatistics"] == statistics
    assert result["models"]["PIPELINE"]["categories"][0]["metrics"][0]["points"] is None
    assert result["models"]["PIPELINE"]["categories"][2]["score"] is None
    assert result["models"]["PIPELINE"]["categories"][3]["score"] is None

def test_identity_is_exact_not_ticker_and_risk_flags_never_disappear():
    row, registry, reviews = fixture()
    with pytest.raises(ValueError, match="identity mismatch"):
        score({**row, "id": "TRIAL|NCT00000002"}, registry, reviews)
    row["trialFilters"].update(primaryOutcome="FAILED", safety="FLAGGED", dilution="FLAGGED", evidence=["CONFLICTING"])
    result = score(row, registry)
    assert len(result["riskFlags"]) == 4
    assert fingerprint(result) == fingerprint(copy.deepcopy(result))
    changed = copy.deepcopy(result)
    changed["reportedStatistics"].append({"p_value": "0.7"})
    assert fingerprint(changed) != fingerprint(result)
    assert row["trialFilters"]["lists"] == ["PIPELINE"]

def test_market_cap_and_reported_date_are_not_valuation_or_verified_catalyst():
    row, registry, _ = fixture()
    row.update(marketCap=1e9, pdufaDate="2026-11-01")
    result = score(row, registry)
    assert result["models"]["GEM_JR"]["categories"][2]["coverage"] == 0
    assert result["models"]["GEM_JR"]["categories"][4]["coverage"] == 0
    row["technical"]["marketDate"] = "2026-01-01"
    row["technical"]["runwayAsOf"] = "2026-01-01"
    result = score(row, registry)
    assert result["models"]["GEM_JR"]["categories"][3]["coverage"] == 0
    assert result["models"]["GEM_JR"]["categories"][6]["coverage"] == 0
    json.dumps(compact(result), allow_nan=False)


def test_candidate_evidence_coverage_never_claims_scientific_levels_active():
    row, registry, reviews = fixture()
    result = score(row, registry, reviews)
    assert result["models"]["PIPELINE"]["coverage"] == 100
    assert result["scientificReadiness"]["levels"] == [1, 2, 3, 4, 5, 6]
    assert result["scientificReadiness"]["status"] == "NOT_VERIFIED"
    assert result["scientificReadiness"]["fdaPrediction"] == "ABSTAIN"


def test_future_dated_registry_amendment_cannot_score_historical_cutoff():
    row, registry, reviews = fixture()
    registry["last_update_posted"]["date"] = "2026-10-21"
    result = score(row, registry, reviews)
    design = result["models"]["PIPELINE"]["categories"][1]
    assert design["coverage"] == 0
    assert all(metric["points"] is None for metric in design["metrics"])
    assert result["models"]["PIPELINE"]["categories"][5]["metrics"][0]["points"] is None


def test_registry_snapshot_checked_before_amendment_cannot_score():
    row, registry, reviews = fixture()
    registry["last_update_posted"]["date"] = "2026-10-20"
    result = score_candidate(row, registry, reviews=reviews, today=TODAY, registry_checked="2026-10-19")
    assert result["models"]["PIPELINE"]["categories"][1]["coverage"] == 0


def test_compact_assessment_retains_unverified_scientific_readiness():
    row, registry, reviews = fixture()
    result = score(row, registry, reviews)
    summary = compact(result)
    assert summary["scientificReadiness"] == result["scientificReadiness"]
    assert summary["scientificReadiness"]["fdaPrediction"] == "ABSTAIN"
    json.dumps(summary, allow_nan=False)


def test_historical_primary_outcome_requires_evidence_available_by_check_date():
    row, registry, reviews = fixture()
    row["trialFilters"]["resultsDate"] = "2026-10-20"
    row["lastChecked"] = "2026-10-19"
    result = score(row, registry, reviews)
    primary = result["models"]["PIPELINE"]["categories"][0]["metrics"][0]
    assert primary["points"] is None
    assert primary["coverage"] == 0


def test_historical_primary_outcome_rejects_future_check_date():
    row, registry, reviews = fixture()
    row["lastChecked"] = "2026-10-21"
    result = score(row, registry, reviews)
    primary = result["models"]["PIPELINE"]["categories"][0]["metrics"][0]
    assert primary["points"] is None
    assert primary["coverage"] == 0


def test_level_one_intake_blocks_missing_registry_phase():
    row, registry, reviews = fixture()
    result = score(row, registry, reviews)
    level = result["levelOneIntake"]
    assert level["executionStatus"] == "BLOCKED_UNVERIFIED_PHASE"
    assert level["phase"] is None
    assert level["fdaPrediction"] == "ABSTAIN"
    assert compact(result)["levelOneIntake"] == level


def test_level_one_intake_phase_two_does_not_require_completed_phase_three():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE2"]
    result = score(row, registry, reviews)
    level = result["levelOneIntake"]
    assert level["executionStatus"] == "INTAKE_ONLY"
    assert level["phase"] == "PHASE2"
    assert "completed Phase 3 results" in level["notYetExpected"]
    assert level["scientificValidation"] == "NOT_VERIFIED"


def test_level_one_intake_rejects_future_dated_registry_phase():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE3"]
    registry["last_update_posted"]["date"] = "2026-10-21"
    result = score(row, registry, reviews)
    assert result["levelOneIntake"]["executionStatus"] == "BLOCKED_UNVERIFIED_PHASE"
    assert result["levelOneIntake"]["phase"] is None


def test_level_one_uses_highest_registry_phase_regardless_of_tag_order():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE3", "PHASE2"]
    result = score(row, registry, reviews)
    assert result["levelOneIntake"]["phase"] == "PHASE3"
    assert result["levelOneIntake"]["executionStatus"] == "INTAKE_ONLY"


def test_level_one_requires_registry_status_as_well_as_phase():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE3"]
    registry.pop("status")
    result = score(row, registry, reviews)
    assert result["levelOneIntake"]["executionStatus"] == "BLOCKED_UNVERIFIED_PHASE"
    assert result["levelOneIntake"]["phase"] is None


def test_phase_first_intake_changes_assessment_fingerprint():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE2"]
    first = score(row, registry, reviews)
    registry["phases"] = ["PHASE3"]
    second = score(row, registry, reviews)
    assert first["models"] == second["models"]
    assert first["levelOneIntake"]["phase"] == "PHASE2"
    assert second["levelOneIntake"]["phase"] == "PHASE3"
    assert fingerprint(first) != fingerprint(second)


def test_level_one_inventory_distinguishes_missing_endpoint_from_later_phase_requirements():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE2"]
    registry["primary_outcomes"] = []
    result = score(row, registry, reviews)["levelOneIntake"]
    assert result["evidenceInventory"]["trial design"] == "OBSERVED"
    assert result["evidenceInventory"]["primary endpoint definition"] == "MISSING"
    assert "primary endpoint definition" in result["missingEvidence"]
    assert "completed Phase 3 results" in result["notYetExpected"]
    assert "completed Phase 3 results" not in result["missingEvidence"]


def test_level_one_unverified_registry_never_labels_design_as_missing():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE3"]
    registry["last_update_posted"]["date"] = "2026-10-21"
    result = score(row, registry, reviews)["levelOneIntake"]
    assert result["evidenceInventory"]["trial design"] == "UNVERIFIED"
    assert "trial design" not in result["missingEvidence"]


def test_level_one_phase_three_requires_separate_efficacy_safety_review():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE3"]
    intake = score(row, registry, reviews)["levelOneIntake"]
    label = "phase-appropriate efficacy and safety evidence"
    assert intake["evidenceInventory"][label] == "NOT_ASSESSED"
    assert label in intake["requiresSourceReview"]
    assert label not in intake["missingEvidence"]
    assert intake["fdaPrediction"] == "ABSTAIN"


def test_level_one_phase_one_does_not_require_pivotal_dossier():
    row, registry, reviews = fixture()
    registry["phases"] = ["PHASE1"]
    intake = score(row, registry, reviews)["levelOneIntake"]
    assert "pivotal efficacy or marketing-application dossier" in intake["notYetExpected"]
    assert intake["requiresSourceReview"] == []
