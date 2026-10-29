"""Point-in-time historical FDA comparison, not a similarity or prediction model.

Each case describes one prespecified review window. Previous target revisions
belong in sourced regulatory history when already known at that window's cutoff.
Aliases of the same application/review cycle never become extra comparators.
Caller-supplied source metadata permits research triage only, not certification.
"""
from collections.abc import Mapping
from copy import deepcopy
from datetime import date, datetime, time, timedelta, timezone
import ipaddress
import re
from urllib.parse import urlsplit

from research.fda_outcome_provenance_gate import build_unvalidated_decision_contract
from research.prediction_v1_1_historical_label_gate import (
    REQUIRED as LABEL_FIELDS, validate_historical_label,
)

SCHEMA = 'scientific-historical-comparison-v1'
EVENT_POLICY = 'FIRST_FORMAL_FDA_ACTION_BY_HORIZON'
COMPARISON_FIELDS = (
    'drug', 'indication', 'therapeutic_class', 'clinical_phase', 'trial_design',
    'primary_endpoint', 'secondary_endpoints', 'safety_findings',
    'regulatory_designations', 'manufacturing_issues', 'previous_fda_decisions',
    'mechanism_of_action', 'efficacy_findings', 'statistical_evidence', 'regulatory_pathway',
)
COMPARISON_CRITERIA = (
    ('indication', ('indication',)),
    ('therapeutic_class', ('therapeutic_class',)),
    ('mechanism', ('mechanism_of_action',)),
    ('endpoints', ('primary_endpoint', 'secondary_endpoints')),
    ('efficacy', ('efficacy_findings',)),
    ('safety', ('safety_findings',)),
    ('trial_design_and_statistics', ('clinical_phase', 'trial_design', 'statistical_evidence')),
    ('regulatory_pathway', ('regulatory_pathway', 'regulatory_designations')),
    ('manufacturing', ('manufacturing_issues',)),
    ('prior_fda_decisions', ('previous_fda_decisions',)),
)
MINIMUM_FIELDS = frozenset({'indication', 'therapeutic_class', 'clinical_phase',
                            'trial_design', 'primary_endpoint'})
BASE_FIELDS = frozenset({'program_id', 'application_id', 'review_cycle', 'program_family',
    'target_date', 'horizon_date', 'evidence_cutoff', 'event_policy', 'field_sources',
    *COMPARISON_FIELDS})
EVENT_FIELDS = frozenset({'kind', 'action_date', 'public_available_on', 'source_url',
                          'target_date', 'revised_target_date', 'decision_label'})
SOURCE_FIELDS = frozenset({'source_id', 'source_url', 'published_on', 'available_on',
                           'source_status', 'fields', 'conflict_fields'})
FORMAL = {'APPROVAL': 'PASS', 'COMPLETE_RESPONSE': 'CRL', 'FORMAL_TARGET_REVISION': 'EXTENSION'}
UNRESOLVED = frozenset({'MISSED_TARGET', 'DELAY', 'UNRESOLVED', 'WITHDRAWN', 'REFUSE_TO_FILE'})
FDA_HOSTS = frozenset({'fda.gov', 'www.fda.gov', 'accessdata.fda.gov',
                       'www.accessdata.fda.gov', 'download.open.fda.gov'})


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        raise ValueError('canonical comparison date required')
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('canonical comparison date required') from exc
    if result.isoformat() != value:
        raise ValueError('canonical comparison date required')
    return result


def _text(value):
    return isinstance(value, str) and 0 < len(value) <= 4000 and value == value.strip() and bool(value)


def _url(value, *, fda=False):
    if not isinstance(value, str) or len(value) > 4000 or any(c.isspace() or ord(c) < 32 for c in value):
        raise ValueError('clean HTTPS source reference required')
    try:
        parsed = urlsplit(value)
        valid = (parsed.scheme == 'https' and parsed.hostname and '.' in parsed.hostname
                 and parsed.username is None and parsed.password is None and not parsed.fragment
                 and parsed.port in (None, 443) and parsed.path not in ('', '/'))
    except ValueError as exc:
        raise ValueError('clean HTTPS source reference required') from exc
    if valid:
        try:
            ipaddress.ip_address(parsed.hostname)
        except ValueError:
            pass
        else:
            valid = False
        if parsed.hostname.endswith(('.localhost', '.local', '.internal')):
            valid = False
    if not valid or (fda and parsed.hostname not in FDA_HOSTS):
        raise ValueError('official FDA action source required' if fda else 'clean HTTPS source reference required')
    return value


