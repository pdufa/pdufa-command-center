"""Source-register integrity and integration tests, not prediction accuracy."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app import main
from app.peak_research import KEY, _load, outcome_readiness, research_register
from app.phase3_research_batch import evaluate_candidate_batch
from app.phase3_sheet_population_preview import build_sheet_population_preview
from app.science_40_dossier import evaluate_science_40


def case():
    return json.loads((Path(__file__).parent / "fixtures/peak_real_trial_20261027.json").read_text())["candidate"]


def test_actual_register_is_complete_question_inventory_not_independent_science():
    r = research_register(exact_key=KEY, as_of="2026-10-28")
    assert [q["id"] for q in r["questions"]] == [f"S{i:02}" for i in range(1, 41)]
    assert len({q["layer"] for q in r["questions"]}) == 8
    assert r["summary"]["questionsWithSourceObservations"] == 27
    assert r["summary"]["missingRequiredDocumentFamilies"] == 12
    assert r["summary"]["independentlyCertifiedAssessments"] == 0
    assert r["summary"]["independentlyAdjudicatedHistoricalCycles"] == 0
    assert r["summary"]["pointInTimeTrainingEligible"] is False
    assert all(s["originalDocumentSha256"] is None for s in r["sources"])
    assert all(q["independentlyReviewed"] is False and q["reviewedDepthLevels"] == [] for q in r["questions"])
    assert r["depthFramework"]["requiredLevels"] == list(range(1, 21))


def test_new_observations_cannot_be_backfilled_or_borrowed_by_a_different_trial():
    assert research_register(exact_key=KEY, as_of="2026-10-27") is None
    assert research_register(exact_key="TRIAL|NCT00000001", as_of="2026-10-28") is None
    baseline = evaluate_science_40(exact_key=KEY, evidence={}, as_of="2026-10-27")
    assert baseline["sourceLeadsDiscovered"] == 10
    assert baseline["independentlyReviewedAssessments"] == 0


@pytest.mark.parametrize("mutate", [
    lambda r:r.update(modelValidated=True),
    lambda r:r.update(approvalProbability=.9),
    lambda r:r["questions"][0].update(independentlyReviewed=True),
    lambda r:r["questions"][0].update(reviewedDepthLevels=[20]),
    lambda r:r["questions"][0].update(id="S02"),
    lambda r:r["questions"][0].update(exactKey="OTHER"),
    lambda r:r["questions"][0].update(sourceIds=["unexamined"]),
    lambda r:r["sources"][0].update(url="https://user:password@example.org/"),
    lambda r:r["sources"][0].update(originalDocumentSha256="a"*64),
    lambda r:r["sources"][0].update(observedOn="2026-10-29"),
    lambda r:r["historicalContexts"][0].update(modelEligible=True),
    lambda r:r["historicalContexts"][0].update(reviewCycle=1),
    lambda r:r["questions"].pop(),
])
def test_identity_dates_receipts_and_review_promotion_fail_closed(mutate):
    r = deepcopy(_load()); mutate(r)
    with pytest.raises(ValueError):
        research_register(exact_key=KEY, as_of="2026-10-28", register=r)


def test_historical_approval_and_nonapproval_claims_are_separate_from_validated_cycles():
    r = research_register(exact_key=KEY, as_of="2026-10-28")
    contexts = r["historicalContexts"]
    assert {h["actionClaim"] for h in contexts} == {"APPROVAL", "ISSUER_REPORTED_COMPLETE_RESPONSE"}
    denied = next(h for h in contexts if h["drug"] == "Poziotinib")
    assert denied["applicationId"] == "NDA215643"
    assert denied["actionDate"] is None and denied["reportedOn"] == "2022-11-25"
    assert all(h["modelEligible"] is h["independentlyAdjudicated"] is False for h in contexts)
    assert all(h["reviewCycle"] is None for h in contexts)


def test_real_batch_combines_science_outcome_main_and_preview_without_prediction():
    batch = evaluate_candidate_batch([case()], as_of="2026-10-28")
    a = batch["rows"][0]["analysis"]
    assert a["science40"]["sourceLeadsDiscovered"] == 10
    assert a["science40"]["independentlyReviewedAssessments"] == 0
    assert a["outcome"]["researchReadinessGrade"] == "RELUCTANT"
    assert a["outcome"]["decisionReadinessGrade"] == "ABSTAIN"
    assert a["outcome"]["predictionValidation"]["status"] == "NOT_VALIDATED"
    assert a["main"]["prediction"] == "INSUFFICIENT_EVIDENCE"
    assert a["main"]["researchRegister"]["summary"]["questionRecords"] == 40
    assert a["approvalProbability"] is a["outcome"]["approvalProbability"] is None
    assert a["outcome"]["tradeAuthorized"] is a["main"]["tradeAuthorized"] is False
    preview = build_sheet_population_preview(batch)
    assert len(preview["rows"]) == 1 and preview["writtenToSheet"] is False


def test_missing_either_gate_does_not_start_register_investigation():
    c = case(); c["pdufa_assignment"] = {}
    with patch("app.phase3_deep_analysis_orchestrator.research_register", side_effect=AssertionError("Early investigation")):
        batch = evaluate_candidate_batch([c], as_of="2026-10-28")
    assert batch["rows"][0]["discoveryVisible"] is True
    assert batch["rows"][0]["analysis"] is None


def test_even_structural_completion_does_not_validate_a_prediction_model():
    science = evaluate_science_40(exact_key=KEY, evidence={}, as_of="2026-10-28")
    science.update(readinessGrade="READY_FOR_ANALYSIS", independentlyReviewedAssessments=40, reviewedDepthLevels=list(range(1,21)))
    o = outcome_readiness(science, None)
    assert o["researchReadinessGrade"] == "READY_FOR_ANALYSIS"
    assert o["decisionReadinessGrade"] == "ABSTAIN" and o["modelValidated"] is False
    assert o["approvalProbability"] is o["confidence"] is None


def test_authenticated_read_only_route_never_uses_storage_or_accepts_external_register():
    with patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY":"synthetic-unprivileged-test-key"}), patch.object(main.ENGINE,"connect", side_effect=AssertionError("Unexpected database access")):
        client = TestClient(main.app)
        path = "/api/internal/phase3-research/peak-register"
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"x-pdufa-internal-key":"wrong"}).status_code == 401
        response = client.get(path, headers={"x-pdufa-internal-key":"synthetic-unprivileged-test-key"})
        assert response.status_code == 200
        assert client.post(path, json={"modelValidated":True}).status_code == 405
    body = response.json()
    assert body["science40"]["independentlyReviewedAssessments"] == 0
    assert body["outcome"]["decisionReadinessGrade"] == "ABSTAIN"
    assert body["sheetWritesEnabled"] is body["productionSchedulingEnabled"] is body["tradeAuthorized"] is False
