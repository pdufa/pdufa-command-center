"""Evidence-review integration tests, using disposable metadata and fixed sources."""
import ast
from datetime import datetime, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import secrets
from types import SimpleNamespace
from typing import Annotated
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DatabaseError

from app import candidate_review_service as service


def study(nct="NCT00000001"):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": "Scientific review fixture"},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": "Test Sponsor"}},
        "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": "Test Compound"}]},
    }}


class Response:
    def __init__(self, payload, status=200):
        self.raw = json.dumps(payload).encode()
        self.status = status
    def __enter__(self):
        return self
    def __exit__(self, *_):
        return False
    def read(self, limit):
        return self.raw[:limit]


@pytest.fixture
def engine(tmp_path):
    engine = create_engine("sqlite:///" + str(tmp_path / "review.sqlite3"), connect_args={"check_same_thread": False})
    service.initialize(engine)
    yield engine
    engine.dispose()


def test_fetch_proof_hash_and_timestamp_correspond_to_actual_body(monkeypatch):
    response = Response({"studies": [study()]})
    monkeypatch.setattr(service, "urlopen", lambda request, timeout: response)
    payload, proof = service.fetch_json("https://clinicaltrials.gov/api/v2/studies?filter.ids=NCT00000001")
    assert payload == {"studies": [study()]}
    assert proof["status"] == "FETCHED"
    assert proof["http_status"] == 200
    assert proof["sha256"] == hashlib.sha256(response.raw).hexdigest()
    assert datetime.fromisoformat(proof["fetched_at"]).tzinfo is not None


@pytest.mark.parametrize("error,status", [(HTTPError("https://api.fda.gov/", 404, "Not Found", {}, None), "UNAVAILABLE"), (URLError("offline"), "ERROR")])
def test_fetch_failure_never_becomes_a_successful_source_check(monkeypatch, error, status):
    def unavailable(*_, **__):
        raise error
    monkeypatch.setattr(service, "urlopen", unavailable)
    payload, proof = service.fetch_json("https://api.fda.gov/drug/drugsfda.json")
    assert payload is None
    assert proof["status"] == status
    assert "sha256" not in proof


def test_registry_no_hit_is_not_an_independently_checked_trial(monkeypatch):
    monkeypatch.setattr(service, "urlopen", lambda *_args, **_kwargs: Response({"studies": []}))
    live, proof = service.live_registry(["NCT00000001"])
    assert live == {}
    dossier = service.build_dossier(study(), live.get("NCT00000001"), source_status=proof["status"], external_evidence={"registry_sourceproof": proof})
    assert not dossier["independently_checked"]
    assert dossier["readiness"] != "READY"
    assert dossier["trade_authorized"] is False


@pytest.mark.parametrize("payload,reason", [
    ({"studies": [study(), study()]}, "UnexpectedRegistryIdentity"),
    ({"studies": [study("NCT00000009")]}, "UnexpectedRegistryIdentity"),
    ({"studies": [study()], "nextPageToken": "MORE"}, "UnexpectedRegistryPagination"),
])
def test_registry_rejects_duplicate_extra_and_paginated_identities(monkeypatch, payload, reason):
    monkeypatch.setattr(service, "urlopen", lambda *_args, **_kwargs: Response(payload))
    records, proof = service.live_registry(["NCT00000001"])
    assert records == {}
    assert proof["status"] == "ERROR"
    assert proof["error_type"] == reason


def test_fda_product_search_does_not_establish_trial_pathway_or_pdufa(monkeypatch):
    payload = {"results": [{"application_number": "NDA999999", "sponsor_name": "Test Sponsor", "products": [{"brand_name": "Test Brand", "active_ingredients": [{"name": "Test Compound"}]}]}]}
    monkeypatch.setattr(service, "urlopen", lambda *_args, **_kwargs: Response(payload))
    lookup = service.fda_lookup(study())
    assert lookup["status"] == "FETCHED"
    assert lookup["applications"][0]["application_number"] == "NDA999999"
    dossier = service.build_dossier(study(), study(), external_evidence={"fda_lookup": lookup})
    assert dossier["fda_regulatory_pathway"]["status"] == "UNRESOLVED"
    assert dossier["pdufa_date"]["status"] == "UNRESOLVED"
    assert dossier["regulatory_submission_evidence"]["status"] == "UNRESOLVED"
    assert dossier["approval_probability"] is None
    assert dossier["regulatory_outcome_prediction"] is None


def test_fda_no_hit_is_not_a_negative_application_conclusion(monkeypatch):
    def missing(*_, **__):
        raise HTTPError("https://api.fda.gov/drug/drugsfda.json", 404, "Not Found", {}, None)
    monkeypatch.setattr(service, "urlopen", missing)
    lookup = service.fda_lookup(study())
    assert lookup["applications"] == []
    assert lookup["status"] != "FETCHED"
    assert "No hit is not evidence of no application" in lookup["caveat"]


