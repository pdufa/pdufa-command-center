"""Synthetic-only end-to-end persistence test inside a disposable CI PostgreSQL container.

NOT a clinical trial analysis. Never import or call the real network registry
collector; the entire dataset and historical decision linkage are fabricated.
Do not run outside an ephemeral GitHub Actions container.
"""
from __future__ import annotations

import hashlib
import json
import os
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DatabaseError

from app import assessment_runtime as runtime
from app import scientific_456_staging as staging

NCT = "NCT00000000"  # deliberately synthetic identity; not a real clinical assessment
CONTRACT = "SCIENTIFIC_1_6"
API = "/api/assessment-runtime"

if os.environ.get("CI") != "true" or os.environ.get("SCIENTIFIC456_EPHEMERAL_TEST") != "1":
    raise SystemExit("Only disposable CI PostgreSQL test mode is allowed")
if os.environ.get("PDUFA_MIGRATION_READ_ONLY") != "0":
    raise SystemExit("Expected explicit write-test override in this disposable process")
url = make_url(os.environ["DATABASE_URL"])
if (url.get_backend_name() != "postgresql" or url.host != "postgres"
        or url.database != "scientific456"):
    raise SystemExit("Refusing any database other than local disposable CI scientific456")

db = staging._database_engine()
with db.connect() as conn:
    assert conn.execute(text("SELECT current_database()")).scalar_one() == "scientific456"
    assert conn.execute(text("SELECT current_user")).scalar_one() == "scientific456_app"

def synthetic_source(captured: str | None = None) -> dict:
    captured = captured or runtime.now()
    original = {
        "protocolSection": {
            "identificationModule": {
                "nctId": NCT, "briefTitle": "Synthetic-only CI research",
                "orgStudyIdInfo": {"id": "CI-FAKE-456"}
            },
            "statusModule": {
                "overallStatus": "COMPLETED",
                "lastUpdatePostDateStruct": {"date": "2020-01-01"}
            },
            "designModule": {
                "phases": ["PHASE3"],
                "designInfo": {"allocation": "RANDOMIZED"},
                "enrollmentInfo": {"count": 100}
            },
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Synthetic, not real, sponsor"}
            },
            "conditionsModule": {"conditions": ["Fictional CI indication"]},
            "eligibilityModule": {"eligibilityCriteria": "Synthetic subjects"},
            "armsInterventionsModule": {
                "interventions": [{"type": "DRUG", "name": "Synthetic-only test agent"}],
                "armGroups": [{"label": "Fake treatment", "type": "EXPERIMENTAL"},
                              {"label": "Fake placebo", "type": "PLACEBO_COMPARATOR"}]
            },
            "outcomesModule": {
                "primaryOutcomes": [{"measure": "Fabricated test endpoint",
                                     "timeFrame": "12 weeks"}]
            }
        },
        "resultsSection": {
            "outcomeMeasuresModule": {
                "outcomeMeasures": [{
                    "type": "PRIMARY", "title": "Fabricated test measurement",
                    "analyses": [{"paramValue": "2", "ciLowerLimit": "1",
                                  "ciUpperLimit": "3"}]
                }]
            },
            "adverseEventsModule": {"description": "Fake safety observations"},
            "participantFlowModule": {"description": "Fake cohort flow"}
        }
    }
    doc = runtime.sanitize(original, NCT, captured)
    raw_digest = hashlib.sha256(b"SYNTHETIC_ONLY_NOT_A_REAL_REGISTRY_RESPONSE").hexdigest()
    return {
        "snapshot_id": str(uuid4()), "nct_id": NCT,
        "captured_at": captured, "published_at": "2020-01-01",
        "source_url": "https://clinicaltrials.gov/api/v2/studies/" + NCT,
        "raw_sha256": raw_digest, "input_sha256": runtime.sha(doc),
        "document_json": runtime.packed(doc)
    }

network_collection_count = 0

def synthetic_collector(nct):
    global network_collection_count
    network_collection_count += 1
    assert nct == NCT, "No other trial may be fetched"
    return synthetic_source()

# TestClient exercises the real staging HTTP routes and real PostgreSQL.
# The isolated process substitutes fake source collection only; no live request.
original_execute = runtime.execute
runtime.execute = lambda engine, run_id: original_execute(
    engine, run_id, collector=synthetic_collector)
runtime.collect_documents = lambda source, level: source

