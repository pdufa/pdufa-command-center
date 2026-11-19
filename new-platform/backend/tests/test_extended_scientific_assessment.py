from datetime import date
from types import SimpleNamespace

import pytest

from app.extended_scientific_assessment import assess_extended_science
from test_scientific_trial_assessment import revise, source


def run(level, frozen=None, cutoff=None):
    request = SimpleNamespace(
        nct='NCT04576949', level=level, cutoffDate=cutoff,
        mode='BLIND_HISTORICAL' if cutoff else 'CURRENT_EVIDENCE',
        contract='EXTENDED_7_20',
    )
    return assess_extended_science(request, frozen or source())


def checks(report):
    return {check['id']: check for check in report['checks']}


@pytest.mark.parametrize('level', range(9, 13))
def test_frozen_source_version_and_abstention_are_independent_per_level(level):
    frozen = source()
    report = run(level, frozen, date(2020, 2, 1))
    assert report['level'] == level
    assert report['engineVersion'].endswith(f'/level-{level}')
    assert report['evidence']['input_sha256'] == frozen['input_sha256']
    assert report['score']['value'] is None
    assert report['score']['status'] == 'NOT_SCORED'
    assert report['fdaPrediction']['outcome'] == 'ABSTAIN'
    assert report['fdaPrediction']['probability'] is None
    assert report['historicalAccuracyEligible'] is False


@pytest.mark.parametrize('level', range(9, 13))
def test_historical_rejects_later_capture_even_when_revision_is_older(level):
    with pytest.raises(ValueError, match='chronology|leakage'):
        run(level, source(), date(2020, 1, 1))


def test_receipt_validates_exact_identity_and_canonical_frozen_payload():
    with pytest.raises(ValueError, match='identity'):
        run(9, {**source(), 'nct_id': 'NCT00000001'})
    with pytest.raises(ValueError, match='digest'):
        run(9, {**source(), 'input_sha256': 'f' * 64})
    with pytest.raises(ValueError, match='exact official registry'):
        run(9, {**source(), 'source_url': 'https://example.org/NCT04576949'})


def test_phase_hierarchy_retains_multiple_registered_phases_and_indication():
    frozen = revise(source(), lambda doc: doc['protocolSection']['designModule'].update(phases=['PHASE2', 'PHASE3']))
    report = run(9, frozen)
    phase_finding = checks(report)['registered_phases']
    assert [row['phase'] for row in phase_finding['value']] == ['PHASE2', 'PHASE3']
    assert phase_finding['citations'][0]['raw_sha256'] == frozen['raw_sha256']
    assert checks(report)['confirmatory_role']['state'] == 'UNVERIFIED'
    assert report['context']['pivotal'] is None
    assert report['observations'][0]['indicationQuestions'][0]['domain'] == 'tobacco cessation'


def test_unknown_phase_blocks_all_downstream_inference():
    frozen = revise(source(), lambda doc: doc['protocolSection']['designModule'].update(phases=['NA']))
    result = run(10, frozen)
    assert result['executionStatus'] == 'BLOCKED_UNVERIFIED_PHASE'
    assert checks(result)['phase_first']['state'] == 'UNVERIFIED'
    assert result['observations'] == []


def test_early_ongoing_trial_abstains_without_requiring_later_readout():
    def ongoing(doc):
        doc['protocolSection']['designModule']['phases'] = ['PHASE1']
        doc['protocolSection']['statusModule']['overallStatus'] = 'RECRUITING'
        doc['resultsSection'] = {}
        doc['originalDocuments'] = []

    frozen = revise(source(), ongoing)
    for level, check in [(10, 'primary_efficacy_readout'), (11, 'reported_adverse_events'), (12, 'reported_primary_analyses')]:
        report = run(level, frozen)
        assert checks(report)[check]['state'] == 'NOT_YET_EXPECTED'
        assert report['evidenceStatus'] == 'NOT_YET_EXPECTED'


