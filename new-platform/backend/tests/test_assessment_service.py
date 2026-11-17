from datetime import datetime, timezone
import copy
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app import main, assessment_service as service, source_workspace, workspace_response
from test_candidate_assessments import fixture

@pytest.fixture
def isolated(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, "ENGINE", engine)
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-key")
    monkeypatch.delenv("PDUFA_MIGRATION_READ_ONLY", raising=False)
    monkeypatch.setattr(service, "_STATE", {"key": "", "building": False, "index": None, "error": "", "snapshot": None, "reviews": {}, "token": ""})
    row, registry, reviews = fixture()
    snapshot = {"workspaceVersion": "a" * 64, "sourceHealth": {"state": "LIVE"}, "pipeline": [row, {"id": "TRIAL|NCT00000002", "ticker": "SAME", "programId": "PDUFA-000002"}], "members": {"GEM_JR": {"rows": []}, "GEM": {"rows": []}}}
    monkeypatch.setattr(source_workspace, "workspace", lambda: snapshot)
    monkeypatch.setattr(workspace_response, "prepared", lambda value: value)
    monkeypatch.setattr(service, "review_evidence", lambda: ({row["id"]: reviews}, "AVAILABLE"))
    with Session(engine) as session:
        session.add(main.FullTrialRecord(nct_id="NCT00000001", payload_gzip=b"not-read-by-scorer", sha256="a" * 64, summary=registry, statistics=[{"p_value": "<0.01"}], fetched_at=datetime(2026, 10, 20, tzinfo=timezone.utc)))
        session.commit()
    yield engine, snapshot
    engine.dispose()

def count(engine):
    with Session(engine) as session: return session.scalar(select(func.count(main.CandidateAssessmentHistory.id)))

def test_every_program_21_categories_history_and_no_same_ticker_leak(isolated):
    engine, snapshot = isolated
    index = service.get_index(synchronous=True)
    assert index["total"] == 2 and len(index["records"]) == 2
    assert index["registryLinked"] == 1 and index["registryMissing"] == 1
    for record in index["records"]:
        assert all(len(record[i]) == 17 for i in (1, 2, 3))
    assert index["records"][1][1][2] == 0  # no peer-trial evidence copied
    assert count(engine) == 2
    assert service.get_index(synchronous=True) is index
    assert count(engine) == 2
    detail = service.exact_detail(snapshot["pipeline"][0]["id"])
    assert detail["programId"] == "PDUFA-000001"
    assert detail["reportedStatistics"] == [{"p_value": "<0.01"}]
    assert len(detail["history"]) == 1
    assert detail["changes"] == {}
    # A new source snapshot with identical evidence does not duplicate history.
    snapshot["workspaceVersion"] = "b" * 64
    service.get_index(synchronous=True)
    assert count(engine) == 2
    snapshot["pipeline"][0]["trialFilters"]["safety"] = "FLAGGED"
    snapshot["workspaceVersion"] = "c" * 64
    service.get_index(synchronous=True)
    assert count(engine) == 3
    assert len(service.exact_detail(snapshot["pipeline"][0]["id"])["history"]) == 2

def test_index_exact_scope_stale_rejection_and_http_auth(isolated):
    _, snapshot = isolated
    main.app.dependency_overrides[main.require_storage] = lambda: None
    try:
        service.get_index(synchronous=True)
        client = TestClient(main.app)
        assert client.get("/api/candidate-assessments").status_code == 401
        headers = {"x-pdufa-internal-key": "test-key"}
        assert client.get("/api/candidate-assessments", headers=headers).json()["total"] == 2
        assert client.get("/api/candidate-assessments/detail", params={"identity": "SAME"}, headers=headers).status_code == 404
        assert client.get("/api/candidate-assessments/detail", params={"identity": "TRIAL|NCT00000002"}, headers=headers).json()["models"]["PIPELINE"]["score"] is None
        snapshot["sourceHealth"]["state"] = "STALE"
        assert client.get("/api/candidate-assessments", headers=headers).status_code == 503
    finally: main.app.dependency_overrides.pop(main.require_storage, None)