def _identity(case):
    app, cycle, family = case.get('application_id'), case.get('review_cycle'), case.get('program_family')
    if (not isinstance(app, str) or not re.fullmatch(r'(NDA|BLA)\d{6}', app)
            or type(cycle) is not int or cycle < 1 or not _text(family)
            or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}', family)):
        raise ValueError('exact canonical application/cycle/program-family identity required')
    return app, cycle


def _scope(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,79}', value):
        raise ValueError('exact research program access scope required')
    return value


def _value(value):
    if value is None:
        return
    if _text(value):
        return
    if isinstance(value, list) and value and all(_text(item) for item in value) and len(set(value)) == len(value):
        return
    raise ValueError('descriptive comparison values must be explicit text, unique text lists or unknown')


def _case(case, *, historical):
    expected = BASE_FIELDS | ({'action_events'} if historical else set())
    if not isinstance(case, Mapping) or set(case) != expected:
        raise ValueError('exact comparison schema required; no current outcome or self-certified claims')
    key = _identity(case)
    _scope(case['program_id'])
    if case['event_policy'] != EVENT_POLICY:
        raise ValueError('prespecified first formal action horizon required')
    target, horizon, cutoff = (_day(case[k]) for k in ('target_date', 'horizon_date', 'evidence_cutoff'))
    if cutoff >= target or horizon < target:
        raise ValueError('features must precede target day and horizon must preserve that target')
    for field in COMPARISON_FIELDS:
        _value(case[field])
    return key, cutoff, horizon


def _features(case, *, boundary):
    sources = case['field_sources']
    if not isinstance(sources, list):
        raise ValueError('field-specific source provenance required')
    usable = {field: [] for field in COMPARISON_FIELDS}
    excluded, seen, conflicts = [], set(), set()
    for source in sources:
        if (not isinstance(source, Mapping) or set(source) != SOURCE_FIELDS
                or not _text(source['source_id']) or source['source_id'] in seen
                or not isinstance(source['fields'], list) or not source['fields']
                or any(not isinstance(field,str) or field not in COMPARISON_FIELDS for field in source['fields'])
                or len(set(source['fields'])) != len(source['fields'])
                or not isinstance(source['conflict_fields'], list)
                or any(not isinstance(field, str) or field not in source['fields'] for field in source['conflict_fields'])
                or len(set(source['conflict_fields'])) != len(source['conflict_fields'])
                or source['source_status'] not in ('SOURCE_REPORTED', 'QUARANTINED', 'REJECTED')):
            raise ValueError('unique, source-bound comparison fields required; no self-verification')
        seen.add(source['source_id'])
        _url(source['source_url'])
        published = None if source['published_on'] is None else _day(source['published_on'])
        observed = None if source['available_on'] is None else _day(source['available_on'])
        if published and observed and published > observed:
            raise ValueError('source availability cannot precede publication')
        if source['source_status'] != 'SOURCE_REPORTED':
            reason = source['source_status']
        elif published is None or observed is None:
            reason = 'PUBLIC_AVAILABILITY_UNKNOWN'
        elif published > boundary or observed > boundary:
            reason = 'AFTER_EVIDENCE_CUTOFF'
        else:
            reason = None
        if reason:
            excluded.append({'source_id': source['source_id'], 'reason': reason})
        else:
            conflicts.update(source['conflict_fields'])
            for field in source['fields']:
                usable[field].append(source['source_id'])
    return usable, excluded, conflicts


def classify_fda_event(event):
    """Classify documented event metadata without authenticating FDA evidence.

    A target revision requires an explicit later target; mere lateness, withdrawal
    or a nonapproval-like legacy string cannot become EXTENSION or CRL.
    """
    if not isinstance(event, Mapping) or set(event) != EVENT_FIELDS:
        raise ValueError('exact FDA event schema required')
    kind = event['kind']
    if not isinstance(kind,str) or (kind not in FORMAL and kind not in UNRESOLVED):
        raise ValueError('exact FDA action kind required; unresolved is not a CRL alias')
    target = _day(event['target_date'])
    action = None if event['action_date'] is None else _day(event['action_date'])
    published = None if event['public_available_on'] is None else _day(event['public_available_on'])
    if kind in FORMAL:
        if action is None:
            raise ValueError('formal action date required')
        _url(event['source_url'], fda=True)
    elif event['source_url'] is not None:
        _url(event['source_url'])
    if published and action and published < action:
        raise ValueError('outcome publication cannot precede its action')
    if kind == 'FORMAL_TARGET_REVISION':
        if _day(event['revised_target_date']) <= target:
            raise ValueError('formal extension must identify a later target')
    elif event['revised_target_date'] is not None:
        raise ValueError('revised target belongs only to formal target revision')
    if event['decision_label'] is not None and not isinstance(event['decision_label'], Mapping):
        raise ValueError('decision label must be explicit provenance or unknown')
    return FORMAL.get(kind, 'UNRESOLVED')


