"""Authorized presentation contract for the future three-outcome engine.

This research-only projection reuses the scientific evidence and comparison gates.
It does not mount a route, persist an audit, fit a model, or certify evidence.
"""
from copy import deepcopy

from research.scientific_comparison_service import build_candidate_research_assessment
from research.scientific_field_catalog import build_scientific_catalog

SECTIONS = (
    ('scientific_evidence', 'Scientific evidence'),
    ('historical_comparisons', 'Historical comparisons'),
    ('regulatory_risk', 'Regulatory risk'),
    ('clinical_efficacy', 'Clinical efficacy'),
    ('safety', 'Safety'),
    ('manufacturing', 'Manufacturing'),
    ('fda_designations', 'FDA designations'),
    ('model_validation', 'Model validation'),
    ('confidence_uncertainty', 'Confidence and uncertainty'),
    ('source_documentation', 'Complete source documentation'),
)


def build_prediction_output(*, principal, current, historical_cases, observations, cutoff):
    """Project authorized source-bound research, always NOT_READY / ABSTAIN.

    No self-certified score/model/verification payload is accepted. The existing
    service authorizes every candidate and comparator scope before evidence is
    projected. Source counts describe availability, never predictive strength.
    """
    catalog = build_scientific_catalog()
    result = build_candidate_research_assessment(
        principal=principal, catalog=catalog, current=current,
        historical_cases=historical_cases, observations=observations, cutoff=cutoff)
    science = result['supporting_details']['scientific_evidence']
    history = result['supporting_details']['historical_comparisons']
    slots = science['slots']

    def domain(*prefixes):
        selected = [deepcopy(row) for row in slots if row['field_id'].split('-')[0] in prefixes]
        return {'assessment_status': 'REQUIRES_INDEPENDENT_SCIENTIFIC_REVIEW',
                'slots': selected, 'risk_score': None,
                'predictive_weight': None, 'eligible_for_predictive_features': False}

    sources = []
    for row in slots:
        for observation in row['observations']:
            sources.append({key: deepcopy(observation[key]) for key in (
                'observation_id', 'field_id', 'source_url', 'document_id',
                'source_document_sha256', 'published_at', 'observed_at',
                'source_role', 'verification_status')})
        for observation in row['excluded_or_quarantined_observations']:
            sources.append({**deepcopy(observation), 'field_id': row['field_id']})
    summaries = science['summary']
    details = {
        'scientific_evidence': {
            **science,
            'disease_biology': {
                **domain('BIO'), 'biological_similarity_score': None,
                'biological_similarity_validated': False,
            },
        },
        'historical_comparisons': history,
        'regulatory_risk': domain('PRECEDENT'),
        'clinical_efficacy': domain('TRIAL', 'EFFICACY'),
        'safety': domain('SAFETY'),
        'manufacturing': domain('CMC'),
        'fda_designations': {
            'assessment_status': 'NOT_INDEPENDENTLY_ASSESSED',
            'comparison_fields': [deepcopy(item) for comparison in history['comparisons']
                                  for item in comparison['criteria']
                                  if item['criterion'] == 'regulatory_designations'],
            'grouped_comparison_criteria': [
                deepcopy(item) for comparison in history['comparisons']
                for item in comparison['comparison_criteria']
                if item['criterion'] == 'regulatory_pathway'],
            'designation_implies_approval': False,
        },
        'model_validation': {
            'training_status': 'NOT_COMPLETED', 'evaluation_status': 'NOT_COMPLETED',
            'calibration_status': 'NOT_VALIDATED', 'model_version': None,
            'independently_verified_decisions': 0, 'evaluated_predictions': 0,
            'measured_performance': None,
        },
        'confidence_uncertainty': {
            'prediction_confidence_grade': 'NOT_ESTABLISHED',
            'model_uncertainty': None, 'uncertainty_interval': None,
            'missing_timely_evidence_slots': summaries['missing_timely_evidence_slots'],
            'conflicted_slots': summaries['conflicted_slots'],
            'uncertainty_reasons': deepcopy(result['outstanding_requirements']),
        },
        'source_documentation': {
            'scope': 'SOURCE_REFERENCES_NOT_AUTHENTICATED_ORIGINAL_DOCUMENTS',
            'scientific_observations': sources,
            'comparison_source_references': [
                {'application_id': report['application_id'],
                 'review_cycle': report['review_cycle'],
                 'outcome_source': deepcopy(report['known_historical_outcome']),
                 'excluded_sources': deepcopy(report['excluded_sources'])}
                for report in history['comparisons']],
            'comparison_input_source_metadata': [
                {'program_id': case['program_id'], 'application_id': case['application_id'],
                 'review_cycle': case['review_cycle'],
                 'source_references': deepcopy(case['field_sources']),
                 'scope': 'AUDIT_METADATA_INCLUDES_EXCLUDED_SOURCES_NOT_MODEL_INPUTS'}
                for case in (current, *historical_cases)],
            'original_document_authentication_established': False,
            'excluded_values_withheld': True,
        },
    }
    return {
        'schema_version': 'official-prediction-output-v1',
        'program_id': result['program_id'], 'application_id': result['application_id'],
        'review_cycle': result['review_cycle'], 'evidence_cutoff': result['evidence_cutoff'],
        'heading': 'PREDICTED FDA DECISION',
        'allowed_decisions': ['PASS', 'CRL', 'EXTENSION', 'ABSTAIN'],
        'predicted_decision': 'ABSTAIN', 'prediction_readiness': 'NOT_READY',
        'prediction_validated': False,
        'evidence_readiness_grade': science['evidence_completeness_grade'],
        'evidence_grade_scope': 'TIMELY_SOURCE_AVAILABILITY_NOT_SCIENTIFIC_VALIDATION',
        'scientific_assessment_readiness_grade': 'NOT_INDEPENDENTLY_ASSESSED',
        'historical_validation_readiness_grade': 'NOT_VALIDATED',
        'prediction_confidence_grade': 'NOT_ESTABLISHED',
        'probabilities': {'PASS': None, 'CRL': None, 'EXTENSION': None},
        'architecture': {'draft_fields': catalog['defined_slots'],
                         'investigation_levels': catalog['implemented_level_count'],
                         'canonical_assessments': len(catalog['canonical_assessment_ids']),
                         'historical_comparison_criteria': history['implemented_comparison_criteria'],
                         'catalog_sha256': catalog['catalog_sha256']},
        'scoring_architecture': {
            'scientific_evidence_score': None, 'historical_comparison_score': None,
            'regulatory_risk_score': None, 'missing_data_penalty': None,
            'weighting_status': 'REQUIRES_PRESPECIFIED_TRAINED_AND_VALIDATED_MODEL',
            'conflict_policy': 'WITHHOLD_CONFLICTED_VALUES_AND_REQUIRE_INDEPENDENT_REVIEW',
            'missing_data_policy': 'KEEP_DENOMINATORS_AND_ABSTAIN',
            'availability_counts_are_predictive_scores': False,
        },
        'sections': [{'id': key, 'title': title, 'expandable': True,
                      'expanded_by_default': False, 'content': details[key]}
                     for key, title in SECTIONS],
        'outstanding_requirements': deepcopy(result['outstanding_requirements']),
        'research_only': True, 'eligible_for_validated_accuracy': False,
        'trading_authorized': False,
        'audit_scope': 'READ_ONLY_PROJECTION_NOT_PERSISTED_REVIEW_LEDGER',
    }