def test_readonly_mode_does_not_write_histories(isolated, monkeypatch):
    engine, _ = isolated
    monkeypatch.setenv("PDUFA_MIGRATION_READ_ONLY", "1")
    index = service.get_index(synchronous=True)
    assert index["historyStatus"] == "READ_ONLY" and count(engine) == 0


def test_saved_registry_phase_inventory_persists_and_versions_without_review_invention(isolated):
    engine, snapshot = isolated
    identity = snapshot["pipeline"][0]["id"]
    with Session(engine) as session:
        record = session.get(main.FullTrialRecord, "NCT00000001")
        record.summary = {**record.summary, "phases": ["PHASE3"],
                          "conditions": ["Fixture disease"], "eligibility": {"minimumAge": "18 Years"}}
        session.commit()
    service.get_index(synchronous=True)
    detail = service.exact_detail(identity)
    assert detail["levelOneIntake"]["executionStatus"] == "INTAKE_ONLY"
    for number in ["2", "3", "4", "5", "6"]:
        assert detail["levelsTwoToSix"][number]["score"] is None
        assert detail["levelsTwoToSix"][number]["fdaPrediction"] == "ABSTAIN"
    assert detail["levelsTwoToSix"]["2"]["registryEvidenceInventory"]["populationAndEligibility"]["state"] == "AVAILABLE_NOT_REVIEWED"
    with Session(engine) as session:
        old = list(session.scalars(select(main.CandidateAssessmentHistory).order_by(main.CandidateAssessmentHistory.id)))
        frozen = [(x.id, copy.deepcopy(x.summary)) for x in old]
        assert old[0].summary["levelsTwoToSix"] == detail["levelsTwoToSix"]
        record = session.get(main.FullTrialRecord, "NCT00000001")
        record.summary = {**record.summary, "eligibility": {"minimumAge": "21 Years"}}
        record.fetched_at = datetime(2026, 10, 21, tzinfo=timezone.utc)
        session.commit()
    service.get_index(synchronous=True)
    assert count(engine) == len(frozen) + 1
    with Session(engine) as session:
        for identity, value in frozen:
            assert session.get(main.CandidateAssessmentHistory, identity).summary == value


def test_population_and_exposure_engines_persist_distinct_versions(isolated, monkeypatch):
    from test_scientific_binary_effects import record
    from test_scientific_population import measurements as population_counts
    from test_scientific_safety_exposure import measurements as exposure_counts
    engine,snapshot=isolated
    identity=snapshot['pipeline'][0]['id']
    population=record();population['measurements']=population_counts()
    safety=record();safety['measurements']=exposure_counts()
    reviews={identity:{'scientificLevelEvidence':{'7.treatmentSubgroupInteraction':population,'8.exposureAdjustedRates':safety}}}
    monkeypatch.setattr(service,'review_evidence',lambda:(reviews,'AVAILABLE'))
    with Session(engine) as session:
        saved=session.get(main.FullTrialRecord,'NCT00000001')
        saved.summary={**saved.summary,'phases':['PHASE3']};session.commit()
    service.get_index(synchronous=True)
    detail=service.exact_detail(identity)
    assert detail['levelsSevenToTwenty']['7']['calculations']['treatmentSubgroupInteraction']['ratioOfRiskRatios']==pytest.approx(4)
    assert detail['levelsSevenToTwenty']['8']['calculations']['exposureAdjustedRates']['incidenceRateRatio']==pytest.approx(2)
    with Session(engine) as session:
        old=list(session.scalars(select(main.CandidateAssessmentHistory).order_by(main.CandidateAssessmentHistory.id)))
        frozen=[(x.id,copy.deepcopy(x.summary)) for x in old]
        assert old[0].summary['levelsSevenToTwenty']==detail['levelsSevenToTwenty']
    population['measurements']['subgroupA']['treatment']['events']=30
    service.get_index(synchronous=True)
    assert count(engine)==len(frozen)+1
    with Session(engine) as session:
        for key,value in frozen:assert session.get(main.CandidateAssessmentHistory,key).summary==value


