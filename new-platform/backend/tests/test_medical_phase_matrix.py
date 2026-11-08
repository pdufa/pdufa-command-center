"""Stage-3 phase-first matrix tests: all 29 × 800 are prompts, not fake science."""
import json
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app import medical_continuous as core
from app import medical_assessment_ledger as ledger
from app import medical_phase_matrix as matrix

PILOT = "NCT06081894"
OTHER = "NCT05507203"
WHEN = "2026-11-08T17:30:00+00:00"


@pytest.fixture
def seeded(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "research.sqlite"),
                           connect_args={"check_same_thread": False})
    core.initialize(engine)
    ids = sorted(core.roster())
    with engine.begin() as c:
        for nct in ids:
            run = str(uuid.uuid4())
            c.execute(text("""INSERT INTO medical_continuous_runs
              (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
              VALUES(:run,:key,:nct,'COMPLETE',12,:now,:now,FALSE)"""),
              {"run":run,"key":str(uuid.uuid4()),"nct":nct,"now":WHEN})
            for i in range(12):
                phases = (["PHASE2","PHASE3"] if nct == PILOT else
                          ["PHASE1"] if nct == OTHER else ["PHASE3"])
                document = {"nct":nct,"source":"https://clinicaltrials.gov/study/"+nct,
                            "title":"Offline evidence only", "phases":phases}
                c.execute(text("""INSERT INTO medical_continuous_stages
                    (run_id,stage_index,state,document,finished_at)
                    VALUES(:run,:i,'SOURCE_RECORDED',:doc,:now)"""),
                    {"run":run,"i":i,"doc":json.dumps(document),"now":WHEN})
    ledger.initialize(engine,test_only=True)
    ledger.seed_roster(engine)
    yield engine
    engine.dispose()


def test_catalog_exactly_8_by_5_by_20_without_conflicting_phase_priorities():
    c = matrix.catalog()
    assert len(c["layers"]) == 8
    assert len(c["assessments"]) == 40
    assert len(c["methods"]) == 20
    assert c["assessments"][0]["id"] == "1.1"
    assert c["assessments"][-1]["id"] == "8.5"
    assert c["phasePriority"]["critical"]["PHASE3"]
    assert c["phaseRiskWatchlist"]["EARLY_PHASE1"]


def test_all_29_coverage_exposes_23200_unscored_positions(seeded):
    report=matrix.coverage(seeded)
    assert report["status"]=="READY_FOR_PHASE_REVIEW"
    assert report["trialCount"]==29
    assert report["sourceComplete"]==29
    assert report["sourceStages"]==348
    assert report["totalPotentialPositions"]==23200
    assert report["savedReviewEvents"]==0
    assert report["phaseVerifiedNcts"]==0
    assert report["scientificSignoff"] is False
    assert report["fdaPrediction"]=="ABSTAIN"


def test_reported_phase_is_only_provisional_investigation_priority(seeded):
    row=matrix.matrix(seeded,"NCT05126758")
    assert row["phase"]=="PHASE3"
    assert row["phaseBasis"]=="PROVISIONAL_REGISTRY_REPORT"
    assert row["sourceResearchStages"]==12
    assert row["testPositions"]==800
    assert len(row["assessments"])==40
    assert all(len(a["methods"])==20 for a in row["assessments"])
    assert sum(x["grade"] is not None for a in row["assessments"] for x in a["methods"])==0
    assert row["reviewedMethodPositions"]==0
    assert row["completedAssessmentCount"]==0
    assert all(a["finalScore"] is None and a["provisionalScore"] is None
               for a in row["assessments"])
    ranks=[x["priorityRank"] for a in row["assessments"] for x in a["methods"]]
    assert sorted(ranks)==list(range(1,801))
    assert row["phaseRiskQuestions"]
    assert all(q["status"]=="PROMPT_NOT_OBSERVED_RISK" for q in row["phaseRiskQuestions"])
    assert row["observedClinicalRiskFindings"]==[]
    assert row["latestVerifiedClinicalMilestone"] is None
    assert row["priorCompletedPhaseBenchmark"] is None
    assert row["fdaPredictions"]["approval"]=="ABSTAIN"
    assert row["certainty"]=="NOT_VALIDATED"


def test_multi_phase_registry_requires_verification_and_no_priority_rank(seeded):
    row=matrix.matrix(seeded,PILOT)
    assert row["phase"]=="UNKNOWN"
    assert row["phaseBasis"]=="VERIFY_PHASE_FIRST"
    assert row["investigationPriority"]["rankedPositions"]==0
    assert all(t["priorityTier"]=="VERIFY_PHASE" and t["priorityRank"] is None
               for a in row["assessments"] for t in a["methods"])


