"""Permanent retirement: active predictions are independent; history survives."""
import ast
import copy
import json
from pathlib import Path
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.pool import StaticPool
from app import phase3_catalog
from app.main import (CustomFdaOverlayPayload, PDUFA_CHART_FEATURES, active_pdufa_chart_features, preserve_retired_feature_archive)
from app.retired_analysis_guard import reject_retired_analysis_payload

@pytest.mark.parametrize('payload', [
    {'raas_score': 90}, {'raasScore': None},
    {'metadata': {'framework': 'RAAS_FIVE_FACTOR'}},
    {'model_version': 'CLINICAL_FIVE_2026_11_05'},
    {'scientific_readiness': 'RAAS_COMPLETE'},
    {'confidence_basis': 'raas-derived rating'},
    {'sourceType': 'RAAS_RESEARCH_SCORE'},
    {'evidence_ids': ['raas:archived-score']},
])
def test_active_prediction_rejects_retired_inputs_before_storage(payload):
    class NoStorage:
        def begin(self):
            raise AssertionError('Retired input reached storage')
    with pytest.raises(ValueError, match='retired|Retired'):
        phase3_catalog.record_prediction(NoStorage(), payload)

def test_source_prose_is_not_an_input_score_or_model():
    payload = {'model_version': 'independent-medical-review-v1',
               'uncertainty': 'Historical RAAS records are excluded from this analysis.',
               'evidence_ids': ['ctgov:original-document-hash'], 'confidence': None}
    original = copy.deepcopy(payload)
    reject_retired_analysis_payload(payload)
    assert payload == original

def test_chart_cannot_reenable_retired_feature_from_new_or_saved_settings():
    assert 'raas-snapshot' not in PDUFA_CHART_FEATURES
    saved = ['safety', 'raas-snapshot', 'countdown'];original = saved[:]
    assert active_pdufa_chart_features(saved) == ['countdown', 'safety']
    assert saved == original
    with pytest.raises(HTTPException) as exc:
        CustomFdaOverlayPayload(version=1, enabledFeatures=['raas-snapshot']).canonical('PDUFA-000069')
    assert exc.value.status_code == 422

def test_archived_prediction_readable_but_never_current_or_validated():
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    phase3_catalog.initialize(engine)
    encoded = json.dumps({'model_version': 'RAAS_30_METRIC_HISTORY', 'grade': 85})
    with engine.begin() as c:
        c.execute(text('''INSERT INTO phase3_predictions
          (prediction_id,nct_id,application_id,decision,created_at,evidence_cutoff,
           evidence_ids,confidence,uncertainty,scientific_readiness,document,recorded_at)
          VALUES('historical-score','NCT00000001','NDA000001:cycle','PASS',
          '2026-01-01T00:00:00Z','2025-12-31T00:00:00Z','[]',0.85,
          'Historical output only','HISTORICAL',:document,'2026-01-01T00:00:00Z')'''), {'document': encoded})
    app = FastAPI();phase3_catalog.install_routes(app, lambda: engine, lambda: None, lambda: None)
    response = TestClient(app).get('/api/phase3-trials/NCT00000001/predictions').json()
    assert response['latest_prediction'] is None and response['decision'] == 'ABSTAIN'
    assert response['status'] == 'ARCHIVE_ONLY'
    historical = response['predictions'][0]
    assert historical['archive_only'] is True
    assert historical['confidence'] == 0.85
    assert historical['correctness'] is None
    with engine.connect() as c:
        assert c.execute(text('SELECT document FROM phase3_predictions')).scalar_one() == encoded
    engine.dispose()

def test_analyze_and_fda_prediction_import_graph_has_no_retired_scoring():
    root = Path(__file__).resolve().parents[1] / 'app'
    pending = ['main', 'nct_live_stream', 'phase3_catalog', 'phase3_ingestion', 'phase3_regulatory'];seen = set()
    while pending:
        module = pending.pop()
        if module in seen:continue
        seen.add(module);path = root / (module + '.py')
        if not path.exists():continue
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ImportFrom):
                imported = node.module or ''
                assert not any(part.startswith('raas') for part in imported.lower().split('.')), path
                if node.level == 1 and imported:pending.append(imported.split('.')[0])
            elif isinstance(node, ast.Import):
                assert all(not any(part.startswith('raas') for part in alias.name.lower().split('.')) for alias in node.names), path
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == '__import__':
                assert not (node.args and isinstance(node.args[0], ast.Constant) and 'raas' in str(node.args[0].value).lower()), path
    assert {'main', 'phase3_catalog', 'nct_live_stream'} <= seen


def test_unrelated_overlay_edits_keep_retired_preferences_as_inert_archive():
    prior = [{'id': 'pdufa-chart-feature-selection-v1', 'kind': 'feature_selection',
              'enabledFeatures': ['safety', 'raas-snapshot']}]
    original = copy.deepcopy(prior)
    current = [{'id': 'pdufa-chart-feature-selection-v1', 'kind': 'feature_selection',
                'enabledFeatures': ['safety']}]
    result = preserve_retired_feature_archive(prior, current)
    assert prior == original
    assert result[0] == current[0]
    assert result[1]['kind'] == 'retired_feature_archive'
    assert result[1]['originalSelection'] == prior[0]
    assert preserve_retired_feature_archive(result, current) == result
