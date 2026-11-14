"""Level 8 exposure rates. Rates are not patient risks or FDA probabilities."""
import math
from .scientific_levels_two_to_six import assess_review_contracts
VERSION='scientific-safety-exposure-v1'
DEFINITION={8:('Safety and tolerability',('safetyAscertainment','adverseEventDenominators','exposureAdjustedRates','treatmentDiscontinuations','seriousEventPatterns'))}


def exposure_contrast(measurements):
    unavailable={'status':'NOT_ASSESSED','reason':'Reviewed event definition, population, common exposure unit and positive person-time required.'}
    if not isinstance(measurements,dict) or measurements.get('exposureUnit') not in {'PERSON_YEARS','PERSON_MONTHS'}:return unavailable
    if any(not isinstance(measurements.get(k),str) or not measurements[k].strip() for k in ('eventDefinition','population')):return unavailable
    arms=[]
    for key in ('treatment','comparator'):
        group=measurements.get(key)
        if key=='comparator' and group is None:break
        if not isinstance(group,dict) or not isinstance(group.get('label'),str) or not group['label'].strip():return unavailable
        events,time=group.get('events'),group.get('personTime')
        if (type(events) is not int or not 0<=events<=2**53-1 or type(time) not in (int,float) or time>2**53-1 or not math.isfinite(time) or time<=0):
            return {'status':'REJECTED_MEASUREMENTS','reason':'Invalid event count or person-time; no exposure inferred from enrollment.'}
        rate=events/time
        if not math.isfinite(100*rate):return {'status':'REJECTED_MEASUREMENTS','reason':'Rate exceeds finite numerical range.'}
        arms.append({'label':group['label'],'events':events,'personTime':time,'eventsPer100PersonTimeUnits':100*rate})
    if len(arms)==2 and arms[0]['label']==arms[1]['label']:return {'status':'REJECTED_MEASUREMENTS','reason':'Distinct comparison groups required.'}
    ratio=None;interval=None;uncertainty='NO_SUPPORTED_COUNT_MODEL_OR_COMPARATOR'
    if len(arms)==2 and arms[1]['events']:
        if arms[0]['events']:
            delta=math.log(arms[0]['events'])-math.log(arms[0]['personTime'])-math.log(arms[1]['events'])+math.log(arms[1]['personTime'])
            if abs(delta)>650:return {'status':'REJECTED_MEASUREMENTS','reason':'Rate ratio exceeds supported numerical range.'}
            ratio=math.exp(delta)
            if measurements.get('eventCountModel')=='INDEPENDENT_POISSON_COUNTS':
                se=math.sqrt(1/arms[0]['events']+1/arms[1]['events'])
                interval={'lower':math.exp(delta-1.959963984540054*se),'upper':math.exp(delta+1.959963984540054*se)}
                uncertainty='NOMINAL_POISSON_LOG_RATE_RATIO'
        else:ratio=0.0;uncertainty='ZERO_EVENTS_NO_WALD_INTERVAL'
    elif len(arms)==2:uncertainty='UNDEFINED_ZERO_COMPARATOR_EVENTS'
    return {'status':'DESCRIPTIVE_EXPOSURE_CONTRAST_NOT_VALIDATED_ASSESSMENT' if len(arms)==2 else 'DESCRIPTIVE_UNCONTROLLED_RATE',
            'methodVersion':VERSION,'methodReference':'https://training.cochrane.org/handbook/current/chapter-06',
            'eventDefinition':measurements['eventDefinition'],'population':measurements['population'],
            'exposureUnit':measurements['exposureUnit'],'arms':arms,'incidenceRateRatio':ratio,
            'nominal95Interval':interval,'uncertaintyStatus':uncertainty,'multiplicityAdjusted':False,
            'scientificValidation':'NOT_VERIFIED','clinicalSignificance':'NOT_ASSESSED','fdaPrediction':'ABSTAIN',
            'limitations':['Event counts need not be numbers of patients with events.',
                          'Exposure, ascertainment, censoring and Poisson assumptions require source review.',
                          'Nominal intervals are not adjusted for multiplicity.',
                          'No causality, safety superiority or overall benefit-risk is inferred.']}


def assess_level_eight(level_one,*,trial_id,evidence=None):
    level_one=level_one if isinstance(level_one,dict) else {}
    evidence=evidence if isinstance(evidence,dict) else {}
    not_due=set()
    if level_one.get('trialStatus') in {'NOT_YET_RECRUITING','RECRUITING','ENROLLING_BY_INVITATION'}:
        not_due={(8,c) for c in DEFINITION[8][1] if c!='safetyAscertainment' and not (evidence or {}).get('8.'+c)}
    result=assess_review_contracts(level_one,trial_id=trial_id,evidence=evidence,definitions=DEFINITION,not_yet_expected=not_due)['8']
    result['engineVersion']=VERSION
    result['acceptanceCriteria']=['Exact trial and source chronology','Reviewed event and exposure definitions',
                                  'No exposure imputation','Explicit uncertainty assumptions; no FDA inference']
    result['calculations']={}
    accepted=result['acceptedEvidence'].get('exposureAdjustedRates')
    if accepted and accepted.get('retrievalProvenance')=='RECORDED':
        source=(evidence or {}).get('8.exposureAdjustedRates',{})
        calculation=exposure_contrast(source.get('measurements'));calculation['provenance']=accepted
        result['calculations']['exposureAdjustedRates']=calculation
    return result
