"""Offline, fail-closed chronological backtest preparation.

This is structural triage, not an outcome adjudicator. Existing provenance
review receipts explicitly do not certify independent verification; this module
therefore never upgrades a downloaded record or a caller assertion to a verified
outcome. Model fitting and performance reporting remain unavailable.
"""
from collections import defaultdict
from datetime import datetime
from hashlib import sha256
import json
import re

from research.prediction_v1_1_historical_label_gate import validate_historical_label
from research.official_sources import AVAILABLE

_APPLICATION = re.compile(r'(?:NDA|BLA)[0-9]{6}\Z')
_DIGEST = re.compile(r'[0-9a-f]{64}\Z')
_INPUT_FIELDS = frozenset({'field_id', 'value', 'source_document_sha256',
                          'source_published_at', 'public_available_at',
                          'source_status', 'conflict'})


def _clock(value):
    if not isinstance(value, str) or 'T' not in value:
        return None
    try:
        clock = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return clock if clock.tzinfo is not None and clock.utcoffset() is not None else None
    except ValueError:
        return None


def _text(value):
    return (isinstance(value, str) and bool(value) and value == value.strip()
            and len(value) <= 512 and not any(ord(c) < 32 for c in value))


def _digest(value):
    return isinstance(value, str) and bool(_DIGEST.fullmatch(value))


