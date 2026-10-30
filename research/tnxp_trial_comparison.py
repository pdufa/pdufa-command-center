"""Source-bound RELIEF/RALLY/RESILIENT comparison, never FDA prediction accuracy.

The matrix preserves the current sponsor-reported record. It cannot turn a
sensitivity analysis into primary success, infer missing populations, pool
statistics, or establish independent scientific adjudication.
"""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

COMPARISON_PATH = Path(__file__).with_name('evidence')/'tnxp_three_trial_comparison.json'
SCHEMA = 'tnxp-three-trial-comparison-v1'
_SOURCE_URLS = {
    'TNXP-RALLY-RELIEF-20220321': ('https://www.sec.gov/Archives/edgar/data/1430306/000138713122003807/ex99-01.htm', '2022-03-21'),
    'TNXP-RESILIENT-EFFECT-20240610': ('https://www.sec.gov/Archives/edgar/data/1430306/000183988224018368/ex99-02.htm', '2024-06-10'),
    'TNXP-RESILIENT-DISPOSITION-2024': ('https://www.sec.gov/Archives/edgar/data/1430306/000183988224043326/ex99-03.htm', None),
}
_PROFILE = {
    'F304': {'name':'RELIEF', 'primary':('0.010','-0.4','0.16','POSITIVE'),
             'sensitivity':('0.004','-0.5',None), 'ae':('8.5','3.5'),
             'populations':(None,)*9, 'design':(None,None), 'registry_id':None},
    'F306': {'name':'RALLY', 'primary':('0.115','-0.2','0.16','FAILED'),
             'sensitivity':('0.014','-0.4','0.16'), 'ae':('15.2','6.2'),
             'populations':(514,None,None,None,None,None,None,None,None),
             'design':(36,14), 'registry_id':None},
    'F307': {'name':'RESILIENT', 'primary':('0.00005','-0.65','0.16','POSITIVE'),
             'sensitivity':None, 'ae':('6.1','3.5'),
             'populations':(457,231,226,456,231,225,457,231,226),
             'design':(33,14), 'registry_id':'NCT05273749'},
}
_POPULATION_FIELDS = ('randomized_total','randomized_active','randomized_placebo',
                      'efficacy_total','efficacy_active','efficacy_placebo',
                      'safety_total','safety_active','safety_placebo')
_TOP_FIELDS = frozenset({'schema_version','event_key','application_id','research_cutoff',
    'original_prediction_cutoff','assembled_on','research_only','sources','trials',
    'comparison_limits','required_resolution_artifacts','independently_completed_assessments',
    'independently_completed_levels','eligible_for_predecision_features',
    'eligible_for_validated_accuracy','trading_authorized'})


def _unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('duplicate TNXP comparison JSON field')
        result[key]=value
    return result


def _text(value):
    return isinstance(value,str) and bool(value.strip())


def _day(value):
    if not isinstance(value,str) or len(value)!=10:
        raise ValueError('explicit comparison date required')
    try:
        parsed=date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('explicit comparison date required') from exc
    if parsed.isoformat()!=value:
        raise ValueError('explicit comparison date required')
    return parsed


def _source_reference(value, sources, *, optional=False):
    if optional and value is None:
        return
    if not isinstance(value,str) or value not in sources:
        raise ValueError('every reported trial measure requires a known source reference')


def _sources(raw,cutoff):
    if not isinstance(raw,list) or len(raw)!=len(_SOURCE_URLS):
        raise ValueError('complete three-source comparison provenance required')
    seen={}
    for row in raw:
        if (not isinstance(row,dict) or set(row)!={'source_id','source_url','document_date','public_availability_verified','original_document_sha256','source_bytes_retained','independently_reviewed','provenance_note'} or not isinstance(row.get('source_id'),str)
                or row['source_id'] not in _SOURCE_URLS or row['source_id'] in seen):
            raise ValueError('unique canonical comparison sources required')
        url,printed = _SOURCE_URLS[row['source_id']]
        if (row.get('source_url')!=url or row.get('document_date')!=printed
                or not _text(row.get('provenance_note'))):
            raise ValueError('source identity and recorded document date cannot be replaced')
        if printed is not None and _day(printed)>cutoff:
            raise ValueError('post-cutoff document cannot enter the comparison')
        if (row.get('public_availability_verified') is not False
                or row.get('source_bytes_retained') is not False
                or row.get('independently_reviewed') is not False
                or row.get('original_document_sha256') is not None):
            raise ValueError('comparison sources remain unadjudicated with unverified availability and bytes')
        seen[row['source_id']]=row
    return seen