def _label_errors(case, event, classification, feature_cutoff, comparison_cutoff):
    """Use the existing label gate; date-only event metadata cannot satisfy it.

    Days in the comparator are UTC calendar boundaries, never reconstructed
    decision or publication timestamps. Those must come from the source.
    """
    label = event['decision_label']
    if label is None:
        return ['Original action document identity, byte hash and aware timestamps missing']
    if set(label) != LABEL_FIELDS:
        return ['Exact historical decision label provenance required']
    if label['program_id'] != case['program_id']:
        return ['Decision label belongs to a different program access scope']
    boundary = datetime.combine(feature_cutoff, time.max, tzinfo=timezone.utc).isoformat()
    try:
        errors = validate_historical_label(dict(label), evidence_cutoff=boundary)
    except (TypeError, ValueError):
        return ['Malformed historical decision label']
    if label['outcome'] != classification:
        errors.append('Decision label outcome disagrees with the FDA event')
    if label['source_url'] != event['source_url']:
        errors.append('Decision label source disagrees with the FDA event')
    for key, event_key in (('decision_at', 'action_date'), ('source_published_at', 'public_available_on')):
        try:
            value = datetime.fromisoformat(label[key].replace('Z', '+00:00'))
        except (AttributeError, TypeError, ValueError):
            continue  # Existing gate reports invalid timestamps.
        if value.tzinfo is None or value.utcoffset() is None:
            continue  # Never localize a naive source timestamp.
        value = value.astimezone(timezone.utc)
        if value.date().isoformat() != event[event_key]:
            errors.append('Decision label timestamp disagrees with ' + event_key)
        if value >= datetime.combine(comparison_cutoff, time.min, tzinfo=timezone.utc):
            errors.append('Decision label is not public before current UTC cutoff')
    return errors


def _outcome(case, *, comparison_cutoff, feature_cutoff, horizon):
    events = case['action_events']
    if not isinstance(events, list):
        raise ValueError('dated FDA event history required')
    formal = []
    for event in events:
        label = classify_fda_event(event)
        if label != 'UNRESOLVED':
            formal.append((event, label))
    formal.sort(key=lambda item: (_day(item[0]['action_date']), item[0]['kind']))
    dates = [item[0]['action_date'] for item in formal]
    if len(dates) != len(set(dates)):
        raise ValueError('ambiguous same-day formal outcomes require adjudication')
    active_target = case['target_date']
    completed = False
    for event, label in formal:
        if completed or event['target_date'] != active_target:
            raise ValueError('review-cycle and target-revision chain must remain distinct')
        if label == 'EXTENSION':
            active_target = event['revised_target_date']
        else:
            completed = True
    if not formal:
        return None, ['NO_DOCUMENTED_BINARY_OR_FORMAL_EXTENSION_EVENT']
    first, label = formal[0]
    action = _day(first['action_date'])
    # Select before testing publication availability. An unknown early CRL or
    # extension must not be replaced by a later published approval.
    if feature_cutoff >= action:
        return None, ['HISTORICAL_FEATURES_NOT_PREDECISION']
    if action > horizon:
        return None, ['NO_FORMAL_ACTION_WITHIN_PRESPECIFIED_HORIZON']
    if action >= comparison_cutoff:
        return None, ['ACTION_NOT_BEFORE_CURRENT_CUTOFF']
    published = first['public_available_on']
    if published is None:
        return None, ['OUTCOME_PUBLIC_AVAILABILITY_UNKNOWN']
    if _day(published) >= comparison_cutoff:
        return None, ['OUTCOME_NOT_PUBLIC_BEFORE_CURRENT_CUTOFF']
    label_errors = _label_errors(case, first, label, feature_cutoff, comparison_cutoff)
    if label_errors:
        return None, ['HISTORICAL_LABEL_GATE: ' + error for error in label_errors]
    return {'classification': label, 'action_date': first['action_date'],
            'public_available_on': published, 'source_url': first['source_url'],
            'target_date': first['target_date'], 'revised_target_date': first['revised_target_date'],
            'event_policy': EVENT_POLICY, 'horizon_date': case['horizon_date'],
            'decision_document_id': first['decision_label']['decision_document_id'],
            'source_document_sha256': first['decision_label']['source_document_sha256'],
            'label_gate_passed_for_research_review': True,
            'independently_verified': False}, []


