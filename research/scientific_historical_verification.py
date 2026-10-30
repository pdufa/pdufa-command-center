"""Reproducible verification worklist for registry v1, never an adjudication.

Unlike the outcome-only acquisition queue, this joins exact case identity,
trial leads, scientific gaps and cutoff exclusions. It performs no retrieval
and does not infer publication timestamps from printed document dates.
"""
from copy import deepcopy
import argparse
import hashlib
import json
from pathlib import Path

from research.historical_decision_registry import (
    DEFAULT_PROGRAM, build_historical_registry, predecision_view, validate_registry,
)


def _hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def build_verification_worklist(registry, *, program_id):
    """Bind open verification tasks to a validated, program-scoped snapshot.

    Registry v1 explicitly forbids independently adjudicated inputs, so all
    tasks remain open. This function must not become a second review gate.
    The hash covers the local registry, not original source-document bytes.
    """
    checked = validate_registry(registry, program_id=program_id)
    cases = []
    for row in sorted(checked['records'], key=lambda item: item['record_id']):
        view = predecision_view(checked, program_id=program_id, record_id=row['record_id'])
        cases.append({
            'record_id': row['record_id'], 'application_id': row['application_id'],
            'drug': row['drug'], 'indication': row['indication'],
            'program_family': row['program_family'],
            'review_cycle_id': row['review_cycle_id'],
            'reported_action': deepcopy(row['reported_action']),
            'evidence_cutoff': row['evidence_cutoff'], 'cutoff_basis': row['cutoff_basis'],
            'original_prediction_cutoff': row['original_prediction_cutoff'],
            'verification_tasks': [
                {'task': task, 'status': 'REQUIRES_INDEPENDENT_REVIEW'} for task in (
                    'AUTHENTICATE_ORIGINAL_FDA_ACTION_DOCUMENT',
                    'ADJUDICATE_DRUG_APPLICATION_INDICATION_AND_REVIEW_CYCLE',
                    'ADJUDICATE_PASS_CRL_EXTENSION_OR_UNRESOLVED',
                    'VERIFY_DECISION_DATE_WITHOUT_INVENTING_TIME',
                    'ESTABLISH_ORIGINAL_PUBLICATION_CLOCK',
                    'RETAIN_ORIGINAL_BYTES_AND_VERIFY_SHA256',
                    'VERIFY_PIVOTAL_TRIAL_IDENTITIES_AND_REGISTRY_HISTORY',
                    'RECONSTRUCT_PRE_CUTOFF_EVIDENCE_FROM_ORIGINAL_SOURCES',
                    'REVIEW_MISSING_AND_CONTRADICTORY_EVIDENCE',
                )],
            'trial_source_leads': deepcopy(row['linked_trial_metadata']),
            'observation_source_leads': deepcopy(row['observations']),
            'cutoff_admitted_research_observation_ids': [
                item['observation_id'] for item in view['source_reported_research_observations']],
            'cutoff_exclusions': deepcopy(view['excluded_observations']),
            'scientific_field_statuses': deepcopy(view['scientific_field_statuses']),
            'missing_documents': deepcopy(row['missing_documents']),
            'local_source_artifacts': deepcopy(row['source_artifacts']),
            'eligible_for_training_or_evaluation': False,
        })
    return {
        'schema_version': 'scientific-historical-verification-worklist-v1',
        'program_id': program_id, 'registry_snapshot_sha256': _hash(checked),
        'hash_scope': 'LOCAL_REGISTRY_NOT_ORIGINAL_SOURCE_BYTES',
        'research_only': True, 'cases': cases,
        'case_count': len(cases),
        'source_observation_count': sum(len(row['observation_source_leads']) for row in cases),
        'cutoff_admitted_research_observation_count': sum(
            len(row['cutoff_admitted_research_observation_ids']) for row in cases),
        'independently_verified_cases': 0, 'evaluated_predictions': 0,
        'measured_performance': None, 'prediction_readiness': 'NOT_READY',
        'prediction_action': 'ABSTAIN', 'probabilities': None,
        'audit_scope': 'REPRODUCIBLE_LOCAL_WORKLIST_NOT_EXTERNAL_TIMESTAMP_OR_REVIEW_RECEIPT',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--program-id', default=DEFAULT_PROGRAM)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args(argv)
    result = build_verification_worklist(build_historical_registry(program_id=args.program_id),
                                         program_id=args.program_id)
    content = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding='utf-8') != content:
            parser.exit(1, 'Verification worklist differs from source registry.\n')
    else:
        # Keep prior audit snapshots: explicit new paths are required.
        with args.output.open('x', encoding='utf-8') as handle:
            handle.write(content)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
