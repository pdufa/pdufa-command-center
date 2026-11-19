"""Independent evidence analyses for Levels 9–12 from a frozen trial snapshot."""

import json
import re
from datetime import datetime, timezone

from .assessment_runtime import NCT, PHASES, clinical_context, now, sha, without_answer_features
from .scientific_trial_assessment import (
    STATUSES,
    day,
    document_evidence,
    document_finding,
    endpoint_assessment,
    finding,
    instant,
    number,
    observed,
)


VERSION = 'extended-trial-science-v1.0.0'
NAMES = {
    9: 'Phase and indication hierarchy',
    10: 'Efficacy',
    11: 'Safety',
    12: 'Statistical validity',
}
PHASE_QUESTIONS = {
    'EARLY_PHASE1': 'Characterize preliminary exposure, feasibility and acute tolerability.',
    'PHASE1': 'Review dose, exposure and tolerability before drawing efficacy conclusions.',
    'PHASE2': 'Examine dose selection, preliminary efficacy and uncertainty for later testing.',
    'PHASE3': 'Examine confirmatory design, comparator, patient benefit, harms and follow-up.',
    'PHASE4': 'Examine effectiveness and longer-term or uncommon harms in the studied setting.',
}


def _source_inputs(request, source):
    doc = json.loads(source['document_json'])
    if sha(doc) != source['input_sha256']:
        raise ValueError('Frozen extended scientific evidence digest mismatch')
    protocol = doc.get('protocolSection', {})
    if (not NCT.fullmatch(request.nct) or source.get('nct_id') != request.nct
            or protocol.get('identificationModule', {}).get('nctId') != request.nct):
        raise ValueError('Extended scientific exact-trial identity mismatch')
    if source.get('source_url') != f'https://clinicaltrials.gov/api/v2/studies/{request.nct}':
        raise ValueError('Extended scientific source URL is not the exact official registry endpoint')
    if not re.fullmatch(r'[a-f0-9]{64}', source.get('raw_sha256', '')):
        raise ValueError('Original registry digest missing')
    published = day(source['published_at'])
    captured = instant(source['captured_at'])
    cutoff = request.cutoffDate if request.mode == 'BLIND_HISTORICAL' else datetime.now(timezone.utc).date()
    if cutoff is None or not published <= captured.date() <= cutoff:
        raise ValueError('Extended scientific evidence chronology or historical leakage failure')
    if day(protocol['statusModule']['lastUpdatePostDateStruct']['date']) != published:
        raise ValueError('Registry revision does not match its source receipt')
    return without_answer_features(doc), cutoff


def _phase_hierarchy(doc, context, source, _cutoff):
    protocol = doc['protocolSection']
    design = protocol['designModule']
    eligibility = protocol['eligibilityModule']
    design_info = design.get('designInfo') or {}
    phases = [{'phase': phase, 'assessmentQuestion': PHASE_QUESTIONS[phase]} for phase in context['phases']]
    conditions = context['conditions']
    arms = protocol.get('armsInterventionsModule', {}).get('armGroups')
    return [
        observed('registered_phases', phases, 'Assess each registered phase separately. A mixed-phase designation does not establish a confirmatory or pivotal role.', 'protocolSection.designModule.phases', source),
        observed('registered_indications', conditions, 'Conditions describe the trial population. Application indication, severity and line of treatment still require source reconciliation.', 'protocolSection.conditionsModule.conditions', source),
        observed('registered_design', design.get('designInfo'), 'Allocation, masking and intervention model inform phase-specific design risks.', 'protocolSection.designModule.designInfo', source),
        observed('registered_population', eligibility, 'The eligibility criteria bound the population for interpretation.', 'protocolSection.eligibilityModule', source),
        observed('registered_comparator_arms', arms, 'Trial arms provide the registered comparator context.', 'protocolSection.armsInterventionsModule.armGroups', source),
        finding('confirmatory_role', 'UNVERIFIED' if 'PHASE3' in context['phases'] else 'NOT_APPLICABLE', 'A pivotal role requires evidence of the study’s confirmatory and application context.', 'source-linked application or protocol'),
    ], [{
        'phaseQuestions': phases,
        'indicationQuestions': context['indicationAnalysis'],
        'designRisks': [
            risk for applies, risk in (
                (design_info.get('allocation') == 'NON_RANDOMIZED', 'Evaluate confounding and selection bias in nonrandomized comparisons.'),
                (design_info.get('maskingInfo', {}).get('masking') == 'NONE', 'Evaluate performance and detection bias in unmasked comparisons.'),
                (design_info.get('interventionModel') == 'SINGLE_GROUP', 'Assess comparability with external references before attributing an effect to treatment.'),
            ) if applies
        ],
    }], []


