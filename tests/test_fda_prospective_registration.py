"""Synthetic registration checks; no actual trial forecast or FDA accuracy."""
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pytest

from research.fda_prospective_registration import (
    COHORT_SCHEMA, POLICY, REQUIRED_ROLES, audit_registration, build_registration,
    main, write_registration,
)

NOW = datetime(2030, 1, 2, 12, tzinfo=timezone.utc)


def fixture():
    spec = {
        'application_id':'NDA999999', 'review_cycle':1,
        'indication':'Synthetic fixture only; no actual trial',
        'program_family':'SYNTHETIC-REGISTRATION', 'ticker':'TEST',
        'target_date':'2030-02-01', 'evidence_cutoff_at':'2030-01-01T23:00:00Z',
        'horizon_at':'2030-02-01T23:59:59Z', 'event_policy':dict(POLICY),
        'model_version':None, 'model_training_cutoff_at':None,
    }
    cohort = {'schema_version':COHORT_SCHEMA, 'selection_rule':'Synthetic prespecified screening fixture',
        'members':[{'application_id':'NDA999999', 'review_cycle':1, 'target_date':'2030-02-01',
                    'disposition':'INCLUDED', 'exclusion_reason':None},
                   {'application_id':'NDA999998', 'review_cycle':1, 'target_date':'2030-02-02',
                    'disposition':'EXCLUDED', 'exclusion_reason':'Synthetic duplicate-program exclusion'}]}
    artifacts = {'features':b'fictional features', 'evidence':b'fictional evidence',
                 'protocol':b'fictional prespecified methodology', 'cohort':json.dumps(cohort).encode()}
    return spec, artifacts


def build():
    spec, artifacts = fixture()
    return build_registration(spec, artifacts, registered_at=NOW), artifacts


def test_bundle_hashes_actual_bytes_and_freezes_denominator_without_claiming_timing_or_forecasts():
    spec, artifacts = fixture()
    before = deepcopy(spec)
    result = build_registration(spec, artifacts, registered_at=NOW)
    assert spec == before
    assert result['artifacts']['features']['sha256'] == hashlib.sha256(artifacts['features']).hexdigest()
    assert result['screening_cohort']['screened_count'] == 2
    assert result['screening_cohort']['included_count'] == result['screening_cohort']['excluded_count'] == 1
    assert result['decision_contract']['predicted_decision'] == 'ABSTAIN'
    assert result['decision_contract']['probabilities'] == {'PASS':None,'CRL':None,'EXTENSION':None}
    audit = audit_registration(result, artifacts)
    assert audit['artifact_bytes_checked'] is True
    assert audit['registration_time_independently_verified'] is False
    assert audit['outcome_unseen_independently_verified'] is False
    assert audit['eligible_for_validated_accuracy'] is audit['trading_authorized'] is False


@pytest.mark.parametrize('field,value',[
    ('fda_action_at','2030-01-01T12:00:00Z'),('actual_outcome','APPROVED'),
    ('independently_verified',True),('probabilities',{'PASS':.9,'CRL':.05,'EXTENSION':.05}),
    ('model_validated',True),('prediction','PASS'),
])
def test_caller_outcomes_certification_or_forecasts_are_not_registration_spec_fields(field,value):
    spec, artifacts = fixture();spec[field]=value
    with pytest.raises(ValueError,match='exact prospective'):build_registration(spec,artifacts,registered_at=NOW)


@pytest.mark.parametrize('time',[
    datetime(2030,1,2,12),
    '2030-01-02T12:00:00Z',
    datetime(2030,2,1,0,tzinfo=timezone.utc),
    datetime(2030,2,2,0,tzinfo=timezone.utc),
])
def test_naive_non_datetime_target_day_or_post_target_registration_rejected(time):
    spec, artifacts = fixture()
    with pytest.raises(ValueError):build_registration(spec,artifacts,registered_at=time)


@pytest.mark.parametrize('field,value',[
    ('evidence_cutoff_at','2030-01-03T00:00:00Z'),
    ('evidence_cutoff_at','2030-01-01T23:00:00'),
    ('horizon_at','2030-01-02T11:00:00Z'),
    ('horizon_at','2030-01-31T00:00:00Z'),
    ('review_cycle',True),('application_id','TNXP'),('target_date','2030-02-30'),
])
def test_invalid_identity_cutoff_or_horizon_rejected(field,value):
    spec, artifacts = fixture();spec[field]=value
    with pytest.raises(ValueError):build_registration(spec,artifacts,registered_at=NOW)


def test_missed_date_or_eventual_approval_cannot_define_an_extension():
    spec, artifacts = fixture();spec['event_policy']['extension']='ANY_DELAY_OR_NONAPPROVAL'
    with pytest.raises(ValueError,match='first formal action'):build_registration(spec,artifacts,registered_at=NOW)


def test_optional_model_requires_actual_bytes_and_prespecified_training_chronology():
    spec, artifacts = fixture();spec['model_version']='UNVALIDATED-SYNTHETIC';spec['model_training_cutoff_at']='2029-12-01T00:00:00Z'
    with pytest.raises(ValueError,match='actual model bytes'):build_registration(spec,artifacts,registered_at=NOW)
    artifacts['model']=b'fictional model artifact'
    result=build_registration(spec,artifacts,registered_at=NOW)
    assert result['model_independently_validated'] is False
    assert result['decision_contract']['model_version'] is None
    spec['model_training_cutoff_at']='2030-01-02T00:00:00Z'
    with pytest.raises(ValueError,match='training cutoff'):build_registration(spec,artifacts,registered_at=NOW)


