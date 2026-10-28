"""Retrospective population-rule audit; neither SAP compliance nor a forecast."""
from copy import deepcopy
from pathlib import Path


AUDIT = Path(__file__).with_name('evidence')/'tnxp_resilient_population_audit.json'


def build_population_issue(record=None):
    if record is None:
        from research.fda_verification_queue import _read_json
        record=_read_json(AUDIT)
    if (not isinstance(record,dict) or record.get('schema_version')!='tnxp-resilient-population-audit-v1'
            or record.get('event_key')!='TNXP|2025-08-15' or record.get('trial_id')!='NCT05273749'
            or record.get('application_id')!='NDA219428' or record.get('protocol_id')!='TNX-CY-F307'
            or record.get('research_cutoff')!='2025-08-14' or record.get('original_prediction_cutoff') is not None):
        raise ValueError('exact TNXP RESILIENT audit identity and scope required')
    for field in ('independently_adjudicated','source_bytes_retained','eligible_for_predecision_features',
                  'eligible_for_validated_accuracy','trading_authorized'):
        if record.get(field) is not False:
            raise ValueError('population research cannot certify compliance, features or accuracy')
    if record.get('protocol_compliance_status')!='NOT_ESTABLISHED' or record.get('original_document_sha256') is not None:
        raise ValueError('final SAP compliance and original byte provenance remain unestablished')
    expected={'randomized_population':(231,226,457),'reported_efficacy_population':(231,225,456),
              'reported_safety_population':(231,226,457)}
    for field,counts in expected.items():
        row=record.get(field)
        if (not isinstance(row,dict) or any(type(row.get(k)) is not int for k in ('active','placebo','total'))
                or tuple(row[k] for k in ('active','placebo','total'))!=counts):
            raise ValueError('reported populations must preserve the exact source denominators')
    if not isinstance(record.get('sources'),list) or len(record['sources'])!=5:
        raise ValueError('source-specific population provenance required')
    expected_sources={
        'ACR-2024-SPONSOR-POSTER':('https://www.tonixpharma.com/wp-content/uploads/2024/11/ACR-2024-Poster-F307-Trial_vFinal2_10-15-2024_QRcode.pdf',None,False),
        'RESILIENT-SAP-FINAL-V1':('https://cdn.clinicaltrials.gov/large-docs/49/NCT05273749/SAP_003.pdf','2023-10-17',False),
        'RESILIENT-PROTOCOL-AMENDMENT-2':('https://cdn.clinicaltrials.gov/large-docs/49/NCT05273749/Prot_002.pdf','2023-06-15',False),
        'RESILIENT-PUBLISHED-PAPER':('https://doi.org/10.1093/pm/pnaf089','2025-07-08',False),
        'SEC-JULY9-SUPPLEMENT':('https://www.sec.gov/Archives/edgar/data/1430306/000199937125008877/ex99-02.htm','2025-07-09',True),
    }
    seen=set()
    for source in record['sources']:
        if (not isinstance(source,dict) or not all(isinstance(source.get(k),str) and source[k].strip()
                for k in ('id','url','location','finding')) or source['id'] in seen
                or source['id'] not in expected_sources):
            raise ValueError('source-specific identity, findings and availability required')
        seen.add(source['id'])
        url,printed,verified=expected_sources[source['id']]
        if (source['url']!=url or source.get('document_date')!=printed
                or source.get('public_availability_verified') is not verified):
            raise ValueError('unverified public availability cannot be promoted or source identity changed')
    if record['sources'][-1].get('availability_source_url')!='https://www.sec.gov/Archives/edgar/data/1430306/000199937125008877/0001999371-25-008877-index.htm':
        raise ValueError('exact SEC supplementary methods filing index required')
    artifacts=record.get('required_resolution_artifacts')
    if not isinstance(artifacts,list) or len(artifacts)<5 or any(not isinstance(x,str) or not x.strip() for x in artifacts):
        raise ValueError('complete unresolved compliance requirements required')
    return {**deepcopy(record),'issue_id':'RESILIENT-457-VS-456',
            'scope':'RETROSPECTIVE_PROTOCOL_COMPLIANCE_AUDIT_NOT_ORIGINAL_FORECAST',
            'arithmetic_reconciliation_status':'SPONSOR_EXPLANATION_RECORDED_NOT_INDEPENDENTLY_ADJUDICATED',
            'scientific_rationale':'Prespecified analysis populations protect randomization; an explained count difference does not establish prespecified exclusion authority.',
            'supporting_findings':[record['sponsor_explanation']],
            'contradictory_findings':[record['population_rule_observed']],
            'missing_information':deepcopy(artifacts),
            'confidence_grade':'NOT_ESTABLISHED',
            'uncertainty':'Neither compliance nor a protocol violation is established without the final dated records and all-randomized analysis.',
            'effect_on_proposed_fda_decision':'ABSTAIN_NO_CERTIFIED_PROBABILITY_EFFECT',
            'approval_probability':None}
