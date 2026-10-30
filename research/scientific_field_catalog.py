"""Versioned draft field architecture, separate from scientific verification.

Legacy field IDs and assessment mappings remain unchanged. New domain grouping
is a research crosswalk, not a renumbering of canonical SCIENCE layers or FS/FA.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path
import re

from research.science_investigation_extension import build_extended_investigation_framework

ROOT=Path(__file__).resolve().parents[1]
LEGACY=ROOT/'research/evidence/prediction_v1_1_field_catalog_draft.json'
QUESTIONS=ROOT/'new-platform/backend/app/science_40_question_catalog.json'
PARTS=ROOT/'research/evidence/scientific_catalog_parts'
SCHEMA='scientific-field-catalog-v1'
STATUS='DRAFT_DEFINITIONS_NOT_SCIENTIFICALLY_VALIDATED'
DOMAIN_SPECS=(
    ('BIO','Biological rationale',70),('MOA','Mechanism of action',70),
    ('TRIAL','Clinical trial design and execution',110),
    ('EFFICACY','Efficacy and statistical evidence',110),
    ('SAFETY','Safety and tolerability',100),
    ('CMC','Chemistry, manufacturing, and controls',80),
    ('PRECEDENT','Regulatory history and FDA precedent',60),
    ('VALIDATION','Independent validation and prediction uncertainty',50),
)
BASE_KEYS={'id','segment','name','definition','data_type','applicability','source','assessment_ids','mandatory','critical'}
EXTRA_KEYS={'scientific_rationale','assessment_criteria','uncertainty_handling','required_source_types'}


def read_json(path):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate scientific catalog JSON key')
            result[key]=value
        return result
    return json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite catalog JSON')))


def _texts(value):
    return isinstance(value,list) and bool(value) and all(isinstance(x,str) and x.strip() for x in value)


def _validate_definition(row, question_ids):
    if not isinstance(row,dict) or set(row) != BASE_KEYS|EXTRA_KEYS|{'mapping_status'}:
        raise ValueError('complete scientific field definition required')
    for key in ('name','definition','data_type','applicability','source','scientific_rationale'):
        if not isinstance(row[key],str) or not row[key].strip():
            raise ValueError('nonempty scientific meaning and rationale required')
    if any(re.search(r'\b(?:placeholder|TBD)\b',row[k],re.I) for k in ('name','definition')):
        raise ValueError('placeholder scientific definitions are not accepted')
    for key in ('assessment_criteria','uncertainty_handling','required_source_types'):
        if not _texts(row[key]): raise ValueError('assessment, source and uncertainty requirements required')
    ids=row['assessment_ids']
    if (not isinstance(ids,list) or not ids or any(not isinstance(x,str) or x not in question_ids for x in ids)
            or len(set(ids))!=len(ids)):
        raise ValueError('unique canonical assessment references required')
    if any(type(row[k]) is not bool for k in ('mandatory','critical')):
        raise ValueError('explicit field applicability flags required')


def build_scientific_catalog(*, legacy=None, parts=None):
    legacy=read_json(LEGACY) if legacy is None else deepcopy(legacy)
    question_catalog=read_json(QUESTIONS)
    question_ids={q['id'] for q in question_catalog['questions']}
    if len(question_ids)!=40: raise ValueError('existing forty canonical assessments required')
    if parts is None:
        parts=[read_json(PARTS/name) for name in ('bio_moa.json','trial_efficacy.json','safety_cmc.json','precedent_validation.json')]
    rows=[]
    for old in legacy['fields']:
        # These additions describe review work, never a completed assessment.
        rows.append({**deepcopy(old),
            'scientific_rationale':'Evaluate '+old['name'].lower()+' using source-bound evidence and independent interpretation.',
            'assessment_criteria':[old['definition'],'Confirm exact application, population and analysis scope before interpreting this field.'],
            'uncertainty_handling':['Missing evidence remains unknown; record contradictory findings separately.','Do not infer clinical truth or FDA probabilities from a populated value.'],
            'required_source_types':[old['source']],
            'mapping_status':'LEGACY_MAPPING_PRESERVED_REQUIRES_SCIENTIFIC_REVIEW'})
    for part in parts:
        if not isinstance(part,dict) or set(part)!={'domains'} or not isinstance(part['domains'],dict):
            raise ValueError('domain authoring fragments required')
        for domain,fields in part['domains'].items():
            if domain not in {d[0] for d in DOMAIN_SPECS} or not isinstance(fields,list):
                raise ValueError('known scientific domain and field list required')
            for field in fields:
                if not isinstance(field,dict) or field.get('segment')!=domain:
                    raise ValueError('field domain mismatch')
                rows.append({**deepcopy(field),'mapping_status':'PROPOSED_CROSSWALK_REQUIRES_SCIENTIFIC_REVIEW'})
    framework=build_extended_investigation_framework(question_catalog,[],reconstruction_cutoff='2026-10-28')
    tasks=framework['levels']
    seen=set(); names=set()
    for row in rows:
        _validate_definition(row,question_ids)
        if row['id'] in seen: raise ValueError('duplicate field identity')
        seen.add(row['id'])
        name=(row['segment'],row['name'].strip().casefold())
        if name in names: raise ValueError('duplicate field meaning/name within domain')
        names.add(name)
        row['investigation_levels']=[task['depth_level'] for task in tasks if set(task['question_ids']) & set(row['assessment_ids'])]
        row['definition_independently_validated']=False
        row['clinical_value']=None
    for code,_,count in DOMAIN_SPECS:
        if {r['id'] for r in rows if r['segment']==code}!={f'{code}-{i:03d}' for i in range(1,count+1)}:
            raise ValueError(f'{code} requires exactly {count} distinct defined IDs')
    if len(rows)!=650 or set().union(*(set(r['assessment_ids']) for r in rows))!=question_ids:
        raise ValueError('650 distinct draft definitions covering all forty canonical assessments required')
    order={code:i for i,(code,_,_) in enumerate(DOMAIN_SPECS)}
    rows.sort(key=lambda r:(order[r['segment']],r['id']))
    for task in tasks:
        linked=[r for r in rows if task['depth_level'] in r['investigation_levels']]
        task.update(input_field_ids=[r['id'] for r in linked],
            assessment_criteria=list(task['requirements']),
            source_requirements=list(task['completion_artifacts']),
            uncertainty_handling=['Explicitly separate absent, conflicting and unverified evidence.','Exclude information unavailable at the evidence cutoff; no missingness-to-outcome inference.'],
            readiness_conditions={'independent_review_required':True,'complete_source_provenance_required':True,
                'unresolved_conflicts_block_readiness':True,'automatic_completion':False})
    result={'schema_version':SCHEMA,'status':STATUS,'proposed_slots':650,
        'defined_slots':len(rows),'independently_validated_definitions':0,
        'canonical_assessment_ids':sorted(question_ids),
        'canonical_assessments':deepcopy(question_catalog['questions']),
        'legacy_field_ids':[r['id'] for r in legacy['fields']],
        'domains':[{'id':code,'name':name,'field_count':count} for code,name,count in DOMAIN_SPECS],
        'fields':rows,'investigation_levels':tasks,'implemented_level_count':50,
        'domain_grouping_scope':'PROPOSED_ORGANIZATION_PRESERVES_CANONICAL_LAYER_IDS_AND_FS_FA',
        'applicability_policy':{
            'mandatory_meaning':'Required only when scientifically applicable; the flag never establishes applicability.',
            'exemptions_require_independent_review':True,
            'missing_evidence_establishes_inapplicability':False,
            'automatic_denominator_reduction_allowed':False},
        'correlation_policy':'Related fields describe aspects of the same evidence; field counts are not independent studies, information weights or predictive strength.',
        'evidence_role_policy':'Catalog membership never authorizes predictive use. Same-case FDA actions, CRL reasons and subsequent evidence are outcome context; model evaluation metrics are evaluation context. Earlier comparator actions require their own availability gate before a different candidate cutoff.',
        'scientific_validation_status':'NOT_INDEPENDENTLY_VALIDATED',
        'prediction_readiness':'NOT_READY','predicted_decision':'ABSTAIN'}
    result['catalog_sha256']=hashlib.sha256(json.dumps(result,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()).hexdigest()
    return result


def load_scientific_catalog():
    return build_scientific_catalog()


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args(argv)
    result=build_scientific_catalog()
    if args.output:
        data=json.dumps(result,indent=2,ensure_ascii=False)+'\n'
        if args.check:
            if not args.output.is_file() or args.output.read_text()!=data:
                parser.exit(1,'Scientific architecture snapshot differs; regenerate and review.\n')
        else:args.output.write_text(data,encoding='utf-8')
    print('650 draft definitions structurally checked; 50 research levels; 0 independently validated definitions; NOT_READY / ABSTAIN')
    return 0


if __name__=='__main__': raise SystemExit(main())
