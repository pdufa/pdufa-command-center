import copy
import json
from pathlib import Path
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from app import main

@pytest.fixture
def client(monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    main.Base.metadata.create_all(engine)
    monkeypatch.setattr(main, 'ENGINE', engine)
    monkeypatch.setenv('PDUFA_INTERNAL_API_KEY', 'test-key')
    monkeypatch.delenv('PDUFA_MIGRATION_READ_ONLY', raising=False)
    main.app.dependency_overrides[main.require_level_assessment_storage] = lambda: None
    yield TestClient(main.app)
    main.app.dependency_overrides.clear()
    engine.dispose()

HEADERS = {'X-Pdufa-Internal-Key': 'test-key'}
URL = '/api/assessments/trial/history'

def report(level):
    # Retained exact-trial record; tests never alter source evidence archives.
    evidence = json.loads((Path(__file__).parents[2] / 'frontend/data/level16AssessmentEvidence.json').read_text())['trials'][0]
    return {'kind': 'TRIAL_LEVEL_ASSESSMENT', 'runId': str(uuid4()), 'nct': evidence['nct'], 'level': level,
            'mode': 'CURRENT_EVIDENCE', 'executedAt': '2026-11-14T00:00:00Z', 'engineVersion': f'phase-first-level-{level}-v1',
            'savedToDatabase': False, 'status': 'PARTIAL_RESEARCH_ENGINE', 'score': None,
            'fdaPrediction': {'outcome': 'ABSTAIN', 'probability': None, 'calibration': 'NO_VALIDATED_FDA_MODEL'},
            'evidence': {'url': evidence['registryUrl'], 'sha256': evidence['registryDigest'], 'verification': 'EXACT_NCT_REGISTRY_RESPONSE_ONLY'},
            'result': {'nct': evidence['nct'], 'levels': [evidence['levels'][level-1]]}}

@pytest.mark.parametrize('level', range(1, 7))
def test_each_level_persists_retrieves_and_never_overwrites(client, level):
    r = report(level)
    saved = client.post(URL, json=r, headers=HEADERS)
    assert saved.status_code == 200 and saved.json()['savedToDatabase'] is True
    history = client.get(URL, params={'nct': r['nct'], 'level': level}, headers=HEADERS).json()['runs']
    assert len(history) == 1 and history[0]['result'] == r['result']
    assert history[0]['engineVersion'] == r['engineVersion']
    assert client.post(URL, json=r, headers=HEADERS).status_code == 409
    r['runId'] = str(uuid4())
    assert client.post(URL, json=r, headers=HEADERS).status_code == 200
    assert len(client.get(URL, params={'nct': r['nct']}, headers=HEADERS).json()['runs']) == 2
    assert client.get(URL, params={'nct': 'NCT99999999'}, headers=HEADERS).json()['runs'] == []

def test_auth_read_only_and_rejected_historical_writes(client, monkeypatch):
    r = report(1)
    assert client.post(URL, json=r).status_code == 401
    assert client.get(URL, params={'nct': r['nct']}).status_code == 401
    for field, value in [('mode', 'BLIND_HISTORICAL'), ('score', 99), ('engineVersion', 'other-level'), ('level', 7), ('savedToDatabase', True)]:
        invalid = copy.deepcopy(r); invalid[field] = value
        assert client.post(URL, json=invalid, headers=HEADERS).status_code == 422
    monkeypatch.setenv('PDUFA_MIGRATION_READ_ONLY', 'true')
    assert client.post(URL, json=r, headers=HEADERS).status_code == 503
    assert client.get(URL, params={'nct': r['nct']}, headers=HEADERS).json()['runs'] == []


def test_hosted_history_refuses_sqlite_even_if_general_storage_allows_it(monkeypatch):
    monkeypatch.setattr(main, 'DATABASE_URL', 'sqlite:///ephemeral.sqlite3')
    monkeypatch.setattr(main, 'require_storage', lambda: None)
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as error:
        main.require_level_assessment_storage()
    assert error.value.status_code == 503
