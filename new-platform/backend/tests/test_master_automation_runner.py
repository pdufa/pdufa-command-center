"""Offline GitHub adapter regression tests. No network or production writes."""
import importlib.util
import io
import json
import sys
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[3] / "scripts/master_automation_runner.py"
spec = importlib.util.spec_from_file_location("master_runner", PATH)
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


def _zip(payload):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,"w") as archive:
        archive.writestr("artifact/report.json", json.dumps(payload))
    return stream.getvalue()


def test_manual_plan_prints_scope_without_external_calls(monkeypatch,capsys):
    monkeypatch.setattr(sys,"argv",["master_automation_runner.py","--mode","plan"])
    monkeypatch.setattr(runner,"backend",lambda *a,**k: (_ for _ in ()).throw(AssertionError("database touched")))
    monkeypatch.setattr(runner,"gh",lambda *a,**k: (_ for _ in ()).throw(AssertionError("github touched")))
    assert runner.main()==0
    out=capsys.readouterr().out
    assert "POOL MANAGED" in out and "FOCUS MANAGED" in out
    assert "ASSESSMENTS NOT_WIRED" in out
    assert "PLAN_ONLY" in out


def test_default_execution_opt_in_blocks_before_any_network(monkeypatch):
    monkeypatch.setattr(sys,"argv",["master_automation_runner.py","--mode","run","--run-key","test-controller"])
    monkeypatch.delenv("PDUFA_MASTER_ALLOW_EXECUTION",raising=False)
    monkeypatch.setattr(runner,"backend",lambda *a,**k: (_ for _ in ()).throw(AssertionError("database touched")))
    with pytest.raises(runner.ControllerError,match="EXECUTION_OPT_IN_DISABLED"):
        runner.main()


def test_in_progress_workflow_blocks_duplicate_dispatch(monkeypatch):
    monkeypatch.setattr(runner,"workflow_runs",lambda stage:[
        {"status":"completed","head_branch":"main"},
        {"status":"in_progress","head_branch":"main"}])
    with pytest.raises(runner.ControllerError,match="WORKFLOW_ALREADY_RUNNING"):
        runner.assert_not_running("FOCUS")


def test_correlated_run_rejects_other_scheduled_and_manual_runs(monkeypatch):
    now=datetime.now(timezone.utc)
    started=now-timedelta(seconds=7)
    stamp=started.isoformat().replace("+00:00","Z")
    expected="MASTER:12345678-aaaa-aaaa-aaaa-111111111111:FOCUS"
    monkeypatch.setattr(runner,"workflow_runs",lambda stage:[
        {"id":1,"event":"workflow_dispatch","display_title":expected,
         "head_branch":"main","created_at":(started-timedelta(minutes=30)).isoformat()},
        {"id":2,"event":"schedule","display_title":expected,
         "head_branch":"main","created_at":stamp},
        {"id":3,"event":"workflow_dispatch","display_title":"another run",
         "head_branch":"main","created_at":stamp},
        {"id":4,"event":"workflow_dispatch","display_title":expected,
         "head_branch":"main","created_at":stamp},
    ])
    actual=runner.correlated_run("FOCUS","12345678-aaaa-aaaa-aaaa-111111111111",now)
    assert actual["id"]==4
    assert runner.correlated_run("POOL","12345678-aaaa-aaaa-aaaa-111111111111",now) is None


def test_source_lineage_rejects_code_edits(monkeypatch):
    original="a"*40
    monkeypatch.setattr(runner,"default_sha",lambda:"b"*40)
    monkeypatch.setattr(runner,"gh",lambda *a,**k:{
        "status":"ahead","total_commits":1,
        "files":[{"filename":"scripts/pdufa-nightly-clinical.py"}]
    })
    with pytest.raises(runner.ControllerError,match="SOURCE_CODE_CHANGED_MID_RUN"):
        runner.source_lineage_ok(original)
    monkeypatch.setattr(runner,"gh",lambda *a,**k:{
        "status":"ahead","total_commits":1,
        "files":[{"filename":"new-platform/frontend/data/p3PostDataActive.json"}]
    })
    runner.source_lineage_ok(original)


def test_focus_success_requires_full_registry_and_coherent_promotion(monkeypatch):
    now=datetime.now(timezone.utc)
    audit={"status":"COMPLETE","asOf":now.isoformat(),"counts":{
        "POOL_RECORDS":11648,"CAP_ELIGIBLE":2732,
        "REGISTRY_QUERIED":2732,"REGISTRY_RECORDS_RETURNED":2732,
        "REVIEW_QUEUE":328,
    }}
    promo={"existing":32,"added":[],"total":32,
           "poolModified":False,"historicalScoresModified":False}
    def fake_gh(method,path,**kwargs):
        if "/runs/9001/jobs" in path:return {"jobs":[{"name":"sync","conclusion":"success"}],"total_count":1}
        return {"status":"completed","conclusion":"success"}
    monkeypatch.setattr(runner,"gh",fake_gh)
    monkeypatch.setattr(runner,"_artifact_json",lambda run,prefix,since:
        audit if prefix.startswith("focus-full") else promo)
    digest,found=runner.evidence("FOCUS",9001,now)
    assert len(digest)==64 and found["total"]==32 and found["reviewQueue"]==328
    monkeypatch.setattr(runner,"_artifact_json",lambda run,prefix,since:
        {**audit,"status":"PARTIAL_REGISTRY_MATCHES"} if prefix.startswith("focus-full") else promo)
    with pytest.raises(runner.ControllerError,match="FOCUS_POOL_COVERAGE_INCOMPLETE"):
        runner.evidence("FOCUS",9001,now)


def test_controller_never_promotes_unwired_stage(monkeypatch):
    monkeypatch.setattr(runner,"gh",lambda *a,**k:{"status":"completed","conclusion":"success"})
    with pytest.raises(runner.ControllerError,match="STAGE_NOT_IMPLEMENTED"):
        runner.evidence("ASSESSMENTS",42,datetime.now(timezone.utc))
