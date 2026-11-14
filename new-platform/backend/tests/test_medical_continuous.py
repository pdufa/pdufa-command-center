"""No live internet in tests; a completed source stage never implies FDA readiness."""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from app import medical_continuous as medical

NCT = "NCT00000001"



def test_packaged_application_context_preserves_three_unmapped_focus_exceptions():
    """Research context is source-linked but never treated as FDA-confirmed."""
    import json
    from pathlib import Path
    base=Path(medical.__file__).resolve().parent
    snapshot=json.loads((base/"data"/"focus_application_snapshot.json").read_text(encoding="utf-8"))
    original=(Path(__file__).resolve().parents[2]/
              "frontend"/"lib"/"medical-intelligence-applications.ts").read_text(encoding="utf-8")
    raw=original.split("export const APPLICATION_CYCLES:",1)[1].split("=[",1)[1].split("] as const;",1)[0]
    published=json.loads("["+raw+"]")
    assert snapshot["schemaVersion"]==1
    assert snapshot["asOf"]=="2026-11-07"
    assert snapshot["sourceVerifiedByFda"] is False
    assert len(published)==23
    rows=snapshot["records"]
    assert len(rows)==29
    assert set(medical.roster()) - {r["nct"] for r in rows} == {"NCT05031780", "NCT06747468", "NCT06553768"}
    assert {r["nct"] for r in rows} <= set(medical.roster())
    by_id={r["nct"]:r for r in rows}
    for study in published:
        for nct in study["ncts"]:
            assert any(a["cycleId"]==study["id"] and
                       a["indication"]==study["indication"] and
                       a["sourceUrl"]==study["sourceUrl"]
                       for a in by_id[nct]["candidateApplications"])
    assert all(row["designations"]==[] for row in rows)
    assert all(row["candidateApplications"] for row in rows)
    multi=medical.program_record("NCT02500381")
    assert len(multi["candidateApplications"])==2
    assert multi["indication"]==""
    assert multi["drug"]==""
    health=medical.application_roster_status()
    assert health["state"]=="PARTIAL"
    assert health["focusNctCount"]==32
    assert health["missingNctIds"]==sorted(set(medical.roster())-{r["nct"] for r in rows})
    assert health["coveredNctCount"]==29
    assert health["focusNctCount"]==32
    assert health["mappingCoverageComplete"] is False
    assert health["unmappedNcts"]==["NCT05031780", "NCT06553768", "NCT06747468"]
    assert health["applicationCycleCount"]==23
    assert "NCT02500381" in health["sharedIndicationUnresolvedNcts"]
    assert health["fdaApplicationStatusVerified"] is False
    capr=medical.program_record("NCT05126758")
    assert capr["indication"]=="Duchenne muscular dystrophy"
    assert capr["drug"]=="Deramiocel"
    assert capr["designations"]==[]


@pytest.mark.parametrize("change", ["drop_mapped", "duplicate", "invent_exception_mapping"])
def test_application_map_rejects_changes_beyond_known_unmapped_exceptions(tmp_path, monkeypatch, change):
    data=json.loads(medical.APPLICATIONS.read_text(encoding="utf-8"))
    if change == "drop_mapped":
        data["records"].pop()
    elif change == "duplicate":
        data["records"].append(data["records"][0])
    else:
        row=json.loads(json.dumps(data["records"][0]))
        row["nct"]="NCT05031780"
        data["records"].append(row)
    path=tmp_path/"synthetic_application_map.json"
    path.write_text(json.dumps(data),encoding="utf-8")
    monkeypatch.setattr(medical,"APPLICATIONS",path)
    with pytest.raises(ValueError):
        medical.application_roster_status()




def test_published_application_indication_leads_are_used_without_cross_indication_leakage(monkeypatch):
    terms=[]
    monkeypatch.setattr(medical,"pm_search",lambda term:terms.append(term) or [])
    state,known=medical.process_stage(5,"NCT05126758")
    assert state=="EVIDENCE_GAP"
    assert known["indication"]=="Duchenne muscular dystrophy"
    assert terms[-1].startswith("Duchenne muscular dystrophy")
    _,shared=medical.process_stage(5,"NCT02500381")
    assert shared["indication"]=="Not reconciled"
    assert "natural history" in terms[-1]
    _,related=medical.process_stage(6,"NCT05126758")
    assert related["drug"]=="Deramiocel"
    assert related["indication"]=="Duchenne muscular dystrophy"
    assert "Deramiocel" in terms[-1]
    assert "Duchenne" in terms[-1]



def test_packaged_focus_roster_matches_frontend_snapshot():
    # Render builds with Docker context new-platform/backend, so the runtime
    # cannot read its sibling frontend/data directory.
    packaged = Path(medical.__file__).resolve().parent / "data" / "focus_snapshot.json"
    frontend = Path(__file__).resolve().parents[2] / "frontend" / "data" / "p3PostDataActive.json"
    assert packaged.is_file(), "FOCUS roster must ship in the backend image"
    bundled = json.loads(packaged.read_text(encoding="utf-8"))
    original = json.loads(frontend.read_text(encoding="utf-8"))
    assert bundled["asOf"] == original["asOf"]
    assert len(bundled["records"]) == 32
    assert bundled["records"] == original["records"]


@pytest.fixture
def engine(tmp_path, monkeypatch):
    roster = tmp_path / "focus.json"
    roster.write_text(json.dumps({"records": [{"nct": NCT, "ticker": "TEST",
        "company": "Fixture", "regulatoryUrl": "https://example.com/research"}]}))
    monkeypatch.setattr(medical, "FOCUS", roster)
    applications = tmp_path / "applications.json"
    applications.write_text(json.dumps({"schemaVersion": 1, "asOf": "2026-11-07", "records": []}))
    monkeypatch.setattr(medical, "APPLICATIONS", applications)
    db = create_engine("sqlite:///" + str(tmp_path / "medical.sqlite3"),
                       connect_args={"check_same_thread": False})
    medical.initialize(db)
    yield db
    db.dispose()


