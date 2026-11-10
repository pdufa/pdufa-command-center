"""Live installation counts keep source work, current grades and signoff distinct."""
import json
import uuid

import pytest
from sqlalchemy import create_engine, inspect, text

from app import installation_monitor as monitor
from app import medical_assessment_ledger as ledger
from app import medical_continuous as source

WHEN = "2026-11-08T18:00:00+00:00"


@pytest.fixture
def evidence_db(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "monitor.sqlite"))
    source.initialize(engine)
    ledger.initialize(engine, test_only=True)
    runs = {}
    with engine.begin() as c:
        for nct in sorted(source.roster()):
            run = runs[nct] = str(uuid.uuid4())
            c.execute(text("""INSERT INTO medical_continuous_runs
                (run_id,request_key,nct_id,status,stage_index,created_at,updated_at,stop_requested)
                VALUES(:run,:key,:nct,'COMPLETE',12,:at,:at,FALSE)"""),
                {"run": run, "key": str(uuid.uuid4()), "nct": nct, "at": WHEN})
            for i in range(12):
                doc = {"nct": nct, "phases": ["PHASE3"],
                       "source": "https://clinicaltrials.gov/study/" + nct}
                c.execute(text("""INSERT INTO medical_continuous_stages
                    (run_id,stage_index,state,document,finished_at)
                    VALUES(:run,:i,'SOURCE_RECORDED',:doc,:at)"""),
                    {"run": run, "i": i, "doc": json.dumps(doc), "at": WHEN})
    yield engine, runs
    engine.dispose()


def snapshot(engine):
    return monitor._medical_installation(engine, set(inspect(engine).get_table_names()),
                                         storage_ready=True)


def test_unavailable_or_missing_ledger_never_becomes_zero_progress(tmp_path):
    db = create_engine("sqlite:///" + str(tmp_path / "empty.sqlite"))
    assert monitor.collect(db, storage_ready=False)["medicalInstallation"]["counts"] is None
    result = snapshot(db)
    assert result["state"] == "UNKNOWN"
    assert result["counts"] is None
    assert "medical_assessment_trial_roster" in result["missingTables"]
    assert inspect(db).get_table_names() == []


def test_unseeded_roster_is_unobserved_not_graded_and_monitor_does_not_seed(evidence_db):
    db, _ = evidence_db
    result = snapshot(db)
    assert result["state"] == "OBSERVED"
    assert result["counts"]["observedTrialLedgers"] == 0
    assert result["counts"]["unobservedMethodPositions"] == 23200
    assert result["counts"]["recordedCurrentPhaseGrades"] == 0
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_trial_roster")).scalar() == 0


def test_source_completion_and_history_do_not_claim_scientific_completion(evidence_db):
    db, runs = evidence_db
    ledger.seed_roster(db)
    result = snapshot(db)
    counts = result["counts"]
    assert counts["sourceCompleteTrials"] == 29
    assert counts["sourceStages"] == 348
    assert counts["methodStates"]["VERIFY_PHASE"] == 23200
    assert counts["recordedCurrentPhaseGrades"] == 0
    assert counts["independentlySignedClinicalReviews"] is None
    assert result["currentTaskId"] == "medical.phase-verification"
    assert result["sourceCollectionDates"]["freshnessValidation"] == "NOT_ADJUDICATED"
    assert result["fdaPredictions"] == {"APPROVAL": "ABSTAIN", "CRL": "ABSTAIN", "REVIEW_DELAY": "ABSTAIN"}
    assert result["certainty"] == "NOT_VALIDATED"
    assert result["taskCounts"] == {"VERIFIED": 1, "ACTIVE": 1, "BLOCKED": 4, "UNKNOWN": 1}

    nct = sorted(runs)[0]
    phase = ledger.record_verified_phase(db, nct=nct, run_id=runs[nct], phase="PHASE3",
                                         reviewer_id="fixture-reviewer", verified_at=WHEN)
    first = ledger.append_review(db, nct=nct, run_id=runs[nct], phase_event_id=phase,
        assessment_index=1, method_index=1, disposition="SCORED", grade=4,
        evidence=[{"stageIndex": 0, "sourceUrl": "https://clinicaltrials.gov/study/" + nct}],
        rationale="Offline fixture validates projection only; this is not a real scientific review.",
        reviewer_id="fixture-reviewer", evidence_reviewed_at=WHEN)
    current = snapshot(db)
    assert current["counts"]["recordedCurrentPhaseGrades"] == 1
    assert current["counts"]["completedAssessments"] == 0
    ledger.append_review(db, nct=nct, run_id=runs[nct], phase_event_id=phase,
        assessment_index=1, method_index=1, disposition="RETRACTED", grade=None, evidence=[],
        rationale="Offline fixture retracts the synthetic grade; retain both revision events.",
        reviewer_id="fixture-reviewer", evidence_reviewed_at=WHEN, supersedes_event_id=first)
    after = snapshot(db)
    assert after["counts"]["historicalReviewEvents"] == 2
    assert after["counts"]["recordedCurrentPhaseGrades"] == 0
    assert after["counts"]["methodStates"]["RETRACTED"] == 1
    assert after["counts"]["pendingObservedMethods"] == 23200
    with db.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar() == 348
        assert c.execute(text("SELECT COUNT(*) FROM medical_assessment_review_events")).scalar() == 2
