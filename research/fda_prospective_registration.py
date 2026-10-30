"""Prospective ABSTAIN research bundles; local integrity is not trusted timing.

Each bundle is write-once at its selected path, not a global append-only registry.
No real trial is registered by importing or testing this module. The CLI records
only explicitly supplied research artifacts, never calls a scanner, and cannot
emit an actionable prediction or certify an independently unseen FDA outcome.
"""
from __future__ import annotations

import argparse
from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile

from research.fda_outcome_provenance_gate import (
    build_unvalidated_decision_contract, validate_unvalidated_decision_contract,
)

SCHEMA = 'fda-prospective-abstention-registration-v1'
COHORT_SCHEMA = 'fda-prospective-screening-cohort-v1'
POLICY = {
    'event_selection': 'FIRST_FORMAL_FDA_ACTION_BY_HORIZON',
    'extension': 'FORMAL_FDA_TARGET_REVISION_ONLY',
    'no_action': 'UNRESOLVED_NOT_AUTOMATIC_EXTENSION',
}
REQUIRED_ROLES = frozenset({'features', 'evidence', 'protocol', 'cohort'})
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024
BLOCKERS = [
    'COHORT_NOT_INDEPENDENTLY_ADJUDICATED',
    'FUTURE_TARGET_DOES_NOT_PROVE_OUTCOME_UNSEEN',
    'NO_INDEPENDENT_TIME_ANCHOR',
    'NO_SOURCE_OR_MODEL_VALIDATION',
]
FLAGS = (
    'outcome_unseen_independently_verified', 'registration_time_independently_verified',
    'source_evidence_independently_verified', 'model_independently_validated',
    'eligible_for_validated_accuracy', 'trading_authorized',
)
SPEC_FIELDS = frozenset({
    'application_id', 'review_cycle', 'indication', 'program_family', 'ticker',
    'target_date', 'evidence_cutoff_at', 'horizon_at', 'event_policy',
    'model_version', 'model_training_cutoff_at',
})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON field in research registration input')
        result[key] = value
    return result


def _json_bytes(value):
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False,
                       allow_nan=False) + '\n').encode('utf-8')


def _load_json(data):
    try:
        return json.loads(data, object_pairs_hook=_unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON value')))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError('valid UTF-8 research JSON required') from exc


def _text(value, field):
    if not isinstance(value, str) or not value.strip() or len(value) > 2000:
        raise ValueError(f'nonempty bounded {field} required')
    return value.strip()


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9]{4}-[0-9]{2}-[0-9]{2}', value):
        raise ValueError('canonical target date required')
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('canonical target date required') from exc


def _instant(value):
    if not isinstance(value, str) or 'T' not in value:
        raise ValueError('aware UTC timestamp required')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError('aware UTC timestamp required') from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError('aware UTC timestamp required')
    return parsed.astimezone(timezone.utc)


def _stamp(value):
    if type(value) is not datetime or value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError('registration time must be an explicit aware UTC datetime')
    return value.astimezone(timezone.utc).isoformat(timespec='microseconds').replace('+00:00', 'Z')


def _identity(row):
    app = row.get('application_id')
    cycle = row.get('review_cycle')
    if (not isinstance(app, str) or not re.fullmatch(r'(NDA|BLA)[0-9]{6}', app)
            or type(cycle) is not int or cycle < 1):
        raise ValueError('canonical FDA application and positive integer cycle required')
    target = _day(row.get('target_date'))
    return f'{app}|cycle-{cycle}|{target.isoformat()}'


def _spec(spec, registered_at, *, has_model):
    if not isinstance(spec, Mapping) or set(spec) != SPEC_FIELDS:
        raise ValueError('exact prospective specification fields required; no FDA outcomes or certification claims')
    normalized = deepcopy(dict(spec))
    key = _identity(spec)
    for field in ('indication', 'program_family', 'ticker'):
        normalized[field] = _text(spec[field], field)
    if not re.fullmatch(r'[A-Z][A-Z0-9.-]{0,14}', normalized['ticker']):
        raise ValueError('canonical ticker required')
    if not re.fullmatch(r'[A-Z0-9][A-Z0-9_.:-]{0,79}', normalized['program_family']):
        raise ValueError('canonical program family required')
    cutoff, horizon = _instant(spec['evidence_cutoff_at']), _instant(spec['horizon_at'])
    target_start = datetime.combine(_day(spec['target_date']), datetime.min.time(), tzinfo=timezone.utc)
    if not cutoff <= registered_at < target_start or not registered_at < horizon or horizon < target_start:
        raise ValueError('evidence cutoff must precede registration, before target day and prespecified horizon')
    if not isinstance(spec['event_policy'], Mapping) or dict(spec['event_policy']) != POLICY:
        raise ValueError('prespecified first formal action policy required; delay is not an extension')
    normalized['event_policy'] = dict(POLICY)
    normalized['evidence_cutoff_at'], normalized['horizon_at'] = _stamp(cutoff), _stamp(horizon)
    if has_model:
        normalized['model_version'] = _text(spec['model_version'], 'unvalidated model version')
        training = _instant(spec['model_training_cutoff_at'])
        if training > cutoff:
            raise ValueError('model training cutoff cannot follow evidence cutoff')
        normalized['model_training_cutoff_at'] = _stamp(training)
    elif spec['model_version'] is not None or spec['model_training_cutoff_at'] is not None:
        raise ValueError('model metadata requires actual model bytes; ABSTAIN may have no model')
    return key, normalized


