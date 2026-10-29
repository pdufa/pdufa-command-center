"""Offline byte-to-case review packets. Integrity is not independent adjudication.

Only the existing registry's exact action-document URLs can be associated with
cases. No PDF text, outcome, cycle or public timestamp is inferred from a receipt.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from research.historical_decision_registry import DEFAULT_PROGRAM, build_historical_registry
from research.official_history_readiness import _clock
from research.official_sources import AVAILABLE, MAX_BYTES, official_url, validate_payload
from research.scientific_historical_verification import build_verification_worklist


def _unique_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate receipt JSON key')
        result[key] = value
    return result


def _read_local(path, root, limit):
    path = Path(path)
    # Do not follow symlinks, including parent directories, even within root.
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('symlink evidence paths are not accepted')
    if not path.resolve().is_relative_to(root):
        raise ValueError('evidence path outside authorized bundle directory')
    with path.open('rb') as handle:
        raw = handle.read(limit + 1)
    if len(raw) > limit:
        raise ValueError('evidence exceeds byte limit')
    return raw


def build_adjudication_packets(receipt_paths, *, evidence_directory):
    """Rehash originals under an explicit local root; preserve every open task.

    Paths inside receipts are resolved relative to the evidence directory unless
    absolute. Exact duplicates are collapsed, conflicting source versions retained.
    Receipt flags cannot authorize model use, authenticate origin or close review.
    """
    root = Path(evidence_directory).resolve(strict=True)
    worklist = build_verification_worklist(build_historical_registry(), program_id=DEFAULT_PROGRAM)
    packets = deepcopy(worklist['cases'])
    by_url = {p['reported_action']['source_url']: p for p in packets}
    for packet in packets:
        packet['original_document_candidates'] = []
    seen = {}
    duplicates = 0
    for receipt_path in receipt_paths:
        path = Path(receipt_path)
        if not path.is_absolute():
            path = root / path
        raw_receipt = _read_local(path, root, 1024 * 1024)
        receipt = json.loads(raw_receipt, object_pairs_hook=_unique_keys)
        if not isinstance(receipt, dict):
            raise ValueError('receipt object required')
        if (receipt.get('source') != 'fda_document'
                or receipt.get('availability') != AVAILABLE
                or receipt.get('validation_errors') != []):
            raise ValueError('successful FDA document receipt required')
        url = receipt.get('url')
        if not isinstance(url, str) or url not in by_url:
            raise ValueError('receipt does not match an exact registry action-document URL')
        official_url('fda_document', url)
        for flag in ('origin_authenticated', 'publication_timestamp_verified',
                     'independently_verified', 'historical_eligible'):
            if receipt.get(flag) is not False:
                raise ValueError('acquisition receipt cannot self-certify review')
        if receipt.get('prediction_action') != 'ABSTAIN':
            raise ValueError('acquisition must preserve abstention')
        if _clock(receipt.get('fetched_at')) is None:
            raise ValueError('aware acquisition timestamp required')
        digest = receipt.get('sha256')
        if (not isinstance(digest, str) or not re.fullmatch('[0-9a-f]{64}', digest)
                or receipt.get('snapshot_id') != digest):
            raise ValueError('exact original snapshot digest required')
        original = receipt.get('original_path')
        if not isinstance(original, str) or not original:
            raise ValueError('original path required')
        original = Path(original)
        if not original.is_absolute():
            original = root / original
        raw = _read_local(original, root, MAX_BYTES)
        if hashlib.sha256(raw).hexdigest() != digest:
            raise ValueError('original SHA-256 mismatch')
        validate_payload('fda_document', raw)
        key = (url, digest)
        receipt_digest = hashlib.sha256(raw_receipt).hexdigest()
        if key in seen:
            duplicates += 1
            # Canonical representative independent of import/list order.
            seen[key]['receipt_sha256'] = min(seen[key]['receipt_sha256'], receipt_digest)
            continue
        candidate = {
            'source_url': url, 'sha256': digest, 'byte_count': len(raw),
            'receipt_sha256': receipt_digest,
            'byte_integrity_rechecked': True,
            'origin_authenticated': False, 'source_published_at': None,
            'publication_timestamp_verified': False,
            'independently_verified': False,
        }
        seen[key] = candidate
        by_url[url]['original_document_candidates'].append(candidate)
    for packet in packets:
        candidates = packet['original_document_candidates']
        candidates.sort(key=lambda c: c['sha256'])
        packet['acquisition_status'] = ('ORIGINAL_BYTES_MISSING' if not candidates
            else 'CONFLICTING_SOURCE_VERSIONS_REQUIRE_REVIEW' if len(candidates) > 1
            else 'BYTE_INTEGRITY_ONLY_REQUIRES_INDEPENDENT_REVIEW')
        packet['adjudicated_outcome'] = None
        packet['adjudicated_review_cycle_id'] = None
    return {
        'schema_version': 'official-adjudication-packets-v1',
        'registry_snapshot_sha256': worklist['registry_snapshot_sha256'],
        'scope': 'LOCAL_BYTE_INTEGRITY_AND_REVIEW_QUEUE_NOT_SOURCE_AUTHENTICATION',
        'cases': packets, 'case_count': len(packets),
        'cases_with_retained_original_candidates': sum(bool(p['original_document_candidates']) for p in packets),
        'duplicate_document_receipts': duplicates,
        'independently_verified_decisions': 0, 'evaluated_predictions': 0,
        'operational_metrics': None, 'probabilities': None,
        'research_only': True, 'prediction_readiness': 'NOT_READY',
        'prediction_action': 'ABSTAIN',
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence-directory', type=Path, required=True)
    parser.add_argument('--receipt', type=Path, action='append', default=[])
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    result = build_adjudication_packets(args.receipt, evidence_directory=args.evidence_directory)
    content = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    with args.output.open('x', encoding='utf-8') as handle:
        handle.write(content)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
