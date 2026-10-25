"""Offline checks for all 20 scientific investigation source-coverage levels."""
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
from app.scientific_investigation_20 import STAGES, investigation_20
from app.scientific_stored_record import verified_record_from_archive

NCT = "NCT04280705"


def study(results=True):
    record = {
        "protocolSection": {
            "identificationModule": {"nctId": NCT, "briefTitle": "Demo study"},
            "conditionsModule": {"conditions": ["Condition"]},
            "designModule": {"phases": ["PHASE3"],
                             "enrollmentInfo": {"count": 300},
                             "designInfo": {"allocation": "RANDOMIZED"}},
            "statusModule": {"overallStatus": "COMPLETED",
                             "startDateStruct": {"date": "2020-01-01"}},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Endpoint"}]},
        },
        "hasResults": results,
    }
    if results:
        record["resultsSection"] = {
            "outcomeMeasuresModule": {"outcomeMeasures": [{"title": "Endpoint"}]},
            "adverseEventsModule": {"seriousEvents": [{"term": "Event"}]},
        }
    return record


def archive(record):
    raw = json.dumps(record, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return gzip.compress(raw), hashlib.sha256(raw).hexdigest()


def test_twenty_stages_are_present_but_not_scientifically_verified():
    record = study()
    dossier = investigation_20(NCT, record, retrieved_at="2026-08-18T00:00:00Z")
    assert len(STAGES) == dossier["levelCount"] == len(dossier["levels"]) == 20
    assert [x["level"] for x in dossier["levels"]] == list(range(1, 21))
    assert len({x["title"] for x in dossier["levels"]}) == 20
    assert dossier["sourceUrl"] == "https://clinicaltrials.gov/study/" + NCT
    assert dossier["retrievedAt"] == "2026-08-18T00:00:00Z"
    assert dossier["scientificallyVerifiedLevels"] == 0
    assert dossier["overallScore"] is None
    assert dossier["fdaApprovalProbability"] is None
    assert all(x["score"] is None and not x["scientificallyVerified"]
               for x in dossier["levels"])
    by_number = {x["level"]: x for x in dossier["levels"]}
    assert by_number[12]["sourceEvidenceCount"] == 1
    assert by_number[12]["status"] == "external_review_required"
    assert by_number[12]["observations"][0]["fieldPath"] == (
        "resultsSection.outcomeMeasuresModule.outcomeMeasures")
    assert by_number[13]["sourceEvidenceCount"] == 1
    assert by_number[20]["sourceFieldCount"] == 0


def test_absent_results_and_false_regulatory_boolean_are_not_conclusions():
    dossier = investigation_20(NCT, study(False))
    assert dossier["recordHasResultsFlag"] is False
    assert dossier["levels"][11]["sourceEvidenceCount"] == 0
    assert dossier["levels"][12]["sourceEvidenceCount"] == 0
    record = study()
    record["protocolSection"]["oversightModule"] = {"isFdaRegulatedDrug": False}
    stage = investigation_20(NCT, record)["levels"][18]
    assert stage["observations"][0]["present"] is True
    assert stage["observations"][0]["value"] is False
    assert stage["status"] == "external_review_required"


@pytest.mark.parametrize("invalid", ["NCT1", "NCT042807050", "", "../NCT04280705"])
def test_bad_exact_id_rejected(invalid):
    with pytest.raises(ValueError, match="Exact NCT"):
        investigation_20(invalid, study())


def test_archive_identity_and_checksum_always_checked():
    record = study()
    with pytest.raises(ValueError, match="identity mismatch"):
        investigation_20("NCT02142738", record)
    payload, _ = archive(record)
    with pytest.raises(ValueError, match="checksum mismatch"):
        verified_record_from_archive(NCT, payload, "0"*64)
    record["protocolSection"]["identificationModule"]["nctId"] = "NCT02142738"
    payload, checksum = archive(record)
    with pytest.raises(ValueError, match="identity mismatch"):
        verified_record_from_archive(NCT, payload, checksum)


def test_authenticated_api_respects_archive_integrity_and_does_not_score(monkeypatch):
    engine = create_engine("sqlite://", poolclass=StaticPool,
                           connect_args={"check_same_thread": False})
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setattr(main, "_DB_STATE", {"available": True, "reason": "READY"})
    monkeypatch.setattr(main, "DATABASE_URL", "postgresql+psycopg://test.invalid/review")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "offline-test-key")
    payload, checksum = archive(study())
    with Session(engine) as session:
        session.add(main.FullTrialRecord(
            nct_id=NCT, payload_gzip=payload, sha256=checksum,
            summary={"nctId": NCT}, statistics=[],
            fetched_at=datetime(2026, 8, 18, tzinfo=timezone.utc)))
        session.commit()
    client = TestClient(main.app)
    url = "/api/scientific-assessment?exact_id=TRIAL%7C" + NCT
    assert client.get(url).status_code == 401
    headers = {"x-pdufa-internal-key": "offline-test-key"}
    response = client.get(url, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["registryEvidenceStatus"] == "source_record_loaded"
    assert data["investigation20"]["levelCount"] == 20
    assert data["investigation20"]["retrievedAt"].startswith("2026-08-18")
    assert data["assessment"]["overall_score"] is None
    assert all(v["score"] is None for v in data["assessment"]["domains"].values())
    with Session(engine) as session:
        row = session.get(main.FullTrialRecord, NCT)
        row.sha256 = "0"*64
        session.commit()
    corrupt = client.get(url, headers=headers).json()
    assert corrupt["registryEvidenceStatus"] == "record_unavailable_or_invalid"
    assert corrupt["investigation20"] is None
    engine.dispose()