def _analysis(row,profile,sources,*,primary):
    fields={'analysis_role','method','endpoint','p_value',
            'placebo_adjusted_ls_mean_difference','standard_error','source_id'}
    if primary:
        fields.add('source_reported_outcome')
    if not isinstance(row,dict) or set(row)!=fields:
        raise ValueError('primary and sensitivity analysis roles must remain separate')
    if (row['analysis_role']!=('PRESPECIFIED_PRIMARY' if primary else 'SENSITIVITY_NOT_PRIMARY')
            or row['method']!=('MMRM_WITH_MULTIPLE_IMPUTATION' if primary else 'MMRM_WITHOUT_MULTIPLE_IMPUTATION')
            or row['endpoint']!='pain numeric rating score'):
        raise ValueError('primary MMRM with imputation cannot be replaced by sensitivity analysis')
    values=(row['p_value'],row['placebo_adjusted_ls_mean_difference'],row['standard_error'])
    if values!=profile[:3] or (primary and row['source_reported_outcome']!=profile[3]):
        raise ValueError('reported analysis values and primary outcomes must match the cited record')
    _source_reference(row['source_id'],sources)


def build_tnxp_trial_comparison(record=None):
    """Return a retrospective source comparison with zero certification.

    This validates the recorded matrix contract, not the scientific truth of the
    underlying publications. Missing source material remains unknown.
    """
    if record is None:
        record=json.loads(COMPARISON_PATH.read_text(encoding='utf-8'),object_pairs_hook=_unique_object)
    if (not isinstance(record,dict) or set(record)!=_TOP_FIELDS
            or record.get('schema_version')!=SCHEMA or record.get('event_key')!='TNXP|2025-08-15'
            or record.get('application_id')!='NDA219428' or record.get('research_cutoff')!='2025-08-14'
            or record.get('original_prediction_cutoff') is not None or record.get('research_only') is not True):
        raise ValueError('exact TNXP research comparison identity and scope required')
    cutoff=_day(record['research_cutoff']); assembled=_day(record.get('assembled_on'))
    if assembled!=date(2026,10,28):
        raise ValueError('retrospective assembly date cannot pretend to be an original forecast')
    for field in ('eligible_for_predecision_features','eligible_for_validated_accuracy','trading_authorized'):
        if record.get(field) is not False:
            raise ValueError('trial comparison cannot certify features, accuracy or trading')
    for field in ('independently_completed_assessments','independently_completed_levels'):
        if type(record.get(field)) is not int or record[field]!=0:
            raise ValueError('comparison must not claim independently completed investigations')
    for field in ('comparison_limits','required_resolution_artifacts'):
        if (not isinstance(record.get(field),list) or len(record[field])<5
                or any(not _text(x) for x in record[field])):
            raise ValueError('explicit comparison limits and unresolved artifacts required')
    sources=_sources(record.get('sources'),cutoff)
    trials=record.get('trials')
    if not isinstance(trials,list) or len(trials)!=3:
        raise ValueError('exact RELIEF, RALLY and RESILIENT comparison required')
    seen=set()
    for trial in trials:
        if (not isinstance(trial,dict) or set(trial)!={'trial_id','name','registry_id','primary_analysis','sensitivity_analyses','populations','design','safety','unresolved_requirements','independently_reviewed','eligible_for_frozen_prediction','assessment_status'} or trial.get('trial_id') not in _PROFILE
                or trial['trial_id'] in seen):
            raise ValueError('unique canonical trial identity required')
        seen.add(trial['trial_id']); expected=_PROFILE[trial['trial_id']]
        if trial.get('name')!=expected['name'] or trial.get('registry_id')!=expected['registry_id']:
            raise ValueError('trial name and known registry identity must match')
        if (trial.get('independently_reviewed') is not False
                or trial.get('eligible_for_frozen_prediction') is not False
                or trial.get('assessment_status')!='SOURCE_REPORTED_NOT_INDEPENDENTLY_ADJUDICATED'):
            raise ValueError('source-reported trial is not an independently completed assessment')
        _analysis(trial.get('primary_analysis'),expected['primary'],sources,primary=True)
        analysis_source=('TNXP-RESILIENT-EFFECT-20240610' if trial['trial_id']=='F307'
                         else 'TNXP-RALLY-RELIEF-20220321')
        if trial['primary_analysis']['source_id']!=analysis_source:
            raise ValueError('analysis source must match the actual cited trial record')
        sensitivity=trial.get('sensitivity_analyses')
        if not isinstance(sensitivity,list) or len(sensitivity)!=(0 if expected['sensitivity'] is None else 1):
            raise ValueError('unverified sensitivity result must remain missing')
        if sensitivity:
            _analysis(sensitivity[0],expected['sensitivity'],sources,primary=False)
            if sensitivity[0]['source_id']!=analysis_source:
                raise ValueError('sensitivity source must match the cited trial record')
        populations=trial.get('populations')
        if not isinstance(populations,dict) or set(populations)!=set(_POPULATION_FIELDS)|{'source_id','status'}:
            raise ValueError('separate population definitions required')
        for field,value in zip(_POPULATION_FIELDS,expected['populations']):
            if (populations.get(field)!=value or type(populations.get(field)) is not type(value)):
                raise ValueError('reported populations cannot be filled or silently reconciled')
        _source_reference(populations.get('source_id'),sources,optional=trial['trial_id']=='F304')
        population_source=(None if trial['trial_id']=='F304' else
            ('TNXP-RESILIENT-DISPOSITION-2024' if trial['trial_id']=='F307' else 'TNXP-RALLY-RELIEF-20220321'))
        statuses={'F304':'NOT_ESTABLISHED_FROM_CURRENT_COMPARISON_SOURCES',
            'F306':'SOURCE_REPORTED_PARTIAL_POPULATION_DEFINITION',
            'F307':'SOURCE_REPORTED_EXCLUSION_COMPLIANCE_NOT_ESTABLISHED'}
        if populations['source_id']!=population_source or populations['status']!=statuses[trial['trial_id']]:
            raise ValueError('population source and uncertainty status must remain bound')
        design=trial.get('design')
        if (not isinstance(design,dict) or set(design)!={'sites','duration_weeks','source_id'}
                or any(design.get(k)!=v or type(design.get(k)) is not type(v)
                       for k,v in zip(('sites','duration_weeks'),expected['design']))):
            raise ValueError('unknown trial design values must remain unknown')
        _source_reference(design.get('source_id'),sources,optional=trial['trial_id']=='F304')
        if design['source_id']!=population_source:
            raise ValueError('design source must match the reported trial design')
        safety=trial.get('safety')
        if not isinstance(safety,dict) or set(safety)!={'ae_related_discontinuation_percent','source_reported_events','causality_status'} or safety.get('causality_status')!='NOT_INDEPENDENTLY_ADJUDICATED':
            raise ValueError('adverse events are not independently adjudicated drug reactions')
        rates=safety.get('ae_related_discontinuation_percent')
        if not isinstance(rates,dict) or set(rates)!={'active','placebo','source_id'} or (rates.get('active'),rates.get('placebo'))!=expected['ae']:
            raise ValueError('reported adverse-event discontinuation rates must remain separate by trial')
        _source_reference(rates.get('source_id'),sources)
        if rates['source_id']!=('TNXP-RESILIENT-DISPOSITION-2024' if trial['trial_id']=='F307' else analysis_source):
            raise ValueError('safety source must match the cited population')
        events=safety.get('source_reported_events')
        if not isinstance(events,list):
            raise ValueError('source-reported safety events required')
        for event in events:
            if (not isinstance(event,dict) or set(event)!={'finding','source_id','independently_adjudicated'} or not _text(event.get('finding'))
                    or event.get('independently_adjudicated') is not False):
                raise ValueError('sponsor event causality cannot be promoted to independent adjudication')
            _source_reference(event.get('source_id'),sources)
            if event['source_id']!=rates['source_id']:
                raise ValueError('safety narrative source must match the reported safety evidence')
        missing=trial.get('unresolved_requirements')
        if not isinstance(missing,list) or not missing or any(not _text(x) for x in missing):
            raise ValueError('trial-specific missing evidence must remain explicit')
    return {**deepcopy(record),
        'comparison_summary':{
            'primary_replication_status':'MIXED_SOURCE_REPORTED_NOT_INDEPENDENTLY_ADJUDICATED',
            'source_reported_positive_primary_trials':['F304','F307'],
            'source_reported_failed_primary_trials':['F306'],
            'rally_sensitivity_does_not_replace_primary':True,
            'within_program_comparison_is_independent_fda_cohort':False,
            'cross_trial_causal_explanation_established':False,
            'resilient_exclusion_compliance_status':'NOT_ESTABLISHED',
            'pooled_p_value':None,'pooled_effect':None,'confidence_interval':None,
            'prediction_accuracy':None,'probabilities':{'PASS':None,'CRL':None,'EXTENSION':None},
            'predicted_decision':'ABSTAIN','confidence_grade':'NOT_ESTABLISHED',
            'independently_completed_assessments':0,'independently_completed_levels':0,
            'source_count':len(sources),'trial_count':len(trials)},
        'interpretation_scope':'DESCRIPTIVE_WITHIN_PROGRAM_RESEARCH_NOT_FORECAST_OR_META_ANALYSIS'}