def _artifacts(artifacts):
    if (not isinstance(artifacts, Mapping) or not REQUIRED_ROLES <= set(artifacts)
            or set(artifacts) - REQUIRED_ROLES - {'model'}):
        raise ValueError('features, evidence, protocol and screening cohort bytes required')
    metadata = {}
    for role, data in artifacts.items():
        if type(data) is not bytes or not 0 < len(data) <= MAX_ARTIFACT_BYTES:
            raise ValueError('each artifact must contain bounded nonempty original bytes')
        metadata[role] = {'sha256': hashlib.sha256(data).hexdigest(), 'byte_count': len(data)}
    return metadata


def _cohort(data, event_key):
    cohort = _load_json(data)
    if (not isinstance(cohort, dict) or set(cohort) != {'schema_version', 'selection_rule', 'members'}
            or cohort['schema_version'] != COHORT_SCHEMA or not isinstance(cohort['members'], list)
            or not cohort['members']):
        raise ValueError('frozen screening cohort and selection rule required')
    selection_rule = _text(cohort['selection_rule'], 'cohort selection rule')
    seen, cycles, included = set(), set(), 0
    membership = False
    for member in cohort['members']:
        if not isinstance(member, dict) or set(member) != {
            'application_id', 'review_cycle', 'target_date', 'disposition', 'exclusion_reason'
        }:
            raise ValueError('exact cohort identity and screening disposition required')
        key = _identity(member)
        cycle_identity = (member['application_id'], member['review_cycle'])
        if key in seen or cycle_identity in cycles:
            raise ValueError('duplicate application/review cycle in screening cohort; target aliases are not independent cases')
        seen.add(key)
        cycles.add(cycle_identity)
        if member['disposition'] == 'INCLUDED' and member['exclusion_reason'] is None:
            included += 1
            membership |= key == event_key
        elif member['disposition'] == 'EXCLUDED':
            _text(member['exclusion_reason'], 'screening exclusion reason')
        else:
            raise ValueError('included/excluded cohort disposition and matching reason required')
    if not membership:
        raise ValueError('registration event must occur exactly once as included in frozen cohort')
    return {'schema_version': COHORT_SCHEMA, 'selection_rule': selection_rule,
            'screened_count': len(seen), 'included_count': included,
            'excluded_count': len(seen) - included, 'registration_event_included': True,
            'denominator_independently_verified': False}


def build_registration(spec, artifacts, *, registered_at):
    """Commit explicit ABSTAIN research inputs, never independent chronology.

    `registered_at` is injectable for deterministic tests. The CLI gets it from
    its own clock, with no backdating option. Neither clock is an external proof.
    A future target does not exclude an earlier, already public FDA action.
    """
    stamp = _stamp(registered_at)
    metadata = _artifacts(artifacts)
    key, normalized = _spec(spec, registered_at, has_model='model' in metadata)
    result = {
        'schema_version': SCHEMA, 'research_only': True, 'registered_at': stamp,
        'event_key': key, 'specification': normalized, 'artifacts': metadata,
        'screening_cohort': _cohort(artifacts['cohort'], key),
        'decision_contract': build_unvalidated_decision_contract(
            blockers=BLOCKERS, as_of=registered_at.date()),
        'clock_provenance': 'LOCAL_RUNTIME_CLOCK_NOT_INDEPENDENT_TIMESTAMP',
        'scope': 'BYTE_COMMITMENT_AND_ABSTENTION_NOT_VALIDATED_PREDICTION_OR_TRUSTED_TIMESTAMP',
        **{flag: False for flag in FLAGS},
    }
    result['registration_sha256'] = hashlib.sha256(_json_bytes(result)).hexdigest()
    return result


