"""Dedicated scientific 456 staging routes, authentication and isolation checks."""
from pathlib import Path
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import assessment_runtime as runtime
from app import scientific_456_staging as staging
from test_assessment_runtime import engine
from test_scientific_trial_assessment import source


KEY = "SYNTHETIC_DEDICATED_456_TEST_KEY"
HEADERS = {"X-Pdufa-Internal-Key": KEY}


@pytest.fixture
def client(engine, monkeypatch):
    monkeypatch.setenv("PDUFA_LEVEL456_BACKEND_ENABLED", "1")
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", KEY)
    monkeypatch.delenv("PDUFA_MIGRATION_READ_ONLY", raising=False)
    staging.app.dependency_overrides[staging.isolated_engine] = lambda: engine
    try:
        with TestClient(staging.app) as api:
            yield api
    finally:
        staging.app.dependency_overrides.clear()


def body(level, *, contract="SCIENTIFIC_1_6"):
    return runtime.RunInput(nct="NCT04576949", level=level,
                            mode="CURRENT_EVIDENCE", contract=contract).model_dump(mode="json")


def test_standalone_only_exposes_scientific_456_and_reports_disabled_state(client, monkeypatch):
    version = client.get("/api/assessment-runtime/version")
    assert version.status_code == 200
    assert version.json()["stagingMode"] == "SCIENTIFIC_456_ISOLATED_ONLY"
    assert version.json()["scientificContracts"] == {"SCIENTIFIC_1_6": [4, 5, 6]}
    assert version.json()["legacy123Separate"] is True
    assert version.json()["scientific456Enabled"] is True
    assert client.get("/api/assessment-runtime/focus", headers=HEADERS).status_code == 404
    assert client.get("/api/assessment-runtime/past", headers=HEADERS).status_code == 404
    assert client.post("/api/assessment-runtime/focus/batch", headers=HEADERS).status_code == 404
    monkeypatch.setenv("PDUFA_LEVEL456_BACKEND_ENABLED", "0")
    assert client.get("/api/assessment-runtime/version").json()["scientific456Enabled"] is False
    assert client.get("/api/assessment-runtime/history/NCT04576949?contract=SCIENTIFIC_1_6",
                      headers=HEADERS).status_code == 503
    assert client.post("/api/assessment-runtime/runs", json=body(4), headers=HEADERS).status_code == 503


def test_readiness_checks_database_and_opt_in_without_exposing_details(client, monkeypatch):
    ready = client.get("/api/assessment-runtime/health")
    assert ready.status_code == 200
    assert ready.json() == {"status": "READY",
                            "stagingMode": "SCIENTIFIC_456_ISOLATED_ONLY",
                            "fdaModel": "ABSTAIN"}
    monkeypatch.setenv("PDUFA_LEVEL456_BACKEND_ENABLED", "0")
    assert client.get("/api/assessment-runtime/health").status_code == 503
    monkeypatch.setenv("PDUFA_LEVEL456_BACKEND_ENABLED", "1")
    monkeypatch.delenv("PDUFA_INTERNAL_API_KEY")
    assert client.get("/api/assessment-runtime/health").status_code == 503
    monkeypatch.setenv("PDUFA_INTERNAL_API_KEY", KEY)

    class UnavailableDatabase:
        def connect(self):
            raise RuntimeError("SENSITIVE_DATABASE_CONNECTION_DETAIL")

    staging.app.dependency_overrides[staging.isolated_engine] = lambda: UnavailableDatabase()
    failed = client.get("/api/assessment-runtime/health")
    assert failed.status_code == 503
    assert "SENSITIVE_DATABASE_CONNECTION_DETAIL" not in failed.text


def test_staging_requires_its_secret_and_rejects_123_or_unknown_contracts(client):
    assert client.get("/api/assessment-runtime/history/NCT04576949?contract=SCIENTIFIC_1_6").status_code == 401
    assert client.get("/api/assessment-runtime/history/NCT04576949?contract=SCIENTIFIC_1_6",
                      headers={"X-Pdufa-Internal-Key": "WRONG"}).status_code == 401
    assert client.post("/api/assessment-runtime/runs", json=body(4)).status_code == 401
    assert client.post("/api/assessment-runtime/runs", json=body(1, contract="SCIENTIFIC_1_3"),
                       headers=HEADERS).status_code == 422
    assert client.post("/api/assessment-runtime/runs", json=body(1), headers=HEADERS).status_code == 422
    assert client.get("/api/assessment-runtime/history/NCT04576949?contract=SCIENTIFIC_1_3",
                      headers=HEADERS).status_code == 422
    assert client.get("/api/assessment-runtime/history/NCT04576949", headers=HEADERS).status_code == 422
    assert client.get("/api/assessment-runtime/runs/NCT04576949/11111111-1111-1111-1111-111111111111",
                      headers=HEADERS).status_code == 422


