import copy
import hashlib
import asyncio
import os
from datetime import date

import pytest
from fastapi import FastAPI, Header, HTTPException
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool

from app import phase3_catalog as catalog


@pytest.fixture
def engine():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    catalog.initialize(engine)
    yield engine
    engine.dispose()


def study(nct="NCT00116805", *, status="COMPLETED", completed="2020-02-03", sponsor="Example Sponsor", drug="Investigational Drug", indication="Example Disease"):
    return {"protocolSection": {
        "identificationModule": {"nctId": nct, "briefTitle": "A Phase 3 investigation"},
        "sponsorCollaboratorsModule": {"leadSponsor": {"name": sponsor}},
        "designModule": {"phases": ["PHASE3"]},
        "armsInterventionsModule": {"interventions": [{"type": "DRUG", "name": drug}]},
        "conditionsModule": {"conditions": [indication]},
        "statusModule": {"overallStatus": status, "completionDateStruct": {"date": completed} if completed else {}},
        "outcomesModule": {"primaryOutcomes": [{"measure": "Reported endpoint"}]},
    }, "resultsSection": {"outcomeMeasuresModule": {"outcomeMeasures": [{"type": "PRIMARY", "title": "Reported endpoint", "unitOfMeasure": "participants", "classes": [{"categories": [{"measurements": [{"value": "37"}]}]}]}]}}}


def record(document=None, *, when="2026-10-30T19:00:00+00:00"):
    doc = document or study()
    nct = doc["protocolSection"]["identificationModule"]["nctId"]
    return {"nct_id": nct, "document": doc, "source_url": "https://clinicaltrials.gov/api/v2/studies/" + nct,
            "sha256": hashlib.sha256(catalog.canonical(doc).encode()).hexdigest(), "verified_at": when}


def insert(engine, **kwargs):
    return catalog.upsert_trial(engine, record(study(**kwargs)))


def regulatory(engine, *, nct="NCT00116805", app_id="NDA000001:example", decision="APPROVED", decision_date="2026-02-03", extra="", pdufa=None, previous=None):
    phrase = {"APPROVED": "FDA approved", "CRL": "Complete response letter", "EXTENDED": "FDA extended review", "PENDING": "Application submitted"}[decision]
    body = f"{phrase}. {nct} NDA000001 Investigational Drug Example Disease Example Sponsor. {extra}"
    source = {"url": "https://www.fda.gov/drugs/test-evidence", "sha256": hashlib.sha256(body.encode()).hexdigest(),
              "retrieved_at": "2026-10-30T19:00:00+00:00", "verification_status": "VERIFIED", "publisher_kind": "FDA", "document": body}
    if previous:
        source["previous_pdufa_date"] = previous
    return catalog.record_regulatory_evidence(engine, application={"application_id": app_id, "application_number": "NDA000001", "sponsor": "Example Sponsor", "drug": "Investigational Drug", "indication": "Example Disease"}, decision=decision, nct_ids=[nct], source=source, published_at="2026-02-03T12:00:00+00:00", decision_date=decision_date, pdufa_date=pdufa, submission_status="ACCEPTED")


def test_source_facts_and_posted_results_are_persisted_without_fda_inference(engine):
    r = record()
    r.update({"company": "Invented sponsor", "decision": "APPROVED", "ticker": "FAKE", "scientific_readiness": "READY"})
    catalog.upsert_trial(engine, r)
    response = catalog.catalog(engine, "PREVIOUS", as_of=date(2026, 10, 30))
    row = response["trials"][0]
    assert response["total"] == response["counts"]["PENDING"] == 1
    assert row["company"] == "Example Sponsor"
    assert row["ticker"] is None and row["actual_decision"] == "PENDING"
    assert row["scientific_readiness"] == "NOT READY"
    assert row["results_available"] is True
    assert "37 participants" in row["primary_endpoint_result"]
    assert "not adjudicated" in row["primary_endpoint_result"]
    assert row["evidence"][0]["verification_status"] == "VERIFIED"


