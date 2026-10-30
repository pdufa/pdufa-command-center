"""Stage-1 evidence-stream tests use synthetic registry fixtures, never live claims."""
from copy import deepcopy
import hashlib
import json
import os
import threading
from types import SimpleNamespace

from fastapi import FastAPI, Header, HTTPException
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError

from app import nct_live_stream as live


NCT = "NCT00000001"
OTHER = "NCT00000002"


def registry_study(nct=NCT):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": "Synthetic stream test"},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Fixture Sponsor"}},
        "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "Fixture Drug"}]},
        "conditionsModule": {"conditions": ["Fixture Disease"]},
        "designModule": {"phases": ["PHASE3"]},
        "outcomesModule": {"primaryOutcomes": [{"measure": "Overall Survival"}]},
        "statusModule": {"overallStatus": "COMPLETED"},
    }, "resultsSection": {
        "outcomeMeasuresModule": {"outcomeMeasures": [{"type": "PRIMARY", "title": "Overall Survival", "analyses": [{"pValue": "0.02", "paramValue": "0.8"}]}]},
        "adverseEventsModule": {"eventGroups": [{"id": "G1", "seriousNumAffected": 0, "seriousNumAtRisk": 10}], "seriousEvents": []},
    }}


def saved_document(nct=NCT):
    return {"nct_id": nct, "sponsor": {"name": "Fixture Sponsor"}, "products": [{"type": "DRUG", "name": "Fixture Drug"}], "indication": ["Fixture Disease"], "phase": ["PHASE3"], "scientific_score": None, "trade_authorized": False}


def fetcher(nct=NCT):
    study = registry_study(nct)
    raw = json.dumps(study).encode()
    return study, {"url": "https://clinicaltrials.gov/api/v2/studies/" + nct,
                   "sha256": hashlib.sha256(raw).hexdigest(), "verified_at": "2026-10-30T20:00:00+00:00", "http_status": 200}


@pytest.fixture
def engine(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "stream.sqlite3"), connect_args={"check_same_thread": False})
    with engine.begin() as c:
        c.execute(text("CREATE TABLE scientific_review_runs (run_id TEXT PRIMARY KEY, verified_at TEXT)"))
        c.execute(text("CREATE TABLE scientific_candidate_dossiers (run_id TEXT,nct_id TEXT,document TEXT,sha256 TEXT,PRIMARY KEY(run_id,nct_id))"))
        c.execute(text("INSERT INTO scientific_review_runs VALUES ('fixture-review','2026-10-30T18:00:00+00:00')"))
        for nct in (NCT, OTHER):
            doc = saved_document(nct)
            c.execute(text("INSERT INTO scientific_candidate_dossiers VALUES ('fixture-review',:nct,:doc,:sha)"), {"nct": nct, "doc": live.canonical(doc), "sha": live.digest(doc)})
    live.initialize(engine)
    yield engine
    engine.dispose()


def node_states(events):
    return {event["node_id"]: event for event in events if event["kind"] == "node"}


def frame_document(frame):
    return json.loads(next(line[6:] for line in frame.splitlines() if line.startswith("data: ")))


def test_exact_dossier_nct_and_hash_required_before_run_creation(engine):
    for invalid in ("NCT1", "NCT１２３４５６７８", "NCT00000001 or 1=1", None):
        with pytest.raises(ValueError):
            live.create_run(engine, invalid, "valid-request-key", submit=False)
    with pytest.raises(LookupError):
        live.create_run(engine, "NCT99999999", "valid-request-key", submit=False)
    with engine.begin() as c:
        c.execute(text("UPDATE scientific_candidate_dossiers SET sha256=:bad WHERE nct_id=:nct"), {"bad": "0" * 64, "nct": NCT})
    with pytest.raises(ValueError, match="checksum"):
        live.create_run(engine, NCT, "valid-request-key", submit=False)
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM nct_stream_runs")).scalar_one() == 0


