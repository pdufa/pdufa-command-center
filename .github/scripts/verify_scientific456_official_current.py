"""Real official-registry current-evidence smoke check in disposable 456 PostgreSQL.

Permits ONLY exact NCT04576949, an existing FOCUS trial, and only in
ephemeral GitHub Actions Docker service 'postgres/scientific456'.
This is NOT a validated clinical review, not a blind historical test, and
not an FDA approval-probability model. We deliberately do NOT collect PDFs;
missing protocol/SAP evidence must remain explicitly missing.
"""
import json
import os

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url

from app import assessment_runtime as runtime
from app import scientific_456_staging as staging

NCT = "NCT04576949"
CONTRACT = "SCIENTIFIC_1_6"
API = "/api/assessment-runtime"
EXPECTED = "https://clinicaltrials.gov/api/v2/studies/" + NCT

if not (os.environ.get("CI") == "true" and
        os.environ.get("SCIENTIFIC456_EPHEMERAL_OFFICIAL_TEST") == "1" and
        os.environ.get("PDUFA_MIGRATION_READ_ONLY") == "0"):
    raise SystemExit("Refusing official-data exercise outside opt-in disposable CI mode")
url = make_url(os.environ.get("DATABASE_URL", ""))
if url.get_backend_name() != "postgresql" or url.host != "postgres" or url.database != "scientific456":
    raise SystemExit("Refusing non-disposable or unexpected PostgreSQL database")
engine = staging._database_engine()
with engine.connect() as conn:
    assert conn.execute(text("SELECT current_database()")).scalar_one() == "scientific456"
    assert conn.execute(text("SELECT current_user")).scalar_one() == "scientific456_app"
    assert conn.execute(text("SELECT count(*) FROM information_schema.tables "
                             "WHERE table_schema='public' AND table_name LIKE 'assessment_v2_%'")).scalar_one() == 0

# Freeze only an original official registry HTTP receipt for each run.
# Deliberately no external PDF fetching: report document gaps, never invent them.
original_execute = runtime.execute
original_collector = runtime.collect_registry
collector_calls = []

def official_only(nct):
    assert nct == NCT, "Never fetch a different trial"
    item = original_collector(nct)  # exact HTTPS official API; enforces redirect/content-type/size
    assert item["source_url"] == EXPECTED
    assert item["nct_id"] == NCT
    document = json.loads(item["document_json"])
    assert document["protocolSection"]["identificationModule"]["nctId"] == NCT
    assert runtime.sha(document) == item["input_sha256"]
    assert item["published_at"] <= item["captured_at"][:10]
    assert len(item["raw_sha256"]) == 64
    assert "actualFdaOutcome" not in item["document_json"]
    collector_calls.append(item["snapshot_id"])
    return item

runtime.execute = lambda db, run_id: original_execute(db, run_id, collector=official_only)
runtime.collect_documents = lambda original, level: original

headers = {"X-Pdufa-Internal-Key": os.environ["PDUFA_INTERNAL_API_KEY"]}
with TestClient(staging.app) as api:
    assert api.get(API + "/health").status_code == 200
    run_ids = []
    for level in (4, 5, 6):
        posted = api.post(API + "/runs", headers=headers,
            json={"nct":NCT,"level":level,"mode":"CURRENT_EVIDENCE","contract":CONTRACT})
        assert posted.status_code == 202, posted.text
        run_id = posted.json()["runId"]
        state = api.get(f"{API}/runs/{NCT}/{run_id}",
                        params={"contract": CONTRACT}, headers=headers)
        assert state.status_code == 200
        result = state.json()
        assert result["status"] == "COMPLETED", result.get("error")
        report = result["report"]
        assert report["nct"] == NCT and report["level"] == level
        assert report["mode"] == "CURRENT_EVIDENCE" and report["contract"] == CONTRACT
        assert report["evidence"]["source_url"] == EXPECTED
        assert len(report["evidence"]["raw_sha256"]) == 64
        assert report["score"]["kind"] == "NOT_VALIDATED" and report["score"]["value"] is None
        assert report["fdaPrediction"]["outcome"] == "ABSTAIN"
        assert report["fdaPrediction"]["probability"] is None
        assert report["scientificStatus"] == "SOURCE_BOUND_ANALYSIS_NOT_VALIDATED"
        assert report["ownerReviewStatus"] == "OWNER_NOT_REVIEWED"
        assert not report["documentEvidence"], "No source PDF was reviewed"
        assert len(report["reportHash"]) == 64
        run_ids.append(run_id)
    assert len(collector_calls) == 3 and len(set(collector_calls)) == 3
    print("PASS official ClinicalTrials.gov source intake on exact FOCUS NCT for L04/L05/L06")

    history = api.get(f"{API}/history/{NCT}", headers=headers,
                      params={"contract": CONTRACT})
    assert history.status_code == 200
    saved = history.json()["runs"]
    assert len(saved) == 3 and {x["runId"] for x in saved} == set(run_ids)
    assert {x["evidence"]["snapshot_id"] for x in saved} == set(collector_calls)
    assert {x["level"] for x in saved} == {4,5,6}
    assert history.json()["hasMore"] is False
    print("PASS saved official-source provenance and immutable versions on temporary PostgreSQL")

    # Read a different NCT and another contract: no leakage across cohorts/frameworks.
    other = api.get(f"{API}/history/NCT00000000", headers=headers,
                    params={"contract": CONTRACT})
    assert other.status_code == 200 and other.json()["runs"] == []
    assert api.get(f"{API}/history/{NCT}", headers=headers,
                   params={"contract":"SCIENTIFIC_1_3"}).status_code == 422
    assert api.get(f"{API}/runs/NCT00000000/{run_ids[0]}", headers=headers,
                   params={"contract":CONTRACT}).status_code == 404
    print("PASS exact-NCT saved history isolation and 123 contract rejection")

with engine.connect() as conn:
    assert conn.execute(text("SELECT count(*) FROM assessment_v2_sources")).scalar_one() == 3
    assert conn.execute(text("SELECT count(*) FROM assessment_v2_results")).scalar_one() == 3

print("PASS current-source research-only exercise; NO FDA forecasts or historical inference")
