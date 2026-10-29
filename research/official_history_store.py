"""Append-only SQLite research history, with retained source-bound claims.

Downloaded metadata, curated cases and scientific facts have separate provenance.
This store cannot confer independent verification or supply training labels.
"""
from copy import deepcopy
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3

from research.historical_decision_registry import build_historical_registry, validate_registry, DEFAULT_PROGRAM
from research.official_sources import application_id, official_url

SCHEMA = 'official-history-store-v1'
FIELDS = frozenset({'record_id', 'program_id', 'company', 'ticker', 'drug', 'indication',
    'application_id', 'review_cycle_id', 'submission_type', 'submission_number',
    'original_pdufa_date', 'pdufa_target_date', 'actual_decision_date', 'decision_category', 'source_documents',
    'trial_identifiers', 'efficacy_results', 'safety_results', 'manufacturing_findings',
    'regulatory_designations', 'evidence_completeness', 'independent_verification_status',
    'provenance', 'program_family'})


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def validate_case(row):
    if not isinstance(row, dict) or set(row) != FIELDS:
        raise ValueError('exact versioned historical case schema required')
    application_id(row['application_id'])
    for field in ('record_id', 'program_id', 'program_family'):
        if not isinstance(row[field], str) or not row[field].strip():
            raise ValueError('explicit record, scope and family required')
    if row['review_cycle_id'] is not None and (not isinstance(row['review_cycle_id'], str) or not row['review_cycle_id'].strip()):
        raise ValueError('exact cycle or null required')
    for field in ('original_pdufa_date', 'pdufa_target_date', 'actual_decision_date'):
        value = row[field]
        if value is not None and (not isinstance(value, str) or date.fromisoformat(value).isoformat() != value):
            raise ValueError('source date precision must be preserved')
    if row['decision_category'] not in ('PASS', 'CRL', 'EXTENSION', 'UNRESOLVED'):
        raise ValueError('explicit regulatory outcome required; no missed-target inference')
    if row['decision_category'] != 'UNRESOLVED' and not row['actual_decision_date']:
        raise ValueError('claimed regulatory decision requires source date')
    if row['independent_verification_status'] != 'UNVERIFIED':
        raise ValueError('imports cannot self-certify independent verification')
    for field in ('source_documents', 'trial_identifiers', 'regulatory_designations', 'provenance'):
        if not isinstance(row[field], list):
            raise ValueError('explicit evidence lists required')
    import re
    if any(not isinstance(n, str) or not re.fullmatch(r'NCT\d{8}', n) for n in row['trial_identifiers']):
        raise ValueError('exact trial identifiers required')
    if not isinstance(row['evidence_completeness'], dict):
        raise ValueError('evidence completeness is separate from verification')
    canonical(row)
    return deepcopy(row)


def curated_cases(registry=None, *, program_id=DEFAULT_PROGRAM):
    checked = validate_registry(registry or build_historical_registry(program_id=program_id), program_id=program_id)
    result = []
    for case in checked['records']:
        action = case['reported_action']
        row = dict.fromkeys(FIELDS)
        row.update({key: deepcopy(case[key]) for key in ('record_id', 'program_id', 'company', 'ticker', 'drug', 'indication', 'application_id', 'review_cycle_id', 'program_family')})
        row.update(original_pdufa_date=None, pdufa_target_date=case['pdufa_target_date'], actual_decision_date=action['action_date'],
            decision_category=action['reported_outcome'],
            source_documents=[{'source_url': action['source_url'], 'source_published_at': None,
                'sha256': None, 'document_id': action['decision_document_id'],
                'status': 'SOURCE_LEAD_NOT_ORIGINAL_BYTES'}],
            trial_identifiers=[], regulatory_designations=[],
            evidence_completeness={'status': 'INCOMPLETE', 'missing_documents': deepcopy(case['missing_documents'])},
            independent_verification_status='UNVERIFIED',
            provenance=[{'kind': 'EXISTING_CURATED_REGISTRY', 'case': deepcopy(case),
                'original_document_authenticated': False}])
        result.append(validate_case(row))
    return result