def test_compact_queue_is_present_in_append_only_assessment_history(isolated):
    engine, snapshot = isolated
    exact_id = snapshot["pipeline"][0]["id"]
    with Session(engine) as session:
        record = session.get(main.FullTrialRecord, "NCT00000001")
        record.summary = {**record.summary, "phases": ["PHASE3"]}
        session.commit()
    service.get_index(synchronous=True)
    detail = service.exact_detail(exact_id)
    queue = detail["advancedEvidenceQueue"]
    assert queue["status"] == "RESEARCH_QUEUE_READY"
    assert queue["unresolvedCriteria"] == 60
    assert len(detail["history"]) == 1
    history = detail["history"][0]["advancedEvidenceQueue"]
    assert history["nctId"] == "NCT00000001"
    assert history["status"] == queue["status"]
    assert history["unresolvedCriteria"] == 60
    assert len(history["taskStates"]) == 60
    assert history["taskStates"][0][0].startswith("NCT00000001:L")
    assert all(len(x) == 3 for x in history["taskStates"])
    assert history["score"] is None and history["fdaPrediction"] == "ABSTAIN"
    assert "tasks" not in history  # no duplicate full queue prose
    with Session(engine) as session:
        old = list(session.scalars(
            select(main.CandidateAssessmentHistory)
            .where(main.CandidateAssessmentHistory.exact_id == exact_id)
        ))
        old_history_id = old[0].id
        frozen = copy.deepcopy(old[0].summary["advancedEvidenceQueue"])
        saved = session.get(main.FullTrialRecord, "NCT00000001")
        saved.summary = {**saved.summary, "phases": ["PHASE1"]}
        saved.fetched_at = datetime(2026, 10, 21, tzinfo=timezone.utc)
        session.commit()
    service.get_index(synchronous=True)
    with Session(engine) as session:
        old_version = session.get(main.CandidateAssessmentHistory, old_history_id)
        assert old_version.summary["advancedEvidenceQueue"] == frozen
    newer = service.exact_detail(exact_id)["history"][0]["advancedEvidenceQueue"]
    assert newer["deferredTaskIds"]
    assert newer["taskStates"] != frozen["taskStates"]


def test_whole_universe_queue_totals_are_counts_not_clinical_coverage(isolated):
    engine, snapshot = isolated
    # One source-linked program with a verified phase, one without a registry.
    with Session(engine) as session:
        source = session.get(main.FullTrialRecord, "NCT00000001")
        source.summary = {**source.summary, "phases": ["PHASE3"]}
        session.commit()
    index = service.get_index(synchronous=True)
    totals = index["advancedResearchQueueTotals"]
    assert totals["programs"] == index["total"] == 2
    assert totals["readyPrograms"] == 1
    assert totals["blockedPrograms"] == 1
    assert totals["noActiveGapPrograms"] == 0
    assert totals["activeTasks"] == 60
    assert totals["deferredCriteria"] == 0
    assert totals["reviewedCriteria"] == 0
    assert len(totals["byLevel"]) == 12
    assert all(totals["byLevel"][str(n)]["active"] == 5 for n in range(9, 21))
    assert "not an FDA prediction" in totals["meaning"]
    assert len(index["records"]) == 2
    assert all(len(record) == 5 for record in index["records"])


def test_unverified_entire_universe_cannot_masquerade_as_missing_evidence(isolated):
    _, _snapshot = isolated
    index = service.get_index(synchronous=True)
    totals = index["advancedResearchQueueTotals"]
    assert totals["programs"] == 2
    assert totals["blockedPrograms"] == 2
    assert totals["activeTasks"] == 0
    assert totals["reviewedCriteria"] == 0
