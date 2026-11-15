"""A genuine registry change stays REVIEW throughout research; no gate promotion."""
from copy import deepcopy
import pytest
from scripts.phase3_qualification_ledger import registry_gate_allows_research
from scripts.phase3_sponsor_rights_triage import build_queue
from scripts.phase3_rights_review_worklist import build_worklist
from scripts.phase3_rights_review_submissions import build_review_coverage
from scripts.phase3_qualification_scorecard import build_scorecard


def changed_source(source):
    source.update(census_status='RECRUITING',current_registry_status='COMPLETED',
                  status_matches_dated_census=False,phase3_in_current_registry=True)


def test_unexplained_or_forged_registry_review_does_not_bypass_source_checks():
    gates={'registry_identity':'REVIEW'}
    for source in [{},{'status_matches_dated_census':False,'phase3_in_current_registry':True},
                   {'status_matches_dated_census':'False','phase3_in_current_registry':True},
                   {'status_matches_dated_census':False,'phase3_in_current_registry':True,'census_status':'COMPLETED','current_registry_status':'COMPLETED'}]:
        assert not registry_gate_allows_research(gates,source)
    source={};changed_source(source)
    assert registry_gate_allows_research(gates,source)
    assert gates['registry_identity']=='REVIEW'
    assert not registry_gate_allows_research({'registry_identity':'PASS'},source)


def test_sponsor_queue_retains_changed_registry_as_unqualified_review():
    from test_phase3_sponsor_rights_triage import SponsorRightsTriageTests
    fixture=SponsorRightsTriageTests();fixture.setUp()
    fixture.ledger['records'][0]['gates']['registry_identity']='REVIEW'
    changed_source(fixture.registry['original_source_records'][0])
    result=build_queue(fixture.ledger,fixture.registry)
    assert result['items'][0]['registry_identity_gate']=='REVIEW'
    assert result['qualified_pipeline_total'] is None
    assert all(x['commercial_rights_verified'] is False for x in result['items'])


def test_casebook_preserves_review_without_promoting_rights():
    from test_phase3_rights_casebook import RightsCasebookTests
    fixture=RightsCasebookTests();fixture.setUp()
    fixture.ledger['records'][0]['gates']['registry_identity']='REVIEW'
    changed_source(fixture.registry['original_source_records'][0])
    result=fixture.run_build()
    assert result['rights_verified_trials']==0
    assert result['qualified_pipeline_total'] is None
    assert fixture.ledger['records'][0]['gates']['registry_identity']=='REVIEW'


def scorecard_sources():
    from test_phase3_rights_review_worklist import Phase3RightsWorklistTests
    fixture=Phase3RightsWorklistTests();fixture.setUp()
    fixture.ledger['records'][0]['gates']['registry_identity']='REVIEW'
    changed_source(fixture.registry['original_source_records'][0])
    worklist=build_worklist(fixture.registry,fixture.ledger,fixture.casebook,fixture.leads,fixture.join)
    reviewed=build_review_coverage(worklist,[])
    fixture.program['trials_with_provisional_drug_or_biologic_mentions']=sum(bool(x['provisional_drug_or_biologic_names']) for x in fixture.program['items'])
    fixture.leads['issuer_metadata_fetched']=130;fixture.leads['issuer_metadata_unavailable_or_invalid']=0
    return fixture.ledger,fixture.program,fixture.leads,fixture.pilot,worklist,reviewed


def test_changed_registry_reaches_scorecard_with_correct_unresolved_denominator():
    values=scorecard_sources();result=build_scorecard(*values)
    assert result['gate_checks_pass']==740
    assert result['gate_checks_review']==5929
    assert result['trials_by_unresolved_gate_count']['9']==1
    assert result['qualified_trial_count'] is None
    assert result['independently_verified_current_rights_trials']==0
    assert 'REGISTRY_STATUS_OR_PHASE_CHANGE_REVIEW' in result['blockers']
    assert values[0]['records'][0]['gates']['registry_identity']=='REVIEW'


def test_scorecard_rejects_forged_promotion_after_source_change_review():
    values=deepcopy(scorecard_sources())
    values[0]['records'][0]['gates']['registry_identity']='PASS'
    with pytest.raises(ValueError):build_scorecard(*values)


def test_source_change_context_cannot_be_removed_or_rebound():
    for mutate in [lambda x:x.pop('registry_review_context'),
                   lambda x:x['registry_review_context'].update(source_sha256='b'*64)]:
        values=deepcopy(scorecard_sources())
        changed=next(x for x in values[4]['items'] if x['registry_identity_gate']=='REVIEW')
        mutate(changed)
        with pytest.raises(ValueError):build_scorecard(*values)