class HistoryStore:
    def __init__(self, path):
        self.connection = sqlite3.connect(path)
        self.connection.execute('PRAGMA foreign_keys=ON')
        self.connection.executescript('''
        CREATE TABLE IF NOT EXISTS metadata(version TEXT PRIMARY KEY);
        CREATE TABLE IF NOT EXISTS claims(
          digest TEXT PRIMARY KEY, record_id TEXT NOT NULL, program_id TEXT NOT NULL,
          application_id TEXT NOT NULL, cycle TEXT, outcome TEXT NOT NULL,
          payload TEXT NOT NULL, imported_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS originals(
          sha256 TEXT PRIMARY KEY, raw BLOB NOT NULL, receipt TEXT NOT NULL);
        CREATE TRIGGER IF NOT EXISTS immutable_claim_update BEFORE UPDATE ON claims BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_claim_delete BEFORE DELETE ON claims BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_original_update BEFORE UPDATE ON originals BEGIN SELECT RAISE(ABORT,'append only'); END;
        CREATE TRIGGER IF NOT EXISTS immutable_original_delete BEFORE DELETE ON originals BEGIN SELECT RAISE(ABORT,'append only'); END;
        ''')
        versions = self.connection.execute('SELECT version FROM metadata').fetchall()
        if versions and versions != [(SCHEMA,)]:
            raise ValueError('unsupported database schema')
        self.connection.execute('INSERT OR IGNORE INTO metadata VALUES (?)', (SCHEMA,))
        self.connection.commit()

    def close(self):
        self.connection.close()

    def retain_original(self, receipt):
        official_url(receipt['source'], receipt['url'])
        raw = Path(receipt['original_path']).read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != receipt['sha256'] or receipt.get('validation_errors'):
            raise ValueError('original integrity/schema failure')
        with self.connection:
            self.connection.execute('INSERT OR IGNORE INTO originals VALUES (?,?,?)',
                (digest, raw, canonical(receipt)))
        return digest

    def import_cases(self, rows):
        checked = [validate_case(row) for row in rows]
        inserted = 0
        with self.connection:
            for row in checked:
                payload = canonical(row)
                digest = hashlib.sha256(payload.encode()).hexdigest()
                cursor = self.connection.execute('INSERT OR IGNORE INTO claims VALUES (?,?,?,?,?,?,?,?)',
                    (digest, row['record_id'], row['program_id'], row['application_id'], row['review_cycle_id'],
                     row['decision_category'], payload, datetime.now(timezone.utc).isoformat()))
                inserted += cursor.rowcount
        return {'inserted_claims': inserted, 'duplicate_claims': len(checked) - inserted,
                'independently_verified_decisions': 0}

    def snapshot(self, *, program_id):
        claims = self.connection.execute('SELECT application_id,cycle,outcome,payload FROM claims WHERE program_id=? ORDER BY record_id,digest', (program_id,)).fetchall()
        conflicts = []
        identities = {}
        for app, cycle, outcome, payload in claims:
            if cycle is not None:
                identities.setdefault((app, cycle.casefold()), set()).add(outcome)
        for (app, cycle), outcomes in identities.items():
            if len(outcomes) > 1:
                conflicts.append({'application_id': app, 'cycle': cycle, 'outcomes': sorted(outcomes)})
        return {'schema_version': SCHEMA, 'claims': [json.loads(r[3]) for r in claims],
                'claim_count': len(claims), 'conflicts': conflicts,
                'independently_verified_decisions': 0, 'prediction_action': 'ABSTAIN'}


def bulk_cases(receipt, *, program_id):
    """Normalize official submission metadata, keeping review cycles unresolved.

    Submission numbers are not independently adjudicated review-cycle numbers.
    Explicit source statuses stay in provenance; they do not become labels here.
    """
    import csv
    import io
    import zipfile
    from research.official_sources import validate_payload
    raw = Path(receipt['original_path']).read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt['sha256'] or receipt.get('validation_errors'):
        raise ValueError('original integrity/schema failure')
    source = receipt['source']
    official_url(source, receipt['url'])
    if source not in ('drugs_fda', 'openfda_bulk'):
        raise ValueError('official application bulk dataset required')
    validate_payload(source, raw)
    entries = []
    if source == 'drugs_fda':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            apps = list(csv.DictReader(io.StringIO(archive.read('Applications.txt').decode('utf-8-sig')), delimiter='\t'))
            submissions = list(csv.DictReader(io.StringIO(archive.read('Submissions.txt').decode('utf-8-sig')), delimiter='\t'))
        by_application = {}
        for submission in submissions:
            by_application.setdefault(submission['ApplNo'].zfill(6), []).append(submission)
        for app in apps:
            app_id = application_id(app['ApplType'].strip() + app['ApplNo'].zfill(6))
            for submission in by_application.get(app['ApplNo'].zfill(6), []):
                entries.append((app_id, app.get('SponsorName'), submission['SubmissionType'], submission['SubmissionNo'], {'application': app, 'submission': submission}))
    else:
        if raw.startswith(b'PK'):
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                raw = archive.read(archive.infolist()[0])
        for app in json.loads(raw)['results']:
            for submission in app['submissions']:
                kind, number = submission.get('submission_type'), submission.get('submission_number')
                if not isinstance(kind, str) or not kind or not isinstance(number, str) or not number:
                    raise ValueError('exact official submission identity required')
                entries.append((app['application_number'], app.get('sponsor_name'), kind, number, {'application': app, 'submission': submission}))
    rows, seen = [], set()
    for app_id, company, kind, number, metadata in entries:
        key = (app_id, kind, number)
        if key in seen:
            raise ValueError('duplicate official submission record')
        seen.add(key)
        row = dict.fromkeys(FIELDS)
        row.update(record_id=':'.join(key), program_id=program_id, company=company,
            application_id=app_id, program_family=app_id,
            submission_type=kind, submission_number=number,
            decision_category='UNRESOLVED', source_documents=[deepcopy(receipt)],
            trial_identifiers=[], regulatory_designations=[],
            evidence_completeness={'status': 'INCOMPLETE', 'missing': ['EXACT_CYCLE_ADJUDICATION', 'ORIGINAL_ACTION_DOCUMENT', 'SCIENTIFIC_EVIDENCE', 'PUBLICATION_CLOCK']},
            independent_verification_status='UNVERIFIED',
            provenance=[{'kind': 'OFFICIAL_SUBMISSION_METADATA_NOT_ADJUDICATED_OUTCOME', 'metadata': metadata}])
        rows.append(validate_case(row))
    return rows


def main():
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--program-id', default=DEFAULT_PROGRAM)
    parser.add_argument('--curated', action='store_true')
    parser.add_argument('--bulk-receipt', type=Path)
    args = parser.parse_args()
    store = HistoryStore(args.database)
    try:
        if args.curated:
            store.import_cases(curated_cases(program_id=args.program_id))
        if args.bulk_receipt:
            receipt = json.loads(args.bulk_receipt.read_text())
            rows = bulk_cases(receipt, program_id=args.program_id)
            store.retain_original(receipt)
            store.import_cases(rows)
        print(json.dumps(store.snapshot(program_id=args.program_id), indent=2))
    finally:
        store.close()


if __name__ == '__main__':
    main()