def audit_registration(manifest, artifacts=None):
    """Check local metadata integrity, optionally against actual artifact bytes.

    A digest can be recomputed after editing, so metadata-only checks authenticate
    neither bytes, chronology nor scientific truth. No receipt is trusted here.
    """
    expected_fields = {'schema_version', 'research_only', 'registered_at', 'event_key',
        'specification', 'artifacts', 'screening_cohort', 'decision_contract', 'clock_provenance',
        'scope', 'registration_sha256', *FLAGS}
    if (not isinstance(manifest, Mapping) or set(manifest) != expected_fields
            or manifest['schema_version'] != SCHEMA or manifest['research_only'] is not True
            or any(manifest[flag] is not False for flag in FLAGS)
            or manifest['clock_provenance'] != 'LOCAL_RUNTIME_CLOCK_NOT_INDEPENDENT_TIMESTAMP'
            or manifest['scope'] != 'BYTE_COMMITMENT_AND_ABSTENTION_NOT_VALIDATED_PREDICTION_OR_TRUSTED_TIMESTAMP'):
        raise ValueError('research registration cannot certify timing, unseen outcomes, accuracy or trading')
    registered_at = _instant(manifest['registered_at'])
    if _stamp(registered_at) != manifest['registered_at']:
        raise ValueError('canonical UTC registration timestamp required')
    metadata = manifest['artifacts']
    if not isinstance(metadata, Mapping) or not REQUIRED_ROLES <= set(metadata) or set(metadata)-REQUIRED_ROLES-{'model'}:
        raise ValueError('exact artifact roles required')
    for entry in metadata.values():
        if (not isinstance(entry, Mapping) or set(entry) != {'sha256', 'byte_count'}
                or not isinstance(entry['sha256'], str) or not re.fullmatch(r'[a-f0-9]{64}', entry['sha256'])
                or type(entry['byte_count']) is not int or not 0 < entry['byte_count'] <= MAX_ARTIFACT_BYTES):
            raise ValueError('actual-byte artifact digest and bounded size metadata required')
    key, spec = _spec(manifest['specification'], registered_at, has_model='model' in metadata)
    if key != manifest['event_key'] or spec != manifest['specification']:
        raise ValueError('canonical registration specification and exact event binding required')
    validate_unvalidated_decision_contract(manifest['decision_contract'])
    if manifest['decision_contract'] != build_unvalidated_decision_contract(blockers=BLOCKERS, as_of=registered_at.date()):
        raise ValueError('registration must preserve the exact ABSTAIN contract')
    cohort = manifest['screening_cohort']
    if (not isinstance(cohort, Mapping) or set(cohort) != {'schema_version', 'selection_rule',
            'screened_count', 'included_count', 'excluded_count', 'registration_event_included',
            'denominator_independently_verified'} or cohort['schema_version'] != COHORT_SCHEMA
            or cohort['registration_event_included'] is not True
            or cohort['denominator_independently_verified'] is not False
            or any(type(cohort[k]) is not int for k in ('screened_count', 'included_count', 'excluded_count'))
            or cohort['included_count'] < 1 or cohort['excluded_count'] < 0
            or cohort['screened_count'] != cohort['included_count'] + cohort['excluded_count']):
        raise ValueError('screening denominator metadata must remain unverified and reconcile')
    _text(cohort['selection_rule'], 'cohort selection rule')
    body = {key: value for key, value in manifest.items() if key != 'registration_sha256'}
    if manifest['registration_sha256'] != hashlib.sha256(_json_bytes(body)).hexdigest():
        raise ValueError('registration content digest mismatch')
    if artifacts is not None and build_registration(spec, artifacts, registered_at=registered_at) != manifest:
        raise ValueError('registration artifacts or cohort bytes differ from committed manifest')
    return {'status': 'LOCAL_INTEGRITY_ONLY_NOT_INDEPENDENT_VALIDATION',
            'artifact_bytes_checked': artifacts is not None, 'event_key': key,
            'registration_time_independently_verified': False,
            'outcome_unseen_independently_verified': False,
            'eligible_for_validated_accuracy': False, 'trading_authorized': False}


def write_registration(output, manifest, *, input_paths=()):
    """Publish one complete bundle atomically without replacing any path.

    This is per-path write-once storage, not a globally append-only registry or a
    guarantee against another file containing the same research event.
    """
    audit_registration(manifest)
    output = Path(output)
    if output.resolve() in {Path(path).resolve() for path in input_paths}:
        raise ValueError('registration output cannot replace an input artifact')
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=output.parent,
                                         prefix='.registration-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(_json_bytes(manifest))
            stream.flush()
            os.fsync(stream.fileno())
        # Same-directory hard link atomically fails when output already exists.
        os.link(temporary, output)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    for role in sorted(REQUIRED_ROLES):
        parser.add_argument('--'+role, type=Path, required=True)
    parser.add_argument('--model', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    paths = {role: getattr(args, role) for role in REQUIRED_ROLES | {'model'}
             if getattr(args, role) is not None}
    for path in [args.spec, *paths.values()]:
        if not path.is_file() or not 0 < path.stat().st_size <= MAX_ARTIFACT_BYTES:
            parser.error('all inputs must be bounded nonempty files')
    artifacts = {role: path.read_bytes() for role, path in paths.items()}
    manifest = build_registration(_load_json(args.spec.read_bytes()), artifacts,
                                  registered_at=datetime.now(timezone.utc))
    write_registration(args.output, manifest, input_paths=[args.spec, *paths.values()])
    print('Saved research ABSTAIN registration; independent timestamp and validation remain unverified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