def test_request_idempotency_and_no_cross_nct_reuse(engine):
    first = live.create_run(engine, NCT, "same-request-key", submit=False)
    second = live.create_run(engine, NCT, "same-request-key", submit=False)
    assert second["run_id"] == first["run_id"]
    assert second["events"] == []
    assert first["dossier_id"] == "fixture-review/" + NCT
    assert first["dossier_sha256"] == live.digest(saved_document())
    with pytest.raises(ValueError):
        live.create_run(engine, OTHER, "same-request-key", submit=False)
    with pytest.raises(LookupError):
        live.snapshot(engine, OTHER, first["run_id"])


def test_real_worker_emits_durable_ordered_hierarchy_without_scoring(engine):
    run = live.create_run(engine, NCT, "hierarchy-request-key", submit=False)
    live.worker(engine, run["run_id"], fetcher=fetcher)
    result = live.snapshot(engine, NCT, run["run_id"])
    assert result["terminal"]
    assert result["status"] == "COMPLETE"
    events = result["events"]
    assert [e["sequence"] for e in events] == list(range(1, len(events) + 1))
    assert len({(e["run_id"], e["sequence"]) for e in events}) == len(events)
    assert all(e["nct_id"] == NCT and e["dossier_id"] == run["dossier_id"] for e in events)
    assert all(e["decision"] == "ABSTAIN" and e["scientific_assessments_completed"] == 0 for e in events)
    states = node_states(events)
    assert states["nct_identifier"]["status"] == "VERIFIED"
    assert states["statistical_significance"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert states["clinical_effect_size"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert states["pdufa_date"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert states["regulatory"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert states["trial"]["status"] == "INSUFFICIENT_EVIDENCE"
    assert states["main"]["status"] == "INSUFFICIENT_EVIDENCE"
    for event in events:
        if event["status"] == "VERIFIED" and event["kind"] == "node":
            assert event["source"]["url"] == "https://clinicaltrials.gov/api/v2/studies/" + NCT
            assert len(event["source"]["sha256"]) == 64
    assert min(e["sequence"] for e in events if e["level"] == 4 and e["status"] == "VERIFIED") < min(e["sequence"] for e in events if e["level"] == 3)
    with engine.connect() as c:
        assert c.execute(text("SELECT document FROM scientific_candidate_dossiers WHERE nct_id=:nct"), {"nct": NCT}).scalar_one() == live.canonical(saved_document())
        assert c.execute(text("SELECT count(*) FROM nct_stream_sources WHERE run_id=:run"), {"run": run["run_id"]}).scalar_one() == 1
    assert live.snapshot(engine, NCT, run["run_id"]) == result


def test_sse_replays_only_committed_events_and_resumes_exact_cursor(engine):
    run = live.create_run(engine, NCT, "resume-request-key", submit=False)
    live.worker(engine, run["run_id"], fetcher=fetcher)
    saved = live.snapshot(engine, NCT, run["run_id"])
    frames = list(live.stream(engine, NCT, run["run_id"]))
    emitted = [frame_document(frame) for frame in frames if "data: " in frame]
    assert emitted == saved["events"]
    with engine.connect() as c:
        for frame, event in zip(frames, emitted):
            assert frame.startswith("id: " + run["run_id"] + ":" + str(event["sequence"]))
            persisted = c.execute(text("SELECT document FROM nct_stream_events WHERE run_id=:run AND sequence=:seq"), {"run": run["run_id"], "seq": event["sequence"]}).scalar_one()
            assert json.loads(persisted) == event
    cursor = emitted[len(emitted) // 2]["sequence"]
    resumed = [frame_document(frame) for frame in live.stream(engine, NCT, run["run_id"], after=cursor)]
    assert resumed == [event for event in emitted if event["sequence"] > cursor]
    assert list(live.stream(engine, NCT, run["run_id"], after=saved["latest_sequence"])) == []
    for cursor in (-1, saved["latest_sequence"] + 1):
        with pytest.raises(ValueError):
            live.stream(engine, NCT, run["run_id"], after=cursor)


def test_incremental_loading_is_available_while_source_fetch_waits(engine):
    run = live.create_run(engine, NCT, "incremental-request-key", submit=False)
    entered, release = threading.Event(), threading.Event()
    def waiting_fetch(nct):
        entered.set()
        assert release.wait(5)
        return fetcher(nct)
    thread = threading.Thread(target=live.worker, args=(engine, run["run_id"]), kwargs={"fetcher": waiting_fetch})
    thread.start()
    try:
        assert entered.wait(5)
        saved = live.snapshot(engine, NCT, run["run_id"])
        assert saved["status"] == "LOADING"
        assert not saved["terminal"]
        assert any(e["status"] == "LOADING" for e in saved["events"])
        frame = next(live.stream(engine, NCT, run["run_id"], duration=.1))
        first = frame_document(frame)
        assert first == saved["events"][0]
    finally:
        release.set()
        thread.join(10)
    assert not thread.is_alive()
    assert live.snapshot(engine, NCT, run["run_id"])["terminal"]


def test_duplicate_emit_and_completed_worker_restart_do_not_duplicate_events(engine):
    run = live.create_run(engine, NCT, "duplicate-request-key", submit=False)
    a = live.emit(engine, run, "nct_identifier", 4, "PENDING", parent_id="trial_identity")
    b = live.emit(engine, run, "nct_identifier", 4, "PENDING", parent_id="trial_identity")
    assert a == b
    live.worker(engine, run["run_id"], fetcher=fetcher)
    first = live.snapshot(engine, NCT, run["run_id"])
    def must_not_refetch(_):
        raise AssertionError("A completed run must not repeat source retrieval")
    live.worker(engine, run["run_id"], fetcher=must_not_refetch)
    assert live.snapshot(engine, NCT, run["run_id"]) == first


def test_failed_run_is_durable_and_new_request_recovers_without_changing_dossier(engine):
    failed = live.create_run(engine, NCT, "failed-request-key", submit=False)
    def unavailable(_):
        raise TimeoutError("Synthetic network timeout")
    live.worker(engine, failed["run_id"], fetcher=unavailable)
    state = live.snapshot(engine, NCT, failed["run_id"])
    assert state["status"] == "FAILED" and state["terminal"]
    assert state["events"][-1]["value"]["error_type"] == "TimeoutError"
    assert not any(e["status"] == "VERIFIED" for e in state["events"])
    recovered = live.create_run(engine, NCT, "recovered-request-key", submit=False)
    assert recovered["run_id"] != failed["run_id"]
    live.worker(engine, recovered["run_id"], fetcher=fetcher)
    assert live.snapshot(engine, NCT, recovered["run_id"])["status"] == "COMPLETE"
    assert live.snapshot(engine, NCT, failed["run_id"]) == state


def test_live_identity_mismatch_never_verifies_saved_trial(engine):
    run = live.create_run(engine, NCT, "wrong-source-request-key", submit=False)
    live.worker(engine, run["run_id"], fetcher=lambda _: fetcher(OTHER))
    result = live.snapshot(engine, NCT, run["run_id"])
    assert result["status"] == "FAILED"
    assert result["events"][-1]["status"] == "FAILED"
    assert not any(e["status"] == "VERIFIED" for e in result["events"])


def test_saved_live_identity_conflict_is_failed_leaf_not_silent_update(engine):
    run = live.create_run(engine, NCT, "conflict-request-key", submit=False)
    def changed(nct):
        study, proof = fetcher(nct)
        study["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"]["name"] = "Changed Sponsor"
        proof["sha256"] = hashlib.sha256(json.dumps(study).encode()).hexdigest()
        return study, proof
    live.worker(engine, run["run_id"], fetcher=changed)
    result = live.snapshot(engine, NCT, run["run_id"])
    sponsor = node_states(result["events"])["sponsor"]
    assert sponsor["status"] == "FAILED"
    assert sponsor["value"]["saved_dossier"] == "Fixture Sponsor"
    assert sponsor["value"]["source_reported"] == "Changed Sponsor"
    assert result["status"] == "FAILED"
    with engine.connect() as c:
        assert json.loads(c.execute(text("SELECT document FROM scientific_candidate_dossiers WHERE nct_id=:nct"), {"nct": NCT}).scalar_one()) == saved_document()


def store_source(engine, run, study, source, *, checksum=None):
    with engine.begin() as c:
        c.execute(text("INSERT INTO nct_stream_sources(run_id,source_url,sha256,document,canonical_sha256,verified_at) VALUES(:run,:url,:sha,:doc,:canonical_sha,:time)"),
                  {"run": run["run_id"], "url": source["url"], "sha": source["sha256"], "doc": live.canonical(study), "canonical_sha": checksum or live.digest(study), "time": source["verified_at"]})


def test_partial_run_resumes_saved_source_without_demoting_verified_leaves(engine):
    run = live.create_run(engine, NCT, "partial-request-key", submit=False)
    study, source = fetcher()
    store_source(engine, run, study, source)
    live.emit(engine, run, "nct_identifier", 4, "VERIFIED", NCT, parent_id="trial_identity", source=source)
    live.emit(engine, run, "sponsor", 4, "LOADING", parent_id="trial_identity", source=source)
    prefix = live.snapshot(engine, NCT, run["run_id"])["events"]
    def must_not_refetch(_):
        raise AssertionError("Interrupted run must reuse checksum-verified persisted source")
    live.worker(engine, run["run_id"], fetcher=must_not_refetch)
    resumed = live.snapshot(engine, NCT, run["run_id"])
    assert resumed["status"] == "COMPLETE"
    assert resumed["events"][:len(prefix)] == prefix
    assert [e["status"] for e in resumed["events"] if e["node_id"] == "nct_identifier"] == ["VERIFIED"]
    assert node_states(resumed["events"])["sponsor"]["status"] == "VERIFIED"


@pytest.mark.parametrize("failure", ["checksum", "identity"])
def test_restored_source_revalidates_canonical_hash_and_exact_nct(engine, failure):
    run = live.create_run(engine, NCT, "restored-request-key", submit=False)
    study, source = fetcher(OTHER if failure == "identity" else NCT)
    store_source(engine, run, study, source, checksum="0" * 64 if failure == "checksum" else None)
    live.worker(engine, run["run_id"], fetcher=lambda _: (_ for _ in ()).throw(AssertionError("Unexpected refetch")))
    result = live.snapshot(engine, NCT, run["run_id"])
    assert result["status"] == "FAILED"
    assert not any(e["status"] == "VERIFIED" for e in result["events"])


@pytest.mark.parametrize("bad_proof", [
    {"url": "https://not-clinicaltrials.gov/study/NCT00000001"},
    {"sha256": "not-a-valid-sha"}, {"http_status": 404}, {"verified_at": "2026-10-30T20:00:00"},
])
def test_missing_or_invalid_source_provenance_cannot_be_verified(engine, bad_proof):
    run = live.create_run(engine, NCT, "bad-proof-request-key", submit=False)
    def invalid(nct):
        study, proof = fetcher(nct)
        return study, {**proof, **bad_proof}
    live.worker(engine, run["run_id"], fetcher=invalid)
    result = live.snapshot(engine, NCT, run["run_id"])
    assert result["status"] == "FAILED"
    assert not any(e["status"] == "VERIFIED" for e in result["events"])


def test_persisted_sources_and_events_are_append_only(engine):
    run = live.create_run(engine, NCT, "immutable-request-key", submit=False)
    live.worker(engine, run["run_id"], fetcher=fetcher)
    for statement in ("DELETE FROM nct_stream_sources", "UPDATE nct_stream_sources SET document='{}'", "DELETE FROM nct_stream_events", "UPDATE nct_stream_events SET document='{}'"):
        with pytest.raises(DatabaseError, match="append-only"):
            with engine.begin() as c:
                c.execute(text(statement))


class SourceResponse:
    def __init__(self, raw, *, status=200, content_type="application/json"):
        self.raw, self.status = raw, status
        self.headers = {"Content-Type": content_type}
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, limit):
        return self.raw[:limit]


def test_fresh_source_receipt_matches_exact_download_body(monkeypatch):
    raw = json.dumps(registry_study(), indent=2).encode()
    def download(request, timeout):
        assert request.full_url == "https://clinicaltrials.gov/api/v2/studies/" + NCT
        assert timeout == 20
        return SourceResponse(raw)
    monkeypatch.setattr(live, "urlopen", download)
    study, source = live.fresh_source(NCT)
    assert study == registry_study()
    assert source["sha256"] == hashlib.sha256(raw).hexdigest()
    assert source["http_status"] == 200


@pytest.mark.parametrize("response", [
    SourceResponse(b"<html>login</html>", content_type="text/html"),
    SourceResponse(b'{}', status=503),
    SourceResponse(json.dumps(registry_study(OTHER)).encode()),
    SourceResponse(b'{"protocolSection":NaN}'),
])
def test_fresh_source_rejects_http_html_wrong_identity_and_nonstandard_json(monkeypatch, response):
    monkeypatch.setattr(live, "urlopen", lambda *_args, **_kwargs: response)
    with pytest.raises(ValueError):
        live.fresh_source(NCT)


@pytest.mark.parametrize("states,result", [([], "PENDING"), (["PENDING", "PENDING"], "PENDING"), (["VERIFIED", "PENDING"], "LOADING"), (["VERIFIED", "FAILED"], "FAILED"), (["VERIFIED", "INSUFFICIENT_EVIDENCE"], "INSUFFICIENT_EVIDENCE"), (["VERIFIED", "VERIFIED"], "VERIFIED")])
def test_parent_state_requires_all_children_terminal(states, result):
    assert live.aggregate(states) == result


def installed_app(engine):
    def require_key(x_pdufa_internal_key: str | None = Header(default=None)):
        if x_pdufa_internal_key != "isolated-stream-test":
            raise HTTPException(401, "Unauthorized")
    app = FastAPI()
    live.install_routes(app, lambda: engine, require_key, lambda: None)
    return app


def test_router_all_routes_require_auth_and_exact_run_scope(engine, monkeypatch):
    app = installed_app(engine)
    registered = [leaf for route in app.routes for leaf in (route.original_router.routes if hasattr(route, "original_router") else [route])]
    routes = {r.path: r for r in registered if r.path.startswith("/api/nct-stream")}
    assert len(routes) == 3
    for route in routes.values():
        assert len(route.dependencies) == 2
        with pytest.raises(HTTPException) as missing:
            route.dependencies[0].dependency(None)
        assert missing.value.status_code == 401
        route.dependencies[0].dependency("isolated-stream-test")
    monkeypatch.setattr(live._pool, "submit", lambda *_args, **_kwargs: None)
    create = routes["/api/nct-stream/{nct_id}/runs"].endpoint
    read = routes["/api/nct-stream/{nct_id}/runs/{run_id}"].endpoint
    events = routes["/api/nct-stream/{nct_id}/runs/{run_id}/events"].endpoint
    run = create(NCT, live.StartRequest(request_key="route-request-key"))
    assert read(NCT, run["run_id"])["events"] == []
    with pytest.raises(HTTPException) as cross_nct:
        read(OTHER, run["run_id"])
    assert cross_nct.value.status_code == 404
    with pytest.raises(HTTPException) as wrong_cursor:
        events(NCT, run["run_id"], after=0, last_event_id="different-run:1")
    assert wrong_cursor.value.status_code == 409
    response = events(NCT, run["run_id"], after=0, last_event_id=None)
    assert response.media_type == "text/event-stream"
    assert response.headers["cache-control"] == "private, no-store, no-transform"
    assert response.headers["x-accel-buffering"] == "no"


@pytest.mark.skipif(not os.environ.get("CI"), reason="Local AnyIO blocking-portal limitation; HTTP also verified on deployed service")
def test_actual_authenticated_http_stream_and_reload(engine, monkeypatch):
    app = installed_app(engine)
    monkeypatch.setattr(live._pool, "submit", lambda *_args, **_kwargs: None)
    with TestClient(app) as client:
        base = "/api/nct-stream/" + NCT + "/runs"
        assert client.post(base, json={"request_key": "http-request-key"}).status_code == 401
        headers = {"X-Pdufa-Internal-Key": "isolated-stream-test"}
        created = client.post(base, headers=headers, json={"request_key": "http-request-key"})
        assert created.status_code == 200
        run = created.json()
        live.worker(engine, run["run_id"], fetcher=fetcher)
        with client.stream("GET", base + "/" + run["run_id"] + "/events", headers=headers) as response:
            assert response.status_code == 200
            frames = [json.loads(line[6:]) for line in response.iter_lines() if line.startswith("data: ")]
        snapshot = client.get(base + "/" + run["run_id"], headers=headers).json()
        reload = client.get(base + "/" + run["run_id"], headers=headers).json()
        assert frames == snapshot["events"] == reload["events"]
        assert frames[-1]["terminal"]