def test_scored_review_only_when_independent_phase_event_and_exact_source(seeded):
    before=matrix.matrix(seeded,OTHER)
    assert before["phase"]=="PHASE1"
    assert before["phaseBasis"]=="PROVISIONAL_REGISTRY_REPORT"
    history=ledger.trial_history(seeded,OTHER)
    run=history["sourceRunId"]
    verified=ledger.record_verified_phase(seeded,nct=OTHER,run_id=run,
        phase="PHASE1",reviewer_id="licensed-reviewer-01",verified_at=WHEN)
    ledger.append_review(seeded,nct=OTHER,run_id=run,phase_event_id=verified,
        assessment_index=1,method_index=1,disposition="SCORED",grade=3,
        evidence=[{"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+OTHER}],
        rationale="Source review is preliminary; replication and outcome validation remain unavailable.",
        reviewer_id="licensed-reviewer-01",evidence_reviewed_at=WHEN)
    after=matrix.matrix(seeded,OTHER)
    assert after["phaseBasis"]=="REVIEWER_VERIFIED"
    a=after["assessments"][0]
    assert a["scoredMethods"]==1 and a["unreviewedMethods"]==19
    assert a["gradeStatus"]=="PROVISIONAL"
    assert a["finalScore"] is None
    assert a["provisionalScore"]==60
    assert a["methods"][0]["grade"]==3
    assert a["methods"][0]["review"]["evidence"][0]["sourceUrl"]=="https://clinicaltrials.gov/study/"+OTHER
    assert after["scientificSignoff"] is False
    assert after["fdaPredictions"]["crl"]=="ABSTAIN"


def test_20_reviewed_methods_can_complete_one_assessment_not_entire_trial(seeded):
    row=ledger.trial_history(seeded,OTHER)
    run=row["sourceRunId"]
    eid=ledger.record_verified_phase(seeded,nct=OTHER,run_id=run,
        phase="PHASE1",reviewer_id="evidence-reviewer",verified_at=WHEN)
    for method in range(1,21):
        ledger.append_review(seeded,nct=OTHER,run_id=run,phase_event_id=eid,
            assessment_index=4,method_index=method,disposition="SCORED",grade=4,
            evidence=[{"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+OTHER}],
            rationale="A saved registry record supports preliminary document provenance review only.",
            reviewer_id="evidence-reviewer",evidence_reviewed_at=WHEN)
    row=matrix.matrix(seeded,OTHER)
    one=row["assessments"][3]
    assert one["gradeStatus"]=="COMPLETE"
    assert one["finalScore"]==80
    assert row["completedAssessmentCount"]==1
    assert row["reviewedMethodPositions"]==20
    assert all(a["gradeStatus"]=="NOT_REVIEWED" for a in row["assessments"] if a!=one)
    assert row["scientificSignoff"] is False


def test_last_completed_phase_never_fabricated_from_latest_phase(seeded):
    history=ledger.trial_history(seeded,PILOT)
    run=history["sourceRunId"]
    first=ledger.record_verified_phase(seeded,nct=PILOT,run_id=run,
        phase="PHASE2",reviewer_id="reviewer_phase",verified_at=WHEN)
    ledger.append_review(seeded,nct=PILOT,run_id=run,phase_event_id=first,
        assessment_index=1,method_index=1,disposition="SCORED",grade=2,
        evidence=[{"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+PILOT}],
        rationale="Phase two preliminary signals need formal endpoint review and replication.",
        reviewer_id="reviewer_phase",evidence_reviewed_at=WHEN)
    second=ledger.record_verified_phase(seeded,nct=PILOT,run_id=run,
        phase="PHASE3",reviewer_id="reviewer_phase",verified_at=WHEN,
        supersedes_event_id=first)
    assert second!=first
    report=matrix.matrix(seeded,PILOT)
    assert report["phase"]=="PHASE3"
    assert report["reviewedMethodPositions"]==0
    assert report["priorCompletedPhaseBenchmark"] is None
    assert report["latestVerifiedClinicalMilestone"] is None


def test_read_only_matrix_routes_and_reject_unknown_nct(seeded):
    app=FastAPI()
    matrix.install_routes(app,lambda:seeded,lambda:None,lambda:None)
    client=TestClient(app)
    assert client.get("/api/internal/medical-phase-matrix/coverage").json()["sourceComplete"]==29
    row=client.get("/api/internal/medical-phase-matrix/NCT05126758")
    assert row.status_code==200 and row.json()["testPositions"]==800
    assert client.post("/api/internal/medical-phase-matrix/coverage").status_code==405
    assert client.get("/api/internal/medical-phase-matrix/NCT99999999").status_code==422
