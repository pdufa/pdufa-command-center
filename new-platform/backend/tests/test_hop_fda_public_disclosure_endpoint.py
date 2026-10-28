"""Authenticated read-only historical source chronology API integration."""
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app

ENDPOINT = "/api/internal/hop/public-outcome-disclosures"

def test_read_only_server_endpoint_auth_no_storage_or_trading():
    with patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only"}, clear=False):
        client = TestClient(app)
        assert client.get(ENDPOINT).status_code == 401
        with patch("app.main.ENGINE.connect", side_effect=AssertionError("DB accessed")):
            ok = client.get(ENDPOINT, headers={"x-pdufa-internal-key": "test-only"})
        assert ok.status_code == 200, ok.text
        payload = ok.json()
        assert payload["publicDisclosureResearch"]["totalPublicReleaseLeads"] == 3
        assert payload["actionLetterResearch"]["sourceLettersInspected"] == 2
        assert payload["originalPdfCaptureResearch"]["capturedPdfRecords"] == 2
        assert payload["approvedSurvivorSequenceResearch"]["reportedSequenceCases"] == 4
        assert payload["historicalFdaSourceCandidateResearch"]["researchCandidateRows"] == 412
        assert payload["historicalFdaSourceCandidateResearch"]["trainingAuthorized"] is False
        assert payload["historicalFdaSourceCandidateResearch"]["fdaApprovalProbability"] is None
        assert payload["approvedSurvivorSequenceResearch"]["priorCRLActionsInEventuallyApprovedCases"] == 7
        assert payload["approvedSurvivorSequenceResearch"]["modelEligibleHistoricalCycles"] == 0
        assert payload["originalPdfCaptureResearch"]["independentlyVerifiedModelCycles"] == 0
        assert payload["trainingAuthorized"] is False
        assert payload["tradeAuthorized"] is False
        assert payload["approvalProbability"] is None
