"""Research-only official acquisition. Byte integrity is never scientific review.

No scanner, authentication, outcome adjudication, or prediction side effects.
Offline imports retain a claimed origin, never authenticate it automatically.
"""
from __future__ import annotations
import argparse
import csv
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
import io
import json
from pathlib import Path
import re
import socket
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener
from research.fda_official_document_fetch import _NoRedirects
import zipfile

SOURCES = {
    'drugs_fda': ('www.fda.gov', 'https://www.fda.gov/media/89850/download'),
    'openfda_index': ('api.fda.gov', 'https://api.fda.gov/download.json'),
    'openfda_bulk': ('download.open.fda.gov', None),
    'crl': ('api.fda.gov', 'https://api.fda.gov/transparency/completeresponseletters.json?limit=1'),
    'clinical_trials': ('clinicaltrials.gov', 'https://clinicaltrials.gov/api/v2/studies?pageSize=1'),
    'fda_document': ('www.accessdata.fda.gov', None),
    'trial_history': ('clinicaltrials.gov', None),
}
AVAILABLE = 'SOURCE AVAILABLE'
TEMPORARY = 'SOURCE TEMPORARILY UNAVAILABLE'
DENIED = 'ACCESS DENIED'
MISSING = 'SOURCE DOCUMENT MISSING'
UNVERIFIED = 'SOURCE DOCUMENT UNVERIFIED'
MAX_BYTES = 256 * 1024 * 1024


def official_url(source, url):
    parts = urlsplit(url)
    hosts = {'www.accessdata.fda.gov', 'www.fda.gov', 'download.open.fda.gov'} if source == 'fda_document' else {SOURCES[source][0]} if source in SOURCES else set()
    if (source not in SOURCES or parts.scheme != 'https' or parts.hostname not in hosts
            or parts.username or parts.password or parts.port not in (None, 443)):
        raise ValueError('unsupported official HTTPS origin')
    return url


def application_id(value):
    if not isinstance(value, str) or not re.fullmatch(r'(NDA|BLA)\d{6}', value):
        raise ValueError('exact NDA/BLA application identifier required')
    return value


def validate_payload(source, raw):
    """Validate minimal official schemas; never manufacture cycle or outcome data."""
    if source == 'drugs_fda':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            if sum(i.file_size for i in archive.infolist()) > MAX_BYTES:
                raise ValueError('expanded archive too large')
            if archive.testzip():
                raise ValueError('archive CRC failure')
            expected = {
                'Applications.txt': {'ApplNo', 'ApplType', 'SponsorName'},
                'Submissions.txt': {'ApplNo', 'SubmissionType', 'SubmissionNo', 'SubmissionStatus', 'SubmissionStatusDate'},
            }
            tables = {}
            for name, columns in expected.items():
                reader = csv.DictReader(io.StringIO(archive.read(name).decode('utf-8-sig')), delimiter='\t')
                if not columns <= set(reader.fieldnames or []):
                    raise ValueError('dataset schema changed: ' + name)
                rows = list(reader)
                if not rows:
                    raise ValueError('empty required table')
                tables[name] = rows
            apps = {}
            for row in tables['Applications.txt']:
                key = application_id(row['ApplType'].strip() + row['ApplNo'].zfill(6))
                if key in apps:
                    raise ValueError('duplicate application')
                apps[key] = row
            application_numbers = {a[3:] for a in apps}
            cycles = set()
            for row in tables['Submissions.txt']:
                key = (row['ApplNo'], row['SubmissionType'], row['SubmissionNo'])
                if not all(key) or key in cycles:
                    raise ValueError('duplicate or missing submission identity')
                if row['ApplNo'].zfill(6) not in application_numbers:
                    raise ValueError('orphan submission application')
                cycles.add(key)
            return {'application_count': len(apps), 'submission_count': len(cycles)}
    if source == 'fda_document':
        if not raw.startswith(b'%PDF-'):
            raise ValueError('expected original PDF; HTML/error bodies are not documents')
        return {'document_count': 1}
    if source == 'openfda_bulk' and raw.startswith(b'PK'):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            members = archive.infolist()
            if (len(members) != 1 or not members[0].filename.endswith('.json')
                    or members[0].file_size > MAX_BYTES or archive.testzip()):
                raise ValueError('unexpected bulk archive layout or integrity')
            raw = archive.read(members[0])
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError('dataset schema changed: expected object')
    if source == 'openfda_index':
        if not isinstance(payload.get('results', {}).get('drug', {}).get('drugsfda', {}).get('partitions'), list):
            raise ValueError('download index schema changed')
        return {'partition_count': len(payload['results']['drug']['drugsfda']['partitions'])}
    if source in ('clinical_trials', 'trial_history'):
        studies = [payload] if source == 'trial_history' else payload.get('studies')
        if not isinstance(studies, list) or not studies:
            raise ValueError('study schema changed or empty')
        for study in studies:
            nct = study['protocolSection']['identificationModule']['nctId']
            if not re.fullmatch(r'NCT\d{8}', nct):
                raise ValueError('incorrect trial identifier')
        return {'study_count': len(studies), 'historical_snapshot_verified': False}
    rows = payload.get('results')
    if not isinstance(rows, list) or not rows:
        raise ValueError('results schema changed or empty')
    if source == 'openfda_bulk':
        seen = set()
        for row in rows:
            key = application_id(row['application_number'])
            if key in seen:
                raise ValueError('duplicate FDA record')
            seen.add(key)
            if not isinstance(row.get('submissions'), list):
                raise ValueError('submission schema changed')
        return {'application_count': len(seen)}
    # CRL field contracts require independent confirmation before normalization.
    return {'source_row_count': len(rows), 'normalization_status': 'REQUIRES_SCHEMA_REVIEW'}


