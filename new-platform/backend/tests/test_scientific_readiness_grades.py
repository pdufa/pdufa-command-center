"""Evidence readiness/reluctance are input audit grades, never trial success ratings."""
import gzip
import hashlib
import json
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.scientific_readiness_grades import RUBRIC_VERSION, review_readiness

NCT = "NCT04280705"


def filled_archive():
    return {
        "protocolSection": {
            "identificationModule": {"nctId": NCT, "briefTitle": "Review test"},
            "conditionsModule": {"conditions": ["Indication"]},
            "designModule": {"studyType": "INTERVENTIONAL", "phases": ["PHASE3"],
                             "enrollmentInfo": {"count": 220}},
            "eligibilityModule": {"eligibilityCriteria": "Adults meeting criteria"},
            "armsInterventionsModule": {
                "armGroups": [{"label": "Arm one"}, {"label": "Arm two"}],
                "interventions": [{"type": "DRUG", "name": "Example"}]},
            "statusModule": {"startDateStruct": {"date": "2021-01-01"},
                             "primaryCompletionDateStruct": {"date": "2024-01-01"}},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Clinical endpoint"}]},
        },
        "hasResults": True,
        "resultsSection": {
            "outcomeMeasuresModule": {"outcomeMeasures": [
                {"type": "PRIMARY", "title": "Clinical endpoint", "analyses": [
                    {"paramValue": "1.2", "pValue": "<0.05",
                     "ciLowerLimit": "1.01", "ciUpperLimit": "1.42"}]},
            ]},
            "adverseEventsModule": {
                "eventGroups": [{"id": "EG001"}, {"id": "EG002"}],
                "seriousEvents": [{"term": "Event", "stats": [
                    {"groupId": "EG001", "numAffected": "5", "numAtRisk": "110"}]}]
            },
            "participantFlowModule": {"periods": [{"title": "Overall study"}]},
            "baselineCharacteristicsModule": {"baselineMeasures": [{"title": "Age"}]},
        },
    }


def _by_id(result):
    return {item["id"]: item for item in result["requirements"]}


def test_complete_registry_snapshot_is_not_full_scientific_ready():
    report = review_readiness(NCT, filled_archive(),
                              archive_retrieved_at="2026-10-20T10:00:00Z")
    assert report["rubricVersion"] == RUBRIC_VERSION
    assert report["archiveRetrievedAt"] == "2026-10-20T10:00:00Z"
    assert len(report["requirements"]) == 16
    assert report["analysisReadiness"]["requirementsCovered"] == 12
    assert report["analysisReadiness"]["requirementsTotal"] == 16
    assert report["analysisReadiness"]["coveragePercent"] == 75
    assert report["analysisReadiness"]["grade"] == "B"
    assert report["analysisReadiness"]["readyForFullScientificConclusion"] is False
    assert report["analysisReadiness"]["passFail"] == "FAIL_INCOMPLETE_INPUTS"
    assert report["scientificReluctance"]["grade"] == "F"
    assert report["scientificReluctance"]["level"] == "CRITICAL"
    assert "does NOT" in report["scientificReluctance"]["note"]
    assert report["scientificScore"] is None
    assert report["fdaApprovalProbability"] is None
    assert report["externalEvidenceVerified"] is False
    assert set(report["missingRequirementIds"]) == {
        "protocol_sap", "published_results", "independent_replication", "official_regulatory"}
    assert all(not _by_id(report)[key]["available"] for key in report["missingRequirementIds"])


def test_sparse_archive_is_not_mislabeled_as_negative_trial():
    report = review_readiness(NCT, {
        "protocolSection": {"identificationModule": {"nctId": NCT}},
        "hasResults": False,
    })
    assert report["analysisReadiness"]["coveragePercent"] < 40
    assert report["analysisReadiness"]["grade"] == "F"
    assert report["analysisReadiness"]["readyForFullScientificConclusion"] is False
    assert report["scientificReluctance"]["grade"] == "F"
    assert report["scientificScore"] is None
    assert report["fdaApprovalProbability"] is None
    assert _by_id(report)["primary_analysis"]["available"] is False


def test_primary_analysis_cannot_be_satisfied_by_secondary_or_p_value_alone():
    record = filled_archive()
    record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"] = [
        {"type": "SECONDARY", "analyses": [{"pValue": "0.001", "paramValue": "1.3"}]},
        {"type": "PRIMARY", "analyses": [{"pValue": "0.05"}]},
    ]
    grade = review_readiness(NCT, record)
    assert _by_id(grade)["primary_analysis"]["available"] is False
    record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][1]["analyses"][0]["paramValue"] = "0.4"
    grade = review_readiness(NCT, record)
    assert _by_id(grade)["primary_analysis"]["available"] is True


