"""Operational smoke contracts; local ASGI results are not production evidence."""
from io import BytesIO
from unittest.mock import patch

from fastapi.testclient import TestClient
import pytest

from app import main as api
from scripts import smoke_real_trial_readonly as smoke


def actual_read():
    with patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "local-test-only"}), \
         patch.object(api.ENGINE, "connect", side_effect=AssertionError("No database access allowed")):
        response = TestClient(api.app).get("/api/internal/phase3-research/peak-register",
            headers={"x-pdufa-internal-key": "local-test-only"})
    assert response.status_code == 200
    return response.json()


def test_actual_server_read_reconciles_science_outcome_main_without_fixture_submission():
    response = actual_read()
    result = smoke.verify_published_chain(response, expected_as_of=response["asOf"])
    assert result["mode"] == "SERVER_PUBLISHED_RESEARCH"
    assert result["independentlyCertified"] == 0
    assert result["outcomeDecision"] == "ABSTAIN"
    assert result["productionDataFlowVerified"] is False


@pytest.mark.parametrize("mutate", [
    lambda x: x.pop("main"),
    lambda x: x["main"].update(exactKey="OTHER"),
    lambda x: x["main"].update(asOf="2026-01-01"),
    lambda x: x["main"].update(researchRegister=None),
    lambda x: x["main"].update(prediction="PASS"),
    lambda x: x["main"].update(modelVersion="unvalidated"),
    lambda x: x["outcome"].update(probabilities={"PASS": .8, "CRL": .1, "EXTENSION": .1}),
    lambda x: x["outcome"].update(predictionClasses=["PASS", "CRL"]),
    lambda x: x["outcome"].update(extensionIsNonapproval=True),
    lambda x: x["outcome"].update(confidence=.9),
    lambda x: x["researchRegister"]["questions"].pop(),
    lambda x: x.update(sheetWritesEnabled=True),
])
def test_missing_stale_cross_trial_and_unsupported_prediction_claims_fail(mutate):
    response = actual_read()
    mutate(response)
    with pytest.raises(RuntimeError):
        smoke.verify_published_chain(response, expected_as_of=response["asOf"])


@pytest.mark.parametrize("url", [
    "http://pdufa-hop-readonly-review.onrender.com",
    "https://attacker.example", "https://pdufa-hop-readonly-review.onrender.com/path",
    "https://user:password@pdufa-hop-readonly-review.onrender.com",
    "https://pdufa-hop-readonly-review.onrender.com?key=private",
])
def test_invalid_origins_rejected_before_any_network_request(url, monkeypatch):
    monkeypatch.setattr("sys.argv", ["smoke", "--published", "--base-url", url])
    with patch.object(smoke, "build_opener") as opener, pytest.raises(ValueError):
        smoke.main()
    opener.assert_not_called()


def test_redirects_never_forward_the_existing_key():
    with pytest.raises(RuntimeError, match="Redirect refused"):
        smoke.NoRedirect().redirect_request(None, None, 302, "redirect", {}, "https://other.example")


@pytest.mark.parametrize("raw", [b'{"ok":true,"ok":false}', b'{"value":NaN}', b'[]'])
def test_ambiguous_or_nonobject_json_is_not_a_passing_response(raw):
    response = BytesIO(raw)
    response.status = 200
    with patch.object(smoke, "build_opener") as opener:
        opener.return_value.open.return_value = response
        with pytest.raises(RuntimeError):
            smoke.get_json(smoke.Request(smoke.DEFAULT_BASE + "/health"))


def test_published_mode_uses_existing_hop_key_and_only_two_gets(monkeypatch, capsys):
    payload = actual_read()
    calls = []
    def response(req):
        calls.append(req)
        if req.full_url.endswith("/health"):
            return {"storage_ready": True, "storage_kind": "postgresql",
                    "service": "pdufa-new-backend", "status": "ok"}
        assert req.get_header("X-pdufa-internal-key") == "dedicated-hop-test-only"
        return payload
    monkeypatch.setenv("PDUFA_HOP_INTERNAL_API_KEY", "dedicated-hop-test-only")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "different-storage-test-only")
    monkeypatch.setattr("sys.argv", ["smoke", "--published"])
    with patch.object(smoke, "get_json", side_effect=response):
        assert smoke.main() == 0
    assert len(calls) == 2 and all(req.get_method() == "GET" for req in calls)
    assert calls[1].full_url.endswith("/peak-register")
    assert "dedicated-hop-test-only" not in capsys.readouterr().out


def test_explicit_empty_hop_credential_never_falls_back(monkeypatch):
    monkeypatch.setenv("PDUFA_HOP_INTERNAL_API_KEY", "")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "different-storage-test-only")
    monkeypatch.setattr("sys.argv", ["smoke", "--published"])
    with patch.object(smoke, "get_json") as network:
        assert smoke.main() == 2
    network.assert_not_called()
