import copy
import pytest
from app.scientific_population import interaction_contrast, assess_level_seven
from test_scientific_binary_effects import record


def measurements():
    return {'endpoint':'Synthetic event','population':'ITT','timeFrame':'12 weeks','subgroupsMutuallyExclusive':True,
            'subgroupA':{'label':'A','treatment':{'events':20,'total':100},'comparator':{'events':10,'total':100}},
            'subgroupB':{'label':'B','treatment':{'events':10,'total':100},'comparator':{'events':20,'total':100}}}


def test_interaction_is_ratio_of_effects_not_difference_in_significance():
    result=interaction_contrast(measurements())
    assert result['ratioOfRiskRatios']==pytest.approx(4)
    assert result['logContrastStandardError']==pytest.approx(0.5099019514)
    assert result['nominal95Interval']['lower']>1
    assert result['nominal95Interval']['upper']>4
    assert result['multiplicityAdjusted'] is False
    assert result['fdaPrediction']=='ABSTAIN'
    value=measurements();value['subgroupA'],value['subgroupB']=value['subgroupB'],value['subgroupA']
    swapped=interaction_contrast(value)
    assert swapped['ratioOfRiskRatios']==pytest.approx(.25)
    assert swapped['nominal95Interval']['upper']==pytest.approx(1/result['nominal95Interval']['lower'])


@pytest.mark.parametrize('mutation',[{'events':0},{'events':-1},{'events':True},{'events':101},{'total':0},{'total':10**100}])
def test_invalid_and_zero_subgroup_counts_never_create_precise_effects(mutation):
    value=measurements();value['subgroupA']['treatment'].update(mutation)
    result=interaction_contrast(value)
    assert 'ratioOfRiskRatios' not in result


def test_overlapping_subgroups_cannot_be_assumed_independent():
    value=measurements();value['subgroupsMutuallyExclusive']=False
    assert interaction_contrast(value)['status']=='NOT_ASSESSED'


def test_level_seven_uses_exact_source_review_and_cutoff():
    intake={'executionStatus':'INTAKE_ONLY','scientificValidation':'NOT_VERIFIED','fdaPrediction':'ABSTAIN',
            'assessmentCutoff':'2026-02-01','phase':'PHASE3','trialStatus':'COMPLETED'}
    evidence=record();evidence['measurements']=measurements()
    def assess(value):return assess_level_seven(intake,trial_id='NCT00000001',evidence={'7.treatmentSubgroupInteraction':value})
    result=assess(evidence)
    assert result['calculations']['treatmentSubgroupInteraction']['ratioOfRiskRatios']==pytest.approx(4)
    assert result['score'] is None
    for mutation in [{'nctId':'NCT00000002'},{'sourceRetrievedAt':'2026-03-01'},{'sourceVerified':False},{'conflict':True}]:
        value=copy.deepcopy(evidence);value.update(mutation)
        assert not assess(value)['calculations']
    blocked=assess_level_seven({**intake,'phase':None},trial_id='NCT00000001')
    assert blocked['status']=='BLOCKED_UNVERIFIED_PHASE'


def test_early_phase_does_not_require_pivotal_subgroup_results():
    intake={'executionStatus':'INTAKE_ONLY','scientificValidation':'NOT_VERIFIED','fdaPrediction':'ABSTAIN',
            'assessmentCutoff':'2026-02-01','phase':'PHASE1','trialStatus':'RECRUITING'}
    result=assess_level_seven(intake,trial_id='NCT00000001')
    assert result['criteria']['treatmentSubgroupInteraction']=='NOT_YET_EXPECTED'
    assert result['criteria']['baselineBalance']=='NOT_YET_EXPECTED'
    assert result['criteria']['populationDefinition']=='NOT_ASSESSED'
    assert not result['calculations']


def test_phase_expectations_remain_independent_across_multiple_definitions():
    from app.scientific_levels_two_to_six import assess_review_contracts
    intake={'executionStatus':'INTAKE_ONLY','scientificValidation':'NOT_VERIFIED','fdaPrediction':'ABSTAIN',
            'assessmentCutoff':'2026-02-01','phase':'PHASE1','trialStatus':'RECRUITING'}
    result=assess_review_contracts(intake,trial_id='NCT00000001',definitions={7:('Population',('subgroup',)),8:('Safety',('rates',))},not_yet_expected={(7,'subgroup'),(8,'rates')})
    assert result['7']['criteria']['subgroup']=='NOT_YET_EXPECTED'
    assert result['8']['criteria']['rates']=='NOT_YET_EXPECTED'
    assert result['7']['score'] is None and result['8']['score'] is None
