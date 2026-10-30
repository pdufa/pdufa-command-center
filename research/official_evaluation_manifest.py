"""Reproducible chronological evaluation preparation; never fit or score a model.

Extends the existing two-partition triage with an explicit calibration boundary,
all-partition application/family isolation and retained exclusion denominators.
Inputs are proposals, not independently verified cohorts or frozen forecasts.
"""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

from research.official_history_readiness import _clock, _text
from research.official_validation import PROTOCOL_SHA256, prepare_operational_validation
from research.official_event_protocol import (
    PROTOCOL_SHA256 as EVENT_PROTOCOL_SHA256, prepare_event_target,
)

PARTITIONS = ('TRAIN', 'CALIBRATION', 'EVALUATION')


def _hash(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                             allow_nan=False).encode()).hexdigest()


def build_evaluation_manifest(records, *, calibration_starts_at, evaluation_starts_at,
                              required_fields):
    """Keep every proposed row, including invalid, duplicate and abstained rows.

    No record flags unlock independent adjudication. Calibration/evaluation rows
    never train a model here; calibration labels must precede final evaluation.
    Missing values are never imputed. Hashes identify local proposals only.
    """
    calibration = _clock(calibration_starts_at)
    evaluation = _clock(evaluation_starts_at)
    if calibration is None or evaluation is None or calibration >= evaluation:
        raise ValueError('explicit ordered aware calibration/evaluation boundaries required')
    if (not isinstance(required_fields, (list, tuple, set, frozenset))
            or not required_fields or any(not _text(f) for f in required_fields)
            or len(set(required_fields)) != len(required_fields)):
        raise ValueError('unique explicit required fields required')
    if not isinstance(records, (list, tuple)):
        raise ValueError('explicit record sequence required')
    snapshot_hash = _hash(records)  # Reject nonfinite/non-JSON input before triage.
    mapped = deepcopy(records)
    for row in mapped:
        if isinstance(row, dict) and row.get('partition') == 'CALIBRATION':
            row['partition'] = 'EVALUATION'
    # Existing TRAIN labels must be known before the earliest held-out boundary.
    triage = prepare_operational_validation(mapped,
        evaluation_starts_at=calibration_starts_at, required_fields=required_fields)
    applications, families = defaultdict(set), defaultdict(set)
    counts = Counter()
    areas = defaultdict(Counter)
    rows = []
    for index, (row, checked) in enumerate(zip(records, triage['readiness']['records'])):
        reasons = set(checked['blocking_reasons'])
        event_target = None
        partition = row.get('partition') if isinstance(row, dict) else None
        partition = partition if isinstance(partition, str) and partition in PARTITIONS else 'UNASSIGNED'
        counts[partition] += 1
        area = row.get('therapeutic_area') if isinstance(row, dict) else None
        if not _text(area):
            area = 'UNKNOWN'
            reasons.add('THERAPEUTIC_AREA_NOT_ESTABLISHED')
        areas[area][partition] += 1
        if isinstance(row, dict):
            app, family = row.get('application_id'), row.get('program_family')
            if _text(app):
                applications[app].add(partition)
            if _text(family):
                families[family.casefold()].add(partition)
            cutoff = _clock(row.get('evidence_cutoff'))
            if partition == 'CALIBRATION':
                if cutoff is None or not calibration <= cutoff < evaluation:
                    reasons.add('CALIBRATION_CUTOFF_OUTSIDE_PRESPECIFIED_WINDOW')
                label = row.get('outcome_label')
                published = _clock(label.get('source_published_at')) if isinstance(label, dict) else None
                action = _clock(label.get('decision_at')) if isinstance(label, dict) else None
                if published is None or action is None or max(published, action) >= evaluation:
                    reasons.add('CALIBRATION_LABEL_NOT_KNOWN_BEFORE_EVALUATION')
            if partition == 'EVALUATION' and (cutoff is None or cutoff < evaluation):
                reasons.add('EVALUATION_CUTOFF_BEFORE_FINAL_BOUNDARY')
            target = row.get('event_target')
            if target is not None:
                try:
                    if (not isinstance(target, dict) or set(target) != {
                            'events', 'original_target_date', 'horizon_at', 'evaluation_as_of'}):
                        raise ValueError('exact event target proposal required')
                    event_target = prepare_event_target(**target,
                        program_id=row.get('program_id'), application_id=app,
                        review_cycle_id=row.get('review_cycle_id'),
                        prediction_cutoff=row.get('evidence_cutoff'))
                    reasons.update(event_target['blocking_reasons'])
                    # Do not allow target labels to be later than the next stage,
                    # even if a separate legacy outcome_label claims an early date.
                    next_stage = calibration if partition == 'TRAIN' else evaluation if partition == 'CALIBRATION' else None
                    candidate = event_target['research_target_candidate']
                    if candidate and next_stage is not None:
                        clock = _clock(candidate['decision_label']['source_published_at'])
                        if clock >= next_stage:
                            reasons.add('EVENT_TARGET_LABEL_NOT_KNOWN_BEFORE_NEXT_PARTITION')
                    if candidate and row.get('outcome_label') != candidate['decision_label']:
                        reasons.add('OUTCOME_LABEL_DISAGREES_WITH_EVENT_TARGET')
                except (ValueError, TypeError, KeyError):
                    reasons.add('INVALID_EVENT_TARGET_PROPOSAL')
        if event_target is None:
            reasons.add('PREDICTION_TARGET_AND_HORIZON_NOT_ESTABLISHED')
        if partition == 'UNASSIGNED':
            reasons.add('EXPLICIT_PARTITION_REQUIRED')
        rows.append({'record_index': index, 'record_sha256': _hash(row),
            'partition': partition, 'therapeutic_area': area,
            'event_target_preparation': event_target,
            'blocking_reasons': reasons, 'decision': 'ABSTAIN',
            'eligible_for_training_or_evaluation': False})
    for row, report in zip(records, rows):
        if isinstance(row, dict):
            app, family = row.get('application_id'), row.get('program_family')
            if _text(app) and len(applications[app]) > 1:
                report['blocking_reasons'].add('APPLICATION_CROSSES_PARTITIONS')
            if _text(family) and len(families[family.casefold()]) > 1:
                report['blocking_reasons'].add('PROGRAM_FAMILY_CROSSES_PARTITIONS')
        report['blocking_reasons'] = sorted(report['blocking_reasons'])
    proposal = {'calibration_starts_at': calibration_starts_at,
                'evaluation_starts_at': evaluation_starts_at,
                'required_fields': sorted(required_fields)}
    report = {
        'schema_version': 'official-evaluation-manifest-v1',
        'input_snapshot_sha256': snapshot_hash,
        'engineering_protocol_sha256': PROTOCOL_SHA256,
        'event_target_protocol_sha256': EVENT_PROTOCOL_SHA256,
        'proposal': proposal, 'proposal_sha256': _hash(proposal),
        'proposal_status': 'NOT_INDEPENDENTLY_PRESPECIFIED_OR_AUTHORIZED',
        'hash_scope': 'LOCAL_COHORT_AND_PARAMETER_PROPOSALS_NOT_FROZEN_FORECASTS',
        'records': rows, 'record_count': len(rows),
        'partition_counts': {p: counts[p] for p in (*PARTITIONS, 'UNASSIGNED')},
        'therapeutic_area_partition_counts': {
            area: {p: count[p] for p in (*PARTITIONS, 'UNASSIGNED')}
            for area, count in sorted(areas.items())},
        'blocked_record_count': len(rows), 'preparation_abstention_count': len(rows),
        'preparation_abstention_scope': 'TRIAGE_ONLY_NOT_OBSERVED_FORECAST_ABSTENTION_RATE',
        'blocking_reasons': sorted(set(triage['blocking_reasons']) | {
            'MISSING_' + p + '_PARTITION' for p in PARTITIONS if not counts[p]}),
        'metrics_implementation': 'research.official_validation.synthetic_fixture_diagnostics',
        'operational_metrics': None, 'independently_verified_decisions': 0,
        'evaluated_predictions': 0, 'probabilities': None,
        'prediction_readiness': 'NOT_READY', 'prediction_action': 'ABSTAIN',
        'research_only': True,
    }
    report['manifest_sha256'] = _hash(report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--records', type=Path, required=True)
    parser.add_argument('--proposal', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    from research.official_adjudication_packets import _unique_keys
    records = json.loads(args.records.read_text(), object_pairs_hook=_unique_keys)
    proposal = json.loads(args.proposal.read_text(), object_pairs_hook=_unique_keys)
    report = build_evaluation_manifest(records, **proposal)
    content = json.dumps(report, indent=2, allow_nan=False) + '\n'
    with args.output.open('x') as handle:
        handle.write(content)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
