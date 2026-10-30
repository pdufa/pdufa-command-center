"""Synthetic PDF bytes exercise intake boundaries, never real FDA outcomes."""
import json

import pytest

from research.official_adjudication_packets import build_adjudication_packets, main
from research.official_sources import OfficialAdapter
from research.scientific_historical_verification import build_verification_worklist
from research.historical_decision_registry import DEFAULT_PROGRAM, build_historical_registry


def fixture(tmp_path, *, raw=b'%PDF-1.7\nSYNTHETIC TEST ONLY\n%%EOF', name='receipt.json', url=None):
    worklist = build_verification_worklist(build_historical_registry(), program_id=DEFAULT_PROGRAM)
    url = url or worklist['cases'][0]['reported_action']['source_url']
    receipt = OfficialAdapter('fda_document').import_bytes(tmp_path, raw, url=url)
    path = tmp_path / name
    path.write_text(json.dumps(receipt))
    return path, receipt


def build(tmp_path, paths=()):
    return build_adjudication_packets(paths, evidence_directory=tmp_path)


def test_missing_originals_preserve_all_six_cases_and_review_tasks(tmp_path):
    report = build(tmp_path)
    worklist = build_verification_worklist(build_historical_registry(), program_id=DEFAULT_PROGRAM)
    assert report['case_count'] == 6
    assert report['cases_with_retained_original_candidates'] == 0
    assert report['registry_snapshot_sha256'] == worklist['registry_snapshot_sha256']
    for case, original in zip(report['cases'], worklist['cases']):
        assert case['verification_tasks'] == original['verification_tasks']
        assert case['cutoff_exclusions'] == original['cutoff_exclusions']
        assert case['review_cycle_id'] == original['review_cycle_id']
        assert case['adjudicated_outcome'] is None
        assert case['adjudicated_review_cycle_id'] is None
        assert case['acquisition_status'] == 'ORIGINAL_BYTES_MISSING'
        assert not case['eligible_for_training_or_evaluation']


def test_retained_bytes_join_exact_lead_without_adjudicating_or_copying_clocks(tmp_path):
    path, receipt = fixture(tmp_path)
    receipt['source_published_at'] = '2020-01-01T00:00:00Z'
    receipt['response_headers'] = {'Last-Modified': 'Wed, 01 Jan 2020 00:00:00 GMT'}
    path.write_text(json.dumps(receipt))
    report = build(tmp_path, [path])
    candidate = report['cases'][0]['original_document_candidates'][0]
    assert candidate['sha256'] == receipt['sha256']
    assert candidate['byte_integrity_rechecked']
    assert candidate['source_published_at'] is None
    assert not candidate['origin_authenticated']
    assert report['cases_with_retained_original_candidates'] == 1
    assert report['independently_verified_decisions'] == report['evaluated_predictions'] == 0
    assert report['prediction_readiness'] == 'NOT_READY'
    assert report['prediction_action'] == 'ABSTAIN'
    assert report['probabilities'] is report['operational_metrics'] is None
    assert 'SYNTHETIC TEST ONLY' not in json.dumps(report)
    assert str(tmp_path) not in json.dumps(report)


def test_duplicate_bytes_never_count_as_additional_cases(tmp_path):
    path, _ = fixture(tmp_path)
    report = build(tmp_path, [path, path])
    assert report['duplicate_document_receipts'] == 1
    assert report['cases_with_retained_original_candidates'] == 1
    assert len(report['cases'][0]['original_document_candidates']) == 1


def test_separate_receipts_for_identical_bytes_are_order_independent(tmp_path):
    first, _ = fixture(tmp_path)
    second, _ = fixture(tmp_path, name='second.json')
    assert build(tmp_path, [first, second]) == build(tmp_path, [second, first])


def test_bounded_original_read(tmp_path, monkeypatch):
    path, _ = fixture(tmp_path)
    monkeypatch.setattr('research.official_adjudication_packets.MAX_BYTES', 5)
    with pytest.raises(ValueError, match='byte limit'):
        build(tmp_path, [path])


