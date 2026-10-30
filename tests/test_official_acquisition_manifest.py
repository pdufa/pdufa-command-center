"""Synthetic acquisition bundles prove boundaries, never real FDA verification."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import zipfile

import pytest

from research.official_acquisition_manifest import build_acquisition_manifest, import_acquisition_bundle, main
from research.official_adjudication_packets import build_adjudication_packets
from research.scientific_historical_comparison import COMPARISON_CRITERIA


def document(family='APPROVAL_LETTER', case_index=0):
    return next(d for d in build_acquisition_manifest()['cases'][case_index]['documents'] if d['family'] == family)


def entry(tmp_path, *, doc=None, raw=b'%PDF-1.7\nSYNTHETIC TEST ONLY\n%%EOF', name='original.pdf'):
    doc = doc or document()
    (tmp_path / name).write_bytes(raw)
    return {'document_id': doc['document_id'], 'path': name,
        'sha256': hashlib.sha256(raw).hexdigest(), 'dataset_version': 'SYNTHETIC-TEST-v1',
        'operator_acquired_at': '2026-10-29T12:00:00Z',
        'claimed_published_at': None, 'publication_evidence': None}


def run(tmp_path, entries):
    return import_acquisition_bundle(entries, evidence_directory=tmp_path,
                                     retention_directory=tmp_path / 'retained')


def test_exact_manifest_reproducible_with_required_families_and_unchanged_catalog():
    result = build_acquisition_manifest()
    path = Path(__file__).parents[1] / 'research/evidence/official_acquisition_manifest_20261029.json'
    assert result == json.loads(path.read_text())
    assert result['case_count'] == 6
    criteria = {c[0] for c in COMPARISON_CRITERIA}
    for case in result['cases']:
        families = {d['family'] for d in case['documents']}
        assert {'APPLICATION_ACTION_DATASET', 'ORIGINAL_TARGET_DATE', 'FORMAL_TARGET_REVISION',
                'MULTIDISCIPLINARY_REVIEW', 'TRIAL_HISTORICAL_RECORD'} <= families
        assert len(case['verification_tasks']) == 9
        assert case['adjudicated_review_cycle_id'] is None
        assert not case['eligible_for_training_or_evaluation']
        for d in case['documents']:
            assert set(d['comparison_criteria']) <= criteria
            assert not d['independently_verified']
            if d['family'] in ('ORIGINAL_TARGET_DATE', 'FORMAL_TARGET_REVISION', 'MULTIDISCIPLINARY_REVIEW', 'TRIAL_HISTORICAL_RECORD'):
                assert d['source_url'] is None
    assert result['prediction_action'] == 'ABSTAIN'
    assert result['scientific_catalog_policy'] == 'EXISTING_650_DEFINITIONS_50_LEVELS_40_ASSESSMENTS_UNCHANGED'


def test_extra_crl_does_not_replace_original_cycle_and_unknown_trials_remain_unknown():
    result = build_acquisition_manifest()
    uncy = next(c for c in result['cases'] if c['application_id'] == 'NDA218607')
    crls = [d for d in uncy['documents'] if d['family'] == 'COMPLETE_RESPONSE_LETTER']
    assert len(crls) == 2
    assert uncy['claimed_review_cycle_id'] is None
    tnxp = next(c for c in result['cases'] if c['application_id'] == 'NDA219428')
    histories = [d for d in tnxp['documents'] if d['family'] == 'TRIAL_HISTORICAL_RECORD']
    assert len(histories) == 3
    assert sum(d['expected_registry_id'] is None for d in histories) == 2


def test_import_official_pdf_reuses_receipts_and_existing_adjudication_packets(tmp_path):
    report = run(tmp_path, [entry(tmp_path)])
    assert report['unique_document_versions_imported'] == 1
    assert report['independently_verified_decisions'] == 0
    assert report['evaluated_predictions'] == 0
    assert report['operational_metrics'] is report['probabilities'] is None
    assert report['prediction_readiness'] == 'NOT_READY'
    retained = tmp_path / 'retained'
    receipts = list(retained.glob('*.receipt.json'))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt['external_operator_provenance']['operator_acquired_at'] == '2026-10-29T12:00:00Z'
    assert not receipt['origin_authenticated']
    assert build_adjudication_packets(receipts, evidence_directory=retained)['cases_with_retained_original_candidates'] == 1


def test_drugsfda_bulk_import_keeps_dataset_separate_from_case_verification(tmp_path):
    handle = io.BytesIO()
    with zipfile.ZipFile(handle, 'w') as archive:
        archive.writestr('Applications.txt', 'ApplNo\tApplType\tSponsorName\n219776\tNDA\tSYNTHETIC TEST\n')
        archive.writestr('Submissions.txt', 'ApplNo\tSubmissionType\tSubmissionNo\tSubmissionStatus\tSubmissionStatusDate\n219776\tORIG\t1\tAP\t20251211\n')
    report = run(tmp_path, [entry(tmp_path, doc=document('APPLICATION_ACTION_DATASET'), raw=handle.getvalue(), name='bulk.zip')])
    assert report['imports'][0]['counts'] == {'application_count': 1, 'submission_count': 1}
    assert report['cases'][0]['documents'][0]['status'] == 'BYTES_RETAINED_REQUIRES_INDEPENDENT_REVIEW'
    assert report['independently_verified_decisions'] == 0


def test_valid_bulk_schema_cannot_bind_an_unrelated_application(tmp_path):
    handle = io.BytesIO()
    with zipfile.ZipFile(handle, 'w') as archive:
        archive.writestr('Applications.txt', 'ApplNo\tApplType\tSponsorName\n123456\tNDA\tSYNTHETIC WRONG CASE\n')
        archive.writestr('Submissions.txt', 'ApplNo\tSubmissionType\tSubmissionNo\tSubmissionStatus\tSubmissionStatusDate\n123456\tORIG\t1\tAP\t20251211\n')
    item = entry(tmp_path, doc=document('APPLICATION_ACTION_DATASET'), raw=handle.getvalue(), name='bulk.zip')
    with pytest.raises(ValueError, match='exact requested application'):
        run(tmp_path, [item])
    assert not (tmp_path / 'retained').exists()


def test_malformed_duplicate_and_conflicting_versions_are_not_silently_resolved(tmp_path):
    first = entry(tmp_path)
    other = entry(tmp_path, raw=b'%PDF-1.7\nSYNTHETIC DIFFERENT VERSION\n%%EOF', name='other.pdf')
    report = run(tmp_path, [first, first, other])
    assert report['duplicate_entries'] == 1
    assert report['unique_document_versions_imported'] == 2
    action = next(d for d in report['cases'][0]['documents'] if d['family'] == 'APPROVAL_LETTER')
    assert action['status'] == 'CONFLICTING_VERSIONS_REQUIRE_REVIEW'
    assert len(action['sha256_candidates']) == 2


def test_same_bytes_with_different_provenance_are_retained_in_both_orders(tmp_path):
    first = entry(tmp_path)
    second = dict(first, claimed_published_at='2020-01-01T00:00:00Z',
                  publication_evidence='SYNTHETIC conflicting availability claim')
    report = run(tmp_path, [first, second])
    reversed_report = run(tmp_path, [second, first])
    assert report == reversed_report
    assert report['unique_document_versions_imported'] == 1
    assert report['unique_acquisition_claims_imported'] == 2
    assert report['duplicate_entries'] == 0
    action = next(d for d in report['cases'][0]['documents'] if d['family'] == 'APPROVAL_LETTER')
    assert action['status'] == 'MULTIPLE_PROVENANCE_CLAIMS_REQUIRE_REVIEW'
    assert action['acquisition_claim_count'] == 2
    receipts = [json.loads(p.read_text()) for p in (tmp_path / 'retained').glob('*.receipt.json')]
    assert {r['source_published_at'] for r in receipts} == {None, '2020-01-01T00:00:00Z'}


@pytest.mark.parametrize('field,value', [
    ('document_id', 'invented'), ('sha256', 'a' * 64),
    ('dataset_version', ''), ('operator_acquired_at', '2025-01-01'),
    ('claimed_published_at', '2025-01-01T00:00:00Z'),
    ('publication_evidence', True), ('path', ''),
    ('independently_verified', True),
])
def test_reject_invalid_metadata_before_retaining_any_bytes(tmp_path, field, value):
    item = entry(tmp_path)
    item[field] = value
    with pytest.raises(ValueError):
        run(tmp_path, [item])
    assert not (tmp_path / 'retained').exists()


def test_preflight_entire_batch_and_unresolved_locator(tmp_path):
    valid = entry(tmp_path)
    invalid = deepcopy(valid)
    invalid['document_id'] = document('FORMAL_TARGET_REVISION')['document_id']
    with pytest.raises(ValueError, match='locator'):
        run(tmp_path, [valid, invalid])
    assert not (tmp_path / 'retained').exists()


def test_source_clock_never_enables_historical_feature_use(tmp_path):
    item = entry(tmp_path)
    item['claimed_published_at'] = '2026-10-28T00:00:00Z'
    item['publication_evidence'] = 'SYNTHETIC operator description, not independently reviewed'
    report = run(tmp_path, [item])
    assert not report['imports'][0]['historical_eligible']
    assert not report['imports'][0]['publication_timestamp_verified']
    receipt = json.loads(next((tmp_path / 'retained').glob('*.receipt.json')).read_text())
    assert receipt['source_published_at'] == item['claimed_published_at']
    assert receipt['external_operator_provenance']['publication_evidence'] == item['publication_evidence']
    item['claimed_published_at'] = '2027-01-01T00:00:00Z'
    with pytest.raises(ValueError, match='cannot follow'):
        run(tmp_path, [item])


def test_trial_identity_is_exact_and_current_record_never_history(tmp_path):
    trial = next(d for c in build_acquisition_manifest()['cases'] for d in c['documents'] if d['family'] == 'TRIAL_CURRENT_RECORD')
    raw = json.dumps({'studies': [{'protocolSection': {'identificationModule': {'nctId': 'NCT05273749'}}}]}).encode()
    item = entry(tmp_path, doc=trial, raw=raw, name='trial.json')
    assert run(tmp_path, [item])['imports'][0]['counts']['historical_snapshot_verified'] is False
    wrong = raw.replace(b'NCT05273749', b'NCT00000001')
    item = entry(tmp_path, doc=trial, raw=wrong, name='wrong.json')
    with pytest.raises(ValueError, match='exact acquisition'):
        run(tmp_path, [item])


def test_duplicate_trial_payload_keys_rejected_before_import(tmp_path):
    trial = next(d for c in build_acquisition_manifest()['cases'] for d in c['documents'] if d['family'] == 'TRIAL_CURRENT_RECORD')
    raw = b'{"studies":[{"protocolSection":{"identificationModule":{"nctId":"NCT00000001","nctId":"NCT05273749"}}}]}'
    item = entry(tmp_path, doc=trial, raw=raw, name='duplicate-trial.json')
    with pytest.raises(ValueError, match='duplicate'):
        run(tmp_path, [item])
    assert not (tmp_path / 'retained').exists()


def test_batch_entry_and_aggregate_limits(tmp_path, monkeypatch):
    item = entry(tmp_path)
    with pytest.raises(ValueError, match='128-entry'):
        run(tmp_path, [item] * 129)
    size = (tmp_path / item['path']).stat().st_size
    monkeypatch.setattr('research.official_acquisition_manifest.MAX_BYTES', size)
    with pytest.raises(ValueError, match='aggregate'):
        run(tmp_path, [item, item])
    assert not (tmp_path / 'retained').exists()


def test_paths_symlinks_and_bounded_reads(tmp_path, monkeypatch):
    item = entry(tmp_path)
    child = tmp_path / 'bundle'
    child.mkdir()
    with pytest.raises(ValueError, match='outside'):
        import_acquisition_bundle([dict(item, path=str(tmp_path / item['path']))], evidence_directory=child, retention_directory=child / 'retained')
    link = tmp_path / 'link.pdf'
    link.symlink_to(tmp_path / item['path'])
    with pytest.raises(ValueError, match='symlink'):
        run(tmp_path, [dict(item, path='link.pdf')])
    monkeypatch.setattr('research.official_acquisition_manifest.MAX_BYTES', 3)
    with pytest.raises(ValueError, match='byte limit'):
        run(tmp_path, [item])


def test_cli_manifest_check_and_offline_bundle_duplicate_json_keys(tmp_path):
    output = tmp_path / 'manifest.json'
    assert main(['--output', str(output)]) == 0
    assert main(['--output', str(output), '--check']) == 0
    with pytest.raises(FileExistsError):
        main(['--output', str(output)])
    bundle = tmp_path / 'bundle.json'
    item = entry(tmp_path)
    bundle.write_text('[' + json.dumps(item)[:-1] + ',"sha256":"duplicate"}]')
    report = tmp_path / 'report.json'
    with pytest.raises(ValueError, match='duplicate'):
        main(['--bundle', str(bundle), '--evidence-directory', str(tmp_path),
              '--retention-directory', str(tmp_path / 'retained'), '--output', str(report)])
    assert not report.exists()


def test_empty_bundle_is_explicit_missing_evidence_report(tmp_path):
    report = run(tmp_path, [])
    assert report['scope'] == 'CURRENT_BUNDLE_ONLY_NOT_COMPLETE_RETENTION_HISTORY'
    assert report['unique_document_versions_imported'] == 0
    assert report['case_count'] == 6
    assert all(d['status'] == 'MISSING' for c in report['cases'] for d in c['documents'])