def test_all_twelve_stages_run_continuously_and_abstain(engine):
    req = "00000000-0000-4000-8000-000000000001"
    seen = []
    snapshot = medical.create(engine, NCT, req, submit=False)
    assert snapshot["status"] == "PENDING"
    assert snapshot["completedStages"] == 0

    def stage(index, nct):
        assert nct == NCT
        seen.append(index)
        return ("SOURCE_RECORDED" if index == 0 else "LEADS_ONLY"), {"source": "https://example.com/", "search": index}

    medical.worker(engine, snapshot["runId"], step=stage)
    result = medical.latest(engine, NCT)
    assert result["status"] == "COMPLETE"
    assert result["completedStages"] == 12
    assert result["decision"] == "ABSTAIN"
    assert result["approvalProbability"] is None
    assert seen == list(range(12))
    assert [s["number"] for s in result["stages"]] == list(range(1, 13))
    assert result["stages"][8]["details"]["review"] == "SOURCE_COLLECTION_ONLY"
    assert result["stages"][8]["details"]["scientificSignoff"] is False
    # Repeating an already completed run does not fetch additional evidence.
    medical.worker(engine, result["runId"], step=lambda *_: pytest.fail("duplicate stage"))
    assert medical.create(engine, NCT, req, submit=False)["runId"] == result["runId"]


def test_fail_closed_when_official_trial_identity_cannot_be_read(engine):
    req = "00000000-0000-4000-8000-000000000002"
    job = medical.create(engine, NCT, req, submit=False)
    def unavailable(index, _):
        raise TimeoutError("fixture network unavailable")
    medical.worker(engine, job["runId"], step=unavailable)
    saved = medical.snapshot(engine, NCT, job["runId"])
    assert saved["status"] == "FAILED"
    assert saved["completedStages"] == 1
    assert saved["stages"][0]["state"] == "SOURCE_UNAVAILABLE"
    assert "failed" in saved["stages"][0]["details"]["gap"].lower()
    assert saved["decision"] == "ABSTAIN"


def test_stop_and_resume_from_saved_stage(engine, monkeypatch):
    req = "00000000-0000-4000-8000-000000000003"
    job = medical.create(engine, NCT, req, submit=False)
    count = 0
    def stage(index, nct):
        nonlocal count
        count += 1
        if index == 2:
            medical.stop(engine, NCT, job["runId"])
        return ("SOURCE_RECORDED" if index == 0 else "EVIDENCE_GAP"), {"index": index}
    medical.worker(engine, job["runId"], step=stage)
    stopped = medical.snapshot(engine, NCT, job["runId"])
    assert stopped["status"] == "STOPPED"
    assert stopped["completedStages"] == 3
    assert count == 3
    called = []
    monkeypatch.setattr(medical._POOL, "submit", lambda fn, *args: called.append((fn, args)))
    medical.resume(engine, NCT, job["runId"])
    assert called and called[0][0] is medical.worker
    medical.worker(engine, job["runId"], step=stage)
    final = medical.snapshot(engine, NCT, job["runId"])
    assert final["status"] == "COMPLETE"
    assert final["completedStages"] == 12


def test_duplicate_active_run_and_no_auto_start_from_read(engine):
    a = medical.create(engine, NCT, "00000000-0000-4000-8000-000000000004", submit=False)
    b = medical.create(engine, NCT, "00000000-0000-4000-8000-000000000005", submit=False)
    assert a["runId"] == b["runId"]
    assert medical.latest(engine, NCT)["completedStages"] == 0
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM medical_continuous_runs")).scalar_one() == 1
    with pytest.raises(ValueError):
        medical.create(engine, "NCT99999999", "00000000-0000-4000-8000-000000000006", submit=False)



def test_startup_requeues_all_29_unfinished_focus_runs(engine, monkeypatch):
    # Simulate the full FOCUS roster and a restart with more than 25 pending runs.
    records = [{"nct": f"NCT{i:08d}", "ticker": "TEST", "company": "Fixture"}
               for i in range(1, 30)]
    medical.FOCUS.write_text(json.dumps({"records": records}), encoding="utf-8")
    expected = set()
    for index, row in enumerate(records, 1):
        key = f"00000000-0000-4000-8000-{index:012d}"
        saved = medical.create(engine, row["nct"], key, submit=False)
        expected.add(saved["runId"])

    submitted = []
    monkeypatch.setattr(medical._POOL, "submit",
                        lambda fn, db, rid: submitted.append((fn, rid)))
    medical.start(engine)
    assert len(submitted) == 29
    assert {rid for _, rid in submitted} == expected
    assert all(fn is medical.worker for fn, _ in submitted)



def test_non_identity_network_outage_is_gap_and_run_can_finish(engine):
    req = "00000000-0000-4000-8000-000000000007"
    job = medical.create(engine, NCT, req, submit=False)
    def stage(index, nct):
        if index == 4:
            raise ConnectionError("FDA fixture inaccessible")
        return "SOURCE_RECORDED", {"source": "https://clinicaltrials.gov/study/" + nct}
    medical.worker(engine, job["runId"], step=stage)
    final = medical.snapshot(engine, NCT, job["runId"])
    assert final["status"] == "COMPLETE"
    assert final["stages"][4]["state"] == "SOURCE_UNAVAILABLE"
    assert final["decision"] == "ABSTAIN"
