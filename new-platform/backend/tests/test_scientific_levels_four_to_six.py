"""Additive L04–L06 scientific research contract: no changes to saved 123."""
from datetime import date
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text

from app import assessment_runtime as runtime
from app import scientific_trial_assessment as scientific
from test_assessment_runtime import engine
from test_scientific_trial_assessment import source, revise


def request(level, *, contract="SCIENTIFIC_1_6", mode="CURRENT_EVIDENCE", cutoff=None):
    return runtime.RunInput(nct="NCT04576949", level=level, mode=mode,
                            cutoffDate=cutoff, contract=contract)


@pytest.mark.parametrize("level,name", [
    (4, "Safety and benefit-risk"),
    (5, "Indication-specific clinical assessment"),
    (6, "FDA regulatory readiness"),
])
def test_opt_in_scientific_456_evaluates_original_sources_without_fda_prediction(level, name):
    report = runtime.assess(request(level), source())
    assert report["contract"] == "SCIENTIFIC_1_6"
    assert report["level"] == level
    assert report["name"] == name
    assert report["kind"] == "EXECUTED_SCIENTIFIC_TRIAL_ASSESSMENT"
    assert report["engineVersion"].startswith(scientific.EXTENDED_VERSION)
    assert report["score"]["kind"] == "NOT_VALIDATED"
    assert report["score"]["value"] is None
    assert report["fdaPrediction"]["outcome"] == "ABSTAIN"
    assert report["fdaPrediction"]["probability"] is None
    assert report["historicalAccuracyEligible"] is False
    assert set(report["prerequisiteAssessments"]) == {str(i) for i in range(1, level)}
    assert report["checks"]


def test_safety_and_regulatory_unknowns_are_not_counted_as_clearance():
    report = runtime.assess(request(4), source())
    checks = {x["id"]: x for x in report["checks"]}
    assert checks["benefit_risk_interpretation"]["state"] == "UNVERIFIED"
    assert checks["benefit_risk_interpretation"]["value"] is None
    regulatory = runtime.assess(request(6), source())
    checks = {x["id"]: x for x in regulatory["checks"]}
    assert checks["application_identity_and_pathway"]["state"] == "UNVERIFIED"
    assert checks["manufacturing_and_inspection"]["state"] == "UNVERIFIED"
    assert regulatory["observations"][0]["reviewTiming"] == "NOT_EVALUATED"


def test_indication_standard_of_care_and_thresholds_are_unverified():
    report = runtime.assess(request(5), source())
    checks = {x["id"]: x for x in report["checks"]}
    assert checks["indication_definition"]["state"] == "SOURCE_VERIFIED"
    assert checks["standard_of_care_context"]["state"] == "UNVERIFIED"
    assert checks["meaningful_effect_threshold"]["state"] == "UNVERIFIED"


def test_early_phase_not_dinged_for_unavailable_regulatory_submission():
    def edit(doc):
        doc["protocolSection"]["designModule"]["phases"] = ["PHASE1"]
        doc["protocolSection"]["statusModule"]["overallStatus"] = "RECRUITING"
        doc["resultsSection"] = {}
    report = runtime.assess(request(6), revise(source(), edit))
    checks = {x["id"]: x for x in report["checks"]}
    assert checks["application_dossier"]["state"] == "NOT_YET_EXPECTED"
    assert checks["manufacturing_and_inspection"]["state"] == "NOT_YET_EXPECTED"
    assert report["fdaPrediction"]["outcome"] == "ABSTAIN"


def test_original_123_scientific_contract_remains_unchanged():
    for level in (1, 2, 3):
        report = runtime.assess(request(level, contract="SCIENTIFIC_1_3"), source())
        assert report["contract"] == "SCIENTIFIC_1_3"
        assert report["name"] == scientific.NAMES[level]
        assert report["engineVersion"] == scientific.VERSION + "/level-" + str(level)
        assert report["score"]["value"] is None
    with pytest.raises(Exception, match="Levels 1–3 only"):
        request(4, contract="SCIENTIFIC_1_3").checked()


def test_isolated_contract_cannot_run_original_levels_123():
    for level in (1, 2, 3):
        with pytest.raises(Exception, match='Levels 4–6 only'):
            request(level).checked()
        # Direct research execution is independently guarded; a caller must
        # never be able to label an original 123 report as scientific 456.
        with pytest.raises(ValueError, match='Levels 4–6 only'):
            runtime.assess(request(level), source())


def test_direct_123_execution_rejects_level_456():
    for level in (4, 5, 6):
        with pytest.raises(ValueError, match='Levels 1–3 only'):
            runtime.assess(request(level, contract='SCIENTIFIC_1_3'), source())


