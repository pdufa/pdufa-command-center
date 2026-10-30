"""Exact six-case acquisition requirements and bounded offline bundle intake.

No network requests, document authentication, independent adjudication or model
activation occurs here. Unknown official document locators remain unknown.
"""
import argparse
import csv
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile

from research.historical_decision_registry import DEFAULT_PROGRAM, build_historical_registry
from research.official_adjudication_packets import _read_local, _unique_keys
from research.official_history_readiness import _clock
from research.official_sources import MAX_BYTES, SOURCES, OfficialAdapter, official_url, validate_payload
from research.scientific_historical_comparison import COMPARISON_CRITERIA
from research.scientific_historical_verification import build_verification_worklist

FAMILY_CRITERIA = {
    'APPLICATION_ACTION_DATASET': ('indication', 'regulatory_pathway', 'prior_fda_decisions'),
    'APPROVAL_LETTER': ('indication', 'regulatory_pathway', 'prior_fda_decisions'),
    'COMPLETE_RESPONSE_LETTER': ('regulatory_pathway', 'manufacturing', 'prior_fda_decisions'),
    'ORIGINAL_TARGET_DATE': ('regulatory_pathway', 'prior_fda_decisions'),
    'FORMAL_TARGET_REVISION': ('regulatory_pathway', 'prior_fda_decisions'),
    'MULTIDISCIPLINARY_REVIEW': tuple(c[0] for c in COMPARISON_CRITERIA),
    'TRIAL_CURRENT_RECORD': ('indication', 'mechanism', 'endpoints', 'trial_design_and_statistics'),
    'TRIAL_HISTORICAL_RECORD': ('indication', 'mechanism', 'endpoints', 'efficacy', 'safety', 'trial_design_and_statistics'),
}
ENTRY_FIELDS = frozenset({'document_id', 'path', 'sha256', 'dataset_version',
                         'operator_acquired_at', 'claimed_published_at', 'publication_evidence'})


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def build_acquisition_manifest():
    worklist = build_verification_worklist(build_historical_registry(), program_id=DEFAULT_PROGRAM)
    cases = []
    for case in worklist['cases']:
        documents = []

        def add(family, source, url=None, *, suffix='', source_observation_ids=(), registry_id=None):
            documents.append({
                'document_id': case['record_id'] + ':' + family + suffix,
                'family': family, 'adapter_source': source, 'source_url': url,
                'locator_status': 'EXACT_SOURCE_LEAD_NOT_AUTHENTICATED' if url else 'OFFICIAL_LOCATOR_REQUIRES_REVIEW',
                'expected_application_id': case['application_id'],
                'expected_registry_id': registry_id,
                'comparison_criteria': list(FAMILY_CRITERIA[family]),
                'source_observation_ids': list(source_observation_ids),
                'purpose': 'OUTCOME_OR_POSTACTION_CONTEXT_NOT_AUTOMATIC_PREDICTION_FEATURE'
                    if family in ('APPROVAL_LETTER', 'COMPLETE_RESPONSE_LETTER', 'MULTIDISCIPLINARY_REVIEW')
                    else 'REQUIRES_PUBLICATION_AND_PRE_CUTOFF_REVIEW',
                'required_independent_checks': ['AUTHENTICATE_ORIGINAL_SOURCE',
                    'VERIFY_EXACT_APPLICATION_INDICATION_AND_CYCLE',
                    'VERIFY_ORIGINAL_PUBLICATION_CLOCK', 'REVIEW_CONFLICTS_AND_CUTOFF'],
                'independently_verified': False,
            })

        add('APPLICATION_ACTION_DATASET', 'drugs_fda', SOURCES['drugs_fda'][1])
        action = case['reported_action']
        family = 'COMPLETE_RESPONSE_LETTER' if action['reported_outcome'] == 'CRL' else 'APPROVAL_LETTER'
        add(family, 'fda_document', action['source_url'])
        # Additional original agency leads remain separate versions/events, never
        # replacements for the exact curated action or proof of a second cycle.
        for observation in case['observation_source_leads']:
            url = observation['source_url']
            if url != action['source_url'] and url.startswith('https://download.open.fda.gov/crl/'):
                add('COMPLETE_RESPONSE_LETTER', 'fda_document', url,
                    suffix=':' + observation['observation_id'],
                    source_observation_ids=[observation['observation_id']])
        for family in ('ORIGINAL_TARGET_DATE', 'FORMAL_TARGET_REVISION', 'MULTIDISCIPLINARY_REVIEW'):
            add(family, 'fda_document')
        trials = case['trial_source_leads']
        if not trials:
            add('TRIAL_HISTORICAL_RECORD', 'trial_history')
        for trial in trials:
            nct = trial['registry_id']
            if nct is None:
                add('TRIAL_HISTORICAL_RECORD', 'trial_history', suffix=':' + trial['trial_id'])
                continue
            # Derived API query from an existing registry identifier is a
            # requested locator, not an observed historical record or timestamp.
            add('TRIAL_CURRENT_RECORD', 'clinical_trials',
                'https://clinicaltrials.gov/api/v2/studies?filter.ids=' + nct,
                suffix=':' + nct, registry_id=nct)
            documents[-1]['locator_status'] = 'DERIVED_CURRENT_API_QUERY_NOT_OBSERVED_HISTORY'
            add('TRIAL_HISTORICAL_RECORD', 'trial_history', suffix=':' + nct, registry_id=nct)
        cases.append({
            'record_id': case['record_id'], 'application_id': case['application_id'],
            'drug': case['drug'], 'indication': case['indication'],
            'claimed_review_cycle_id': case['review_cycle_id'],
            'adjudicated_review_cycle_id': None,
            'evidence_cutoff': case['evidence_cutoff'],
            'cutoff_basis': case['cutoff_basis'],
            'original_prediction_cutoff': case['original_prediction_cutoff'],
            'documents': documents,
            'existing_observation_source_leads': deepcopy(case['observation_source_leads']),
            'trial_source_leads': deepcopy(case['trial_source_leads']),
            'verification_tasks': deepcopy(case['verification_tasks']),
            'missing_documents': deepcopy(case['missing_documents']),
            'eligible_for_training_or_evaluation': False,
        })
    report = {'schema_version': 'official-acquisition-manifest-v1',
        'registry_snapshot_sha256': worklist['registry_snapshot_sha256'],
        'hash_scope': 'LOCAL_REQUIREMENTS_NOT_SOURCE_AUTHENTICATION',
        'cases': cases, 'case_count': len(cases),
        'scientific_catalog_policy': 'EXISTING_650_DEFINITIONS_50_LEVELS_40_ASSESSMENTS_UNCHANGED',
        'source_observations_are_claims_not_verified_features': True,
        'independently_verified_decisions': 0, 'prediction_readiness': 'NOT_READY',
        'prediction_action': 'ABSTAIN', 'probabilities': None, 'research_only': True}
    return report


