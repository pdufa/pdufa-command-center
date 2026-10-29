"""Point-in-time scientific evidence availability, separate from evidence quality.

This pure research projection neither authenticates source documents nor writes
an audit ledger. A source report, asserted date, populated value, or computed
input digest never certifies a scientific assessment or FDA prediction.
"""
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, time, timezone
import hashlib
import json
import re
from urllib.parse import urlsplit

SCHEMA = 'scientific-evidence-registry-v1'
CATALOG_SCHEMA = 'scientific-field-catalog-v1'
CATALOG_STATUS = 'DRAFT_DEFINITIONS_NOT_SCIENTIFICALLY_VALIDATED'
DOMAIN_IDS = frozenset({'BIO', 'MOA', 'TRIAL', 'EFFICACY', 'SAFETY', 'CMC', 'PRECEDENT', 'VALIDATION'})
OBSERVATION_FIELDS = frozenset({'observation_id', 'program_id', 'field_id', 'source_url',
    'document_id', 'source_document_sha256', 'source_role', 'published_at', 'observed_at', 'value', 'conflict_ids', 'uncertainty', 'verification_status'})
CANDIDATE = 'TIMELY_SOURCE_REPORT_NOT_VERIFIED'


def _text(value, name, *, limit=4000):
    if (not isinstance(value, str) or not value.strip() or value != value.strip()
            or len(value) > limit or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError(f'bounded canonical {name} required')
    return value


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('valid ISO date required') from exc


def _instant(value, name, *, allow_day=False):
    if allow_day and type(value) is date:
        return datetime.combine(value, time.max, timezone.utc)
    day = _day(value) if isinstance(value, str) else None
    if day is not None:
        if not allow_day:
            raise ValueError(f'{name} requires an aware timestamp')
        return datetime.combine(day, time.max, timezone.utc)
    if not isinstance(value, str) or 'T' not in value or len(value) > 50:
        raise ValueError(f'{name} requires an aware ISO timestamp')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'{name} requires an aware ISO timestamp') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f'{name} requires an aware ISO timestamp')
    return parsed.astimezone(timezone.utc)


def _stamp(instant):
    return instant.isoformat().replace('+00:00', 'Z')


def _source_url(value):
    if value is None:
        return
    _text(value, 'source URL')
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname and parsed.path not in ('', '/')
                 and parsed.username is None and parsed.password is None
                 and not parsed.fragment and parsed.port in (None, 443))
    except ValueError:
        valid = False
    if not valid:
        raise ValueError('source URL must be a clean HTTPS document reference')


def _texts(value, name):
    if not isinstance(value, list) or not value:
        raise ValueError(f'nonempty {name} list required')
    return [_text(item, name) for item in value]


def _catalog(catalog):
    if (not isinstance(catalog, dict) or catalog.get('schema_version') != CATALOG_SCHEMA
            or catalog.get('status') != CATALOG_STATUS
            or type(catalog.get('proposed_slots')) is not int or not 1 <= catalog['proposed_slots'] <= 650):
        raise ValueError('explicit draft scientific catalog required')
    domains = catalog.get('domains')
    if not isinstance(domains, list) or not domains:
        raise ValueError('scientific domains required')
    domain_names = {}
    for domain in domains:
        if (not isinstance(domain, dict) or not isinstance(domain.get('id'), str) or domain.get('id') not in DOMAIN_IDS
                or domain['id'] in domain_names):
            raise ValueError('unique canonical scientific domains required')
        domain_names[domain['id']] = _text(domain.get('name'), 'scientific domain')
    fields = catalog.get('fields')
    if not isinstance(fields, list) or len(fields) != catalog['proposed_slots']:
        raise ValueError('defined field count must equal the declared registry denominator')
    seen = set()
    for field in fields:
        if not isinstance(field, dict):
            raise ValueError('scientific field objects required')
        identifier, domain = field.get('id'), field.get('segment')
        if (not isinstance(identifier, str) or not isinstance(domain, str) or domain not in domain_names
                or not re.fullmatch(re.escape(domain) + r'-\d{3}', identifier) or identifier in seen):
            raise ValueError('unique scientific field identity and declared domain required')
        seen.add(identifier)
        for key in ('name', 'definition', 'data_type', 'applicability', 'source', 'scientific_rationale'):
            _text(field.get(key), key)
        for key in ('mandatory', 'critical'):
            if type(field.get(key)) is not bool:
                raise ValueError('explicit mandatory/critical flags required')
        ids = field.get('assessment_ids')
        if (not isinstance(ids, list) or not ids or any(not isinstance(q, str) or not re.fullmatch(r'S(?:0[1-9]|[123][0-9]|40)', q) for q in ids)
                or len(set(ids)) != len(ids)):
            raise ValueError('unique canonical assessment mappings required')
        levels = field.get('investigation_levels')
        if (not isinstance(levels, list) or not levels or any(type(level) is not int or not 1 <= level <= 50 for level in levels)
                or len(set(levels)) != len(levels)):
            raise ValueError('unique investigation levels 1 through 50 required')
        for key in ('required_source_types', 'assessment_criteria', 'uncertainty_handling'):
            _texts(field.get(key), key)
    return fields, domain_names


