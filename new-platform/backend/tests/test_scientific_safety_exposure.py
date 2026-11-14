from copy import deepcopy
import pytest
from app.scientific_safety_exposure import exposure_contrast,assess_level_eight
from test_scientific_binary_effects import record

def measurements():
    return {'eventDefinition':'Synthetic serious event','population':'Safety treated','exposureUnit':'PERSON_YEARS',
            'eventCountModel':'INDEPENDENT_POISSON_COUNTS','treatment':{'label':'A','events':20,'personTime':100},
            'comparator':{'label':'B','events':10,'personTime':100}}

def test_rates_are_not_patient_risks_or_fda_predictions():
    result=exposure_contrast(measurements())
    assert result['arms'][0]['eventsPer100PersonTimeUnits']==20
    assert result['incidenceRateRatio']==pytest.approx(2)
    assert result['nominal95Interval']['lower']<2<result['nominal95Interval']['upper']
    assert result['clinicalSignificance']=='NOT_ASSESSED'
    assert result['fdaPrediction']=='ABSTAIN'

def test_unsupported_count_model_does_not_invent_precision():
    value=measurements();value.pop('eventCountModel')
    result=exposure_contrast(value)
    assert result['incidenceRateRatio']==pytest.approx(2)
    assert result['nominal95Interval'] is None

@pytest.mark.parametrize('change',[{'events':True},{'events':-1},{'personTime':0},{'personTime':float('nan')},{'personTime':1e-308}])
def test_bad_measurements_are_rejected(change):
    value=measurements();value['treatment'].update(change)
    assert exposure_contrast(value)['status']=='REJECTED_MEASUREMENTS'

def test_single_arm_early_phase_and_zero_comparator():
    value=measurements();value.pop('comparator')
    result=exposure_contrast(value)
    assert result['status']=='DESCRIPTIVE_UNCONTROLLED_RATE'
    assert result['incidenceRateRatio'] is None
    value=measurements();value['comparator']['events']=0
    result=exposure_contrast(value)
    assert result['incidenceRateRatio'] is None
    assert result['nominal95Interval'] is None

def test_source_provenance_cutoff_and_trial_binding():
    intake={'executionStatus':'INTAKE_ONLY','scientificValidation':'NOT_VERIFIED','fdaPrediction':'ABSTAIN',
            'assessmentCutoff':'2026-02-01','phase':'PHASE1','trialStatus':'COMPLETED'}
    evidence=record();evidence['measurements']=measurements()
    def assess(value):return assess_level_eight(intake,trial_id='NCT00000001',evidence={'8.exposureAdjustedRates':value})
    result=assess(evidence)
    assert result['calculations']['exposureAdjustedRates']['incidenceRateRatio']==pytest.approx(2)
    assert result['score'] is None
    for change in [{'nctId':'NCT00000002'},{'sourceRetrievedAt':'2026-03-01'},{'sourceVerified':False},{'conflict':True}]:
        value=deepcopy(evidence);value.update(change)
        assert not assess(value)['calculations']


def test_prerecruitment_safety_outcomes_are_not_required_as_missing_documents():
    intake={'executionStatus':'INTAKE_ONLY','scientificValidation':'NOT_VERIFIED','fdaPrediction':'ABSTAIN',
            'assessmentCutoff':'2026-02-01','phase':'PHASE1','trialStatus':'NOT_YET_RECRUITING'}
    result=assess_level_eight(intake,trial_id='NCT00000001')
    assert result['criteria']['exposureAdjustedRates']=='NOT_YET_EXPECTED'
    assert result['criteria']['safetyAscertainment']=='NOT_ASSESSED'
    assert result['score'] is None