class OfficialAdapter:
    def __init__(self, source, *, timeout=30, attempts=3, interval=1, opener=None, sleep=time.sleep):
        if source not in SOURCES or not 0 < timeout <= 120 or not 1 <= attempts <= 5 or interval < 1:
            raise ValueError('invalid bounded connection policy')
        self.source, self.timeout, self.attempts, self.interval = source, timeout, attempts, interval
        self.opener, self.sleep = opener or build_opener(_NoRedirects()), sleep

    def retrieve(self, directory, *, url=None):
        url = official_url(self.source, url or SOURCES[self.source][1] or '')
        events = []
        for attempt in range(self.attempts):
            self.sleep(self.interval)
            try:
                request = Request(url, headers={'User-Agent': 'PDUFA-Research-Official-Data/1.0', 'Accept': '*/*'})
                with self.opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(MAX_BYTES + 1)
                    headers = dict(response.headers)
                receipt = self.import_bytes(directory, raw, url=url, dataset_version=headers.get('ETag'),
                                            transport='OFFICIAL_HTTPS', response_headers=headers)
                receipt['attempts'] = events + [{'status': 200}]
                return self._audit(directory, receipt)
            except HTTPError as exc:
                state = DENIED if exc.code in (401, 403) else MISSING if exc.code in (404, 410) else TEMPORARY if exc.code == 429 or exc.code >= 500 else UNVERIFIED
                events.append({'status': exc.code, 'classification': state})
                if exc.code != 429 and exc.code < 500:
                    break
                # Respect Retry-After only within a bounded wait; otherwise stop.
                retry = exc.headers.get('Retry-After') if exc.headers else None
                if retry:
                    try:
                        delay = float(retry) if retry.isdigit() else (parsedate_to_datetime(retry) - datetime.now(timezone.utc)).total_seconds()
                    except (ValueError, TypeError, OverflowError):
                        break
                    if delay > 30:
                        break
                    self.sleep(max(0, delay))
            except (URLError, TimeoutError, socket.timeout, ConnectionError) as exc:
                state = TEMPORARY
                events.append({'classification': state, 'error_type': type(exc).__name__})
            if attempt + 1 < self.attempts:
                self.sleep(min(2 ** attempt, 8))
        return self._audit(directory, {'source': self.source, 'url': url, 'availability': state,
            'fetched_at': datetime.now(timezone.utc).isoformat(), 'attempts': events,
            'independently_verified': False, 'prediction_action': 'ABSTAIN'})

    def import_bytes(self, directory, raw, *, url, dataset_version=None, published_at=None,
                     expected_sha256=None, transport='OFFLINE_OPERATOR_IMPORT', response_headers=None):
        official_url(self.source, url)
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(raw).hexdigest()
        path = directory / (digest + '.original')
        duplicate = path.exists()
        if duplicate and hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError('stored original integrity failure')
        if not duplicate:
            with path.open('xb') as handle:
                handle.write(raw)
        errors, counts = [], {}
        if len(raw) > MAX_BYTES:
            errors.append('download exceeds byte limit')
        if expected_sha256 is not None and expected_sha256 != digest:
            errors.append('SHA-256 mismatch')
        try:
            if not errors:
                counts = validate_payload(self.source, raw)
        except (ValueError, KeyError, TypeError, UnicodeError, zipfile.BadZipFile, RuntimeError) as exc:
            errors.append('schema or document validation failed: ' + type(exc).__name__)
        # Publication time is independent of HTTP Last-Modified, fetch time and clinical event dates.
        if published_at is not None:
            from research.prediction_v1_1_historical_label_gate import _date
            if _date(published_at) is None:
                errors.append('invalid publication timestamp')
                published_at = None
        return {'source': self.source, 'url': url, 'sha256': digest, 'original_path': str(path),
            'fetched_at': datetime.now(timezone.utc).isoformat(), 'source_published_at': published_at,
            'dataset_version': dataset_version, 'snapshot_id': digest, 'transport': transport,
            'response_headers': {k: v for k, v in (response_headers or {}).items() if k.lower() in ('etag', 'last-modified', 'content-type')},
            'availability': UNVERIFIED if errors else AVAILABLE, 'validation_errors': errors,
            'origin_authenticated': False, 'publication_timestamp_verified': False,
            'counts': counts, 'duplicate_bytes': duplicate, 'independently_verified': False,
            'historical_eligible': False, 'prediction_action': 'ABSTAIN'}

    @staticmethod
    def _audit(directory, receipt):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        content = json.dumps(receipt, sort_keys=True, indent=2) + '\n'
        name = hashlib.sha256(content.encode()).hexdigest() + '.receipt.json'
        with (directory / name).open('x') as handle:
            handle.write(content)
        return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', choices=SOURCES)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--url')
    parser.add_argument('--import-file', type=Path)
    parser.add_argument('--sha256')
    parser.add_argument('--published-at')
    parser.add_argument('--dataset-version')
    args = parser.parse_args()
    adapter = OfficialAdapter(args.source)
    if args.import_file:
        if not args.sha256 or not args.dataset_version or not args.url:
            parser.error('offline import requires --sha256, --dataset-version and --url')
        with args.import_file.open('rb') as handle:
            raw = handle.read(MAX_BYTES + 1)
        receipt = adapter.import_bytes(args.directory, raw, url=args.url, expected_sha256=args.sha256,
                                      dataset_version=args.dataset_version, published_at=args.published_at)
        adapter._audit(args.directory, receipt)
    else:
        receipt = adapter.retrieve(args.directory, url=args.url)
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
