"""Source-dated COGT PEAK case for the research-only batch API.

The source-reviewed sponsor statements confirm public disclosure chronology,
NOT independent FDA-cycle adjudication or a complete clinical evaluation.
"""
import json
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.phase3_research_batch import evaluate_candidate_batch
from app.phase3_sheet_population_preview import build_sheet_population_preview

_FIXTURE = Path(__file__).parent / "fixtures" / "peak_real_trial_20261027.json"
_ENDPOINT = "/api/internal/phase3-research/evaluate-batch"


def source_case():
    return json.loads(_FIXTURE.read_text(encoding="utf-8"))


def test_real_peak_case_eligible_to_start_research_but_not_ready_to_predict():
    case = source_case()
    candidate = case["candidate"]
    result = evaluate_candidate_batch([candidate], as_of=case["as_of"])
    preview = build_sheet_population_preview(result)

    assert result["totalDiscovered"] == 1
    assert result["eligibleForResearch"] == 1
    assert result["blockedFromResearch"] == 0
    assert result["tradeAuthorized"] is False
    assert result["sheetPopulationStatus"] == "NOT_WRITTEN"

    row = result["rows"][0]
    assert row["exactKey"] == candidate["exact_key"]
    assert row["listMemberships"] == []  # Never fabricate GEM membership
    assert row["discoveryVisible"] is True
    assert row["deepAnalysisEligible"] is True
    assert row["analysis"]["status"] == "RESEARCH_IN_PROGRESS"
    assert row["analysis"]["gate"]["pdufaTargetDate"] == "2026-11-30"
    assert row["analysis"]["science"]["reviewed"] == 0
    assert row["analysis"]["science"]["required"] > 0
    assert row["analysis"]["science"]["scientificScore"] is None
    assert row["analysis"]["outcome"]["decisionReadinessGrade"] == "ABSTAIN"
    assert row["analysis"]["outcome"]["approvalProbability"] is None
    assert row["analysis"]["main"]["prediction"] == "INSUFFICIENT_EVIDENCE"
    assert row["analysis"]["approvalProbability"] is None

    assert preview["mode"] == "PREVIEW_ONLY"
    assert preview["writtenToSheet"] is False
    assert preview["requiresManualSourceReview"] is True
    assert len(preview["rows"]) == 1
    assert preview["rows"][0]["trialExactKey"] == candidate["exact_key"]
    assert preview["rows"][0]["readinessGrade"] == "NOT ASSESSED"
    assert preview["rows"][0]["approvalProbability"] is None
    assert preview["rows"][0]["independentConclusion"] is None


@pytest.mark.parametrize("as_of,expected_eligible", [
    ("2026-05-27", False),  # Neither future announcement is usable
    ("2026-05-29", False),  # Phase 3 detailed results not yet public
    ("2026-05-30", True),   # Both source disclosures now published
])
def test_real_peak_case_respects_as_of_cutoff(as_of, expected_eligible):
    case = source_case()
    result = evaluate_candidate_batch([case["candidate"]], as_of=as_of)
    row = result["rows"][0]
    assert row["deepAnalysisEligible"] is expected_eligible
    assert row["discoveryVisible"] is True
    assert row["tradeAuthorized"] is False
    assert row["analysis"] is None if not expected_eligible else row["analysis"] is not None
    if not expected_eligible:
        assert build_sheet_population_preview(result)["rows"] == []


@pytest.mark.parametrize("field", ["phase3_results", "pdufa_assignment"])
def test_source_review_revocation_fails_closed(field):
    case = source_case()
    candidate = deepcopy(case["candidate"])
    candidate[field]["review_status"] = "UNVERIFIED"
    result = evaluate_candidate_batch([candidate], as_of=case["as_of"])
    assert result["eligibleForResearch"] == 0
    assert result["rows"][0]["analysis"] is None
    assert build_sheet_population_preview(result)["rows"] == []


def test_real_peak_authenticated_batch_is_read_only_and_requires_key():
    case = source_case()
    payload = {"candidates": [case["candidate"]]}
    with patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only-secret"}):
        client = TestClient(app)
        assert client.post(_ENDPOINT, json=payload).status_code == 401
        response = client.post(
            _ENDPOINT, json=payload,
            headers={"x-pdufa-internal-key": "test-only-secret"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["eligibleForResearch"] == 1
    assert body["sheetPreview"]["writtenToSheet"] is False
    assert len(body["sheetPreview"]["rows"]) == 1
    assert body["sheetPreview"]["rows"][0]["approvalProbability"] is None
    assert body["tradeAuthorized"] is False


def test_duplicate_real_identity_is_rejected():
    case = source_case()
    candidate = case["candidate"]
    with pytest.raises(ValueError, match="Duplicate exact identity"):
        evaluate_candidate_batch([candidate, deepcopy(candidate)], as_of=case["as_of"])
