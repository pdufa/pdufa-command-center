"""Stage-2 ledger regression: exact-NCT provenance, no invented grades, append-only."""
from __future__ import annotations

import json
import os
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError, IntegrityError

from app import medical_continuous as source
from app import medical_assessment_ledger as ledger


def populated_history(db, nct, run):
    """Synthetic test reviews only; never a clinical review or live signoff."""
    when = "2026-11-08T18:00:00Z"
    phase = ledger.record_verified_phase(db, nct=nct, run_id=run,
        phase="PHASE3", reviewer_id="offline-fixture-reviewer", verified_at=when)
    ledger.append_review(db, nct=nct, run_id=run, phase_event_id=phase,
        assessment_index=1, method_index=1, disposition="SCORED", grade=3,
        evidence=[{"stageIndex": 0, "sourceUrl": "https://clinicaltrials.gov/study/" + nct}],
        rationale="Synthetic fixture verifies persistence, not independently assessed clinical evidence.",
        reviewer_id="offline-fixture-reviewer", evidence_reviewed_at=when)
    ledger.append_evidence_gap(db, nct=nct, run_id=run, assessment_index=1,
        method_index=2, gap_code="MISSING_ORIGINAL_PROTOCOL",
        evidence_note="Synthetic fixture has no independently examined original protocol.")
    return ledger.trial_history(db, nct)


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


def test_source_url_prefix_and_wrong_saved_registry_identity_fail_closed(seeded):
    db, focus, runs = seeded
    ledger.seed_roster(db)
    nct, other = focus[:2]
    when = "2026-11-08T18:00:00Z"
    phase = ledger.record_verified_phase(db, nct=nct, run_id=runs[nct],
        phase="PHASE3", reviewer_id="reviewer_one", verified_at=when)
    with pytest.raises(ValueError, match="saved source stage"):
        ledger.append_review(db, nct=nct, run_id=runs[nct], phase_event_id=phase,
            assessment_index=1, method_index=1, disposition="SCORED", grade=4,
            evidence=[{"stageIndex": 0, "sourceUrl": "https://clinicaltrials.gov/study/NCT"}],
            rationale="A URL prefix must never authenticate a saved original source.",
            reviewer_id="reviewer_one", evidence_reviewed_at=when)
    # Deliberately corrupt only the isolated fixture; immutable live sources
    # must never be changed to reconcile an identity mismatch.
    with db.begin() as c:
        c.execute(text("UPDATE medical_continuous_stages SET document=:doc WHERE run_id=:run AND stage_index=0"),
            {"doc": json.dumps({"source": "https://clinicaltrials.gov/study/" + other,
                                "nct": other, "phases": ["PHASE3"]}), "run": runs[nct]})
    with pytest.raises(ValueError, match="exact NCT"):
        ledger.record_verified_phase(db, nct=nct, run_id=runs[nct], phase="PHASE3",
            reviewer_id="reviewer_one", verified_at=when, supersedes_event_id=phase)
    assert ledger.trial_history(db, nct)["reviewEvents"] == []


def test_read_only_authenticated_route_shape_without_write_route(seeded):
    db,focus,_=seeded
    ledger.seed_roster(db)
    app=FastAPI()
    ledger.install_routes(app,lambda:db,lambda:None,lambda:None)
    client=TestClient(app)
    assert client.get("/api/internal/medical-assessments/coverage").json()["sourceComplete"]==29
    assert client.get("/api/internal/medical-assessments/"+focus[0]+"/history").json()["nct"]==focus[0]
    assert client.post("/api/internal/medical-assessments/coverage").status_code==405