def test_efficacy_preserves_descriptive_effect_and_keeps_meaningfulness_unresolved():
    def reconcile(doc):
        doc['protocolSection']['outcomesModule']['primaryOutcomes'][0]['measure'] = ' synthetic  SMOKING abstinence '

    report = run(10, revise(source(), reconcile))
    endpoint = report['observations'][0]['endpointEvaluations'][0]
    assert endpoint['calculatedContrasts'][0]['absoluteDifferencePercentagePoints'] == 20
    assert endpoint['calculatedContrasts'][0]['confidenceInterval'] is None
    assert checks(report)['endpoint_label_window_reconciliation']['state'] == 'CHECKED'
    assert checks(report)['clinically_meaningful_effect']['state'] == 'UNVERIFIED'


def test_mismatched_label_or_window_does_not_establish_endpoint_reconciliation():
    report = run(10)
    assert checks(report)['endpoint_label_window_reconciliation']['state'] == 'UNVERIFIED'


def test_efficacy_preserves_conflicting_result_group_names_without_calculation():
    def duplicate(doc):
        endpoint = doc['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]
        endpoint['groups'].append({'id': 'active', 'title': 'Different active arm'})

    report = run(10, revise(source(), duplicate))
    endpoint = report['observations'][0]['endpointEvaluations'][0]
    assert len(endpoint['groups']) == 3
    assert endpoint['calculatedContrasts'] == []
    assert checks(report)['result_group_identity']['state'] == 'CONFLICTING'


def test_safety_conflicting_counts_do_not_produce_rates_and_zero_is_preserved():
    def add_safety(doc):
        doc['resultsSection']['adverseEventsModule'] = {
            'timeFrame': '12 weeks',
            'eventGroups': [
                {'id': 'G1', 'title': 'Active', 'seriousNumAffected': '2', 'seriousNumAtRisk': 10,
                 'deathsNumAffected': 0, 'deathsNumAtRisk': 10},
                {'id': 'G2', 'title': 'Control', 'seriousNumAffected': 9, 'seriousNumAtRisk': 8,
                 'deathsNumAffected': 0, 'deathsNumAtRisk': 0},
            ],
        }

    report = run(11, revise(source(), add_safety))
    rows = report['observations'][0]['groupProportions']
    assert { (row['groupId'], row['category']): row['observedProportion'] for row in rows } == {
        ('G1', 'seriousAdverseEvents'): 0.2,
        ('G1', 'allCauseMortality'): 0.0,
        ('G2', 'seriousAdverseEvents'): None,
        ('G2', 'allCauseMortality'): None,
    }
    assert report['evidenceStatus'] == 'CONFLICTING'
    assert checks(report)['clinical_safety_conclusion']['state'] == 'UNVERIFIED'


def test_statistics_exposes_interval_conflict_and_does_not_validate_prespecification():
    def conflicting(doc):
        doc['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]['analyses'][0]['ciLowerLimit'] = '5'

    report = run(12, revise(source(), conflicting))
    rows = checks(report)
    assert rows['reported_interval_consistency']['state'] == 'CONFLICTING'
    assert rows['type_one_error_control']['state'] == 'DOCUMENT_REPORTED'
    assert rows['type_one_error_control']['citations'][0]['raw_sha256'] == 'b' * 64
    assert rows['prespecification_and_execution']['state'] == 'UNVERIFIED'


@pytest.mark.parametrize('changes, status', [
    ({'ciNumSides': 'ONE_SIDED', 'ciUpperLimit': None}, 'CHECKED'),
    ({'ciNumSides': 'TWO_SIDED', 'ciUpperLimit': None}, 'CONFLICTING'),
    ({'ciPctValue': 'nonnumeric'}, 'CONFLICTING'),
])
def test_statistics_checks_one_sided_bounds_and_reported_level(changes, status):
    def change_interval(doc):
        doc['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]['analyses'][0].update(changes)

    report = run(12, revise(source(), change_interval))
    assert checks(report)['reported_interval_consistency']['state'] == status


def test_statistics_excludes_late_sap_and_embedded_outcome_key():
    def late(doc):
        doc['originalDocuments'][1]['capturedAt'] = '2020-02-02T12:00:00Z'
        doc['resultsSection']['outcomeMeasuresModule']['outcomeMeasures'][0]['analyses'][0]['actualFdaOutcome'] = 'masked clinical answer'

    report = run(12, revise(source(), late), date(2020, 2, 1))
    assert checks(report)['type_one_error_control']['state'] == 'UNVERIFIED'
    assert report['rejectedEvidence'][0]['state'] == 'REJECTED_EVIDENCE'
    assert 'masked clinical answer' not in str(report)