@pytest.mark.parametrize("mutation", ["wrong_nct", "phase2", "no_results", "wrong_source", "bad_hash", "hash_mismatch", "naive_time", "missing_sponsor"])
def test_ineligible_or_bad_provenance_rejected(engine, mutation):
    r = record()
    if mutation == "wrong_nct": r["nct_id"] = "NCT99999999"
    if mutation == "phase2": r["document"]["protocolSection"]["designModule"]["phases"] = ["PHASE2"]
    if mutation == "no_results": r["document"].pop("resultsSection")
    if mutation == "wrong_source": r["source_url"] = "https://example.org/trial"
    if mutation == "bad_hash": r["sha256"] = "not-a-checksum"
    if mutation == "hash_mismatch": r["sha256"] = "0" * 64
    if mutation == "naive_time": r["verified_at"] = "2026-10-30T19:00:00"
    if mutation == "missing_sponsor": r["document"]["protocolSection"].pop("sponsorCollaboratorsModule")
    with pytest.raises(ValueError): catalog.upsert_trial(engine, r)
    assert catalog.catalog(engine, "CURRENT")["total"] == 0


def test_current_and_historical_boundaries_unknown_date_and_ongoing(engine):
    insert(engine, nct="NCT00000001", completed="2024-10-29")
    insert(engine, nct="NCT00000002", completed="2024-10-30")
    insert(engine, nct="NCT00000003", status="RECRUITING", completed="2020-01-01")
    insert(engine, nct="NCT00000004", completed=None)
    assert catalog.catalog(engine, "PREVIOUS", as_of=date(2026, 10, 30))["total"] == 1
    assert catalog.catalog(engine, "CURRENT", as_of=date(2026, 10, 30))["total"] == 3


def test_search_pagination_sort_are_server_side_and_not_limited_to_228(engine):
    for i in range(231):
        insert(engine, nct="NCT" + str(i).zfill(8), sponsor="Alpha" if i % 2 else "Beta")
    first = catalog.catalog(engine, "PREVIOUS", q="alpha", sort="nct_id", direction="asc", page=1, page_size=20)
    second = catalog.catalog(engine, "PREVIOUS", q="alpha", sort="nct_id", direction="asc", page=2, page_size=20)
    assert first["total"] == 115 and first["pages"] == 6
    assert len(first["trials"]) == len(second["trials"]) == 20
    assert set(r["nct_id"] for r in first["trials"]).isdisjoint(r["nct_id"] for r in second["trials"])
    assert catalog.catalog(engine, "PREVIOUS")["total"] == 231
    assert catalog.catalog(engine, "PREVIOUS", q="%_")["total"] == 0


@pytest.mark.parametrize("kwargs", [{"period": "BAD"}, {"decision": "PASS"}, {"sort": "nct_id;DROP TABLE phase3_trials"}, {"page": 0}, {"page_size": 101}, {"q": "x" * 201}])
def test_invalid_filters_fail_closed(engine, kwargs):
    with pytest.raises(ValueError): catalog.catalog(engine, **kwargs)


def test_counts_apply_period_and_search_before_selected_decision(engine):
    insert(engine)
    insert(engine, nct="NCT00000002")
    insert(engine, nct="NCT00000003", sponsor="Other Company")
    regulatory(engine)
    response = catalog.catalog(engine, "PREVIOUS", q="Example Sponsor", decision="APPROVED")
    assert response["total"] == 1
    assert response["counts"] == {"APPROVED": 1, "CRL": 0, "EXTENDED": 0, "PENDING": 1}
    assert response["trials"][0]["regulatory_application_ids"] == ["NDA000001:example"]


def test_dossier_revisions_immutable_and_frozen_stream_dossier_survives_update(engine):
    old = insert(engine)
    doc = study(drug="Revised name")
    newer = catalog.upsert_trial(engine, record(doc))
    assert old["dossier_id"] != newer["dossier_id"]
    with engine.connect() as c:
        frozen = catalog.saved_catalog_dossier(c, "NCT00116805", old["dossier_id"])
        latest = catalog.saved_catalog_dossier(c, "NCT00116805")
    assert frozen["document"]["products"] == [{"name": "Investigational Drug"}]
    assert latest["sha256"] == newer["sha256"]
    with pytest.raises(Exception):
        with engine.begin() as c: c.execute(text("DELETE FROM phase3_dossier_versions"))


