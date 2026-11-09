"""The hosted acceptance driver never forges a session or grades source data."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'verify_medical_preview.py'
spec = importlib.util.spec_from_file_location('medical_preview_acceptance', SCRIPT)
acceptance = importlib.util.module_from_spec(spec)
spec.loader.exec_module(acceptance)


def test_missing_test_secret_stops_before_network_or_auth_attempt(monkeypatch):
    monkeypatch.delenv('DASHBOARD_PASSWORD', raising=False)
    monkeypatch.setattr(acceptance, 'build_opener', lambda *a: pytest.fail('No network without authorized credential'))
    with pytest.raises(acceptance.VerificationError, match='MISSING_AUTHORIZED'):
        acceptance.main()


def test_backend_projection_is_accepted_but_unreviewed_score_is_rejected():
    from app.medical_method_projection import project_trial_history
    data = {'review': project_trial_history({'nct':acceptance.PILOT})}
    assert acceptance.matrix_snapshot(data)['counts']['VERIFY_PHASE'] == 800
    data['review']['assessments'][0]['scoreOutOf100'] = 0
    with pytest.raises(acceptance.VerificationError, match='UNREVIEWED_EVIDENCE_SCORED'):
        acceptance.matrix_snapshot(data)


def test_changed_trial_and_forecast_cannot_pass_readback():
    from app.medical_method_projection import project_trial_history
    data = {'review':project_trial_history({'nct':'NCT05507203'})}
    with pytest.raises(acceptance.VerificationError, match='WRONG_MATRIX_IDENTITY'):
        acceptance.matrix_snapshot(data)
    data['review']['nct'] = acceptance.PILOT
    data['review']['fdaPredictions']['APPROVAL'] = 0.9
    with pytest.raises(acceptance.VerificationError, match='UNVALIDATED_FORECAST_RELEASED'):
        acceptance.matrix_snapshot(data)


def test_redirects_and_absolute_paths_cannot_forward_credentials():
    with pytest.raises(acceptance.VerificationError, match='UNEXPECTED_REDIRECT'):
        acceptance.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example')
    with pytest.raises(acceptance.VerificationError, match='INVALID_FIXED_ORIGIN_PATH'):
        acceptance.request(None, '//other.example/steal')


def test_revision36_panel_requires_each_original_digest_and_unresolved_population_label():
    import json
    data=json.loads((SCRIPT.parents[3]/'new-platform/frontend/data/acacia-original-history-revision36.json').read_text())
    text=' '.join(['Original registry evidence recovered', 'v26, v27, v29 and v30',
                  'do not resolve the reported 516 versus 517', 'ESTIMATED',
                  '18 mapped source leads', '782 positions not source mapped', '0/800',
                  'independent review before a clinical integrity judgment or grade',
                  'NOT CALIBRATED', 'ABSTAIN', 'r36.source-reconciliation', 'Locate active source task']+
                 [value for version in data['versions'] for value in
                  [version['submitted'],version['posted'],version['sourceSha256']]])
    acceptance.confirm_original_registry_panel(text)
    with pytest.raises(acceptance.VerificationError,match='ORIGINAL_REGISTRY_PANEL_INCOMPLETE'):
        acceptance.confirm_original_registry_panel(text.replace(data['versions'][2]['sourceSha256'],''))
    with pytest.raises(acceptance.VerificationError,match='ORIGINAL_REGISTRY_PANEL_INCOMPLETE'):
        acceptance.confirm_original_registry_panel(text.replace('do not resolve the reported 516 versus 517','resolved'))