def _populated(value):
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return True  # Numeric zero and an explicitly reported false are evidence values.


def _observations(observations, fields, program, cutoff):
    if not isinstance(observations, list) or len(observations) > 10000:
        raise ValueError('bounded observation list required')
    by_id = {}
    field_ids = {field['id'] for field in fields}
    for record in observations:
        if not isinstance(record, dict) or set(record) != OBSERVATION_FIELDS:
            raise ValueError('exact unverified observation schema required; no self-certification or applicability claims')
        identifier = _text(record['observation_id'], 'observation identity', limit=128)
        if identifier in by_id:
            raise ValueError('duplicate observation identity')
        if record['program_id'] != program:
            raise ValueError('cross-program scientific evidence rejected')
        if not isinstance(record['field_id'], str) or record['field_id'] not in field_ids:
            raise ValueError('unknown scientific field identity')
        if record['verification_status'] != 'UNVERIFIED':
            raise ValueError('populated evidence cannot self-certify verification or non-applicability')
        if record['source_role'] not in ('PREDECISION_RESEARCH','OUTCOME_ONLY'):
            raise ValueError('explicit predecision or outcome-only source role required')
        digest=record['source_document_sha256']
        if digest is not None and (not isinstance(digest,str) or not re.fullmatch(r'[a-f0-9]{64}',digest)):
            raise ValueError('source document digest must be a lowercase SHA-256 or unknown')
        _source_url(record['source_url'])
        if record['document_id'] is not None:
            _text(record['document_id'], 'document identity', limit=512)
        _text(record['uncertainty'], 'reported uncertainty')
        observed = _instant(record['observed_at'], 'observed_at')
        published = None if record['published_at'] is None else _instant(record['published_at'], 'published_at', allow_day=True)
        published_day = _day(record['published_at']) if isinstance(record['published_at'], str) else None
        publication_start = datetime.combine(published_day, time.min, timezone.utc) if published_day else published
        conflicts = record['conflict_ids']
        if (not isinstance(conflicts, list) or any(not isinstance(c, str) or not c for c in conflicts)
                or len(set(conflicts)) != len(conflicts) or identifier in conflicts):
            raise ValueError('unique non-self conflicting observation references required')
        try:
            encoded = json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                                 allow_nan=False).encode('utf-8')
        except (ValueError, TypeError) as exc:
            raise ValueError('finite JSON observation values required') from exc
        if len(encoded) > 65536:
            raise ValueError('observation payload exceeds research registry bound')
        if record['source_role']=='OUTCOME_ONLY':
            classification='EXCLUDED_OUTCOME_ONLY'
        elif observed > cutoff:
            classification = 'EXCLUDED_OBSERVED_AFTER_CUTOFF'
        elif published is None:
            classification = 'QUARANTINED_UNKNOWN_PUBLICATION'
        elif published > cutoff:
            classification = 'EXCLUDED_PUBLICATION_AFTER_CUTOFF'
        elif publication_start is not None and observed < publication_start:
            classification = 'QUARANTINED_OBSERVATION_BEFORE_PUBLICATION'
        elif record['source_url'] is None or record['document_id'] is None:
            classification = 'QUARANTINED_SOURCE_IDENTITY_MISSING'
        else:
            classification = CANDIDATE
        by_id[identifier] = {'record': record, 'observed': observed, 'published': published,
            'classification': classification, 'populated': _populated(record['value']),
            'input_record_sha256': hashlib.sha256(encoded).hexdigest()}
    for identifier, item in by_id.items():
        for conflict in item['record']['conflict_ids']:
            if conflict not in by_id:
                raise ValueError('unknown conflicting observation reference')
            if by_id[conflict]['record']['field_id'] != item['record']['field_id']:
                raise ValueError('conflicting evidence must reference the same scientific field')
    return by_id


