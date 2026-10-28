"""Dated dashboard artifacts must track audited sources, without validation claims."""
from datetime import date
import json

import pytest

from research.fda_holdout_dashboard_snapshot import build_dashboard_snapshot, main, DASHBOARD_SNAPSHOT
from research.fda_verification_queue import build_verification_queue
from test_fda_holdout_reconstruction_integration import ACTIONS, HISTORY, PACKET


def test_committed_dashboard_is_reproducible_from_the_actual_six_case_sources():
    snapshot=build_dashboard_snapshot(as_of=date(2026,10,28))
    assert json.loads(DASHBOARD_SNAPSHOT.read_text()) == snapshot
    assert snapshot['historyRecords'] == 146
    assert len(snapshot['caseReports']) == 6
    for case in snapshot['caseReports']:
        dossier=case['scientific_dossier']
        assert len(dossier['layers']) == 8
        assert sum(len(layer['questions']) for layer in dossier['layers']) == 40
        assert dossier['summary']['independently_completed_assessments'] == 0
        assert len(dossier['depth_framework']['levels']) == 20
        assert dossier['depth_framework']['semantic_level_definitions_status'] == 'DEFINED_RESEARCH_PROTOCOL_NOT_INDEPENDENTLY_VALIDATED'
        assert case['main']['status'] == 'INSUFFICIENT_EVIDENCE'


def test_check_mode_detects_stale_snapshot_without_overwriting_it(tmp_path):
    path=tmp_path/'stale.json'
    path.write_text('{}\n')
    with pytest.raises(SystemExit) as err:
        main(['--as-of','2026-10-28','--output',str(path),'--check'])
    assert err.value.code == 1 and path.read_text() == '{}\n'
    assert main(['--as-of','2026-10-28','--output',str(path)]) == 0
    assert main(['--as-of','2026-10-28','--output',str(path),'--check']) == 0


def test_real_packet_preserves_contrary_clinical_results_and_regulatory_resolution():
    snapshot=build_dashboard_snapshot(as_of=date(2026,10,28))
    cases={case['event_key'].split('|')[0]:case for case in snapshot['caseReports']}
    tnxp={s['source_id']:s for s in cases['TNXP']['source_classification']}
    assert 'negative RALLY (F306)' in tnxp['TNXP-10K-TRIAL-CONSISTENCY']['finding']
    assert 'pancreatitis' in tnxp['TNXP-10K-SAFETY']['finding']
    uncy=next(s for s in cases['UNCY']['source_classification'] if s['source_id']=='UNCY-UNI-OLC-201-DENOMINATORS')
    assert all(denominator in uncy['finding'] for denominator in ('106','86','71','1/71','5/86','77/86'))
    assert 'not designed to evaluate efficacy' in uncy['finding']
    comparator=next(p for p in cases['UNCY']['related_precedents'] if p.get('application_id')=='NDA021468')
    assert comparator['public_availability_verified'] is False
    assert comparator['eligible_for_training'] is False
    assert 'cannot be compared directly' in comparator['comparison']
    vnda={s['source_id']:s for s in cases['VNDA']['source_classification']}
    assert vnda['VNDA-NOV28-HOLD-REVIEW']['available_on'] < vnda['VNDA-DEC4-HOLD-LIFTED']['available_on'] < cases['VNDA']['reconstruction_cutoff']
    assert 'distinct from NDA approval' in vnda['VNDA-DEC4-HOLD-LIFTED']['finding']
    assert all(s['classification']=='PREDECISION_RESEARCH_CANDIDATE' for s in (tnxp['TNXP-10K-SAFETY'],uncy,vnda['VNDA-DEC4-HOLD-LIFTED']))


def test_late_contrary_source_is_excluded_from_question_level_dossier(tmp_path):
    packet=json.loads(PACKET.read_text())
    row=next(c for c in packet['cases'] if c['ticker']=='TNXP')
    safety=next(s for s in row['observations'] if s['id']=='TNXP-10K-SAFETY')
    safety['available_on']='2025-08-16'
    path=tmp_path/'late.json';path.write_text(json.dumps(packet))
    queue=build_verification_queue(HISTORY,ACTIONS,reconstruction_manifest=path,as_of=date(2026,10,28))
    case=next(r['predecision_reconstruction'] for r in queue['queue'] if r.get('event_key')=='TNXP|2025-08-15')
    question=next(q for layer in case['scientific_dossier']['layers'] for q in layer['questions'] if q['question_id']=='S16')
    assert not question['observations']
    assert any(s['source_id']=='TNXP-10K-SAFETY' and s['reason']=='EXCLUDED_AFTER_RECONSTRUCTION_CUTOFF' for s in question['excluded_or_quarantined_sources'])
    assert question['scientific_conclusion'] is None


def test_new_nvax_and_bcrx_sources_use_filing_availability_not_trial_or_period_dates():
    cases={c['event_key'].split('|')[0]:c for c in build_dashboard_snapshot(as_of=date(2026,10,28))['caseReports']}
    nvax={s['source_id']:s for s in cases['NVAX']['source_classification']}
    assert nvax['NVAX-2023-PREVENT19']['available_on']=='2023-02-28'
    assert '29,949' in nvax['NVAX-2023-PREVENT19']['finding']
    assert 'not an FDA approval probability' in nvax['NVAX-2023-PREVENT19']['finding']
    assert all(p['eligible_for_training'] is False for p in cases['NVAX']['related_precedents'])
    bcrx={s['source_id']:s for s in cases['BCRX']['source_classification']}
    assert bcrx['BCRX-AUG5-REVIEW-EXTENSION']['available_on']=='2025-08-05'
    assert bcrx['BCRX-AUG5-REVIEW-EXTENSION']['classification']=='PREDECISION_RESEARCH_CANDIDATE'
    assert bcrx['BCRX-APEX-P-LEAD']['classification']=='QUARANTINED_PRINTED_DATE_ONLY'
    assert 'not its June 30 period end' in bcrx['BCRX-AUG5-REVIEW-EXTENSION']['finding']