def test_deduplicated_source_retrieval_keeps_canonical_frozen_hash(engine):
    old = insert(engine)
    again = catalog.upsert_trial(engine, record(when="2026-10-31T19:00:00+00:00"))
    assert again["sha256"] == old["sha256"]
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM phase3_trials")).scalar_one() == 1
        assert c.execute(text("SELECT COUNT(*) FROM phase3_dossier_versions")).scalar_one() == 1


def test_no_catalog_is_lookup_error_not_schema_error():
    empty = create_engine("sqlite://")
    with empty.connect() as c:
        with pytest.raises(LookupError): catalog.saved_catalog_dossier(c, "NCT00116805")


def test_conflicting_regulatory_evidence_remains_pending(engine):
    insert(engine)
    regulatory(engine)
    regulatory(engine, decision="CRL")
    row = catalog.catalog(engine, "PREVIOUS")["trials"][0]
    assert row["actual_decision"] == "PENDING" and row["fda_submission_status"] == "CONFLICTING"
    assert len(row["evidence"]) == 3


def test_different_applications_can_have_different_outcomes_without_approval_leakage(engine):
    insert(engine)
    regulatory(engine)
    regulatory(engine, app_id="NDA000001:other-scope", decision="CRL", decision_date="2026-03-04")
    assert catalog.catalog(engine, "PREVIOUS")["trials"][0]["actual_decision"] == "PENDING"


def test_later_outcome_for_same_application_supersedes_earlier_crl(engine):
    insert(engine)
    regulatory(engine, decision="CRL", decision_date="2026-01-01")
    regulatory(engine, decision="APPROVED", decision_date="2026-03-01")
    assert catalog.catalog(engine, "PREVIOUS")["trials"][0]["actual_decision"] == "APPROVED"


def test_extension_requires_real_changed_timeline_not_expired_date(engine):
    insert(engine)
    with pytest.raises(ValueError): regulatory(engine, decision="EXTENDED", pdufa="2026-10-01")
    regulatory(engine, decision="EXTENDED", pdufa="2027-01-01", previous="2026-10-01")
    assert catalog.catalog(engine, "PREVIOUS")["trials"][0]["actual_decision"] == "EXTENDED"


def test_explicit_fda_application_source_retained_independently(engine):
    insert(engine)
    body = "FDA approved Investigational Drug for Example Disease. Trial NCT00116805."
    application_body = '{"application_number":"NDA000001","sponsor":"Example Sponsor","drug":"Investigational Drug"}'
    source = {"url": "https://www.fda.gov/drugs/article", "sha256": hashlib.sha256(body.encode()).hexdigest(), "retrieved_at": "2026-10-30T19:00:00+00:00", "verification_status": "VERIFIED", "publisher_kind": "FDA", "document": body}
    app_source = {"url": "https://api.fda.gov/drug/drugsfda.json", "sha256": hashlib.sha256(application_body.encode()).hexdigest(), "retrieved_at": "2026-10-30T19:00:00+00:00", "verification_status": "VERIFIED", "document": application_body}
    catalog.record_regulatory_evidence(engine, application={"application_id": "NDA000001:scope", "application_number": "NDA000001", "sponsor": "Example Sponsor", "drug": "Investigational Drug", "indication": "Example Disease"}, decision="APPROVED", nct_ids=["NCT00116805"], source=source, application_source=app_source, published_at="2026-02-03T12:00:00+00:00", decision_date="2026-02-03")
    assert catalog.catalog(engine, "PREVIOUS")["trials"][0]["decision"] == "APPROVED"
    with engine.connect() as c:
        assert c.execute(text("SELECT COUNT(*) FROM phase3_evidence")).scalar_one() == 3


def test_unmapped_or_missing_regulatory_evidence_rejected(engine):
    insert(engine)
    with pytest.raises(ValueError): regulatory(engine, nct="NCT99999999")
    with pytest.raises(ValueError):
        catalog.record_regulatory_evidence(engine, application={}, decision="APPROVED", nct_ids=["NCT00116805"], source={"verification_status": "UNVERIFIED"}, published_at="2026-01-01T00:00:00Z")


