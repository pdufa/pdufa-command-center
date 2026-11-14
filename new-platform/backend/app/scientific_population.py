"""Level 7: population and subgroup validity; no composite or FDA probability.

An interaction contrast is conditional on reviewed, mutually exclusive groups.
It does not establish subgroup prespecification, multiplicity control or external
validity. Source collection alone never satisfies review criteria.
"""
import math
from .scientific_levels_two_to_six import assess_review_contracts

VERSION = 'scientific-population-v1'
DEFINITION = {7: ('Population and subgroup validity', (
    'populationDefinition', 'eligibilityApplicability', 'baselineBalance',
    'subgroupPrespecification', 'treatmentSubgroupInteraction'))}
METHOD_REFERENCE = 'https://training.cochrane.org/handbook/current/chapter-06'


def interaction_contrast(measurements):
    """Ratio of risk ratios with an unadjusted Wald interval on the log scale."""
    unavailable = {'status':'NOT_ASSESSED','reason':'Reviewed disjoint subgroup counts, common endpoint, population and time window are required.'}
    if not isinstance(measurements, dict) or measurements.get('subgroupsMutuallyExclusive') is not True:
        return unavailable
    if any(not isinstance(measurements.get(k),str) or not measurements[k].strip()
           for k in ('endpoint','population','timeFrame')):
        return unavailable
    groups=[]
    for key in ('subgroupA','subgroupB'):
        group=measurements.get(key)
        if not isinstance(group,dict) or not isinstance(group.get('label'),str) or not group['label'].strip():
            return unavailable
        counts=[]
        for arm in ('treatment','comparator'):
            value=group.get(arm)
            if not isinstance(value,dict): return unavailable
            events,total=value.get('events'),value.get('total')
            if type(events) is not int or type(total) is not int or not 0 <= events <= total <= 2**53-1 or total <= 0:
                return {'status':'REJECTED_MEASUREMENTS','reason':'Invalid exact integer subgroup counts.'}
            if events == 0:
                return {'status':'NOT_ESTIMABLE','reason':'Zero events; no continuity correction or precise interaction is imputed.'}
            counts.append((events,total))
        (a,n),(c,m)=counts
        log_rr=math.log(a/n)-math.log(c/m)
        variance=1/a-1/n+1/c-1/m
        groups.append({'label':group['label'],'logRiskRatio':log_rr,'variance':variance,
                       'treatment':group['treatment'],'comparator':group['comparator']})
    if groups[0]['label']==groups[1]['label']:
        return {'status':'REJECTED_MEASUREMENTS','reason':'Distinct subgroup labels required.'}
    delta=groups[0]['logRiskRatio']-groups[1]['logRiskRatio']
    se=math.sqrt(groups[0]['variance']+groups[1]['variance'])
    if se == 0:
        return {'status':'NOT_ESTIMABLE','reason':'Degenerate binomial variance; no precise interval is imputed.'}
    return {'status':'DESCRIPTIVE_INTERACTION_NOT_VALIDATED_ASSESSMENT',
            'methodVersion':VERSION,'methodReference':METHOD_REFERENCE,
            'endpoint':measurements['endpoint'],'population':measurements['population'],'timeFrame':measurements['timeFrame'],
            'subgroups':groups,'ratioOfRiskRatios':math.exp(delta),'logContrastStandardError':se,
            'nominal95Interval':{'lower':math.exp(delta-1.959963984540054*se),'upper':math.exp(delta+1.959963984540054*se)},
            'multiplicityAdjusted':False,'prespecification':'NOT_ESTABLISHED_BY_CALCULATION',
            'clinicalSignificance':'NOT_ASSESSED','scientificValidation':'NOT_VERIFIED','fdaPrediction':'ABSTAIN',
            'limitations':['Requires independent binomial groups; sparse/all-event data may invalidate asymptotic intervals.',
                           'A nominal interaction interval does not establish a clinically meaningful subgroup effect.',
                           'Never infer subgroup interaction from one significant and one nonsignificant within-group test.']}


def assess_level_seven(level_one, *, trial_id, evidence=None):
    level_one=level_one if isinstance(level_one,dict) else {}
    evidence=evidence if isinstance(evidence,dict) else {}
    not_due=set()
    early=level_one.get('phase') in {'EARLY_PHASE1','PHASE1'}
    incomplete=level_one.get('trialStatus') not in {'COMPLETED','TERMINATED'}
    for criterion in DEFINITION[7][1]:
        if ((early and criterion in {'subgroupPrespecification','treatmentSubgroupInteraction'}) or
                (incomplete and criterion=='baselineBalance')) and not (evidence or {}).get('7.'+criterion):
            not_due.add((7,criterion))
    result=assess_review_contracts(level_one,trial_id=trial_id,evidence=evidence,definitions=DEFINITION,not_yet_expected=not_due)['7']
    result['engineVersion']=VERSION
    result['acceptanceCriteria']=['Exact trial and eligible chronology','Source-reviewed population and subgroup definitions',
                                  'Prespecification and multiplicity considered separately','Traceable calculations; no fabricated approval model']
    result['calculations']={}
    accepted=result['acceptedEvidence'].get('treatmentSubgroupInteraction')
    if accepted and accepted.get('retrievalProvenance')=='RECORDED':
        source=(evidence or {}).get('7.treatmentSubgroupInteraction',{})
        calculation=interaction_contrast(source.get('measurements'))
        calculation['provenance']=accepted
        result['calculations']['treatmentSubgroupInteraction']=calculation
    return result
