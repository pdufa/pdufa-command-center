"""Controlled three-NCT batch requires real stage stop/resume, unique IDs and saved history.

Test network calls are replaced by deterministic fixtures; the deployed batch
uses the official registry and never fabricates research source results.
"""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

from app import medical_continuous as core
from app import medical_on_demand as saved
from app import medical_pilot_batch as batch

TRIALS=("NCT05507203","NCT04576949","NCT05126758")
CAMPAIGN="NOV08_BATCH_A"


def configure(monkeypatch):
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_AUTORUN","true")
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_CAMPAIGN",CAMPAIGN)
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_NCTS",",".join(TRIALS))
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","false")
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_CANARY_NCT","NCT06081894")


def test_batch_allowlist_only_three_and_original_canary(monkeypatch):
    configure(monkeypatch)
    assert batch.requested()==(CAMPAIGN,TRIALS)
    assert batch.allowed_ncts()==set(TRIALS)
    assert all(saved.eligible_for_analysis(nct) for nct in TRIALS)
    assert saved.eligible_for_analysis("NCT06081894")
    assert not saved.eligible_for_analysis("NCT05507216")
    assert not saved.eligible_for_analysis("NCT99999999")
    assert batch._idempotency(CAMPAIGN,TRIALS[0])==batch._idempotency(CAMPAIGN,TRIALS[0])
    assert batch._idempotency(CAMPAIGN,TRIALS[0])!=batch._idempotency(CAMPAIGN,TRIALS[1])


@pytest.mark.parametrize("ncts",[
    "NCT05507203,NCT05507203,NCT05126758",
    "NCT06081894,NCT04576949,NCT05126758",
    "NCT99999999,NCT04576949,NCT05126758",
    "NCT05507203",
    "NCT05507203,NCT04576949,NCT05126758,NCT05244304",
    "NCT05507203,NCT04576949,NCTXXXXYYYY",
])
def test_invalid_cohorts_fail_before_writes(monkeypatch,ncts):
    configure(monkeypatch)
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_NCTS",ncts)
    with pytest.raises(ValueError):
        batch.requested()


def test_global_all_rollout_cannot_be_used_with_batch(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("PDUFA_ANALYZE_NOW_ALL_ENABLED","true")
    with pytest.raises(ValueError, match="Global"):
        batch.requested()


def test_batch_inactive_does_not_start_on_import_or_startup(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("PDUFA_MEDICAL_BATCH_AUTORUN","false")
    assert batch.requested() is None
    assert batch.allowed_ncts()==set()


def test_controlled_first_trial_stops_after_real_stage_then_resumes_without_duplicates(
        tmp_path,monkeypatch):
    configure(monkeypatch)
    focus=tmp_path/"focus.json"
    focus.write_text(json.dumps({"records":[{"nct":x,"ticker":"TEST",
                                              "company":"Fixture"} for x in TRIALS]}),
                     encoding="utf-8")
    monkeypatch.setattr(core,"FOCUS",focus)
    engine=create_engine("sqlite+pysqlite:///:memory:")
    core.initialize(engine)
    with engine.begin() as c:
        c.execute(text("""CREATE TABLE medical_batch_campaigns (
            campaign_key TEXT PRIMARY KEY, first_nct TEXT NOT NULL,
            stop_resume_verified BOOLEAN NOT NULL DEFAULT FALSE,
            verified_at TEXT, details TEXT NOT NULL DEFAULT 'PENDING')"""))
        c.execute(text("""INSERT INTO medical_batch_campaigns(campaign_key,first_nct)
            VALUES(:campaign,:first)"""),{"campaign":CAMPAIGN,"first":TRIALS[0]})

    stage_calls=[]
    def actual_source_fixture(index,nct):
        stage_calls.append(index)
        assert nct==TRIALS[0]
        state="SOURCE_RECORDED" if index==0 else "EVIDENCE_GAP"
        return state,{"source":"https://clinicaltrials.gov/study/"+nct,"index":index}
    monkeypatch.setattr(core,"process_stage",actual_source_fixture)
    # Resume dispatch executes inline for a deterministic integration test.
    monkeypatch.setattr(core._POOL,"submit",
                        lambda fn,*args: fn(*args,step=actual_source_fixture))
    result=batch._one(engine,CAMPAIGN,TRIALS[0],stop_after_first=True)
    assert result["status"]=="COMPLETE"
    assert result["completedStages"]==12
    assert result["revision"]==1
    assert stage_calls==list(range(12))  # real first stage executed ONCE
    assert batch._proof(engine,CAMPAIGN,TRIALS[0])
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_runs")).scalar_one()==1
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_stages")).scalar_one()==12
        assert c.execute(text("SELECT COUNT(*) FROM medical_prediction_revisions")).scalar_one()==1

    # Recreating the same campaign must not cause a second revision or source fetch.
    same=batch._one(engine,CAMPAIGN,TRIALS[0],stop_after_first=True)
    assert same["runId"]==result["runId"] and same["revision"]==1
    assert stage_calls==list(range(12))
    engine.dispose()