def _validate_entry(entry, documents, root):
    if not isinstance(entry, dict) or set(entry) != ENTRY_FIELDS:
        raise ValueError('exact offline acquisition entry schema required; no verification assertions')
    document_id = entry['document_id']
    if not isinstance(document_id, str) or document_id not in documents:
        raise ValueError('unknown exact acquisition document identifier')
    document = documents[document_id]
    if document['source_url'] is None:
        raise ValueError('official document locator requires independent resolution before import')
    official_url(document['adapter_source'], document['source_url'])
    if (not isinstance(entry['sha256'], str) or not re.fullmatch('[0-9a-f]{64}', entry['sha256'])
            or not isinstance(entry['dataset_version'], str) or not entry['dataset_version'].strip()
            or _clock(entry['operator_acquired_at']) is None):
        raise ValueError('original digest, dataset version and aware acquisition timestamp required')
    published = entry['claimed_published_at']
    proof = entry['publication_evidence']
    if published is not None and (_clock(published) is None or not isinstance(proof, str) or not proof.strip()):
        raise ValueError('claimed publication clock requires retained evidence description')
    if proof is not None and (not isinstance(proof, str) or not proof.strip()):
        raise ValueError('publication evidence must be an explicit description or null')
    if published is not None and _clock(published) > _clock(entry['operator_acquired_at']):
        raise ValueError('claimed publication cannot follow external acquisition')
    if not isinstance(entry['path'], str) or not entry['path']:
        raise ValueError('explicit local original path required')
    path = Path(entry['path'])
    if not path.is_absolute():
        path = root / path
    raw = _read_local(path, root, MAX_BYTES)
    if hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError('offline original SHA-256 mismatch')
    counts = validate_payload(document['adapter_source'], raw)
    if document['adapter_source'] == 'drugs_fda':
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            rows = csv.DictReader(io.StringIO(archive.read('Applications.txt').decode('utf-8-sig')), delimiter='\t')
            applications = {r['ApplType'].strip() + r['ApplNo'].zfill(6) for r in rows}
        if document['expected_application_id'] not in applications:
            raise ValueError('dataset does not contain exact requested application; absence is not an FDA outcome')
    if document['adapter_source'] == 'clinical_trials':
        studies = json.loads(raw, object_pairs_hook=_unique_keys)['studies']
        ids = [s['protocolSection']['identificationModule']['nctId'] for s in studies]
        if ids != [document['expected_registry_id']]:
            raise ValueError('trial payload does not match exact acquisition requirement')
    return document, raw, counts