def test_current_phase_method_matrix_is_read_only_and_no_source_lead_is_a_grade(seeded):
    db, focus, runs = seeded
    ledger.seed_roster(db)
    app = FastAPI()
    ledger.install_routes(app, lambda: db, lambda: None, lambda: None)
    client = TestClient(app)
    nct = focus[0]
    url = "/api/internal/medical-assessments/" + nct + "/matrix"
    before = client.get(url).json()
    assert before["totalPositions"] == 800
    assert before["counts"]["VERIFY_PHASE"] == 800
    assert before["counts"]["SCORED"] == 0
    assert before["fdaPredictions"]["APPROVAL"] == "ABSTAIN"

    phase_id = ledger.record_verified_phase(
        db, nct=nct, run_id=runs[nct], phase="PHASE3",
        reviewer_id="evidence_reviewer", verified_at="2026-11-08T18:00:00Z")
    after_phase = client.get(url + "?assessmentIndex=1").json()
    assert after_phase["counts"]["UNREVIEWED"] == 800
    assert after_phase["selectedAssessment"]["scoreOutOf100"] is None

    ledger.append_review(
        db, nct=nct, run_id=runs[nct], phase_event_id=phase_id,
        assessment_index=1, method_index=1, disposition="SCORED", grade=4,
        evidence=[{"stageIndex": 0, "sourceUrl": "https://clinicaltrials.gov/study/" + nct}],
        rationale="Verified source comparison with trial-specific statistical limitations.",
        reviewer_id="evidence_reviewer", evidence_reviewed_at="2026-11-08T18:00:00Z")
    reviewed = client.get(url + "?assessmentIndex=1").json()
    assert reviewed["counts"]["SCORED"] == 1
    assert reviewed["selectedAssessment"]["status"] == "PROVISIONAL"
    assert reviewed["selectedAssessment"]["scoreOutOf100"] == 80.0
    assert reviewed["selectedAssessment"]["methods"][0]["sourceEvidence"][0]["stageDocumentSha256"]
    assert client.get(url + "?assessmentIndex=41").status_code == 422
    assert client.post(url).status_code == 405
    assert reviewed["clinicalSignoff"] is False
    assert reviewed["certainty"] == "NOT_VALIDATED"


@pytest.mark.parametrize("table,column", [
    ("medical_assessment_trial_roster", "source_completed_at"),
    ("medical_assessment_phase_events", "reviewer_id"),
    ("medical_assessment_review_events", "rationale"),
    ("medical_assessment_gap_events", "evidence_note"),
])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_direct_mutations_rejected_without_losing_history(seeded, table, column, operation):
    db, focus, runs = seeded
    ledger.seed_roster(db)
    nct = focus[0]
    before = populated_history(db, nct, runs[nct])
    statement = (f"UPDATE {table} SET {column}=:changed WHERE nct_id=:nct"
                 if operation == "UPDATE" else f"DELETE FROM {table} WHERE nct_id=:nct")
    # Table and column names come only from the static test parameter list.
    with pytest.raises(IntegrityError, match="append-only"):
        with db.begin() as c:
            c.execute(text(statement), {"nct": nct, "changed": "Rejected accidental overwrite"})
    assert ledger.trial_history(db, nct) == before
    coverage = ledger.coverage(db)
    assert coverage["sourceComplete"] == 29
    assert coverage["sourceStageCount"] == 348
    assert coverage["phaseVerifiedNcts"] == 1
    assert coverage["reviewEvents"] == 1
    assert coverage["explicitGapEvents"] == 1


def test_initialize_and_seed_restart_preserve_existing_rows_and_allow_new_revisions(seeded):
    db, focus, runs = seeded
    ledger.seed_roster(db)
    nct = focus[0]
    before = populated_history(db, nct, runs[nct])
    with db.connect() as c:
        roster_before = list(c.execute(text("SELECT * FROM medical_assessment_trial_roster ORDER BY nct_id")))
        sources_before = list(c.execute(text("SELECT * FROM medical_continuous_stages ORDER BY run_id,stage_index")))
    for _ in range(2):
        ledger.initialize(db, test_only=True)
        assert ledger.seed_roster(db)["sourceComplete"] == 29
    assert ledger.trial_history(db, nct) == before
    with db.connect() as c:
        assert list(c.execute(text("SELECT * FROM medical_assessment_trial_roster ORDER BY nct_id"))) == roster_before
        assert list(c.execute(text("SELECT * FROM medical_continuous_stages ORDER BY run_id,stage_index"))) == sources_before
    original = before["reviewEvents"][0]
    ledger.append_review(db, nct=nct, run_id=runs[nct], phase_event_id=original["phase_event_id"],
        assessment_index=1, method_index=1, disposition="RETRACTED", grade=None, evidence=[],
        rationale="Synthetic fixture tests an append-only retraction after a repeated initialization.",
        reviewer_id="offline-fixture-reviewer", evidence_reviewed_at="2026-11-08T19:00:00Z",
        supersedes_event_id=original["review_event_id"])
    after = ledger.trial_history(db, nct)
    assert len(after["reviewEvents"]) == 2
    assert after["reviewEvents"][0] == original
    assert after["reviewEvents"][1]["supersedes_event_id"] == original["review_event_id"]
    assert after["reviewEvents"][1]["disposition"] == "RETRACTED"