def _results(doc):
    return doc.get('resultsSection', {}).get('outcomeMeasuresModule', {}).get('outcomeMeasures', [])


def _normalized(value):
    return ' '.join(value.casefold().split()) if isinstance(value, str) else ''


def _endpoint(row, source):
    result = endpoint_assessment(row, source)
    groups = row.get('groups', [])
    if len(groups) != len(result['groups']):
        # Duplicates and malformed identifiers are lost in the helper's key
        # index. Keep the original arms and suppress ambiguous contrasts.
        result['groups'] = groups
        result['calculatedContrasts'] = []
        result['groupIdentityStatus'] = 'CONFLICTING'
    return result


def _efficacy(doc, context, source, _cutoff):
    planned = doc['protocolSection']['outcomesModule'].get('primaryOutcomes', [])
    reported = _results(doc)
    endpoints = [_endpoint(row, source) for row in reported if row.get('type') in {'PRIMARY', 'SECONDARY', 'OTHER_PRE_SPECIFIED', 'POST_HOC'}]
    primary = [row for row in endpoints if row['endpointType'] == 'PRIMARY']
    quantitative = any(
        number(measurement.get('value')) is not None
        for row in primary for group in row['reportedMeasurements']
        for category in group.get('categories', [])
        for measurement in category.get('measurements', [])
    )
    planned_pairs = {(_normalized(row.get('measure')), _normalized(row.get('timeFrame'))) for row in planned}
    reported_pairs = {(_normalized(row['title']), _normalized(row['timeFrame'])) for row in primary}
    matched = bool(planned_pairs) and planned_pairs == reported_pairs and all(all(pair) for pair in planned_pairs)
    # Distinct endpoints can share the same label and window. Preserve them and
    # do not call a many-to-one registration reconciliation a match.
    matched = matched and len(planned_pairs) == len(planned) == len(primary)
    result_state = 'MISSING' if context['resultsExpected'] else 'NOT_YET_EXPECTED'
    checks = [
        observed('planned_primary_endpoints', planned, 'Registered endpoint definitions are retained alongside posted results.', 'protocolSection.outcomesModule.primaryOutcomes', source),
        finding('primary_efficacy_readout', 'SOURCE_REPORTED' if primary else result_state, 'Primary results retain group, denominator, time frame and observation provenance.', 'resultsSection.outcomeMeasuresModule', primary),
        finding('quantitative_primary_measurements', 'SOURCE_REPORTED' if quantitative else 'UNVERIFIED' if primary else result_state,
                'Check whether posted primary endpoints include numerical measurements. Review the population and denominator before using any estimate.',
                'resultsSection.outcomeMeasuresModule.outcomeMeasures.classes'),
        finding('endpoint_label_window_reconciliation', 'CHECKED' if matched else 'UNVERIFIED' if primary else result_state,
                'This check compares exact normalized labels and windows. Differently worded endpoints and amendment timing require review.', 'protocolSection.outcomesModule; resultsSection.outcomeMeasuresModule'),
        finding('clinically_meaningful_effect', 'UNVERIFIED' if primary else result_state, 'A clinically meaningful effect requires a sourced, population-specific threshold and adequate comparator and follow-up.', 'source-linked indication and endpoint interpretation'),
    ]
    ambiguous = [row['title'] for row in endpoints if row.get('groupIdentityStatus') == 'CONFLICTING']
    if ambiguous:
        checks.append(finding('result_group_identity', 'CONFLICTING', 'Resolve duplicate or malformed result-group identifiers before computing arm contrasts.', 'resultsSection.outcomeMeasuresModule.groups', ambiguous))
    interpretation = 'Early-phase efficacy observations can inform dose selection and design of subsequent studies.'
    if not context['earlyPhase']:
        interpretation = 'Interpret estimated effects against the comparator, follow-up, patient population and confirmatory design.'
    return checks, [{'endpointEvaluations': endpoints, 'indicationQuestions': context['indicationAnalysis'], 'interpretation': interpretation}], []


def _count(value):
    if type(value) is int and value >= 0:
        return value
    if isinstance(value, str) and re.fullmatch(r'[0-9]{1,12}', value):
        return int(value)
    return None