def evaluate_registry(catalog, *, program_id, cutoff, observations):
    """Project a single program's source reports; always NOT_READY / ABSTAIN.

    `observed_at` means the original availability/observation claim, not the date
    an analyst later reconstructs history. Both claimed clocks must precede the
    cutoff. A date-only publication uses end-of-day UTC against intraday cutoffs.
    No clock or value supplied here is independently authenticated.
    """
    program = _text(program_id, 'program identity', limit=256)
    boundary = _instant(cutoff, 'cutoff', allow_day=True)
    fields, domains = _catalog(catalog)
    indexed = _observations(observations, fields, program, boundary)
    rows = []
    for field in fields:
        items = [item for item in indexed.values() if item['record']['field_id'] == field['id']]
        items.sort(key=lambda item: (item['observed'], item['record']['observation_id']))
        timely = [item for item in items if item['classification'] == CANDIDATE]
        populated = [item for item in timely if item['populated']]
        timely_ids = {item['record']['observation_id'] for item in populated}
        pairs = set()
        ignored = []
        for item in items:
            identifier = item['record']['observation_id']
            for target in item['record']['conflict_ids']:
                if identifier in timely_ids and target in timely_ids:
                    pairs.add(tuple(sorted((identifier, target))))
                else:
                    ignored.append({'from_observation_id': identifier, 'to_observation_id': target,
                        'status': 'NOT_ADMITTED_AS_A_TIMELY_POPULATED_CONFLICT'})
        conflicts = [{'observation_ids': list(pair), 'status': 'REPORTED_DISAGREEMENT_NOT_ADJUDICATED'}
                     for pair in sorted(pairs)]
        availability = 'SOURCE_REPORTED_VALUE_AVAILABLE' if populated else 'MISSING_TIMELY_EVIDENCE'
        quality = ('CONFLICT_REPORTED_UNADJUDICATED' if conflicts else
                   'UNVERIFIED_SOURCE_REPORTS' if populated else 'MISSING_OR_UNVERIFIED')
        rows.append({
            'field_id': field['id'], 'program_id': program, 'scientific_domain': field['segment'],
            'scientific_domain_name': domains[field['segment']], 'name': field['name'],
            'required_evidence': field['definition'], 'data_type':field['data_type'],
            'applicability':field['applicability'], 'source_requirements':field['source'],
            'scientific_rationale': field['scientific_rationale'],
            'assessment_ids': deepcopy(field['assessment_ids']),
            'investigation_levels': deepcopy(field['investigation_levels']),
            'required_source_types': deepcopy(field['required_source_types']),
            'assessment_criteria': deepcopy(field['assessment_criteria']),
            'mandatory': field['mandatory'], 'critical': field['critical'],
            'evidence_cutoff_at': _stamp(boundary), 'applicability_status': 'NOT_INDEPENDENTLY_DETERMINED',
            'availability_status': availability, 'quality_status': quality,
            'verification_status': 'NOT_INDEPENDENTLY_VERIFIED',
            'completeness': 'POPULATED_SOURCE_REPORT_ONLY' if populated else 'MISSING',
            'observations': [{**deepcopy(item['record']), 'classification': CANDIDATE,
                'eligible_for_predictive_features': False} for item in timely],
            'excluded_or_quarantined_observations': [
                {key: deepcopy(item['record'][key]) for key in ('observation_id', 'source_url', 'document_id', 'source_document_sha256', 'source_role', 'published_at', 'observed_at')}
                | {'classification': item['classification'], 'value_withheld': True}
                for item in items if item['classification'] != CANDIDATE],
            'conflicting_evidence': conflicts, 'unadmitted_conflict_references': ignored,
            'uncertainty': list(dict.fromkeys([*field['uncertainty_handling'],
                'Source reports and their asserted clocks are not independently authenticated.',
                *[item['record']['uncertainty'] for item in timely]])),
            'assessment_result': None, 'prediction_confidence': None,
            'independently_verified': False, 'eligible_for_predictive_features': False,
            'audit_scope': 'DERIVED_REFERENCE_HISTORY_NOT_PERSISTED_LEDGER',
            'audit_metadata_eligible_for_predictive_features': False,
            'audit_history': [{'observation_id': item['record']['observation_id'],
                'observed_at': item['record']['observed_at'], 'classification': item['classification'],
                'input_record_sha256': item['input_record_sha256'],
                'hash_scope': 'LOCAL_INPUT_IDENTITY_NOT_SOURCE_DOCUMENT_AUTHENTICATION'} for item in items],
        })
    counts = Counter(item['classification'] for item in indexed.values())
    available = sum(row['availability_status'] == 'SOURCE_REPORTED_VALUE_AVAILABLE' for row in rows)
    conflicts = sum(bool(row['conflicting_evidence']) for row in rows)
    # Availability summaries must not change when a later outcome is submitted.
    # Inventory and hash metadata belong to a separately labelled audit view;
    # neither that view nor this unverified projection is a model feature export.
    reported = available
    submitted_populated = len({item['record']['field_id'] for item in indexed.values()
                               if item['populated']})
    grade = ('NO_TIMELY_EVIDENCE' if not available else 'SOURCE_REPORTED_FOR_ALL_DEFINED_SLOTS'
             if available == len(rows) else 'PARTIAL_SOURCE_REPORTED')
    return {
        'schema_version': SCHEMA, 'research_only': True, 'program_id': program,
        'evidence_cutoff_at': _stamp(boundary), 'catalog_status': catalog['status'], 'slots': rows,
        'summary_scope': 'POINT_IN_TIME_UNVERIFIED_AVAILABILITY_NOT_MODEL_FEATURES',
        'summary': {'defined_slots': len(rows), 'proposed_slots': catalog['proposed_slots'],
            'reported_populated_slots': reported, 'available_before_cutoff_slots': available,
            'missing_timely_evidence_slots': len(rows)-available, 'conflicted_slots': conflicts,
            'independently_verified_slots': 0, 'independently_completed_assessments': 0,
            'applicability_exclusions': 0, 'observations': len(indexed),
            'observation_classification_counts': dict(sorted(counts.items())),
            'mandatory_slots': sum(row['mandatory'] for row in rows),
            'mandatory_missing_timely_evidence_slots': sum(row['mandatory'] and row['completeness']=='MISSING' for row in rows),
            'critical_slots': sum(row['critical'] for row in rows),
            'critical_missing_timely_evidence_slots': sum(row['critical'] and row['completeness']=='MISSING' for row in rows)},
        'audit_diagnostics': {
            'scope': 'SUBMITTED_INVENTORY_INCLUDES_EXCLUDED_RECORDS_NOT_MODEL_FEATURES',
            'submitted_populated_slots': submitted_populated,
            'submitted_observations': len(indexed),
            'eligible_for_predictive_features': False,
            'source_document_authentication_established': False,
            'append_only_audit_persisted': False,
        },
        'evidence_completeness_grade': grade,
        'source_quality_grade': 'CONFLICTS_REQUIRE_REVIEW' if conflicts else 'NOT_INDEPENDENTLY_VERIFIED',
        'scientific_readiness_grade': 'NOT_READY', 'prediction_confidence_grade': 'NOT_ESTABLISHED',
        'calibration_status': 'NOT_VALIDATED', 'independent_validation_status': 'NOT_VALIDATED',
        'predicted_decision': 'ABSTAIN', 'probabilities': {'PASS': None, 'CRL': None, 'EXTENSION': None},
        'eligible_for_validated_accuracy': False, 'trading_authorized': False,
    }