def test_isolated_postgres_rejects_update_delete_truncate_and_preserves_restarts(seeded):
    """Optional real PostgreSQL contract test in a disposable loopback database.

    Remote databases are deliberately rejected. Each execution owns only its
    randomly named schema, which it removes after verifying the ledger.
    """
    configured = os.getenv("PDUFA_TEST_POSTGRES_URL")
    if not configured:
        pytest.skip("Isolated loopback PostgreSQL test database is not configured")
    url = make_url(configured)
    if (url.drivername != "postgresql+psycopg" or url.host not in ("127.0.0.1", "localhost")
            or url.port != 55432 or url.database != "pdufa_ledger_test" or url.query):
        pytest.fail("PostgreSQL ledger test requires the dedicated loopback test database")
    schema = "medical_ledger_test_" + uuid.uuid4().hex
    admin = create_engine(url)
    db = create_engine(url, connect_args={"options": "-csearch_path=" + schema})
    local, focus, runs = seeded
    created = False
    try:
        with admin.begin() as c:
            c.execute(text(f"CREATE SCHEMA {schema}"))
        created = True
        source.initialize(db)
        ledger.initialize(db)
        # Copy only synthetic local-fixture source runs into the owned schema.
        # No production records or real clinical review findings are involved.
        with local.connect() as c:
            source_runs = [dict(row) for row in c.execute(text("SELECT * FROM medical_continuous_runs")).mappings()]
            source_stages = [dict(row) for row in c.execute(text("SELECT * FROM medical_continuous_stages")).mappings()]
        for row in source_runs:
            row["stop_requested"] = bool(row["stop_requested"])
        with db.begin() as c:
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
                VALUES(:run_id,:request_key,:nct_id,:status,:stage_index,:created_at,:updated_at,:stop_requested)"""), source_runs)
            c.execute(text("""INSERT INTO medical_continuous_stages
                (run_id,stage_index,state,document,finished_at)
                VALUES(:run_id,:stage_index,:state,:document,:finished_at)"""), source_stages)
        ledger.seed_roster(db)
        nct = focus[0]
        before = populated_history(db, nct, runs[nct])
        counts = ledger.coverage(db)
        for table, column in (
            ("medical_assessment_trial_roster", "source_completed_at"),
            ("medical_assessment_phase_events", "reviewer_id"),
            ("medical_assessment_review_events", "rationale"),
            ("medical_assessment_gap_events", "evidence_note"),
        ):
            for statement in (
                f"UPDATE {table} SET {column}=:changed WHERE nct_id=:nct",
                f"DELETE FROM {table} WHERE nct_id=:nct",
                f"TRUNCATE {table} CASCADE",
            ):
                with pytest.raises(DBAPIError, match="append-only"):
                    with db.begin() as c:
                        c.execute(text(statement), {"nct": nct, "changed": "Rejected accidental overwrite"})
                assert ledger.trial_history(db, nct) == before
                assert ledger.coverage(db) == counts
        for _ in range(2):
            ledger.initialize(db)
            assert ledger.seed_roster(db) == counts
        assert ledger.trial_history(db, nct) == before
        original = before["reviewEvents"][0]
        ledger.append_review(db, nct=nct, run_id=runs[nct], phase_event_id=original["phase_event_id"],
            assessment_index=1, method_index=1, disposition="RETRACTED", grade=None, evidence=[],
            rationale="Synthetic PostgreSQL fixture verifies a new append-only revision after rejected DML.",
            reviewer_id="offline-fixture-reviewer", evidence_reviewed_at="2026-11-08T19:00:00Z",
            supersedes_event_id=original["review_event_id"])
        after = ledger.trial_history(db, nct)
        assert len(after["reviewEvents"]) == 2
        assert after["reviewEvents"][0] == original
        assert after["reviewEvents"][1]["supersedes_event_id"] == original["review_event_id"]
        assert after["reviewEvents"][1]["disposition"] == "RETRACTED"
    finally:
        db.dispose()
        if created:
            with admin.begin() as c:
                c.execute(text(f"DROP SCHEMA {schema} CASCADE"))
        admin.dispose()


def test_rejects_review_against_superseded_phase_and_another_saved_source_run(seeded):
    """A stale phase ID must never create a grade even if the label is the same."""
    db, focus, runs = seeded
    ledger.seed_roster(db)
    nct = focus[0]
    when = "2026-11-08T18:00:00Z"
    first = ledger.record_verified_phase(db, nct=nct, run_id=runs[nct],
        phase="PHASE3", reviewer_id="fixture_phase", verified_at=when)
    second = ledger.record_verified_phase(db, nct=nct, run_id=runs[nct],
        phase="PHASE3", reviewer_id="fixture_phase", verified_at=when,
        supersedes_event_id=first)
    review = dict(nct=nct,run_id=runs[nct],phase_event_id=first,
        assessment_index=1,method_index=1,disposition="SCORED",grade=3,
        evidence=[{"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+nct}],
        rationale="This test refuses a stale source-linked phase grade after a newer phase event.",
        reviewer_id="fixture_method",evidence_reviewed_at=when)
    with pytest.raises(ValueError,match="latest verified phase"):
        ledger.append_review(db,**review)
    assert ledger.trial_history(db,nct)["reviewEvents"] == []
    ledger.append_review(db,**{**review,"phase_event_id":second})
    assert len(ledger.trial_history(db,nct)["reviewEvents"]) == 1

    # An alternative complete source run must not replace the immutable
    # exact-NCT attachment, even if the source URL looks legitimate.
    alternate=str(uuid.uuid4())
    with db.begin() as c:
        c.execute(text("""INSERT INTO medical_continuous_runs
          (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
          VALUES(:run,:key,:nct,'COMPLETE',12,:now,:now,FALSE)"""),
          {"run":alternate,"key":str(uuid.uuid4()),"nct":nct,"now":when})
        for i in range(12):
            c.execute(text("""INSERT INTO medical_continuous_stages
              (run_id,stage_index,state,document,finished_at)
              VALUES(:run,:idx,'SOURCE_RECORDED',:document,:now)"""),
              {"run":alternate,"idx":i,"document":json.dumps({
                  "nct":nct,"source":"https://clinicaltrials.gov/study/"+nct,"phases":["PHASE3"]}),
               "now":when})
    with pytest.raises(ValueError,match="roster-attached"):
        ledger.record_verified_phase(db,nct=nct,run_id=alternate,phase="PHASE3",
            reviewer_id="fixture_phase",verified_at=when,supersedes_event_id=second)
    with pytest.raises(ValueError,match="roster-attached"):
        ledger.append_review(db,**{**review,"run_id":alternate,"phase_event_id":second,
                                    "supersedes_event_id":ledger.trial_history(db,nct)["reviewEvents"][0]["review_event_id"]})


def test_isolated_human_reviewer_writes_are_role_bound_and_default_disabled(seeded, monkeypatch):
    from app import medical_reviewer_submission as intake
    db,focus,runs=seeded
    ledger.seed_roster(db)
    nct="NCT06081894"
    assert nct in focus
    app=FastAPI()
    intake.install_routes(app,lambda:db,lambda:None,lambda:None)
    client=TestClient(app)
    when=__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat()
    phase_body={
        "sourceRunId":runs[nct],"verifiedPhase":"PHASE3","verifiedAt":when,
        "attestation":intake.PHASE_ATTESTATION}
    phase_url=f"/api/internal/medical-reviewer-intake/{nct}/phase"
    method_url=f"/api/internal/medical-reviewer-intake/{nct}/method"
    phase_headers={"X-PDUFA-Reviewer-Id":"phase_reviewer","X-PDUFA-Reviewer-Key":"P"*40}
    method_headers={"X-PDUFA-Reviewer-Id":"method_reviewer","X-PDUFA-Reviewer-Key":"M"*40}
    assert client.post(phase_url,headers=phase_headers,json=phase_body).status_code==503
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEW_WRITES_ENABLED","true")
    assert client.post(phase_url,headers=phase_headers,json=phase_body).status_code==503
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEWER_CREDENTIALS_JSON",json.dumps({
        "phase":{"phase_reviewer":"P"*40},"method":{"method_reviewer":"M"*40}}))
    assert client.post(phase_url,headers=method_headers,json=phase_body).status_code==401
    assert client.post(method_url,headers=phase_headers,json={}).status_code in (401,422)
    assert client.post(phase_url,headers=phase_headers,
        json={**phase_body,"inventedClinicalScore":5}).status_code==422
    assert ledger.trial_history(db,nct)["phaseEvents"]==[]

    first=client.post(phase_url,headers=phase_headers,json=phase_body)
    assert first.status_code==201,first.text
    phase_id=first.json()["eventId"]
    assert first.json()["fdaPredictions"]["APPROVAL"]=="ABSTAIN"
    assert first.json()["clinicalSignoff"] is False
    method_body={
      "sourceRunId":runs[nct],"currentPhaseEventId":phase_id,
      "assessmentIndex":1,"methodIndex":1,"disposition":"SCORED","grade":0,
      "sourceEvidence":[{"stageIndex":0,"sourceUrl":"https://clinicaltrials.gov/study/"+nct,
        "classification":"UNFAVORABLE","sourceLocation":"Registry source test fixture",
        "examinedFinding":"This is an explicitly synthetic reviewer finding against a saved source; no real clinical fact is asserted."}],
      "rationale":"Synthetic evidence comparison for the test fixture: a numeric zero here means an actual signed review in a fixture, not missing source data.",
      "evidenceReviewedAt":when,"attestation":intake.METHOD_ATTESTATION
    }
    missing=client.post(method_url,headers=method_headers,json={
        **method_body,"sourceEvidence":[{**method_body["sourceEvidence"][0],
                                         "classification":"MISSING"}]})
    assert missing.status_code==422
    denied=client.post(method_url,headers=phase_headers,json=method_body)
    assert denied.status_code==401
    actual=client.post(method_url,headers=method_headers,json=method_body)
    assert actual.status_code==201,actual.text
    assert actual.json()["certainty"]=="NOT_VALIDATED"
    history=ledger.trial_history(db,nct)
    assert history["reviewEvents"][0]["grade"]==0
    assert history["reviewEvents"][0]["reviewer_id"]=="method_reviewer"
    assert history["scientificSignoff"] is False
    assert client.post(method_url,headers=method_headers,json=method_body).status_code==409
    assert len(ledger.trial_history(db,nct)["reviewEvents"])==1
    wrong=f"/api/internal/medical-reviewer-intake/NCT00000001/phase"
    assert client.post(wrong,headers=phase_headers,json=phase_body).status_code==404
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEW_WRITES_ENABLED","false")
    assert client.post(phase_url,headers=phase_headers,json=phase_body).status_code==503


def test_reviewer_configuration_rejects_shared_identity_or_shared_secret(monkeypatch):
    from app import medical_reviewer_submission as intake
    monkeypatch.setenv("PDUFA_MEDICAL_REVIEW_WRITES_ENABLED","true")
    for settings in (
        {"phase":{"same":"P"*40},"method":{"same":"M"*40}},
        {"phase":{"phase":"P"*40},"method":{"method":"P"*40}},
        {"phase":{"phase":"short"},"method":{"method":"M"*40}},
        {"phase":{"phase":"P"*40},"method":{}},
    ):
        monkeypatch.setenv("PDUFA_MEDICAL_REVIEWER_CREDENTIALS_JSON",json.dumps(settings))
        with pytest.raises(__import__("fastapi").HTTPException) as exc:
            intake._authenticate("phase","P"*40,"phase")
        assert exc.value.status_code==503