def _normal(value):
    if isinstance(value, list):
        return sorted(item.casefold() for item in value)
    return value.casefold()


def _criterion_summary(field_rows):
    rows = {row['criterion']: row for row in field_rows}
    criteria = []
    for name, fields in COMPARISON_CRITERIA:
        states = [rows[field]['status'] for field in fields]
        if 'CONFLICTED_EVIDENCE' in states:
            status = 'CONFLICTED_EVIDENCE'
        elif all(state == 'UNKNOWN' for state in states):
            status = 'UNKNOWN'
        elif 'UNKNOWN' in states:
            status = 'PARTIAL_EVIDENCE'
        elif 'MISMATCHED_REPORTED_VALUE' in states:
            status = 'MISMATCHED_REPORTED_VALUES'
        else:
            status = 'MATCHED_REPORTED_VALUES'
        criteria.append({'criterion': name, 'fields': list(fields), 'status': status,
                         'scientific_equivalence_established': False})
    known = sum(row['status'] in ('MATCHED_REPORTED_VALUES', 'MISMATCHED_REPORTED_VALUES') for row in criteria)
    matched = sum(row['status'] == 'MATCHED_REPORTED_VALUES' for row in criteria)
    return criteria, {'matched_criteria': matched, 'comparable_criteria': known,
        'total_criteria': len(COMPARISON_CRITERIA),
        'matched_fraction': matched / known if known else None,
        'coverage_fraction': known / len(COMPARISON_CRITERIA),
        'policy': 'UNWEIGHTED_EXACT_REPORTED_AGREEMENT_AMONG_FULLY_OBSERVED_CRITERIA',
        'clinical_similarity_validated': False, 'approval_probability': None}


