import hashlib
import io
import json
from urllib.error import HTTPError
import zipfile

import pytest

from research.official_sources import (OfficialAdapter, AVAILABLE, DENIED, MISSING,
    TEMPORARY, UNVERIFIED, SOURCES, validate_payload, application_id)

URL = SOURCES['clinical_trials'][1]
RAW = json.dumps({'studies': [{'protocolSection': {'identificationModule': {'nctId': 'NCT01234567'}}}]}).encode()


class Response(io.BytesIO):
    headers = {'ETag': 'version-1', 'Last-Modified': 'Wed, 28 Oct 2026 00:00:00 GMT'}


class Transport:
    def __init__(self, values):
        self.values, self.calls = iter(values), 0

    def open(self, request, timeout):
        self.calls += 1
        assert timeout == 30
        value = next(self.values)
        if isinstance(value, Exception):
            raise value
        return Response(value)


def test_success_preserves_bytes_and_never_self_certifies(tmp_path):
    transport = Transport([RAW])
    result = OfficialAdapter('clinical_trials', opener=transport, sleep=lambda _: None).retrieve(tmp_path)
    assert result['availability'] == AVAILABLE
    assert result['sha256'] == hashlib.sha256(RAW).hexdigest()
    assert result['source_published_at'] is None
    assert not result['historical_eligible'] and not result['independently_verified']
    assert result['dataset_version'] == 'version-1'
    assert list(tmp_path.glob('*.original'))[0].read_bytes() == RAW
    assert len(list(tmp_path.glob('*.receipt.json'))) == 1


@pytest.mark.parametrize('code,state,calls', [(403, DENIED, 1), (404, MISSING, 1), (429, TEMPORARY, 3), (503, TEMPORARY, 3)])
def test_http_classification(tmp_path, code, state, calls):
    transport = Transport([HTTPError(URL, code, 'error', {}, None)] * 3)
    result = OfficialAdapter('clinical_trials', opener=transport, sleep=lambda _: None).retrieve(tmp_path)
    assert result['availability'] == state
    assert transport.calls == calls
    assert 'outcome' not in result
    assert result['prediction_action'] == 'ABSTAIN'


def test_timeout_and_recovery(tmp_path):
    transport = Transport([TimeoutError(), RAW])
    result = OfficialAdapter('clinical_trials', opener=transport, sleep=lambda _: None).retrieve(tmp_path)
    assert result['availability'] == AVAILABLE and len(result['attempts']) == 2


def test_exhausted_timeout(tmp_path):
    result = OfficialAdapter('clinical_trials', opener=Transport([TimeoutError()] * 3), sleep=lambda _: None).retrieve(tmp_path)
    assert result['availability'] == TEMPORARY


def test_retry_after_not_ignored(tmp_path):
    transport = Transport([HTTPError(URL, 429, 'wait', {'Retry-After': '3600'}, None)])
    result = OfficialAdapter('clinical_trials', opener=transport, sleep=lambda _: None).retrieve(tmp_path)
    assert result['availability'] == TEMPORARY and transport.calls == 1


@pytest.mark.parametrize('raw', [b'not zip', b'PK\x03\x04corrupt'])
def test_corrupt_archives_preserved_unverified(tmp_path, raw):
    result = OfficialAdapter('drugs_fda').import_bytes(tmp_path, raw, url=SOURCES['drugs_fda'][1])
    assert result['availability'] == UNVERIFIED
    assert list(tmp_path.glob('*.original'))[0].read_bytes() == raw


def test_schema_drift_and_checksum(tmp_path):
    adapter = OfficialAdapter('clinical_trials')
    assert adapter.import_bytes(tmp_path, b'{}', url=URL)['availability'] == UNVERIFIED
    assert adapter.import_bytes(tmp_path, RAW, url=URL, expected_sha256='0' * 64)['validation_errors'] == ['SHA-256 mismatch']
    assert adapter.import_bytes(tmp_path, RAW, url=URL, published_at='2020-01-01')['availability'] == UNVERIFIED


def test_duplicate_bytes_and_missing_publication(tmp_path):
    adapter = OfficialAdapter('clinical_trials')
    first = adapter.import_bytes(tmp_path, RAW, url=URL)
    second = adapter.import_bytes(tmp_path, RAW, url=URL)
    assert not first['duplicate_bytes'] and second['duplicate_bytes']
    assert first['source_published_at'] is None and not first['historical_eligible']


def test_bulk_duplicate_and_identifier():
    row = {'application_number': 'NDA123456', 'submissions': []}
    assert validate_payload('openfda_bulk', json.dumps({'results': [row]}).encode())['application_count'] == 1
    with pytest.raises(ValueError, match='duplicate'):
        validate_payload('openfda_bulk', json.dumps({'results': [row, row]}).encode())
    for bad in ['123456', 'NDA12345', 'NDA1234567', 'nda123456']:
        with pytest.raises(ValueError):
            application_id(bad)


def test_tsv_schema_identity_and_counts():
    def archive(apps, submissions):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as z:
            z.writestr('Applications.txt', apps)
            z.writestr('Submissions.txt', submissions)
        return buffer.getvalue()
    apps = 'ApplNo\tApplType\tSponsorName\n123456\tNDA\tSponsor\n'
    submissions = 'ApplNo\tSubmissionType\tSubmissionNo\tSubmissionStatus\tSubmissionStatusDate\n123456\tORIG\t1\tAP\t2020-01-01\n'
    assert validate_payload('drugs_fda', archive(apps, submissions)) == {'application_count': 1, 'submission_count': 1}
    with pytest.raises(ValueError):
        validate_payload('drugs_fda', archive(apps, submissions + submissions.splitlines(True)[1]))
    with pytest.raises(ValueError):
        validate_payload('drugs_fda', archive('changed\n', submissions))


@pytest.mark.parametrize('url', ['http://clinicaltrials.gov/x', 'https://evil.test/x', 'https://clinicaltrials.gov.evil.test/x', 'https://user:pass@clinicaltrials.gov/x'])
def test_source_origin_restrictions(tmp_path, url):
    with pytest.raises(ValueError):
        OfficialAdapter('clinical_trials').retrieve(tmp_path, url=url)


def test_official_bulk_zip_and_history_snapshot():
    row = {'application_number': 'BLA123456', 'submissions': []}
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as z:
        z.writestr('drug-drugsfda-0001-of-0001.json', json.dumps({'results': [row]}))
    assert validate_payload('openfda_bulk', buffer.getvalue())['application_count'] == 1
    study = json.loads(RAW)['studies'][0]
    result = validate_payload('trial_history', json.dumps(study).encode())
    assert not result['historical_snapshot_verified']


@pytest.mark.parametrize('url', ['https://www.fda.gov/media/186545/download?stream=top', 'https://download.open.fda.gov/crl/CRL_NDA219398_20260128.pdf', 'https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2025/219776Orig1s000ltr.pdf'])
def test_all_curated_official_document_hosts_supported(tmp_path, url):
    receipt = OfficialAdapter('fda_document').import_bytes(tmp_path, b'%PDF-synthetic', url=url)
    assert receipt['availability'] == AVAILABLE
    assert not receipt['independently_verified']