def test_staging_persists_456_without_starting_main_scans(client, monkeypatch):
    monkeypatch.setattr(runtime, "collect_documents", lambda value, level: value)
    original_execute = runtime.execute
    monkeypatch.setattr(runtime, "execute",
                        lambda db, run_id: original_execute(db, run_id,
                                                            lambda nct: source()))
    for level in (4, 5, 6):
        posted = client.post("/api/assessment-runtime/runs", json=body(level), headers=HEADERS)
        assert posted.status_code == 202, posted.text
        run_id = posted.json()["runId"]
        status = client.get("/api/assessment-runtime/runs/NCT04576949/"+run_id
                            +"?contract=SCIENTIFIC_1_6", headers=HEADERS)
        assert status.status_code == 200, status.text
        state = status.json()
        assert state["status"] == "COMPLETED", state.get("error")
        report = state["report"]
        assert report["level"] == level
        assert report["contract"] == "SCIENTIFIC_1_6"
        assert report["score"]["value"] is None
        assert report["fdaPrediction"]["outcome"] == "ABSTAIN"
        assert status.json()["report"]["reportHash"]
        assert client.get("/api/assessment-runtime/runs/NCT04576949/"+run_id
                          +"?contract=SCIENTIFIC_1_3", headers=HEADERS).status_code == 422
    history = client.get("/api/assessment-runtime/history/NCT04576949?contract=SCIENTIFIC_1_6",
                         headers=HEADERS)
    assert history.status_code == 200
    reports = history.json()["runs"]
    assert {x["level"] for x in reports} == {4, 5, 6}
    # Dedicated staging preserves the same exact-contract keyset semantics.
    cursor = reports[0]["executedAt"] + "|" + reports[0]["runId"]
    older = client.get("/api/assessment-runtime/history/NCT04576949",
                       headers=HEADERS,
                       params={"contract": "SCIENTIFIC_1_6", "before": cursor})
    assert older.status_code == 200
    assert len(older.json()["runs"]) == 2
    assert reports[0]["runId"] not in {x["runId"] for x in older.json()["runs"]}
    assert client.get("/api/assessment-runtime/history/NCT04576949",
                      headers=HEADERS,
                      params={"contract": "SCIENTIFIC_1_6",
                              "before": "invalid"}).status_code == 422


def test_read_only_staging_does_not_accept_new_jobs(client, monkeypatch):
    monkeypatch.setenv("PDUFA_MIGRATION_READ_ONLY", "1")
    assert client.post("/api/assessment-runtime/runs", json=body(4),
                       headers=HEADERS).status_code == 503
    assert client.get("/api/assessment-runtime/history/NCT04576949?contract=SCIENTIFIC_1_6",
                      headers=HEADERS).status_code == 200


def test_dedicated_service_rejects_sqlite_or_wrong_named_postgres(monkeypatch):
    staging._database_engine.cache_clear()
    monkeypatch.setenv("PDUFA_REQUIRE_POSTGRES", "1")
    monkeypatch.setenv("PDUFA_LEVEL456_DATABASE_NAME", "scientific456")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///tmp/anything.sqlite")
    with pytest.raises(HTTPException) as err:
        staging._database_engine()
    assert err.value.status_code == 503
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:secret@localhost/not_the_expected_database")
    with pytest.raises(HTTPException) as err:
        staging._database_engine()
    assert err.value.status_code == 503
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test:secret@localhost/scientific456")
    monkeypatch.setenv("PDUFA_REQUIRE_POSTGRES", "0")
    with pytest.raises(HTTPException) as err:
        staging._database_engine()
    assert err.value.status_code == 503
    staging._database_engine.cache_clear()


def test_local_free_staging_compose_cannot_reach_production_or_write_assessments():
    """Local fallback must be isolated and read-only by default."""
    root = Path(__file__).resolve().parents[3]
    config = (root / 'infra/scientific456-local/compose.yaml').read_text(encoding='utf-8')
    launcher = (root / 'infra/scientific456-local/Start-Scientific456Local.ps1').read_text(encoding='utf-8')
    ignore = (root / '.gitignore').read_text(encoding='utf-8')
    assert 'name: pdufa-scientific456-local' in config
    assert 'image: postgres:16-alpine' in config
    assert 'POSTGRES_DB: scientific456' in config
    assert 'POSTGRES_USER: scientific456_app' in config
    assert 'scientific456_pgdata:/var/lib/postgresql/data' in config
    assert config.count('ports:') == 1
    assert '"127.0.0.1:8765:8000"' in config
    assert 'Dockerfile.scientific456' in config
    for required in (
        'PDUFA_LEVEL456_DATABASE_NAME: scientific456',
        'PDUFA_REQUIRE_POSTGRES: "1"',
        'PDUFA_MIGRATION_READ_ONLY: "1"',
        'PDUFA_MIGRATION_COPY_ON_BOOT: "0"',
        'PDUFA_MEDICAL_BATCH_AUTORUN: "0"',
        'PDUFA_INSTALL_MONITOR_ENABLED: "0"',
    ):
        assert required in config
    assert 'PDUFA_LEVEL456_BACKEND_ENABLED: "1"' in config
    assert 'SCIENTIFIC456_INTERNAL_API_KEY' in config
    assert 'SCIENTIFIC456_DB_PASSWORD' in config
    assert 'localhost:5432' not in config
    assert '.env' in ignore
    assert 'WriteAllText($envFile' in launcher
    assert 'RandomNumberGenerator' in launcher
    assert launcher.count('Where-Object { $_ -match') == 2
    assert 'docker context inspect' in launcher
    assert "docker info --format '{{.OSType}}'" in launcher
    assert "Remote Docker context refused" in launcher
    assert 'config --quiet' in launcher
    assert 'up -d --build' in launcher
    verifier = (root / 'infra/scientific456-local/Test-Scientific456Local.ps1').read_text(encoding='utf-8')
    assert 'Invoke-RestMethod -Method Get' in verifier
    assert '$base/health' in verifier and '$base/version' in verifier
    assert 'NCT00000000?contract=SCIENTIFIC_1_6' in verifier
    assert 'PDUFA_MIGRATION_READ_ONLY: "1"' in verifier
    assert 'Invoke-RestMethod -Method Post' not in verifier
    assert not any(k in config for k in ('ALPACA_API_KEY', 'TELEGRAM_BOT_TOKEN',
                                         'PDUFA_API_BASE_URL', 'PDUFA_LEVEL123_API_BASE_URL'))
