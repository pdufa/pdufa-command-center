from copy import deepcopy
import hashlib
import json
import sqlite3
import pytest

from research.official_history_store import HistoryStore, curated_cases, validate_case, bulk_cases
from research.official_sources import OfficialAdapter


def test_existing_six_remain_unverified_and_idempotent(tmp_path):
    rows = curated_cases()
    store = HistoryStore(tmp_path / 'history.sqlite')
    assert len(rows) == 6
    assert store.import_cases(rows)['inserted_claims'] == 6
    assert store.import_cases(rows)['duplicate_claims'] == 6
    report = store.snapshot(program_id=rows[0]['program_id'])
    assert report['claim_count'] == 6 and report['independently_verified_decisions'] == 0
    assert all(r['independent_verification_status'] == 'UNVERIFIED' for r in report['claims'])
    assert not store.snapshot(program_id='OTHER')['claims']
    store.close()


def test_conflict_retained_and_immutable(tmp_path):
    row = curated_cases()[0]
    row['review_cycle_id'] = 'ORIG:1'
    other = deepcopy(row)
    other['decision_category'] = 'EXTENSION' if row['decision_category'] != 'EXTENSION' else 'CRL'
    store = HistoryStore(tmp_path / 'history.sqlite')
    store.import_cases([row, other])
    report = store.snapshot(program_id=row['program_id'])
    assert len(report['conflicts']) == 1 and report['claim_count'] == 2
    with pytest.raises(sqlite3.IntegrityError, match='append only'):
        store.connection.execute('DELETE FROM claims')
    store.close()


@pytest.mark.parametrize('field,value', [('application_id', '123456'), ('independent_verification_status', 'VERIFIED'), ('decision_category', 'DELAY'), ('trial_identifiers', ['NCTinvalid'])])
def test_invalid_or_self_certified_import_rejected(tmp_path, field, value):
    row = curated_cases()[0]
    row[field] = value
    with pytest.raises(ValueError):
        validate_case(row)


def test_original_integrity_and_official_bulk(tmp_path):
    raw = json.dumps({'results': [{'application_number': 'NDA123456', 'sponsor_name': 'Sponsor', 'submissions': [{'submission_type': 'ORIG', 'submission_number': '1', 'submission_status': 'AP', 'submission_status_date': '20200101'}]}]}).encode()
    receipt = OfficialAdapter('openfda_bulk').import_bytes(tmp_path, raw, url='https://download.open.fda.gov/drug/drugsfda/example.json.zip')
    rows = bulk_cases(receipt, program_id='RESEARCH')
    assert len(rows) == 1 and rows[0]['decision_category'] == 'UNRESOLVED'
    assert rows[0]['review_cycle_id'] is None
    assert rows[0]['submission_number'] == '1'
    store = HistoryStore(tmp_path / 'history.sqlite')
    store.retain_original(receipt)
    assert store.import_cases(rows)['inserted_claims'] == 1
    assert store.connection.execute('SELECT raw FROM originals').fetchone()[0] == raw
    receipt['sha256'] = '0' * 64
    with pytest.raises(ValueError, match='integrity'):
        store.retain_original(receipt)
    store.close()


def test_batch_rejected_atomically(tmp_path):
    rows = curated_cases()
    rows[-1]['application_id'] = 'bad'
    store = HistoryStore(tmp_path / 'history.sqlite')
    with pytest.raises(ValueError):
        store.import_cases(rows)
    assert store.snapshot(program_id=rows[0]['program_id'])['claim_count'] == 0
    store.close()


def test_source_target_is_not_invented_as_original_pdufa_date():
    for row in curated_cases():
        assert row['original_pdufa_date'] is None
        assert row['pdufa_target_date']


def test_saved_snapshot_is_reproducible():
    from pathlib import Path
    store = HistoryStore(':memory:')
    store.import_cases(curated_cases())
    expected = json.loads((Path(__file__).parents[1] / 'research/evidence/historical_store_snapshot_20261029.json').read_text())
    assert store.snapshot(program_id='FDA_HISTORICAL_RESEARCH') == expected
    store.close()