def _safety(doc, context, source, _cutoff):
    module = doc.get('resultsSection', {}).get('adverseEventsModule', {})
    groups = module.get('eventGroups', [])
    window = module.get('timeFrame')
    rows = []
    conflicts = []
    keys = (
        ('allCauseMortality', 'deathsNumAffected', 'deathsNumAtRisk'),
        ('seriousAdverseEvents', 'seriousNumAffected', 'seriousNumAtRisk'),
        ('otherAdverseEvents', 'otherNumAffected', 'otherNumAtRisk'),
    )
    group_ids = [group.get('id') for group in groups]
    for group in groups:
        group_id = group.get('id')
        if not group_id or group_ids.count(group_id) != 1:
            conflicts.append('Missing or duplicate safety group ID.')
            continue
        for category, numerator, denominator in keys:
            affected = _count(group.get(numerator))
            at_risk = _count(group.get(denominator))
            if numerator not in group and denominator not in group:
                continue
            consistent = affected is not None and at_risk is not None and affected <= at_risk
            if not consistent:
                conflicts.append(f'Unreconciled affected/at-risk counts for {group_id}, {category}.')
            rows.append({
                'groupId': group_id, 'groupTitle': group.get('title'), 'category': category,
                'affected': group.get(numerator), 'atRisk': group.get(denominator),
                'observedProportion': affected / at_risk if consistent and at_risk else None,
            })
    result_state = 'MISSING' if context['resultsExpected'] else 'NOT_YET_EXPECTED'
    phase_question = 'Examine dose-limiting toxicities, dose and exposure windows.'
    if not context['earlyPhase']:
        phase_question = 'Review cumulative exposure, discontinuation, severe and uncommon harms, and follow-up completeness.'
    checks = [
        observed('reported_adverse_events', module, 'Preserve deaths, serious and other events with separate groups and reporting thresholds.', 'resultsSection.adverseEventsModule', source) if module else finding('reported_adverse_events', result_state, 'No eligible registry adverse-event results were supplied.', 'resultsSection.adverseEventsModule'),
        observed('safety_observation_window', window, 'Reported risk proportions are descriptive and require comparable follow-up and ascertainment.', 'resultsSection.adverseEventsModule.timeFrame', source) if window else finding('safety_observation_window', 'UNVERIFIED' if module else result_state, 'The adverse-event observation window is unresolved.', 'resultsSection.adverseEventsModule.timeFrame'),
        finding('adverse_event_count_consistency', 'CONFLICTING' if conflicts else 'CHECKED' if rows else result_state, 'Check reported participant counts against their category-specific denominators.', 'resultsSection.adverseEventsModule.eventGroups', conflicts),
        finding('clinical_safety_conclusion', 'UNVERIFIED' if module else result_state, 'Clinical safety requires exposure, ascertainment, event attribution, comparison and follow-up review.', 'source-linked safety interpretation'),
    ]
    return checks, [{'observationWindow': window, 'groupProportions': rows, 'phaseQuestion': phase_question}], []


def _statistics(doc, context, source, cutoff):
    primary = [_endpoint(row, source) for row in _results(doc) if row.get('type') == 'PRIMARY']
    analyses = [{'endpoint': row['title'], 'citation': row['citation'], **analysis,
                 'intervalConsistency': _interval_consistency(analysis['reported'])}
                for row in primary for analysis in row['statisticalAnalyses']]
    conflicts = [row['endpoint'] for row in analyses if row['intervalConsistency'] == 'CONFLICTING']
    documents, rejected = document_evidence(doc, source, cutoff)
    methods = [
        ('estimand_and_population', r'estimand|intent.to.treat|analysis\s+(?:population|set)', 'Review the estimand, analysis population and strategies for intercurrent events.'),
        ('missingness_and_sensitivity', r'missing\s+data|multiple\s+imput|sensitivity\s+analys', 'Review missing-data assumptions and sensitivity analyses.'),
        ('type_one_error_control', r'multiplicity|family.wise|Bonferroni|Hochberg|Holm|gate.keep', 'Review the testing family, order and control of type I error.'),
    ]
    expected = context['resultsExpected'] or bool(analyses)
    result_state = 'MISSING' if expected else 'NOT_YET_EXPECTED'
    checks = [
        finding('reported_primary_analyses', 'SOURCE_REPORTED' if analyses else result_state, 'Retain reported effect estimates, interval bounds and nominal p-value statements with endpoint provenance.', 'resultsSection.outcomeMeasuresModule.analyses', analyses),
        finding('reported_interval_consistency', 'CONFLICTING' if conflicts else 'CHECKED' if analyses and all(row['intervalConsistency'] == 'CONSISTENT' for row in analyses) else 'UNVERIFIED' if analyses else result_state, 'Evaluate supplied interval bounds and whether they contain the reported estimate.', 'resultsSection.outcomeMeasuresModule.analyses', conflicts),
        *(document_finding(key, documents, 'hasSap', pattern, explanation, expected)
          for key, pattern, explanation in methods),
        finding('prespecification_and_execution', 'UNVERIFIED' if expected else 'NOT_YET_EXPECTED', 'Reconcile SAP versions, database lock, unblinding and actual execution before judging statistical validity.', 'original SAP and trial conduct chronology'),
    ]
    return checks, [{'reportedAnalyses': analyses}], rejected


