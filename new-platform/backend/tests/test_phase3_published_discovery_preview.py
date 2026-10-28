"""Published discovery research preview: strict provenance, identity and no writes."""
from copy import deepcopy
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.phase3_published_discovery_preview import preview_published_discoveries

PEAK = "APPLICATION|COGT|BEZUCLASTINIB_GIST_20261130"
UNKNOWN = "TRIAL|NCT01234567"
ENDPOINT = "/api/internal/phase3-research/preview-published-discovery"


def snapshot():
    return {
        "mode": "LIVE_READ_ONLY_GITHUB_SOURCE",
        "asOf": "2026-10-27",
        "sourceHealth": {"state": "COMPLETE_PUBLISHED", "issues": []},
        "pipeline": [
            {"id": PEAK, "ticker": "COGT", "nctId": "NCT05208047",
             "pdufaDate": "2026-11-30", "stage": "PDUFA Decision",
             "phase3Status": "NOT VERIFIED"},
            {"id": UNKNOWN, "ticker": "A123", "stage": "Phase 3 Results",
             "phase3Date": "2026-01-01", "pdufaDate": "2027-03-01",
             "phase3Status": "VERIFIED"},
        ],
        "members": {
            "GEM_JR": {"rows": [{
                "id": PEAK, "ticker": "COGT", "candidateLinked": True,
                "membershipStatus": "ACTIVE IN PUBLISHED STAGE LEDGER",
            }]},
            "GEM": {"rows": []},
        },
    }


def test_curated_peak_starts_science_only_and_never_authorizes_trade():
    result = preview_published_discoveries(snapshot(), [PEAK])
    assert result["mode"] == "READ_ONLY_PUBLISHED_DISCOVERY_RESEARCH_PREVIEW"
    assert result["sourceResearchVerified"] is True
    assert (result["requested"], result["totalDiscovered"]) == (1, 1)
    assert result["eligibleForResearch"] == 1
    row = result["rows"][0]
    assert row["exactKey"] == PEAK
    assert row["sourceWarning"] is None
    assert row["listMemberships"] == ["GEM JR"]
    assert row["discoveryFeed"] == "PUBLISHED_PIPELINE_INDEX"
    assert row["deepAnalysisEligible"] is True
    assert row["analysis"]["status"] == "RESEARCH_IN_PROGRESS"
    assert row["analysis"]["science"]["reviewed"] == 0
    assert row["analysis"]["approvalProbability"] is None
    assert row["analysis"]["outcome"] is None
    assert row["analysis"]["main"] is None
    assert result["sheetPopulationStatus"] == "NOT_WRITTEN"
    assert result["sheetPreview"]["mode"] == "PREVIEW_ONLY"
    assert result["sheetPreview"]["requiresManualSourceReview"] is True
    assert result["sheetPreview"]["writtenToSheet"] is False
    assert result["sheetPreview"]["rows"][0]["approvalProbability"] is None
    assert result["tradeAuthorized"] is False
    assert result["scannerScheduled"] is False


def test_scanner_stage_or_verification_flag_cannot_certify_unknown_candidate():
    s = snapshot()
    # A "VERIFIED" label in the scanner row must never become a research gate.
    s["pipeline"][1]["phase3_results"] = {
        "review_status": "VERIFIED", "published_at": "2026-01-01",
        "event_date": "2026-01-01", "source_url": "https://example.org"
    }
    result = preview_published_discoveries(s, [UNKNOWN])
    assert result["eligibleForResearch"] == 0
    assert result["rows"][0]["deepAnalysisEligible"] is False
    assert result["rows"][0]["analysis"] is None
    assert result["rows"][0]["sourceWarning"] == "NO_CURATED_PHASE3_PDUFA_SOURCE_PAIR"
    assert result["sheetPreview"]["rows"] == []


@pytest.mark.parametrize("mode,state,issues", [
    ("STALE_PREVIOUS_FETCH", "STALE", []),
    ("LIVE_READ_ONLY_GITHUB_SOURCE", "PARTIAL", ["Missing source"]),
    ("LIVE_READ_ONLY_GITHUB_SOURCE", "COMPLETE_PUBLISHED", ["Failed source"]),
])
def test_unhealthy_source_never_starts_research_but_keeps_discovery(mode, state, issues):
    s = snapshot()
    s["mode"] = mode
    s["sourceHealth"] = {"state": state, "issues": issues}
    result = preview_published_discoveries(s, [PEAK])
    assert result["totalDiscovered"] == 1
    assert result["eligibleForResearch"] == 0
    assert result["rows"][0]["discoveryVisible"] is True
    assert result["rows"][0]["sourceWarning"] == "PUBLISHED_SOURCE_HEALTH_NOT_COMPLETE"
    assert result["sheetPreview"]["rows"] == []