def test_safety_counts_require_affected_and_at_risk():
    record = filled_archive()
    group = record["resultsSection"]["adverseEventsModule"]["seriousEvents"][0]["stats"][0]
    group.pop("numAtRisk")
    assert _by_id(review_readiness(NCT, record))["safety_denominators"]["available"] is False
    group["numAtRisk"] = "110"
    assert _by_id(review_readiness(NCT, record))["safety_denominators"]["available"] is True


def test_impossible_primary_pvalues_and_reversed_intervals_are_not_gradeable():
    record = filled_archive()
    analysis = record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["analyses"][0]
    analysis["pValue"] = "1.7"
    analysis["ciLowerLimit"] = "1.8"
    analysis["ciUpperLimit"] = "1.1"
    assert _by_id(review_readiness(NCT, record))["primary_analysis"]["available"] is False
    analysis["ciLowerLimit"] = "-0.3"
    analysis["ciUpperLimit"] = "1.1"
    assert _by_id(review_readiness(NCT, record))["primary_analysis"]["available"] is True


def test_safety_gate_rejects_impossible_negative_fractional_and_excess_counts():
    record = filled_archive()
    group = record["resultsSection"]["adverseEventsModule"]["seriousEvents"][0]["stats"][0]
    for affected, at_risk in (("-1", "100"), ("101", "100"), ("1.5", "100"), ("1", "0")):
        group["numAffected"] = affected
        group["numAtRisk"] = at_risk
        assert _by_id(review_readiness(NCT, record))["safety_denominators"]["available"] is False
    group["numAffected"], group["numAtRisk"] = "0", "100"
    assert _by_id(review_readiness(NCT, record))["safety_denominators"]["available"] is True


def test_registry_claims_about_fda_and_publications_cannot_self_certify():
    record = filled_archive()
    record["externalEvidenceVerified"] = True
    record["protocolSection"]["referencesModule"] = {"references": [
        {"pmid": "1234", "citation": "Some article"}]}
    record["protocolSection"]["oversightModule"] = {"isFdaRegulatedDrug": True}
    record["resultsSection"]["outcomeMeasuresModule"]["outcomeMeasures"][0]["analyses"][0]["pValue"] = "<0.00001"
    result = review_readiness(NCT, record)
    assert result["analysisReadiness"]["grade"] == "B"
    assert result["analysisReadiness"]["readyForFullScientificConclusion"] is False
    assert result["scientificReluctance"]["grade"] == "F"
    assert result["externalEvidenceVerified"] is False


@pytest.mark.parametrize("bad", ["NCT0001", "NCT042807050", "", "../NCT04280705"])
def test_strict_trial_identity(bad):
    with pytest.raises(ValueError, match="Exact NCT"):
        review_readiness(bad, filled_archive())


def test_registry_identity_mismatch_rejected():
    with pytest.raises(ValueError, match="identity mismatch"):
        review_readiness("NCT02142738", filled_archive())


def test_endpoint_auth_and_checksum_fail_closed(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://offline.invalid/db")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "grade-test-secret")
    raw = json.dumps(filled_archive(), sort_keys=True, separators=(",", ":")).encode()
    with Session(engine) as session:
        session.add(main.FullTrialRecord(
            nct_id=NCT, payload_gzip=gzip.compress(raw),
            sha256=hashlib.sha256(raw).hexdigest(), statistics=[],
            summary={"nctId": NCT}, fetched_at=datetime.now(timezone.utc)))
        session.commit()

    client = TestClient(main.app)
    url = "/api/scientific-assessment?exact_id=TRIAL%7C" + NCT
    assert client.get(url).status_code == 401
    data = client.get(url, headers={"x-pdufa-internal-key": "grade-test-secret"}).json()
    grades = data["readinessGrades"]
    assert grades["analysisReadiness"]["grade"] == "B"
    assert grades["scientificReluctance"]["grade"] == "F"
    assert data["assessment"]["overall_score"] is None

    with Session(engine) as session:
        row = session.get(main.FullTrialRecord, NCT)
        row.sha256 = "0" * 64
        session.commit()
    broken = client.get(url, headers={"x-pdufa-internal-key": "grade-test-secret"}).json()
    assert broken["registryEvidenceStatus"] == "record_unavailable_or_invalid"
    assert broken["readinessGrades"] is None
    engine.dispose()