def _interval_consistency(analysis):
    if analysis.get('ciLowerLimit') in (None, '') and analysis.get('ciUpperLimit') in (None, ''):
        return 'NOT_REPORTED'
    values = {key: number(analysis.get(key)) for key in ('ciLowerLimit', 'ciUpperLimit', 'paramValue', 'ciPctValue')}
    if any(analysis.get(key) not in (None, '') and value is None for key, value in values.items()):
        return 'CONFLICTING'
    low, high, estimate, coverage = values.values()
    if coverage is not None and not 0 < coverage <= 100:
        return 'CONFLICTING'
    if low is not None and high is not None and low > high:
        return 'CONFLICTING'
    if estimate is not None and (low is not None and estimate < low or high is not None and estimate > high):
        return 'CONFLICTING'
    if analysis.get('ciNumSides') == 'ONE_SIDED' and (low is None) != (high is None):
        return 'CONSISTENT'
    if low is not None and high is not None and analysis.get('ciNumSides') != 'ONE_SIDED':
        return 'CONSISTENT'
    return 'CONFLICTING'


ENGINES = {9: _phase_hierarchy, 10: _efficacy, 11: _safety, 12: _statistics}


def assess_extended_science(request, source):
    """Evaluate the requested level with independent findings and abstention."""
    engine = ENGINES[request.level]
    doc, cutoff = _source_inputs(request, source)
    context = clinical_context(doc)
    phases = context['phases']
    phase_known = bool(phases) and all(phase in PHASES and phase != 'NA' for phase in phases)
    # This contract keeps the pivotal role unresolved until confirmed by
    # protocol and application evidence.
    context['pivotal'] = None
    if not phase_known:
        context['phaseVerification'] = 'UNRESOLVED'
    phase_ok = phase_known and context['registryStatus'] in STATUSES
    if phase_ok:
        checks, observations, rejected = engine(doc, context, source, cutoff)
    else:
        checks = [finding('phase_first', 'UNVERIFIED', 'Resolve exact trial phase and status before applying phase-specific scientific methods.', 'protocolSection.designModule.phases')]
        observations, rejected = [], []
    states = {check['state'] for check in checks}
    gaps = [check['explanation'] for check in checks if check['state'] in {'MISSING', 'UNVERIFIED', 'CONFLICTING'}]
    evidence_status = 'AVAILABLE_WITH_LIMITATIONS'
    if 'CONFLICTING' in states:
        evidence_status = 'CONFLICTING'
    elif gaps or rejected:
        evidence_status = 'INSUFFICIENT'
    elif 'NOT_YET_EXPECTED' in states:
        evidence_status = 'NOT_YET_EXPECTED'
    return {
        'schemaVersion': 3,
        'kind': 'EXECUTED_EXTENDED_SCIENTIFIC_ASSESSMENT',
        'contract': request.contract,
        'nct': request.nct,
        'level': request.level,
        'name': NAMES[request.level],
        'engineVersion': f'{VERSION}/level-{request.level}',
        'mode': request.mode,
        'cutoffDate': request.cutoffDate.isoformat() if request.cutoffDate else None,
        'executedAt': now(),
        'executionStatus': 'COMPLETED_WITH_LIMITATIONS' if phase_ok else 'BLOCKED_UNVERIFIED_PHASE',
        'evidenceStatus': evidence_status,
        'scientificStatus': 'SOURCE_BOUND_ANALYSIS_NOT_VALIDATED',
        'activationStatus': 'RESEARCH_EXECUTION_ONLY',
        'ownerReviewStatus': 'OWNER_NOT_REVIEWED',
        'score': {'value': None, 'kind': 'NOT_VALIDATED', 'status': 'NOT_SCORED', 'available': 0, 'applicable': 0, 'scale': None},
        'fdaPrediction': {'outcome': 'ABSTAIN', 'probability': None, 'confidence': 'NOT_VALIDATED', 'calibration': 'NO_VALIDATED_FDA_MODEL'},
        'explanation': 'The level reports source-bound observations and unresolved requirements. No validated scoring or FDA prediction model is available.',
        'checks': checks,
        'observations': observations,
        'risks': gaps,
        'recommendations': gaps,
        'rejectedEvidence': rejected,
        'context': context,
        'limitations': ['Registry observations are sponsor-reported and retain their original provenance.', 'Historical cutoff isolation alone cannot establish genuine blindness or accuracy.'],
        'evidence': {key: source[key] for key in ('snapshot_id', 'nct_id', 'captured_at', 'published_at', 'source_url', 'raw_sha256', 'input_sha256')},
        'historicalAccuracyEligible': False,
        'savedToDatabase': True,
    }