@pytest.mark.parametrize("edit,warning", [
    ({"pdufaDate": "2026-12-30"}, "CURATED_ATTESTATION_NOT_CURRENT_OR_TARGET_MISMATCH"),
    ({"pdufaDate": ""}, "CURATED_ATTESTATION_NOT_CURRENT_OR_TARGET_MISMATCH"),
    ({"nctId": "NCT99999999"}, "CLINICAL_TRIAL_IDENTITY_MISMATCH"),
])
def test_date_or_trial_identity_disagreement_blocks_promotion(edit, warning):
    s = snapshot()
    s["pipeline"][0].update(edit)
    result = preview_published_discoveries(s, [PEAK])
    assert result["eligibleForResearch"] == 0
    assert result["rows"][0]["sourceWarning"] == warning
    assert result["sheetPreview"]["rows"] == []


def test_verified_curated_record_not_usable_before_its_actual_review_date():
    s = snapshot()
    s["asOf"] = "2026-05-30"
    result = preview_published_discoveries(s, [PEAK])
    assert result["eligibleForResearch"] == 0
    assert result["rows"][0]["sourceWarning"] == "CURATED_ATTESTATION_NOT_CURRENT_OR_TARGET_MISMATCH"


def test_active_member_must_match_exact_ticker_and_linked_identity():
    s = snapshot()
    s["members"]["GEM_JR"]["rows"][0]["ticker"] = "OTHER"
    r = preview_published_discoveries(s, [PEAK])
    assert r["eligibleForResearch"] == 1
    assert r["rows"][0]["listMemberships"] == []
    s["members"]["GEM_JR"]["rows"][0]["ticker"] = "COGT"
    s["members"]["GEM_JR"]["rows"][0]["candidateLinked"] = False
    assert preview_published_discoveries(s, [PEAK])["rows"][0]["listMemberships"] == []


def test_duplicate_selected_or_discovered_exact_identity_rejected():
    with pytest.raises(ValueError, match="Duplicate requested"):
        preview_published_discoveries(snapshot(), [PEAK, PEAK])
    s = snapshot()
    s["pipeline"].append(deepcopy(s["pipeline"][0]))
    with pytest.raises(ValueError, match="Duplicate exact identity"):
        preview_published_discoveries(s, [PEAK])


def test_missing_exact_key_is_reported_not_silently_added():
    requested = "TRIAL|NCT11111111"
    r = preview_published_discoveries(snapshot(), [requested, PEAK])
    assert (r["requested"], r["totalDiscovered"]) == (2, 1)
    assert r["missingExactKeys"] == [requested]
    assert len(r["rows"]) == 1


def test_source_catalog_cannot_be_spoofed_from_scanner_row():
    s = snapshot()
    s["pipeline"][0]["review_status"] = "VERIFIED"
    s["pipeline"][0]["pdufa_assignment"] = {"review_status": "VERIFIED"}
    # A vetted server-side catalog mismatch blocks the gate regardless
    # of what the published discovery itself claims.
    r = preview_published_discoveries(s, [PEAK], catalog={
        "schemaVersion": "pdufa-curated-phase3-announcements-v1",
        "cases": {}
    })
    assert r["eligibleForResearch"] == 0
    assert r["sheetPreview"]["rows"] == []


def test_authenticated_http_preview_without_database_or_writes():
    with (patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only"}, clear=False),
          patch("app.source_workspace.workspace", return_value=snapshot())):
        client = TestClient(app)
        payload = {"exact_keys": [PEAK, UNKNOWN]}
        assert client.post(ENDPOINT, json=payload).status_code == 401
        response = client.post(
            ENDPOINT, json=payload,
            headers={"x-pdufa-internal-key": "test-only"},
        )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["totalDiscovered"] == 2
    assert body["eligibleForResearch"] == 1
    assert body["blockedFromResearch"] == 1
    assert body["sheetPreview"]["writtenToSheet"] is False
    assert body["tradeAuthorized"] is False


def test_http_preview_fails_closed_when_published_source_unavailable():
    with (patch.dict("os.environ", {"PDUFA_INTERNAL_API_KEY": "test-only"}, clear=False),
          patch("app.source_workspace.workspace", side_effect=RuntimeError("fetch failed"))):
        result = TestClient(app).post(
            ENDPOINT, json={"exact_keys": [PEAK]},
            headers={"x-pdufa-internal-key": "test-only"},
        )
    assert result.status_code == 503
    assert result.json()["detail"] == "Published discovery unavailable"


def test_invalid_inputs_are_rejected_without_publishing():
    for exact_keys in ([], [PEAK, PEAK], [""]):
        with pytest.raises(ValueError):
            preview_published_discoveries(snapshot(), exact_keys)
    with pytest.raises(ValueError):
        preview_published_discoveries(snapshot(), [str(x) for x in range(201)])