def execute_fixture(engine, monkeypatch, *, absent=None):
    ids = ["NCT00000001", "NCT00000002"]
    selected = [(nct, gzip.compress(json.dumps(study(nct)).encode()), "a" * 64) for nct in ids]
    monkeypatch.setattr(service, "EXPECTED", 2)
    monkeypatch.setattr(service, "curated_evidence", lambda: {})
    monkeypatch.setattr(service, "source_inventory", lambda _: (selected, [], {"database": "sqlite_test", "manifest_sha256": "b" * 64, "archive_count": 11622}))
    monkeypatch.setattr(service, "verify_http", lambda: None)
    def request(request, timeout):
        parsed = urlsplit(request.full_url)
        if parsed.hostname == "clinicaltrials.gov":
            requested = parse_qs(parsed.query)["filter.ids"][0].split(",")
            return Response({"studies": [study(nct) for nct in requested if nct != absent]})
        assert parsed.hostname == "api.fda.gov"
        return Response({"results": []})
    monkeypatch.setattr(service, "urlopen", request)
    return service.execute_review(engine)


def test_persisted_counts_proofs_dossiers_and_no_repeat(engine, monkeypatch):
    summary = execute_fixture(engine, monkeypatch)
    assert summary["status"] == "COMPLETE"
    assert summary["candidates_identified"] == summary["candidates_independently_checked"] == summary["scientific_dossiers_created"] == 2
    assert sum(summary[k] for k in ("ready", "reluctant", "not_ready")) == 2
    assert summary["full_scientific_investigations_completed"] == 0
    result = service.list_reviews(engine)
    assert len(result["candidates"]) == 2
    for item in result["candidates"]:
        dossier = service.detail(engine, item["nct_id"])
        assert dossier["independently_checked"]
        assert any(p["source_type"] == "REGISTRY_FETCH_PROOF" and p["status"] == "FETCHED" and len(p["sha256"]) == 64 for p in dossier["provenance"])
        assert not dossier["trade_authorized"]
    assert service.execute_review(engine)["status"] == "ALREADY_COMPLETED"
    with engine.connect() as c:
        assert c.execute(text("SELECT count(*) FROM scientific_review_runs")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM scientific_candidate_dossiers")).scalar_one() == 2


def test_nohit_reduces_checked_count_and_requires_review(engine, monkeypatch):
    summary = execute_fixture(engine, monkeypatch, absent="NCT00000002")
    assert summary["status"] == "REVIEW_REQUIRED"
    assert summary["candidates_independently_checked"] == 1
    assert summary["scientific_dossiers_created"] == 2
    assert not service.detail(engine, "NCT00000002")["independently_checked"]


def test_dossier_metadata_is_append_only(engine, monkeypatch):
    execute_fixture(engine, monkeypatch)
    for sql in ("DELETE FROM scientific_candidate_dossiers", "UPDATE scientific_candidate_dossiers SET document='{}'", "DELETE FROM scientific_review_runs", "UPDATE scientific_review_runs SET summary='{}'"):
        with pytest.raises(DatabaseError, match="append-only"):
            with engine.begin() as c:
                c.execute(text(sql))


def test_corrupt_dossier_checksum_is_rejected(engine):
    document = {"nct_id": "NCT00000001", "readiness": "NOT READY"}
    summary = {"scientific_dossiers_created": 1, "last_verified": "2026-10-30T00:00:00+00:00"}
    with engine.begin() as c:
        c.execute(text("INSERT INTO scientific_review_runs VALUES ('test','2026-10-30T00:00:00+00:00',:summary)"), {"summary": json.dumps(summary)})
        c.execute(text("INSERT INTO scientific_candidate_dossiers VALUES ('test','NCT00000001',:doc,:hash)"), {"doc": json.dumps(document), "hash": "0" * 64})
    with pytest.raises(ValueError, match="checksum"):
        service.detail(engine, "NCT00000001")
    with pytest.raises(ValueError, match="checksum"):
        service.list_reviews(engine)


def test_persisted_count_inconsistency_is_rejected(engine):
    with engine.begin() as c:
        c.execute(text("INSERT INTO scientific_review_runs VALUES ('test','2026-10-30T00:00:00+00:00',:summary)"), {"summary": json.dumps({"scientific_dossiers_created": 1})})
    with pytest.raises(ValueError, match="counts"):
        service.list_reviews(engine)


def test_overlap_guard_returns_without_network_or_storage_work(engine):
    service._lock.acquire()
    try:
        assert service.execute_review(engine)["status"] == "SKIPPED_OVERLAP"
    finally:
        service._lock.release()


class QueryResult:
    def __init__(self, value):
        self.value = value
    def scalar_one(self):
        return self.value
    def one(self):
        return self.value
    def all(self):
        return self.value


class InventoryConnection:
    def __init__(self, *, duplicate=False):
        self.ids = ["NCT" + str(n).zfill(8) for n in range(1, 11623)]
        self.rows = self.ids[:] if not duplicate else self.ids[:-1] + [self.ids[0]]
        self.baseline = {"records": [{"nct_id": nct, "sha256": "a" * 64} for nct in self.ids]}
        self.offsets = []
    def execute(self, statement, params=None):
        sql = str(statement)
        assert sql.lstrip().startswith("SELECT"), "Source inventory must never write archive tables"
        if "FROM archive_manifests" in sql:
            return QueryResult((json.dumps(self.baseline), service.digest(self.baseline)))
        if "count(*)" in sql:
            return QueryResult(11622)
        assert "LIMIT 100 OFFSET" in sql
        self.offsets.append(params["offset"])
        return QueryResult([(nct, b"packed", "a" * 64) for nct in self.rows[params["offset"]:params["offset"] + 100]])


@pytest.mark.parametrize("duplicate", [False, True])
def test_source_inventory_checks_exact_baseline_membership_and_bounds(monkeypatch, duplicate):
    connection = InventoryConnection(duplicate=duplicate)
    closed = []
    monkeypatch.setattr(service, "EXPECTED", 2)
    monkeypatch.setattr(service, "read_connection", lambda _: connection)
    monkeypatch.setattr(service, "close_read", lambda c: closed.append(c))
    monkeypatch.setattr(service, "inspect_payload", lambda nct, *_: ({}, study(nct)))
    monkeypatch.setattr(service, "study_readiness", lambda study, today: {"scientific_ready": study["protocolSection"]["identificationModule"]["nctId"] in ("NCT00000002", "NCT00000003")})
    monkeypatch.setattr(service, "extract_regulatory_identifiers", lambda _: [])
    engine = SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))
    if duplicate:
        with pytest.raises(ValueError):
            service.source_inventory(engine)
    else:
        selected, regulators, baseline = service.source_inventory(engine)
        assert len(selected) == 2
        assert regulators == []
        assert baseline["archive_count"] == 11622
        assert len(connection.offsets) == 118
        assert connection.offsets[:3] == [0, 100, 200]
    assert closed == [connection]


