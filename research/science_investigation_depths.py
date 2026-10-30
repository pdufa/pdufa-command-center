"""Versioned twenty-level analytical protocol, separate from evidence certification.

Definitions describe work to perform. They neither reconstruct prior historical
semantics nor turn source leads into independent reviews or FDA probabilities.
"""
from collections.abc import Mapping
from copy import deepcopy
from datetime import date
import json
from pathlib import Path

DEPTH_CATALOG_PATH = Path(__file__).with_name('evidence')/'science_investigation_depth_catalog.json'
PROTOCOL_VERSION = 'science-investigation-depth-catalog-v1'
PROTOCOL_STATUS = 'DEFINED_RESEARCH_PROTOCOL_NOT_INDEPENDENTLY_VALIDATED'
QUESTION_IDS = tuple(f'S{i:02d}' for i in range(1,41))


def _text(value):
    return isinstance(value,str) and bool(value.strip())


def _texts(value):
    return isinstance(value,list) and bool(value) and all(_text(item) for item in value)


def _unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('duplicate investigation protocol JSON field')
        result[key]=value
    return result


def validate_depth_catalog(protocol, question_catalog):
    """Fail closed on missing levels, uncovered questions or invalid dependencies."""
    if not isinstance(question_catalog,Mapping):
        raise ValueError('existing SCIENCE question catalog required')
    questions=question_catalog.get('questions')
    if (question_catalog.get('schemaVersion')!='science-40-question-catalog-v1'
            or not isinstance(questions,list) or len(questions)!=40
            or any(not isinstance(q,Mapping) or q.get('id')!=QUESTION_IDS[i]
                   or q.get('layer')!=1+i//5 for i,q in enumerate(questions))):
        raise ValueError('existing SCIENCE question identity and layer contract required')
    if (not isinstance(protocol,Mapping) or protocol.get('schema_version')!=PROTOCOL_VERSION
            or protocol.get('protocol_status')!=PROTOCOL_STATUS
            or protocol.get('question_catalog_version')!=question_catalog['schemaVersion']
            or type(protocol.get('required_levels')) is not int or protocol['required_levels']!=20
            or protocol.get('required_question_ids')!=list(QUESTION_IDS)
            or not _texts(protocol.get('basis')) or not _text(protocol.get('scope'))):
        raise ValueError('versioned twenty-level research protocol required')
    expected_policy={'source_leads_complete_levels':False,'automatic_completion_enabled':False,
        'fixed_800_review_requirement':False,'independent_evidence_and_interpretation_required':True,
        'missing_evidence_is_unknown':True}
    policy=protocol.get('completion_policy')
    if (not isinstance(policy,Mapping) or set(policy)!=set(expected_policy)
            or any(policy[key] is not expected for key,expected in expected_policy.items())):
        raise ValueError('research protocol cannot auto-complete or certify evidence')
    levels=protocol.get('levels')
    if not isinstance(levels,list) or len(levels)!=20:
        raise ValueError('exactly twenty investigation levels required')
    coverage=set()
    for number,level in enumerate(levels,1):
        if (not isinstance(level,Mapping) or type(level.get('depth_level')) is not int
                or level['depth_level']!=number or level.get('level_id')!=f'D{number:02d}'
                or not _text(level.get('title')) or not _text(level.get('objective'))
                or not _texts(level.get('requirements')) or not _texts(level.get('completion_artifacts'))):
            raise ValueError('ordered investigation identity and concrete requirements required')
        ids=level.get('question_ids')
        if (not isinstance(ids,list) or not ids or any(not isinstance(q,str) or q not in QUESTION_IDS for q in ids)
                or len(set(ids))!=len(ids)):
            raise ValueError('unique existing SCIENCE question mappings required')
        prerequisites=level.get('prerequisite_levels')
        if (not isinstance(prerequisites,list) or any(type(p) is not int or not 1<=p<number for p in prerequisites)
                or len(set(prerequisites))!=len(prerequisites)):
            raise ValueError('investigation prerequisites must be unique earlier levels')
        coverage.update(ids)
    if coverage!=set(QUESTION_IDS):
        raise ValueError('investigation protocol must cover all forty existing SCIENCE questions')
    return deepcopy(dict(protocol))


def load_depth_catalog(question_catalog, path=DEPTH_CATALOG_PATH):
    protocol=json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_unique_object)
    return validate_depth_catalog(protocol,question_catalog)


def _day(value):
    if not isinstance(value,str) or len(value)!=10:
        raise ValueError('audited pre-cutoff research source dates required')
    try:
        parsed=date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError('audited pre-cutoff research source dates required') from exc
    if parsed.isoformat()!=value:
        raise ValueError('audited pre-cutoff research source dates required')
    return parsed


def build_depth_framework(question_catalog, sources, *, reconstruction_cutoff, protocol=None):
    """Associate audited research leads with tasks; every level stays unreviewed.

    A source can inform several tasks without constituting independent evidence.
    No reviewed/completed state is accepted through this research-only adapter.
    """
    definition=(load_depth_catalog(question_catalog) if protocol is None
                else validate_depth_catalog(protocol,question_catalog))
    cutoff=_day(reconstruction_cutoff)
    if not isinstance(sources,list):
        raise ValueError('audited source classifications required')
    candidates=[]; seen=set()
    for source in sources:
        if (not isinstance(source,Mapping) or not _text(source.get('source_id'))
                or source['source_id'] in seen or not isinstance(source.get('science_question_ids'),list)
                or any(not isinstance(q,str) or q not in QUESTION_IDS for q in source['science_question_ids'])):
            raise ValueError('unique question-linked audited sources required')
        seen.add(source['source_id'])
        if source.get('independently_reviewed') is not False or source.get('eligible_for_frozen_prediction') is not False:
            raise ValueError('research leads cannot certify independent review or frozen features')
        if source.get('classification')!='PREDECISION_RESEARCH_CANDIDATE':
            continue
        if (source.get('source_role')!='PREDECISION_RESEARCH'
                or source.get('availability_basis')!='SEC_FILING_INDEX'
                or not _text(source.get('availability_source_url'))
                or _day(source.get('available_on'))>cutoff):
            raise ValueError('outcome or unverified availability cannot satisfy investigation research leads')
        candidates.append(source)
    levels=[]
    for level in definition['levels']:
        linked=[s for s in candidates if set(s['science_question_ids']) & set(level['question_ids'])]
        observed={q for s in linked for q in s['science_question_ids']}
        levels.append({**deepcopy(level), 'status':'INDEPENDENT_REVIEW_MISSING',
            'source_lead_ids':[source['source_id'] for source in linked],
            'question_ids_with_source_leads':[q for q in level['question_ids'] if q in observed],
            'question_ids_without_source_leads':[q for q in level['question_ids'] if q not in observed],
            'independently_reviewed_question_ids':[],
            'completion_artifacts_status':'NOT_INDEPENDENTLY_ADJUDICATED',
            'blocking_prerequisite_levels':list(level['prerequisite_levels']),
            'independently_completed':False, 'ready_for_independent_certification':False})
    return {'source':'Versioned analytical research protocol grounded in the existing SCIENCE catalog and investigation domains',
        'catalog_version':definition['schema_version'], 'protocol_basis':definition['basis'],
        'protocol_scope':definition['scope'], 'semantic_level_definitions_status':definition['protocol_status'],
        'required_levels':list(range(1,21)), 'independently_reviewed_levels':[], 'levels':levels,
        'completion_policy':deepcopy(definition['completion_policy']),
        'completion_rule':'Definitions and source leads describe work; independent source-bound review and completion artifacts remain required.',
        'predictive_value_validated':False}