def test_conflicting_versions_are_preserved_in_both_orders(tmp_path):
    first, _ = fixture(tmp_path)
    second, _ = fixture(tmp_path, raw=b'%PDF-1.7\nOTHER SYNTHETIC VERSION\n%%EOF', name='second.json')
    report = build(tmp_path, [first, second])
    assert report == build(tmp_path, [second, first])
    assert len(report['cases'][0]['original_document_candidates']) == 2
    assert report['cases'][0]['acquisition_status'] == 'CONFLICTING_SOURCE_VERSIONS_REQUIRE_REVIEW'


@pytest.mark.parametrize('field,value', [
    ('url', 'https://www.accessdata.fda.gov/unrelated.pdf'),
    ('source', 'openfda_bulk'), ('availability', 'ACCESS DENIED'),
    ('validation_errors', ['SHA-256 mismatch']), ('snapshot_id', '0' * 64),
    ('sha256', 'bad'), ('fetched_at', '2020-01-01'),
    ('origin_authenticated', True), ('publication_timestamp_verified', True),
    ('independently_verified', True), ('historical_eligible', True),
    ('prediction_action', 'PASS'), ('original_path', ''),
])
def test_invalid_receipts_cannot_self_certify(tmp_path, field, value):
    path, receipt = fixture(tmp_path)
    receipt[field] = value
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        build(tmp_path, [path])


def test_original_is_rehashed_each_time(tmp_path):
    path, receipt = fixture(tmp_path)
    from pathlib import Path
    Path(receipt['original_path']).write_bytes(b'%PDF-1.7\nTAMPERED\n%%EOF')
    with pytest.raises(ValueError, match='SHA-256'):
        build(tmp_path, [path])


def test_non_pdf_rejected_even_with_matching_digest(tmp_path):
    path, receipt = fixture(tmp_path)
    import hashlib
    from pathlib import Path
    raw = b'<html>not a PDF</html>'
    Path(receipt['original_path']).write_bytes(raw)
    receipt['sha256'] = receipt['snapshot_id'] = hashlib.sha256(raw).hexdigest()
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='expected original PDF'):
        build(tmp_path, [path])


def test_receipt_and_original_paths_must_be_inside_bundle(tmp_path):
    bundle = tmp_path / 'bundle'
    bundle.mkdir()
    path, receipt = fixture(tmp_path)
    with pytest.raises(ValueError, match='outside'):
        build_adjudication_packets([path], evidence_directory=bundle)
    copy = bundle / 'receipt.json'
    copy.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='outside'):
        build_adjudication_packets([copy], evidence_directory=bundle)


def test_symlinks_rejected(tmp_path):
    path, receipt = fixture(tmp_path)
    link = tmp_path / 'link.json'
    link.symlink_to(path)
    with pytest.raises(ValueError, match='symlink'):
        build(tmp_path, [link])
    from pathlib import Path
    original = Path(receipt['original_path'])
    original_link = tmp_path / 'original-link'
    original_link.symlink_to(original)
    receipt['original_path'] = str(original_link)
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match='symlink'):
        build(tmp_path, [path])


def test_relocated_bundle_relative_paths_and_duplicate_keys(tmp_path):
    path, receipt = fixture(tmp_path)
    from pathlib import Path
    receipt['original_path'] = Path(receipt['original_path']).name
    path.write_text(json.dumps(receipt))
    assert build(tmp_path, [path.name])['cases_with_retained_original_candidates'] == 1
    path.write_text(json.dumps(receipt)[:-1] + ', "historical_eligible": true}')
    with pytest.raises(ValueError, match='duplicate'):
        build(tmp_path, [path])


def test_cli_never_overwrites_or_creates_output_after_rejected_receipt(tmp_path):
    path, receipt = fixture(tmp_path)
    output = tmp_path / 'packets.json'
    args = ['--evidence-directory', str(tmp_path), '--receipt', str(path), '--output', str(output)]
    assert main(args) == 0
    saved = output.read_bytes()
    with pytest.raises(FileExistsError):
        main(args)
    assert output.read_bytes() == saved
    output.unlink()
    receipt['independently_verified'] = True
    path.write_text(json.dumps(receipt))
    with pytest.raises(ValueError):
        main(args)
    assert not output.exists()