def regulatory_record():
    return {"associated_nct_id": "NCT00000001", "sponsor": "Test Sponsor", "products": [{"type": "DRUG", "name": "Test Compound"}],
            "identifiers": [{"identifier": "IND 123456"}], "archive_sha256": "a" * 64}


def test_curated_evidence_cannot_replace_record_identity_or_products():
    key = "NCT00000001|IND 123456"
    evidence = {key: {"status": "UNRESOLVED", "associated_nct_id": "NCT99999999", "identifier": "NDA 000000", "products": ["Wrong Product"],
                      "explanation": "Search is incomplete", "evidence": [{"url": "https://www.fda.gov/drugs/", "checked_at": "2026-10-30T00:00:00+00:00", "supports": "Search location only; no exact identifier verification"}]}}
    rows = service.reconcile_regulators([regulatory_record(), regulatory_record()], {}, {}, evidence)
    assert len(rows) == 1
    assert rows[0]["associated_nct_id"] == "NCT00000001"
    assert rows[0]["identifier"] == "IND 123456"
    assert rows[0]["products"] == ["Test Compound"]
    assert rows[0]["status"] == "UNRESOLVED"


def test_verified_reconciliation_rejects_deceptive_fda_hostname():
    evidence = {"NCT00000001|IND 123456": {"status": "VERIFIED", "evidence": [{"url": "https://notfda.gov/application", "checked_at": "2026-10-30T00:00:00+00:00", "supports": "Claim"}]}}
    with pytest.raises(ValueError):
        service.reconcile_regulators([regulatory_record()], {}, {}, evidence)


def test_actual_protected_api_route_contract_and_dossier_errors(engine, monkeypatch):
    execute_fixture(engine, monkeypatch)
    source = Path(service.__file__).with_name("main.py")
    syntax = ast.parse(source.read_text())
    wanted = {"require_internal_key", "scientific_candidate_reviews", "scientific_candidate_dossier"}
    extracted = ast.Module(body=[node for node in syntax.body if isinstance(node, ast.FunctionDef) and node.name in wanted], type_ignores=[])
    assert len(extracted.body) == len(wanted)
    app = FastAPI()
    context = {"__name__": "app.candidate_route_test", "__package__": "app", "app": app, "ENGINE": engine,
               "Depends": Depends, "Header": Header, "Annotated": Annotated, "HTTPException": HTTPException,
               "os": os, "secrets": secrets, "re": re, "require_storage": lambda: None}
    exec(compile(extracted, str(source), "exec"), context)
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", "test-review-key")
    with pytest.raises(HTTPException) as unauthorized:
        context["require_internal_key"]()
    assert unauthorized.value.status_code == 401
    context["require_internal_key"]("test-review-key")
    response = JSONResponse(jsonable_encoder(context["scientific_candidate_reviews"]()))
    assert response.status_code == 200
    assert len(json.loads(response.body)["candidates"]) == 2
    assert context["scientific_candidate_dossier"]("NCT00000001")["nct_id"] == "NCT00000001"
    for nct, expected in (("NCTbogus", 422), ("NCT00000003", 404)):
        with pytest.raises(HTTPException) as raised:
            context["scientific_candidate_dossier"](nct)
        assert raised.value.status_code == expected
    for path in ("/api/scientific-candidates", "/api/scientific-candidates/{nct_id}"):
        route = next(route for route in app.routes if route.path == path)
        assert route.methods == {"GET"}
        assert len(route.dependencies) == 2