@pytest.mark.parametrize('change',['duplicate','target_alias','missing_event','missing_reason','outcome_field','duplicate_json'])
def test_screening_denominator_requires_distinct_bound_included_identity_and_exclusion_reasons(change):
    spec, artifacts = fixture();cohort=json.loads(artifacts['cohort'])
    if change=='duplicate':cohort['members'].append(deepcopy(cohort['members'][0]))
    if change=='target_alias':
        alias=deepcopy(cohort['members'][0]);alias['target_date']='2030-03-01';cohort['members'].append(alias)
    if change=='missing_event':cohort['members']=cohort['members'][1:]
    if change=='missing_reason':cohort['members'][1]['exclusion_reason']=None
    if change=='outcome_field':cohort['members'][0]['outcome']='APPROVED'
    if change=='duplicate_json':artifacts['cohort']=b'{"schema_version":"x","schema_version":"x"}'
    else:artifacts['cohort']=json.dumps(cohort).encode()
    with pytest.raises(ValueError):build_registration(spec,artifacts,registered_at=NOW)


def test_missing_empty_or_extra_artifacts_rejected():
    for change in ('missing','empty','extra'):
        spec,artifacts=fixture()
        if change=='missing':del artifacts['protocol']
        if change=='empty':artifacts['features']=b''
        if change=='extra':artifacts['actual_outcomes']=b'APPROVED'
        with pytest.raises(ValueError):build_registration(spec,artifacts,registered_at=NOW)


def test_artifact_changes_and_prediction_tampering_fail_integrity_audit():
    result, artifacts = build()
    changed=dict(artifacts);changed['features']+=b' changed after freeze'
    with pytest.raises(ValueError,match='artifacts'):audit_registration(result,changed)
    result['decision_contract']['predicted_decision']='PASS'
    with pytest.raises(ValueError):audit_registration(result,artifacts)


@pytest.mark.parametrize('field,value',[
    ('registration_time_independently_verified',True),('outcome_unseen_independently_verified',True),
    ('trading_authorized',1),('eligible_for_validated_accuracy',True),
])
def test_local_hashes_cannot_self_certify_external_timing_or_eligibility(field,value):
    result,_=build();result[field]=value
    with pytest.raises(ValueError,match='cannot certify'):audit_registration(result)


def test_malformed_hash_edited_timestamp_and_unanchored_metadata_remain_untrusted():
    result, _ = build()
    assert audit_registration(result)['artifact_bytes_checked'] is False
    result['artifacts']['features']['sha256']='g'*64
    with pytest.raises(ValueError,match='digest'):audit_registration(result)
    result,_=build();result['registered_at']='2030-01-02T13:00:00.000000Z'
    with pytest.raises(ValueError):audit_registration(result)


def test_atomic_publication_never_overwrites_a_manifest_or_original_input(tmp_path):
    result,_=build();output=tmp_path/'registration.json'
    write_registration(output,result)
    original=output.read_bytes()
    with pytest.raises(FileExistsError):write_registration(output,result)
    assert output.read_bytes()==original
    assert not list(tmp_path.glob('.registration-*'))
    with pytest.raises(ValueError,match='replace'):write_registration(output,result,input_paths=[output])


def test_failed_atomic_publication_removes_temporary_file(tmp_path,monkeypatch):
    result,_=build();output=tmp_path/'registration.json'
    def fail(*_):raise OSError('simulated link failure')
    monkeypatch.setattr('research.fda_prospective_registration.os.link',fail)
    with pytest.raises(OSError,match='link failure'):write_registration(output,result)
    assert not output.exists() and not list(tmp_path.glob('.registration-*'))


def test_cli_has_no_backdate_option_and_does_not_overwrite_inputs(tmp_path):
    with pytest.raises(SystemExit):main(['--registered-at','2020-01-01T00:00:00Z'])
    spec, artifacts=fixture()
    # Future fixture permits execution-clock registration in this test without
    # registering an actual company or silently injecting a historical clock.
    spec['target_date']='2099-02-01';spec['horizon_at']='2099-02-01T23:59:59Z';spec['evidence_cutoff_at']='2000-01-01T00:00:00Z'
    cohort=json.loads(artifacts['cohort']);cohort['members'][0]['target_date']=spec['target_date'];artifacts['cohort']=json.dumps(cohort).encode()
    paths={role:tmp_path/(role+'.bin') for role in REQUIRED_ROLES}
    for role,path in paths.items():path.write_bytes(artifacts[role])
    spec_path=tmp_path/'spec.json';spec_path.write_text(json.dumps(spec))
    args=['--spec',str(spec_path)]
    for role,path in paths.items():args+=['--'+role,str(path)]
    original=paths['features'].read_bytes()
    with pytest.raises(ValueError,match='replace'):main(args+['--output',str(paths['features'])])
    assert paths['features'].read_bytes()==original
    output=tmp_path/'record.json'
    assert main(args+['--output',str(output)])==0
    record=json.loads(output.read_text())
    assert record['decision_contract']['predicted_decision']=='ABSTAIN'
    assert record['registration_time_independently_verified'] is False
    with pytest.raises(FileExistsError):main(args+['--output',str(output)])