def compare_historical_cases(current, historical_cases, *, cutoff, authorized_program_ids=None):
    """Compare only source-bound predecision features with earlier public actions.

    Exact text/list agreement is descriptive only. It is not clinical equivalence
    or a validated relevance weighting. Unknown fields and mismatches remain
    explicit. The descriptive agreement fraction has a visible known-evidence
    denominator; it is not an approval probability or validated similarity model.

    program_id is an access scope; program_family identifies the drug program.
    Default scope is current.program_id. A server adapter may supply an explicit
    frozenset of scopes obtained from its trusted principal directory. This pure
    computation is not an authentication boundary or a grant-creation API.
    """
    if type(cutoff) is not date:
        raise ValueError('explicit current historical comparison cutoff required')
    current_key, current_cutoff, _ = _case(current, historical=False)
    if current_cutoff != cutoff:
        raise ValueError('current evidence cutoff must match comparison cutoff exactly')
    if not isinstance(historical_cases, (list, tuple)):
        raise ValueError('historical comparison cases must be an explicit sequence')
    keys = [_case(case, historical=True)[0] for case in historical_cases]
    if authorized_program_ids is None:
        authorized_program_ids = frozenset({current['program_id']})
    if (not isinstance(authorized_program_ids, frozenset) or not authorized_program_ids
            or any(_scope(scope) != scope for scope in authorized_program_ids)):
        raise ValueError('server-resolved immutable program access scopes required')
    if any(case['program_id'] not in authorized_program_ids for case in (current, *historical_cases)):
        raise PermissionError('historical comparison program access denied')
    if len(keys) != len(set(keys)):
        raise ValueError('duplicate application/review cycle or target-date alias')
    current_sources, excluded_current, current_conflicts = _features(current, boundary=cutoff)
    reports = []
    for case, key in zip(historical_cases, keys):
        _, feature_cutoff, horizon = _case(case, historical=True)
        outcome, reasons = _outcome(case, comparison_cutoff=cutoff,
                                    feature_cutoff=feature_cutoff, horizon=horizon)
        # Even excluded cases must never expose future/post-action feature values
        # in the comparison matrix. Claimed cutoffs are not permission to leak.
        feature_boundary = min(feature_cutoff, cutoff - timedelta(days=1))
        formal_dates = [_day(event['action_date']) for event in case['action_events']
                        if event['kind'] in FORMAL]
        if formal_dates:
            feature_boundary = min(feature_boundary, min(formal_dates) - timedelta(days=1))
        sources, excluded, conflicts = _features(case, boundary=feature_boundary)
        if key[0] == current_key[0]:
            reasons.append('SAME_APPLICATION_NOT_INDEPENDENT_PRECEDENT')
        if case['program_family'].casefold() == current['program_family'].casefold():
            reasons.append('SAME_PROGRAM_FAMILY_NOT_INDEPENDENT_PRECEDENT')
        criteria, matched, mismatched, unknown, conflicted = [], [], [], [], []
        for field in COMPARISON_FIELDS:
            left = current[field] if current_sources[field] else None
            right = case[field] if sources[field] else None
            if field in current_conflicts or field in conflicts:
                # Withhold an unadjudicated value rather than pick a side.
                if field in current_conflicts: left = None
                if field in conflicts: right = None
                state = 'CONFLICTED_EVIDENCE'
                conflicted.append(field)
            elif left is None or right is None:
                state = 'UNKNOWN'
                unknown.append(field)
            elif _normal(left) == _normal(right):
                state = 'MATCHED_REPORTED_VALUE'
                matched.append(field)
            else:
                state = 'MISMATCHED_REPORTED_VALUE'
                mismatched.append(field)
            criteria.append({'criterion': field, 'status': state,
                'current_value': deepcopy(left), 'historical_value': deepcopy(right),
                'current_source_ids': current_sources[field], 'historical_source_ids': sources[field]})
        if 'indication' in mismatched:
            reasons.append('DIFFERENT_INDICATION_REQUIRES_SEPARATE_REVIEW')
        if MINIMUM_FIELDS.intersection(unknown):
            reasons.append('MINIMUM_SCIENTIFIC_COMPARISON_EVIDENCE_MISSING')
        if conflicted:
            reasons.append('UNADJUDICATED_CONTRADICTORY_EVIDENCE')
        if feature_cutoff >= cutoff:
            reasons.append('HISTORICAL_CUTOFF_NOT_BEFORE_CURRENT_CUTOFF')
        grouped, agreement = _criterion_summary(criteria)
        selection_reasons = ['SOURCE_BOUND_REPORTED_AGREEMENT: ' + group['criterion']
                             for group in grouped if group['status'] == 'MATCHED_REPORTED_VALUES']
        limitations = ['REPORTED_VALUES_DIFFER: ' + field for field in mismatched]
        limitations += ['EVIDENCE_UNKNOWN: ' + field for field in unknown]
        limitations += ['EVIDENCE_CONFLICTED: ' + field for field in conflicted]
        limitations.append('Exact reported agreement does not establish clinical equivalence or predictive value')
        limitations.append('Sources, clinical interpretation and historical action are not independently certified')
        reports.append({'program_id': case['program_id'], 'application_id': key[0], 'review_cycle': key[1],
            'program_family': case['program_family'], 'evidence_cutoff': case['evidence_cutoff'],
            'criteria': criteria, 'matched_criteria': matched, 'mismatched_criteria': mismatched,
            'unknown_criteria': unknown, 'conflicted_criteria': conflicted, 'excluded_sources': excluded,
            'comparison_criteria': grouped, 'descriptive_agreement': agreement,
            'selection_reasons': selection_reasons, 'relevance_limitations': limitations,
            'known_historical_outcome': outcome, 'exclusion_reasons': sorted(set(reasons)),
            'context_eligible': not reasons,
            'selection_status': 'RESEARCH_CONTEXT_CANDIDATE' if not reasons else 'EXCLUDED_PENDING_ADJUDICATION',
            'relevance_status': 'UNADJUDICATED_DESCRIPTIVE_COMPARISON',
            'similarity_score': None, 'independently_reviewed': False,
            'eligible_for_predictive_training': False, 'eligible_for_validated_accuracy': False})
    return {'schema_version': SCHEMA, 'research_only': True,
        'current_program_id': current['program_id'], 'implemented_comparison_criteria': len(COMPARISON_CRITERIA),
        'current_application_id': current_key[0], 'current_review_cycle': current_key[1],
        'current_cutoff': cutoff.isoformat(), 'comparisons': reports,
        'current_excluded_sources': excluded_current,
        'historical_cases_processed': len(reports),
        'research_context_candidates': sum(row['context_eligible'] for row in reports),
        'independently_validated_comparisons': 0,
        'current_outcome_unseen_independently_verified': False,
        'matching_policy': 'EXACT_REPORTED_VALUES_NOT_CLINICAL_EQUIVALENCE_OR_VALIDATED_SIMILARITY',
        'ranking_policy': 'NO_AUTOMATED_CLINICAL_RELEVANCE_RANKING',
        'decision_contract': build_unvalidated_decision_contract(as_of=cutoff),
        'trading_authorized': False}
