"""Generate a dated, read-only dashboard view from the audited research queue.

No network, storage writes, prediction generation or list membership operations.
The CLI writes only the explicitly selected output artifact, or checks drift.
"""
import argparse
import json
from datetime import date
from pathlib import Path

from research.fda_verification_queue import build_verification_queue

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / 'research/evidence'
DASHBOARD_SNAPSHOT = ROOT / 'new-platform/frontend/lib/fda-holdout-reconstruction-snapshot.json'


def build_dashboard_snapshot(*, as_of: date) -> dict:
    queue = build_verification_queue(
        ROOT/'data/prediction_engine_history.csv',
        SOURCES/'2025_holdout_fda_action_evidence.json',
        reconstruction_manifest=SOURCES/'2025_holdout_predecision_reconstruction.json',
        as_of=as_of,
    )
    summary = queue['predecision_reconstruction_summary']
    if summary['validated_cases'] != 0 or any(v is not None for v in summary['metrics'].values()):
        raise ValueError('research snapshot cannot publish validated prediction metrics')
    cases = [row['predecision_reconstruction'] for row in queue['queue']
             if 'predecision_reconstruction' in row]
    return {'schemaVersion':'fda-holdout-reconstruction-view-v1', 'researchOnly':True,
            'asOf':summary['as_of'], 'historyRecords':queue['total_records'],
            'caseReports':cases, 'validatedCases':0, 'tradingAuthorized':False}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', required=True, type=date.fromisoformat)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--check', action='store_true', help='Fail if the existing artifact differs; never writes')
    args=parser.parse_args(argv)
    rendered=json.dumps(build_dashboard_snapshot(as_of=args.as_of),indent=2,ensure_ascii=False)+'\n'
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding='utf-8') != rendered:
            parser.exit(1,'Dashboard research snapshot differs from audited sources; regenerate and review.\n')
    else:
        args.output.write_text(rendered,encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