def test_latest_existing_analysis_run_is_available_for_reuse(engine):
    insert(engine)
    with engine.begin() as c:
        c.execute(text("CREATE TABLE nct_stream_runs(run_id TEXT,nct_id TEXT,created_at TEXT)"))
        c.execute(text("INSERT INTO nct_stream_runs VALUES('old','NCT00116805','2026-01-01'),('new','NCT00116805','2026-02-01')"))
    assert catalog.catalog(engine, "PREVIOUS")["trials"][0]["latest_run_id"] == "new"


def test_predictions_are_immutable_provenance_bound_and_no_retrospective_accuracy(engine):
    insert(engine)
    regulatory(engine, decision_date="2026-02-03")
    source_id = "ctgov:" + record()["sha256"]
    prediction = {"prediction_id": "prediction-1", "nct_id": "NCT00116805", "application_id": "NDA000001:example", "decision": "PASS", "created_at": "2026-11-01T00:00:00Z", "evidence_cutoff": "2026-10-30T23:00:00Z", "evidence_ids": [source_id]}
    catalog.record_prediction(engine, prediction)
    report = catalog.historical_validation(engine)
    assert report["number_evaluated"] == 0 and report["temporally_eligible_predictions"] == 0
    assert report["accuracy_by_decision"]["PASS"]["accuracy"] is None
    with pytest.raises(Exception):
        with engine.begin() as c: c.execute(text("UPDATE phase3_predictions SET decision='CRL'"))
    prediction["prediction_id"] = "prediction-2"
    prediction["evidence_cutoff"] = "2026-09-01T00:00:00Z"
    with pytest.raises(ValueError): catalog.record_prediction(engine, prediction)


def test_prediction_without_verified_trial_application_relationship_rejected(engine):
    insert(engine)
    with pytest.raises(ValueError):
        catalog.record_prediction(engine, {"prediction_id": "unmapped", "nct_id": "NCT00116805", "application_id": "NDA000099:unknown", "decision": "PASS", "created_at": "2026-11-01T00:00:00Z", "evidence_cutoff": "2026-10-30T23:00:00Z", "evidence_ids": ["ctgov:" + record()["sha256"]]})


def test_historical_validation_empty_is_honest(engine):
    report = catalog.historical_validation(engine)
    assert report["status"] == "NOT_VALIDATED" and report["number_evaluated"] == 0
    assert report["calibration_metrics"] is None


def test_routes_keep_existing_auth_and_storage_dependencies(engine):
    app = FastAPI()
    def key(x_pdufa_internal_key: str | None = Header(default=None)):
        if x_pdufa_internal_key != "authorized-test-key": raise HTTPException(401)
    def storage(): return None
    catalog.install_routes(app, lambda: engine, key, storage)
    # Validate dependency graph without a local blocking-portal transport.
    routes = [r for r in app.routes if getattr(r, "path", "").startswith("/api/phase3-trials")]
    if not routes:
        nested = [getattr(r, "original_router", None) for r in app.routes]
        routes = [r for router in nested if router for r in router.routes]
    assert routes
    for route in routes:
        calls = {d.call for d in route.dependant.dependencies}
        assert key in calls and storage in calls


@pytest.mark.skipif(not os.environ.get("CI"), reason="Local AnyIO thread transport limitation; actual HTTP assertions execute in CI")
def test_actual_http_catalog_rejects_unauthorized_and_validates_filters(engine):
    import httpx
    app = FastAPI()
    async def key(x_pdufa_internal_key: str | None = Header(default=None)):
        if x_pdufa_internal_key != "authorized-test-key": raise HTTPException(401)
    async def storage(): return None
    catalog.install_routes(app, lambda: engine, key, storage)
    insert(engine)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            denied = await client.get("/api/phase3-trials?period=PREVIOUS")
            assert denied.status_code == 401
            accepted = await client.get("/api/phase3-trials?period=PREVIOUS", headers={"X-Pdufa-Internal-Key": "authorized-test-key"})
            assert accepted.status_code == 200 and accepted.json()["total"] == 1
            invalid = await client.get("/api/phase3-trials?period=BAD", headers={"X-Pdufa-Internal-Key": "authorized-test-key"})
            assert invalid.status_code == 422
            invalid_sort = await client.get("/api/phase3-trials?sort=drop", headers={"X-Pdufa-Internal-Key": "authorized-test-key"})
            assert invalid_sort.status_code == 422
    asyncio.run(exercise())
