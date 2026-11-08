"""Stage-2 ledger regression: exact-NCT provenance, no invented grades, append-only."""
from __future__ import annotations

import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import medical_continuous as source
from app import medical_assessment_ledger as ledger


@pytest.fixture
def seeded(tmp_path):
    db = create_engine("sqlite:///" + str(tmp_path / "assessments.sqlite"),
                       connect_args={"check_same_thread": False})
    source.initialize(db)
    focus = sorted(source.roster())
    runs = {}
    now = "2026-11-08T17:05:00+00:00"
    with db.begin() as c:
        for nct in focus:
            run_id = str(uuid.uuid4())
            runs[nct] = run_id
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
                VALUES (:run,:key,:nct,'COMPLETE',12,:now,:now,FALSE)"""),
                {"run":run_id, "key":str(uuid.uuid4()),"nct":nct,"now":now})
            for index in range(12):
                document = {"source":"https://clinicaltrials.gov/study/" + nct,
                            "nct":nct, "phases":["PHASE3"],
                            "stageResearchOnly":True}
                c.execute(text("""INSERT INTO medical_continuous_stages
                    (run_id,stage_index,state,document,finished_at)
                    VALUES(:run,:index,'SOURCE_RECORDED',:document,:now)"""),
                    {"run":run_id, "index":index, "document":json.dumps(document),
                     "now":now})
    ledger.initialize(db,test_only=True)
    yield db,focus,runs
    db.dispose()


def test_all_29_source_runs_become_29_unscored_assessment_rows(seeded):
    db, focus, runs = seeded
    report = ledger.seed_roster(db)
    assert len(focus) == 29
    assert report["status"] == "READY_FOR_REVIEW"
    assert report["sourceComplete"] == 29
    assert report["canonicalTrials"] == 29
    assert report["sourceStageCount"] == 348
    assert report["potentialMethodPositions"] == 23200
    assert report["phaseVerifiedNcts"] == 0
    assert report["reviewEvents"] == 0
    assert report["scientificSignoff"] is False
    assert report["fdaPrediction"] == "ABSTAIN"
    assert report["certainty"] == "NOT_VALIDATED"
    assert ledger.seed_roster(db)["sourceComplete"] == 29  # idempotent restart
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_trial_roster")).scalar_one() == 29
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar_one() == 348
    item = ledger.trial_history(db,focus[0])
    assert item["sourceRunId"] == runs[focus[0]]
    assert item["scientificGradeStatus"] == "NOT_REVIEWED"
    assert item["phaseStatus"] == "NOT_VERIFIED"
    assert item["reviewEvents"] == []
    assert item["potentialMethodPositions"] == 800
    assert item["fdaPrediction"] == "ABSTAIN"


def test_missing_source_stage_fails_closed_without_partial_seed(seeded):
    db,focus,runs = seeded
    with db.begin() as c:
        c.execute(text("DELETE FROM medical_continuous_stages WHERE run_id=:run AND stage_index=11"),
                  {"run":runs[focus[0]]})
    with pytest.raises(RuntimeError, match="Refusing partial"):
        ledger.seed_roster(db)
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_trial_roster")).scalar_one() == 0


def test_explicit_phase_and_source_provenanced_grades_are_append_only(seeded):
    db,focus,runs = seeded
    ledger.seed_roster(db)
    nct = focus[0]
    when = "2026-11-08T17:10:00+00:00"
    phase = ledger.record_verified_phase(db,nct=nct,run_id=runs[nct],
        phase="PHASE3",reviewer_id="reviewer_one",verified_at=when)
    before = ledger.trial_history(db,nct)
    assert before["phaseStatus"] == "REVIEWED"
    assert before["scientificGradeStatus"] == "NOT_REVIEWED"
    evidence = [{"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+nct}]
    first = ledger.append_review(db,nct=nct,run_id=runs[nct],phase_event_id=phase,
        assessment_index=1,method_index=1,disposition="SCORED",grade=3,
        evidence=evidence,rationale="Preliminary source review documents limitations and outcome data.",
        reviewer_id="reviewer_one",evidence_reviewed_at=when)
    with pytest.raises(ValueError, match="supersede"):
        ledger.append_review(db,nct=nct,run_id=runs[nct],phase_event_id=phase,
            assessment_index=1,method_index=1,disposition="SCORED",grade=4,
            evidence=evidence,rationale="New source review needs an explicit earlier event reference.",
            reviewer_id="reviewer_one",evidence_reviewed_at=when)
    second = ledger.append_review(db,nct=nct,run_id=runs[nct],phase_event_id=phase,
        assessment_index=1,method_index=1,disposition="SCORED",grade=4,
        evidence=evidence,rationale="Later independent assessment with newly reviewed source context.",
        reviewer_id="reviewer_two",evidence_reviewed_at=when,supersedes_event_id=first)
    assert first != second
    history = ledger.trial_history(db,nct)
    assert [r["revision"] for r in history["reviewEvents"]] == [1,2]
    assert [r["grade"] for r in history["reviewEvents"]] == [3,4]
    assert history["reviewEvents"][1]["supersedes_event_id"] == first
    assert len(history["reviewEvents"][0]["evidence"][0]["stageDocumentSha256"]) == 64
    assert history["scientificSignoff"] is False
    assert ledger.coverage(db)["reviewEvents"] == 2
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar_one() == 348


def test_missing_fabricated_or_wrong_trial_evidence_never_becomes_score(seeded):
    db,focus,runs = seeded
    ledger.seed_roster(db)
    nct,other = focus[0],focus[1]
    when="2026-11-08T17:10:00+00:00"
    with pytest.raises(ValueError, match="phase"):
        ledger.record_verified_phase(db,nct=nct,run_id=runs[nct],
            phase="PHASE4",reviewer_id="reviewer_one",verified_at=when)
    phase=ledger.record_verified_phase(db,nct=nct,run_id=runs[nct],
        phase="PHASE3",reviewer_id="reviewer_one",verified_at=when)
    kwargs=dict(nct=nct,run_id=runs[nct],phase_event_id=phase,assessment_index=1,
                method_index=2,disposition="SCORED",grade=2,
                rationale="Recorded preliminary source has specific method uncertainty.",
                reviewer_id="reviewer_one",evidence_reviewed_at=when)
    with pytest.raises(ValueError,match="captured"):
        ledger.append_review(db,**kwargs,evidence=[])
    with pytest.raises(ValueError,match="saved source stage"):
        ledger.append_review(db,**kwargs,evidence=[
            {"stageIndex":0,"sourceUrl":"https://example.com/forged"}])
    with pytest.raises(ValueError,match="12-stage source"):
        ledger.append_review(db,**{**kwargs,"nct":other},evidence=[
            {"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+nct}])
    with pytest.raises(ValueError,match="grade"):
        ledger.append_review(db,**{**kwargs,"grade":9},evidence=[
            {"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+nct}])
    assert ledger.trial_history(db,nct)["reviewEvents"]==[]


def test_explicit_evidence_gaps_have_independent_append_only_history(seeded):
    db,focus,runs = seeded
    ledger.seed_roster(db)
    nct=focus[0]
    gap_id=ledger.append_evidence_gap(db,nct=nct,run_id=runs[nct],
        assessment_index=3,method_index=11,gap_code="NO_POSTED_ENDPOINT_RESULTS",
        evidence_note="No prespecified primary outcome results were independently confirmed.")
    history=ledger.trial_history(db,nct)
    assert history["reviewEvents"]==[]
    assert history["explicitGapEvents"][0]["gap_event_id"]==gap_id
    assert history["scientificGradeStatus"]=="NOT_REVIEWED"
    assert ledger.coverage(db)["explicitGapEvents"]==1


def test_read_only_authenticated_route_shape_without_write_route(seeded):
    db,focus,_=seeded
    ledger.seed_roster(db)
    app=FastAPI()
    ledger.install_routes(app,lambda:db,lambda:None,lambda:None)
    client=TestClient(app)
    assert client.get("/api/internal/medical-assessments/coverage").json()["sourceComplete"]==29
    assert client.get("/api/internal/medical-assessments/"+focus[0]+"/history").json()["nct"]==focus[0]
    assert client.post("/api/internal/medical-assessments/"+focus[0]+"/reviews").status_code==405
