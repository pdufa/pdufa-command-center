"""Frozen first-formal-event target preparation; never FDA adjudication.

One cycle can contain extension then approval/CRL. The event sequence survives
target derivation, and missing early provenance cannot be replaced by later news.
"""
from copy import deepcopy
from datetime import date, timezone
from hashlib import sha256
import json
from pathlib import Path

from research.official_history_readiness import _clock, _text
from research.official_sources import application_id as validate_application_id
from research.prediction_v1_1_historical_label_gate import REQUIRED as LABEL_FIELDS, validate_historical_label
from research.scientific_historical_comparison import classify_fda_event

PROTOCOL_PATH = Path(__file__).parent / 'evidence' / 'official_event_protocol_v1.json'
PROTOCOL_SHA256 = 'afb5f56c191bff5c400d91a77b5d380976d1606dac329cf31d83dec93e4bd803'
_EVENT_ENVELOPE = frozenset({'event_id', 'application_id', 'review_cycle_id', 'event'})


def load_event_protocol(path=PROTOCOL_PATH):
    raw = Path(path).read_bytes()
    if sha256(raw).hexdigest() != PROTOCOL_SHA256:
        raise ValueError('frozen event protocol integrity mismatch; create a new reviewed version')
    return json.loads(raw)


def prepare_event_target(events, *, program_id, application_id, review_cycle_id,
                         original_target_date, prediction_cutoff, horizon_at,
                         evaluation_as_of):
    """Return all chronology and a provenance-gated *research* target candidate.

    Events have exact envelopes ``event_id/application_id/review_cycle_id/event``;
    ``event`` reuses the existing FDA event schema and decision-label provenance.
    Horizon and evaluation dates are mandatory aware timestamps, never inferred
    from a missed PDUFA date. Malformed schemas raise; conflicts remain blockers.
    Even a structurally usable candidate remains independently unverified.
    """
    load_event_protocol()
    validate_application_id(application_id)
    if not _text(program_id) or not _text(review_cycle_id):
        raise ValueError('explicit program and exact review cycle required')
    cutoff, horizon, as_of = map(_clock, (prediction_cutoff, horizon_at, evaluation_as_of))
    if cutoff is None or horizon is None or as_of is None or not cutoff < horizon <= as_of:
        raise ValueError('aware cutoff < horizon <= evaluation_as_of required')
    if not isinstance(events, (list, tuple)):
        raise ValueError('explicit event sequence required')
    blockers = []
    if original_target_date is None:
        blockers.append('ORIGINAL_PDUFA_TARGET_UNKNOWN')
    elif (not isinstance(original_target_date, str)
          or date.fromisoformat(original_target_date).isoformat() != original_target_date):
        raise ValueError('original target must preserve exact date precision or remain null')
    history = []
    seen = set()
    for item in events:
        if not isinstance(item, dict) or set(item) != _EVENT_ENVELOPE or not _text(item['event_id']):
            raise ValueError('exact dated-event envelope required')
        if item['event_id'] in seen:
            raise ValueError('duplicate event identity')
        seen.add(item['event_id'])
        if item['application_id'] != application_id or item['review_cycle_id'] != review_cycle_id:
            raise ValueError('event application/review cycle identity mismatch')
        classification = classify_fda_event(item['event'])
        history.append({**deepcopy(item), 'classification': classification})
    history.sort(key=lambda row: (row['event']['action_date'] or '9999-12-31', row['event_id']))
    formal = [row for row in history if row['classification'] != 'UNRESOLVED']
    active_target = original_target_date
    terminal_seen = False
    formal_days = set()
    for row in formal:
        event = row['event']
        if event['action_date'] in formal_days:
            blockers.append('AMBIGUOUS_SAME_DAY_FORMAL_EVENTS')
        formal_days.add(event['action_date'])
        if terminal_seen:
            blockers.append('FORMAL_EVENT_AFTER_TERMINAL_ACTION_IN_SAME_CYCLE')
        if active_target is not None and event['target_date'] != active_target:
            blockers.append('BROKEN_TARGET_REVISION_CHAIN')
        if row['classification'] == 'EXTENSION':
            active_target = event['revised_target_date']
        else:
            terminal_seen = True
    candidate = None
    selected = formal[0] if formal else None
    if selected is None:
        blockers.append('NO_FORMAL_ACTION_WITHIN_HORIZON')
    else:
        event = selected['event']
        label = event['decision_label']
        # Selection precedes checking provenance; no later-event substitution.
        if event['action_date'] < cutoff.astimezone(timezone.utc).date().isoformat():
            blockers.append('FIRST_FORMAL_ACTION_PRECEDES_PREDICTION_CUTOFF')
        if event['action_date'] > horizon.astimezone(timezone.utc).date().isoformat():
            blockers.append('NO_FORMAL_ACTION_WITHIN_HORIZON')
        if not isinstance(label, dict):
            blockers.append('ORIGINAL_DOCUMENT_AND_AWARE_LABEL_CLOCKS_MISSING')
        else:
            label_errors = validate_historical_label(label, evidence_cutoff=prediction_cutoff)
            if label_errors:
                blockers.append('HISTORICAL_LABEL_PROVENANCE_INVALID')
            if (label.get('program_id') != program_id
                    or label.get('application_id') != application_id
                    or label.get('review_cycle_id') != review_cycle_id):
                blockers.append('LABEL_EXACT_IDENTITY_MISMATCH')
            if label.get('outcome') != selected['classification'] or label.get('source_url') != event['source_url']:
                blockers.append('LABEL_EVENT_SOURCE_OR_OUTCOME_MISMATCH')
            action = _clock(label.get('decision_at'))
            published = _clock(label.get('source_published_at'))
            if action is not None:
                if action.astimezone(timezone.utc).date().isoformat() != event['action_date']:
                    blockers.append('ACTION_DATE_CLOCK_MISMATCH')
                if not cutoff < action <= horizon:
                    blockers.append('FIRST_FORMAL_ACTION_OUTSIDE_PREDICTION_WINDOW')
            if published is not None:
                if published.astimezone(timezone.utc).date().isoformat() != event['public_available_on']:
                    blockers.append('PUBLICATION_DATE_CLOCK_MISMATCH')
                if published >= as_of:
                    blockers.append('LABEL_NOT_PUBLIC_BEFORE_EVALUATION_AS_OF')
            if not blockers:
                candidate = {'event_id': selected['event_id'],
                    'outcome': selected['classification'],
                    'decision_label': {key: deepcopy(label[key]) for key in
                        (*sorted(LABEL_FIELDS), 'application_id', 'review_cycle_id')},
                    'source_document_sha256': label['source_document_sha256'],
                    'independently_verified': False}
    blockers.append('AUTHENTICATED_INDEPENDENT_ADJUDICATION_NOT_ESTABLISHED')
    snapshot = {'events': events, 'program_id': program_id, 'application_id': application_id,
        'review_cycle_id': review_cycle_id, 'original_target_date': original_target_date,
        'prediction_cutoff': prediction_cutoff, 'horizon_at': horizon_at,
        'evaluation_as_of': evaluation_as_of}
    digest = sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
    return {'schema_version': 'official-event-target-preparation-v1',
        'protocol_sha256': PROTOCOL_SHA256, 'input_snapshot_sha256': digest,
        'prediction_target': 'FIRST_FORMAL_FDA_ACTION_IN_THE_REVIEW_CYCLE_BY_EXPLICIT_HORIZON',
        'prediction_cutoff': prediction_cutoff, 'horizon_at': horizon_at,
        'evaluation_as_of': evaluation_as_of, 'original_target_date': original_target_date,
        'application_id': application_id, 'review_cycle_id': review_cycle_id,
        'chronology': history, 'selected_first_formal_event_id': selected['event_id'] if selected else None,
        'research_target_candidate': candidate, 'blocking_reasons': sorted(set(blockers)),
        'independently_verified_decisions': 0, 'eligible_for_training_or_evaluation': False,
        'operational_metrics': None, 'probabilities': None, 'research_only': True,
        'prediction_readiness': 'NOT_READY', 'prediction_action': 'ABSTAIN'}