def prepare_chronological_backtest(records, *, evaluation_starts_at, required_fields):
    """Check exact cases and clocks, returning blockers without predictions.

    Each case supplies separate ``prediction_inputs`` and ``outcome_label``.
    Allowlisted input envelopes reject outcome payloads and unknown metadata.
    Train labels must be publicly available strictly before the evaluation
    boundary. Families and applications are disjoint across the partitions.
    A source's AVAILABLE status means retrieval only, never scientific review.
    ``required_fields`` must come from a prespecified reviewed model protocol;
    this helper cannot establish clinical sufficiency of that protocol.
    """
    boundary = _clock(evaluation_starts_at)
    if boundary is None:
        raise ValueError('aware evaluation boundary required')
    if (not isinstance(required_fields, (set, frozenset, tuple, list))
            or not required_fields or any(not _text(f) for f in required_fields)):
        raise ValueError('prespecified nonempty required field identifiers required')
    if not isinstance(records, (list, tuple)):
        raise ValueError('explicit record sequence required')
    required = frozenset(required_fields)
    results = []
    identities = defaultdict(list)
    applications = defaultdict(set)
    families = defaultdict(set)
    for index, row in enumerate(records):
        reasons = []
        result = {'record_index': index, 'blocking_reasons': reasons}
        results.append(result)
        if not isinstance(row, dict):
            reasons.append('INVALID_RECORD')
            continue
        application = row.get('application_id')
        cycle = row.get('review_cycle_id')
        family = row.get('program_family')
        split = row.get('partition')
        cutoff = _clock(row.get('evidence_cutoff'))
        if not isinstance(application, str) or not _APPLICATION.fullmatch(application):
            reasons.append('INVALID_APPLICATION_ID')
        if not _text(cycle):
            reasons.append('MISSING_EXACT_REVIEW_CYCLE')
        if not _text(family):
            reasons.append('MISSING_PROGRAM_FAMILY')
        if split not in ('TRAIN', 'EVALUATION'):
            reasons.append('INVALID_PARTITION')
        if cutoff is None:
            reasons.append('INVALID_CUTOFF')
        elif split == 'TRAIN' and cutoff >= boundary:
            reasons.append('TRAINING_CUTOFF_NOT_BEFORE_EVALUATION')
        elif split == 'EVALUATION' and cutoff < boundary:
            reasons.append('EVALUATION_CUTOFF_BEFORE_BOUNDARY')
        if _text(application) and _text(cycle):
            identities[(application, cycle)].append(index)
        if _text(application) and isinstance(split, str):
            applications[application].add(split)
        if _text(family) and isinstance(split, str):
            families[family.casefold()].add(split)
        label = row.get('outcome_label')
        label_errors = validate_historical_label(label, evidence_cutoff=row.get('evidence_cutoff'))
        if label_errors:
            reasons.append('INVALID_OR_UNVERIFIED_OUTCOME_LABEL')
        if isinstance(label, dict):
            if label.get('program_id') != row.get('program_id'):
                reasons.append('LABEL_PROGRAM_IDENTITY_MISMATCH')
            # Do not discard submission/cycle identity when associating labels.
            if (label.get('application_id') != application
                    or label.get('review_cycle_id') != cycle):
                reasons.append('LABEL_APPLICATION_CYCLE_MISMATCH')
            published = _clock(label.get('source_published_at'))
            decision = _clock(label.get('decision_at'))
            if split == 'TRAIN' and (published is None or decision is None
                                     or published >= boundary or decision >= boundary):
                reasons.append('TRAINING_LABEL_NOT_KNOWN_BEFORE_EVALUATION')
        inputs = row.get('prediction_inputs')
        seen = set()
        if not isinstance(inputs, list) or not inputs:
            reasons.append('MISSING_PREDICTION_EVIDENCE')
            inputs = []
        for item in inputs:
            if not isinstance(item, dict) or set(item) != _INPUT_FIELDS:
                reasons.append('INVALID_INPUT_ENVELOPE_OR_OUTCOME_LEAKAGE')
                continue
            field = item['field_id']
            if not isinstance(field, str) or field not in required:
                reasons.append('INPUT_OUTSIDE_PRESPECIFIED_FIELDS')
                continue
            if field in seen:
                reasons.append('DUPLICATE_OR_CONFLICTING_FIELD')
            seen.add(field)
            if item['value'] is None:
                reasons.append('MISSING_FIELD_VALUE')
            if item['conflict'] is not False:
                reasons.append('UNRESOLVED_SCIENTIFIC_CONFLICT')
            if item['source_status'] != AVAILABLE or not _digest(item['source_document_sha256']):
                reasons.append('SOURCE_VERIFICATION_FAILED')
            published = _clock(item['source_published_at'])
            available = _clock(item['public_available_at'])
            if published is None or available is None:
                reasons.append('MISSING_VERIFIABLE_PUBLICATION_CLOCK')
            elif available < published or cutoff is None or max(published, available) >= cutoff:
                reasons.append('HISTORICAL_EVIDENCE_LEAKAGE')
            if isinstance(label, dict) and item['source_document_sha256'] == label.get('source_document_sha256'):
                reasons.append('OUTCOME_DOCUMENT_IN_PREDICTION_INPUTS')
        if required - seen:
            reasons.append('MISSING_REQUIRED_EVIDENCE')
        reasons.append('INDEPENDENT_OUTCOME_AND_SCIENTIFIC_REVIEW_NOT_ESTABLISHED')
    for indices in identities.values():
        if len(indices) > 1:
            labels = {records[i].get('outcome_label', {}).get('outcome')
                      for i in indices if isinstance(records[i].get('outcome_label'), dict)
                      and isinstance(records[i]['outcome_label'].get('outcome'), str)}
            for i in indices:
                results[i]['blocking_reasons'].append('DUPLICATE_APPLICATION_REVIEW_CYCLE')
                if len(labels) > 1:
                    results[i]['blocking_reasons'].append('CONFLICTING_REGULATORY_OUTCOMES')
    for result, row in zip(results, records):
        if isinstance(row, dict):
            family = row.get('program_family')
            application = row.get('application_id')
            if _text(application) and {'TRAIN', 'EVALUATION'} <= applications[application]:
                result['blocking_reasons'].append('RELATED_APPLICATION_SPLIT_LEAKAGE')
            if _text(family) and {'TRAIN', 'EVALUATION'} <= families[family.casefold()]:
                result['blocking_reasons'].append('RELATED_PROGRAM_SPLIT_LEAKAGE')
        result['blocking_reasons'] = sorted(set(result['blocking_reasons']))
        result['eligible_for_training_or_evaluation'] = False
    encoded = json.dumps(records, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return {'schema_version': 'official-history-readiness-v1',
            'input_snapshot_sha256': sha256(encoded).hexdigest(),
            'hash_scope': 'LOCAL_INPUT_SNAPSHOT_NOT_SOURCE_AUTHENTICATION',
            'records': results, 'record_count': len(results),
            'independently_verified_decisions': 0, 'evaluated_predictions': 0,
            'measured_performance': None, 'prediction_readiness': 'NOT_READY',
            'prediction_action': 'ABSTAIN', 'research_only': True}
