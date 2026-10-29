"""Authorized research projection joining SCIENCE evidence and FDA comparisons.

This is a server integration interface, not an HTTP route or authentication
provider. The existing verified identity/directory boundary must construct the
principal. Explicit source reports remain unverified; no production data is read
or written and no prediction can be activated by supplying a complete payload.
"""
from datetime import date

from research.prediction_v1_1_authorization import authorize_research_read
from research.scientific_evidence_registry import evaluate_registry
from research.scientific_historical_comparison import compare_historical_cases
from research.historical_decision_registry import (
    action_label_review, predecision_view, validate_registry,
)


def build_candidate_research_assessment(*, principal, catalog, current,
                                        historical_cases, observations, cutoff):
    """Authorize every scope before projecting any candidate or comparison data.

    `program_id` is an access scope, while `program_family` identifies related
    drugs and prevents counting the same program as independent precedent.
    Public historical evidence still needs an explicit server-owned scope grant.
    The caller must provide an immutable historical input snapshot; this helper
    does not imply that asserted dates, sources or observation clocks are true.
    """
    if not isinstance(current, dict):
        raise ValueError('explicit current research case required')
    program_id = current.get('program_id')
    authorize_research_read(principal, program_id)
    if not isinstance(historical_cases, (list, tuple)):
        raise ValueError('explicit historical case sequence required')
    for case in historical_cases:
        if not isinstance(case, dict):
            raise ValueError('explicit historical research case required')
        authorize_research_read(principal, case.get('program_id'))
    if type(cutoff) is not date:
        raise ValueError('explicit comparison date required')

    science = evaluate_registry(catalog, program_id=program_id,
                                cutoff=cutoff, observations=observations)
    history = compare_historical_cases(current, historical_cases, cutoff=cutoff,
                                      authorized_program_ids=principal.program_ids)
    return {
        'schema_version': 'scientific-comparison-service-v1',
        'program_id': program_id,
        'application_id': current['application_id'],
        'review_cycle': current['review_cycle'],
        'evidence_cutoff': cutoff.isoformat(),
        'research_only': True,
        'primary_result': 'ABSTAIN',
        'readiness_grade': 'NOT_READY',
        'evidence_completeness_grade': science['evidence_completeness_grade'],
        'source_quality_grade': science['source_quality_grade'],
        'scientific_readiness_grade': science['scientific_readiness_grade'],
        'prediction_confidence': 'NOT_ESTABLISHED',
        'prediction_uncertainty': None,
        'calibration_status': 'NOT_VALIDATED',
        'independent_validation_status': 'NOT_VALIDATED',
        'regulatory_risk_assessment': 'NOT_INDEPENDENTLY_ASSESSED',
        'probabilities': {'PASS': None, 'CRL': None, 'EXTENSION': None},
        'last_verified_update': None,
        'model_version': None,
        'evidence_summary': science['summary'],
        'supporting_details': {'scientific_evidence': science,
                               'historical_comparisons': history},
        'outstanding_requirements': [
            'Independent scientific review of draft catalog definitions and applicability.',
            'Retained source bytes, attributable public timestamps and independent evidence review.',
            'Adjudicated contradictory evidence and clinically justified historical relevance.',
            'Prespecified model, outcome horizon, chronological holdout and calibration protocol.',
            'Independently validated predictions on genuinely unseen FDA decisions.',
        ],
        'audit_scope': 'READ_ONLY_PROJECTION_NOT_AN_APPEND_ONLY_AUDIT_LEDGER',
        'eligible_for_validated_accuracy': False,
        'trading_authorized': False,
    }


def build_registry_candidate_research_assessment(*, principal, catalog, current,
        historical_registry, registry_program_id, observations, cutoff):
    """Triage the source-lead registry without manufacturing engine-ready cases.

    Registry v1 contains unadjudicated cycles and source leads, whereas the
    comparison engine requires an exact, prespecified numeric review window and
    source-bound features. Mapping an unknown cycle to `1`, or filling feature
    values from an outcome narrative, would erase those gates. A future reviewed
    registry version needs an explicit adapter; this version returns exclusions.
    """
    if not isinstance(current, dict):
        raise ValueError('explicit current research case required')
    authorize_research_read(principal, current.get('program_id'))
    authorize_research_read(principal, registry_program_id)
    checked = validate_registry(historical_registry, program_id=registry_program_id)
    if type(cutoff) is not date:
        raise ValueError('explicit comparison date required')
    excluded = []
    for record in checked['records']:
        reasons = ['REGISTRY_V1_REVIEW_CYCLE_NOT_INDEPENDENTLY_ADJUDICATED',
                   'REGISTRY_V1_REQUIRES_REVIEWED_ENGINE_INPUT_ADAPTER']
        if record['application_id'] == current.get('application_id'):
            reasons.append('SAME_APPLICATION_NOT_INDEPENDENT_PRECEDENT')
        if record['program_family'].casefold() == str(current.get('program_family', '')).casefold():
            reasons.append('SAME_PROGRAM_FAMILY_NOT_INDEPENDENT_PRECEDENT')
        action_day = record['reported_action']['action_date']
        if action_day is None or date.fromisoformat(action_day) >= cutoff:
            reasons.append('ACTION_NOT_KNOWN_BEFORE_CURRENT_CUTOFF')
        if date.fromisoformat(record['evidence_cutoff']) >= cutoff:
            reasons.append('HISTORICAL_CUTOFF_NOT_BEFORE_CURRENT_CUTOFF')
        label_review = action_label_review(record)
        if not label_review['accepted_for_research_review']:
            reasons.append('HISTORICAL_LABEL_GATE_REJECTED_SOURCE_PROVENANCE')
        view = predecision_view(checked, program_id=registry_program_id,
                                record_id=record['record_id'])
        if not any(value is not None for value in view['scientific_fields'].values()):
            reasons.append('SOURCE_BOUND_SCIENTIFIC_COMPARISON_FEATURES_MISSING')
        excluded.append({
            'record_id': record['record_id'], 'application_id': record['application_id'],
            'exclusion_reasons': reasons, 'eligible_for_comparison_engine': False,
            'independently_validated': False,
        })
    result = build_candidate_research_assessment(
        principal=principal, catalog=catalog, current=current, historical_cases=[],
        observations=observations, cutoff=cutoff)
    result['historical_registry_triage'] = {
        'records_examined': len(excluded), 'engine_ready_records': 0,
        'comparisons_executed': 0, 'exclusions': excluded,
        'outcome_values_withheld': True,
        'status': 'SOURCE_LEAD_REGISTRY_REQUIRES_INDEPENDENT_ADJUDICATION',
    }
    return result