headers = {"X-Pdufa-Internal-Key": os.environ["PDUFA_INTERNAL_API_KEY"]}
runs = []
with TestClient(staging.app) as client:
    assert client.get(API + "/health").status_code == 200
    for level in (4, 5, 6):
        payload = {"nct": NCT, "level": level,
                   "mode": "CURRENT_EVIDENCE", "contract": CONTRACT}
        posted = client.post(API + "/runs", headers=headers, json=payload)
        assert posted.status_code == 202, posted.text
        run_id = posted.json()["runId"]
        response = client.get(f"{API}/runs/{NCT}/{run_id}",
                              params={"contract": CONTRACT}, headers=headers)
        assert response.status_code == 200, response.text
        state = response.json()
        assert state["status"] == "COMPLETED", state.get("error")
        report = state["report"]
        assert report["nct"] == NCT and report["level"] == level
        assert report["contract"] == CONTRACT
        assert report["score"]["kind"] == "NOT_VALIDATED"
        assert report["score"]["value"] is None
        assert report["fdaPrediction"]["outcome"] == "ABSTAIN"
        assert report["fdaPrediction"]["probability"] is None
        assert len(report["reportHash"]) == 64
        runs.append(run_id)
    assert network_collection_count == 3, "One fake collection per current run"
    print("PASS actual PostgreSQL API execution/persistence for L04, L05 and L06")

    first = client.get(f"{API}/history/{NCT}", params={"contract": CONTRACT},
                       headers=headers)
    assert first.status_code == 200
    items = first.json()["runs"]
    assert len(items) == 3 and {x["runId"] for x in items} == set(runs)
    assert {x["level"] for x in items} == {4, 5, 6}
    assert first.json()["hasMore"] is False
    assert client.get(f"{API}/history/{NCT}", params={"contract": "SCIENTIFIC_1_3"},
                      headers=headers).status_code == 422
    assert client.get(f"{API}/runs/NCT00000001/{runs[0]}",
                      params={"contract": CONTRACT}, headers=headers).status_code == 404
    assert client.get(f"{API}/history/{NCT}",
                      params={"contract": CONTRACT, "before": "invalid"},
                      headers=headers).status_code == 422
    print("PASS immutable run/status/history readback, exact NCT and contract isolation")

    blind_payload = {"nct": NCT, "level": 6, "mode": "BLIND_HISTORICAL",
                     "cutoffDate": "2021-01-01", "contract": CONTRACT}
    denied = client.post(API + "/runs", json=blind_payload, headers=headers)
    assert denied.status_code == 409
    print("PASS blind history refuses missing verified decision-date linkage")

    # Entirely synthetic historical application and original pre-cutoff source.
    with db.begin() as c:
        c.execute(text("""CREATE TABLE phase3_trial_applications (
            nct_id TEXT, application_id TEXT, verification_status TEXT)"""))
        c.execute(text("""CREATE TABLE phase3_fda_decisions (
            application_id TEXT, decision_date TEXT, verification_status TEXT,
            decision TEXT)"""))
        c.execute(text("""INSERT INTO phase3_trial_applications VALUES
            ('NCT00000000','CI-FAKE-APPLICATION','VERIFIED')"""))
        c.execute(text("""INSERT INTO phase3_fda_decisions VALUES
            ('CI-FAKE-APPLICATION','2021-02-01','VERIFIED',
             'OUTCOME_MUST_NEVER_LEAK')"""))
        frozen = synthetic_source("2020-02-01T00:00:00+00:00")
        c.execute(text("""INSERT INTO assessment_v2_sources
            (snapshot_id,nct_id,captured_at,published_at,source_url,
             raw_sha256,input_sha256,document_json)
            VALUES(:snapshot_id,:nct_id,:captured_at,:published_at,:source_url,
                   :raw_sha256,:input_sha256,:document_json)"""), frozen)

    before = network_collection_count
    created = client.post(API + "/runs", json=blind_payload, headers=headers)
    assert created.status_code == 202, created.text
    blind_run = created.json()["runId"]
    result = client.get(f"{API}/runs/{NCT}/{blind_run}",
                        params={"contract": CONTRACT}, headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "COMPLETED", result.json().get("error")
    blind = result.json()["report"]
    assert blind["mode"] == "BLIND_HISTORICAL"
    assert blind["cutoffDate"] == "2021-01-01"
    assert blind["evidence"]["captured_at"].startswith("2020-02-01")
    assert blind["fdaPrediction"]["outcome"] == "ABSTAIN"
    assert "OUTCOME_MUST_NEVER_LEAK" not in runtime.packed(blind)
    assert network_collection_count == before, "Blind run must not fetch current sources"
    print("PASS blind saved-report chronology, decision-label exclusion, no current-source fetch")

    # Verify the database, not just Python code, refuses changes to saved evidence.
    for table in ("assessment_v2_sources", "assessment_v2_results"):
        for mutation in (f"DELETE FROM {table}",
                         f"UPDATE {table} SET nct_id = 'NCT00000001'"):
            try:
                with db.begin() as c:
                    c.execute(text(mutation))
            except DatabaseError:
                pass
            else:
                raise AssertionError(f"PostgreSQL must reject {mutation}")
    final = client.get(f"{API}/history/{NCT}", params={"contract": CONTRACT},
                       headers=headers)
    assert final.status_code == 200
    assert {x["runId"] for x in final.json()["runs"]} == set(runs + [blind_run])
    print("PASS PostgreSQL triggers block DELETE/UPDATE of immutable snapshots and results")

print("PASS disposable synthetic-only write-mode persistence test completed")