def import_acquisition_bundle(entries, *, evidence_directory, retention_directory):
    """Preflight the entire offline batch, then retain immutable acquisition data.

    No database or production state is touched. I/O failure during retention can
    leave valid earlier receipts; it never erases/overwrites a prior audit.
    """
    if not isinstance(entries, list):
        raise ValueError('explicit offline acquisition entry list required')
    if len(entries) > 128:
        raise ValueError('offline batch exceeds 128-entry limit')
    root = Path(evidence_directory).resolve(strict=True)
    manifest = build_acquisition_manifest()
    documents = {d['document_id']: d for c in manifest['cases'] for d in c['documents']}
    checked = []
    total_bytes = 0
    for entry in entries:
        document, raw, counts = _validate_entry(entry, documents, root)
        total_bytes += len(raw)
        if total_bytes > MAX_BYTES:
            raise ValueError('aggregate offline batch exceeds byte limit')
        checked.append((entry, document, raw, counts))
    retention = Path(retention_directory)
    if any(p.is_symlink() for p in (retention, *retention.parents)):
        raise ValueError('symlink retention paths are not accepted')
    for entry, _, _, _ in checked:
        if (retention / (entry['sha256'] + '.original')).is_symlink():
            raise ValueError('symlink retained original is not accepted')
    imported = []
    seen = set()
    for entry, document, raw, counts in checked:
        provenance = {k: entry[k] for k in (
            'dataset_version', 'operator_acquired_at', 'claimed_published_at', 'publication_evidence')}
        claim_digest = _hash({'document_id': entry['document_id'],
                              'sha256': entry['sha256'], 'provenance': provenance})
        key = claim_digest
        if key in seen:
            continue
        seen.add(key)
        adapter = OfficialAdapter(document['adapter_source'])
        receipt = adapter.import_bytes(retention_directory, raw, url=document['source_url'],
            dataset_version=entry['dataset_version'], expected_sha256=entry['sha256'],
            published_at=entry['claimed_published_at'])
        receipt['acquisition_manifest_sha256'] = _hash(manifest)
        receipt['document_id'] = document['document_id']
        receipt['external_operator_provenance'] = {
            k: entry[k] for k in ('operator_acquired_at', 'claimed_published_at', 'publication_evidence')}
        adapter._audit(retention_directory, receipt)
        imported.append({'document_id': document['document_id'], 'sha256': receipt['sha256'],
            'source': receipt['source'], 'counts': counts,
            'acquisition_claim_sha256': claim_digest, 'operator_provenance': provenance,
            'origin_authenticated': False, 'publication_timestamp_verified': False,
            'independently_verified': False, 'historical_eligible': False})
    versions = {}
    for row in imported:
        versions.setdefault(row['document_id'], set()).add(row['sha256'])
    cases = []
    for case in manifest['cases']:
        rows = []
        for document in case['documents']:
            digests = sorted(versions.get(document['document_id'], ()))
            claim_count = sum(r['document_id'] == document['document_id'] for r in imported)
            rows.append({'document_id': document['document_id'], 'family': document['family'],
                'sha256_candidates': digests, 'acquisition_claim_count': claim_count,
                'status': 'MISSING' if not digests else 'CONFLICTING_VERSIONS_REQUIRE_REVIEW'
                    if len(digests) > 1 else 'MULTIPLE_PROVENANCE_CLAIMS_REQUIRE_REVIEW'
                    if claim_count > 1 else 'BYTES_RETAINED_REQUIRES_INDEPENDENT_REVIEW'})
        cases.append({'record_id': case['record_id'], 'documents': rows,
                      'eligible_for_training_or_evaluation': False})
    return {'schema_version': 'official-acquisition-import-report-v1',
        'scope': 'CURRENT_BUNDLE_ONLY_NOT_COMPLETE_RETENTION_HISTORY',
        'acquisition_manifest_sha256': _hash(manifest), 'case_count': len(cases),
        'cases': cases, 'imports': sorted(imported, key=lambda r: (r['document_id'], r['sha256'], r['acquisition_claim_sha256'])),
        'unique_document_versions_imported': sum(len(v) for v in versions.values()),
        'unique_acquisition_claims_imported': len(imported),
        'duplicate_entries': len(entries) - len(imported),
        'independently_verified_decisions': 0, 'evaluated_predictions': 0,
        'prediction_readiness': 'NOT_READY', 'prediction_action': 'ABSTAIN',
        'operational_metrics': None, 'probabilities': None, 'research_only': True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--bundle', type=Path)
    parser.add_argument('--evidence-directory', type=Path)
    parser.add_argument('--retention-directory', type=Path)
    args = parser.parse_args(argv)
    if args.bundle:
        if args.check or not args.evidence_directory or not args.retention_directory:
            parser.error('bundle import requires evidence/retention directories and cannot use --check')
        root = args.evidence_directory.resolve(strict=True)
        path = args.bundle if args.bundle.is_absolute() else root / args.bundle
        entries = json.loads(_read_local(path, root, 4 * 1024 * 1024), object_pairs_hook=_unique_keys)
        if args.output.exists():
            raise FileExistsError(args.output)
        result = import_acquisition_bundle(entries, evidence_directory=root,
                                          retention_directory=args.retention_directory)
    else:
        result = build_acquisition_manifest()
    content = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    if args.check:
        if args.output.read_text(encoding='utf-8') != content:
            parser.exit(1, 'Acquisition manifest differs from source registry.\n')
    else:
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(content)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