def test_456_historical_source_chronology_and_answer_separation():
    q = request(4, mode="BLIND_HISTORICAL", cutoff=date(2021, 1, 1))
    base = runtime.assess(q, source())
    modified = revise(source(), lambda doc: doc.update({
        "fdaActualOutcome": "APPROVED",
        "cachedPrediction": {"probability": 0.99},
    }))
    compared = runtime.assess(q, modified)
    assert base["checks"] == compared["checks"]
    assert base["observations"] == compared["observations"]
    with pytest.raises(ValueError, match="leakage|chronology"):
        runtime.assess(request(6, mode="BLIND_HISTORICAL", cutoff=date(2019, 1, 1)), source())


@pytest.mark.parametrize("level", [4, 5, 6])
def test_456_runs_persist_as_separate_immutable_reports(engine, monkeypatch, level):
    monkeypatch.setattr(runtime, "collect_documents", lambda value, document_level: value)
    q = request(level)
    run_id = runtime.create(engine, q)
    runtime.execute(engine, run_id, lambda _: source())
    saved = runtime.status(engine, q.nct, run_id)
    assert saved["status"] == "COMPLETED"
    assert saved["report"]["contract"] == "SCIENTIFIC_1_6"
    assert saved["report"]["level"] == level
    assert saved["report"]["fdaPrediction"]["outcome"] == "ABSTAIN"


def test_staging_456_http_requires_explicit_opt_in_and_preserves_123(engine, monkeypatch):
    """No 456 writes if the runtime has not been explicitly enabled."""
    monkeypatch.delenv('PDUFA_LEVEL456_BACKEND_ENABLED', raising=False)
    monkeypatch.setattr(runtime, 'execute', lambda db, run_id: None)
    app = FastAPI()
    app.include_router(runtime.router(lambda: engine, lambda: None, lambda: None,
                                      lambda: None, allow_local=True))
    url = '/api/assessment-runtime/runs'
    with TestClient(app) as client:
        refused = client.post(url, json=request(4).model_dump(mode='json'))
        assert refused.status_code == 503
        with engine.connect() as connection:
            assert connection.execute(text('SELECT count(*) FROM assessment_v2_jobs')).scalar_one() == 0
        # The existing 123 path remains independently usable.
        original = client.post(url, json=request(1, contract='SCIENTIFIC_1_3').model_dump(mode='json'))
        assert original.status_code == 202
        monkeypatch.setenv('PDUFA_LEVEL456_BACKEND_ENABLED', '1')
        accepted = client.post(url, json=request(4).model_dump(mode='json'))
        assert accepted.status_code == 202
        result = client.get('/api/assessment-runtime/runs/NCT04576949/'+accepted.json()['runId'])
        assert result.status_code == 200
        assert result.json()['status'] == 'QUEUED'
        with engine.connect() as connection:
            assert connection.execute(text('SELECT count(*) FROM assessment_v2_jobs')).scalar_one() == 2


def test_history_contract_filter_is_applied_before_fifty_result_limit(engine, monkeypatch):
    """Many new 123 reports must never hide older saved scientific 456 evidence."""
    monkeypatch.setattr(runtime, 'collect_documents', lambda value, document_level: value)
    q = request(4)
    original_run = runtime.create(engine, q)
    runtime.execute(engine, original_run, lambda _: source())
    assert runtime.status(engine, q.nct, original_run)['status'] == 'COMPLETED'
    for i in range(55):
        old_q = request(1, contract='SCIENTIFIC_1_3')
        old_run = runtime.create(engine, old_q)
        report = {'contract': 'SCIENTIFIC_1_3', 'nct': q.nct, 'level': 1,
                  'runId': old_run, 'fdaPrediction': {'outcome': 'ABSTAIN'}}
        with engine.begin() as conn:
            conn.execute(text('''INSERT INTO assessment_v2_results
                (run_id,nct_id,level,engine_version,mode,created_at,report_hash,report_json)
                VALUES(:run,:nct,1,'old-science-1','CURRENT_EVIDENCE',:created,:hash,:report)'''),
                {'run': old_run, 'nct': q.nct, 'created': f'2035-01-01T00:00:{i:02d}+00:00',
                 'hash': runtime.sha(report), 'report': runtime.packed(report)})
    unfiltered = runtime.history(engine, q.nct)
    assert len(unfiltered['runs']) == 50
    assert unfiltered['hasMore'] is True
    filtered = runtime.history(engine, q.nct, contract='SCIENTIFIC_1_6')
    assert filtered['hasMore'] is False
    assert len(filtered['runs']) == 1
    assert filtered['runs'][0]['runId'] == original_run
    assert filtered['runs'][0]['level'] == 4
    assert filtered['runs'][0]['contract'] == 'SCIENTIFIC_1_6'
    app = FastAPI()
    app.include_router(runtime.router(lambda: engine, lambda: None, lambda: None,
                                      lambda: None, allow_local=True))
    with TestClient(app) as client:
        response = client.get('/api/assessment-runtime/history/NCT04576949?contract=SCIENTIFIC_1_6')
        assert response.status_code == 200
        assert len(response.json()['runs']) == 1
        assert client.get('/api/assessment-runtime/history/NCT04576949?contract=untrusted').status_code == 422
