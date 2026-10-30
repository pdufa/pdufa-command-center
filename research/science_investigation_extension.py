"""Fifty-level research-task extension; definitions never certify investigation.

The first twenty definitions are inherited from their existing versioned
catalog. Only thirty additional definitions are stored here. Backend review
boundaries and existing question definitions are unchanged.
"""
from collections.abc import Mapping
from copy import deepcopy
import json
from pathlib import Path

from research.science_investigation_depths import (
    PROTOCOL_STATUS, PROTOCOL_VERSION, QUESTION_IDS,
    build_depth_framework, load_depth_catalog,
)

EXTENSION_PATH = Path(__file__).with_name('evidence')/'science_investigation_50_level_extension.json'
EXTENSION_VERSION = 'science-investigation-50-level-extension-v1'
_LEVEL_FIELDS = frozenset({'level_id','depth_level','title','objective','question_ids',
                          'prerequisite_levels','requirements','completion_artifacts'})
_EXTENSION_FIELDS = frozenset({'schema_version','protocol_status','extends_catalog_version',
    'question_catalog_version','inherited_levels','required_levels','required_question_ids',
    'scope','completion_policy','additional_levels'})


def _text(value):
    return isinstance(value,str) and bool(value.strip())


def _texts(value):
    return isinstance(value,list) and bool(value) and all(_text(item) for item in value)


def _unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:
            raise ValueError('duplicate fifty-level extension JSON field')
        result[key]=value
    return result


def validate_extension_catalog(extension, question_catalog):
    """Resolve the base protocol and reject incomplete or self-certifying tasks."""
    base=load_depth_catalog(question_catalog)
    if (not isinstance(extension,Mapping) or set(extension)!=_EXTENSION_FIELDS
            or extension.get('schema_version')!=EXTENSION_VERSION
            or extension.get('protocol_status')!=PROTOCOL_STATUS
            or extension.get('extends_catalog_version')!=PROTOCOL_VERSION
            or extension.get('question_catalog_version')!=question_catalog['schemaVersion']
            or type(extension.get('inherited_levels')) is not int or extension['inherited_levels']!=20
            or type(extension.get('required_levels')) is not int or extension['required_levels']!=50
            or extension.get('required_question_ids')!=list(QUESTION_IDS)
            or not _text(extension.get('scope'))):
        raise ValueError('versioned fifty-level research extension of the existing twenty levels required')
    policy=extension.get('completion_policy')
    if (not isinstance(policy,Mapping) or set(policy)!=set(base['completion_policy'])
            or any(policy[key] is not value for key,value in base['completion_policy'].items())):
        raise ValueError('extension cannot auto-complete or independently certify research')
    levels=extension.get('additional_levels')
    if not isinstance(levels,list) or len(levels)!=30:
        raise ValueError('exactly thirty additional investigation definitions required')
    coverage=set()
    titles={level['title'] for level in base['levels']}
    objectives={level['objective'] for level in base['levels']}
    for number,level in enumerate(levels,21):
        if (not isinstance(level,Mapping) or set(level)!=_LEVEL_FIELDS
                or type(level.get('depth_level')) is not int or level['depth_level']!=number
                or level.get('level_id')!=f'D{number:02d}'
                or not _text(level.get('title')) or not _text(level.get('objective'))
                or not _texts(level.get('requirements')) or not _texts(level.get('completion_artifacts'))):
            raise ValueError('ordered D21-D50 task identities and concrete artifacts required')
        if level['title'] in titles or level['objective'] in objectives:
            raise ValueError('investigation tasks must have distinct titles and objectives')
        titles.add(level['title']);objectives.add(level['objective'])
        ids=level.get('question_ids')
        if (not isinstance(ids,list) or not ids
                or any(not isinstance(q,str) or q not in QUESTION_IDS for q in ids)
                or len(set(ids))!=len(ids)):
            raise ValueError('unique existing SCIENCE question mappings required')
        prerequisites=level.get('prerequisite_levels')
        if (not isinstance(prerequisites,list) or not prerequisites
                or any(type(p) is not int or not 1<=p<number for p in prerequisites)
                or len(set(prerequisites))!=len(prerequisites)):
            raise ValueError('extension prerequisites must be unique earlier levels')
        coverage.update(ids)
    if coverage!=set(QUESTION_IDS):
        raise ValueError('additional investigation tasks must cover all forty existing questions')
    return deepcopy(dict(extension))


def load_extension_catalog(question_catalog, path=EXTENSION_PATH):
    raw=json.loads(Path(path).read_text(encoding='utf-8'),object_pairs_hook=_unique_object)
    return validate_extension_catalog(raw,question_catalog)


def build_extended_investigation_framework(question_catalog, sources, reconstruction_cutoff, *, extension=None):
    """Build fifty unreviewed tasks while preserving the first twenty exactly.

    Audited pre-cutoff source leads inform task requirements. They do not prove
    source truth, SAP compliance, completed analyses, probabilities or accuracy.
    Independent evidence adjudication remains outside this research adapter.
    """
    base=build_depth_framework(question_catalog,sources,reconstruction_cutoff=reconstruction_cutoff)
    definition=(load_extension_catalog(question_catalog) if extension is None
                else validate_extension_catalog(extension,question_catalog))
    candidates=[source for source in sources
                if source.get('classification')=='PREDECISION_RESEARCH_CANDIDATE']
    additional=[]
    for level in definition['additional_levels']:
        linked=[s for s in candidates if set(s['science_question_ids']) & set(level['question_ids'])]
        observed={q for s in linked for q in s['science_question_ids']}
        additional.append({**deepcopy(level), 'status':'INDEPENDENT_REVIEW_MISSING',
            'source_lead_ids':[s['source_id'] for s in linked],
            'question_ids_with_source_leads':[q for q in level['question_ids'] if q in observed],
            'question_ids_without_source_leads':[q for q in level['question_ids'] if q not in observed],
            'independently_reviewed_question_ids':[],
            'completion_artifacts_status':'NOT_INDEPENDENTLY_ADJUDICATED',
            'blocking_prerequisite_levels':list(level['prerequisite_levels']),
            'independently_completed':False, 'ready_for_independent_certification':False})
    return {**deepcopy(base),
        'source':'Fifty-level research extension inheriting the existing twenty-level investigation protocol',
        'catalog_version':definition['schema_version'],
        'base_catalog_version':base['catalog_version'],
        'inherited_levels':list(range(1,21)),
        'protocol_scope':definition['scope'],
        'required_levels':list(range(1,51)),
        'levels':deepcopy(base['levels'])+additional,
        'completion_policy':deepcopy(definition['completion_policy']),
        'independently_completed_level_count':0,
        'legacy_backend_review_boundary_changed':False,
        'predictive_value_validated':False}
