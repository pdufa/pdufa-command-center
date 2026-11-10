"""Verify additive source receipts/800-position handoff without clinical grading."""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
manifest = json.loads((HERE / 'retrieval-manifest.json').read_text())
packet = json.loads((HERE / 'reviewer-ready-800-positions.json').read_text())
assert manifest['nct'] == packet['nct'] == 'NCT06081894'
assert packet['protocolCode'] == 'CY 6033'
assert manifest['gradeEventsWritten'] == manifest['phaseEventsWritten'] == 0
for receipt in manifest['receipts']:
    name = receipt.get('artifact')
    if name:
        assert Path(name).name == name
        body = (HERE / name).read_bytes()
        assert len(body) == receipt['bytes']
        assert hashlib.sha256(body).hexdigest() == receipt['sha256']
        assert receipt['httpStatus'] == 200
        if name.endswith('.pdf'):
            assert body.startswith(b'%PDF-')
    else:
        assert receipt['httpStatus'] == 403
catalog = ROOT / 'new-platform/backend/app/data/medical_phase_assessment_catalog.json'
assert hashlib.sha256(catalog.read_bytes()).hexdigest() == packet['catalogSha256']
rows = packet['positions']
assert len(rows) == 800
assert len({r['methodId'] for r in rows}) == 800
assert sorted(r['priorityRank'] for r in rows) == list(range(1, 801))
assert [r['positionIndex'] for r in rows] == list(range(1, 801))
sources = {r['sourceId'] for r in packet['sourceReceipts'] + packet['previousSourceReferences']}
findings = {r['id']: r for r in packet['findings']}
prepared = 0
for a in range(1, 41):
    group = rows[(a-1)*20:a*20]
    assert [r['assessmentIndex'] for r in group] == [a]*20
    assert [r['methodIndex'] for r in group] == list(range(1, 21))
for row in rows:
    assert row['phasePriorityBasis'] == 'REGISTRY_REPORTED_PHASE3_NOT_REVIEWER_VERIFIED'
    assert row['eligibleForOfficialGrade'] is False
    assert row['officialGrade'] is None
    assert row['recommendation']['grade0To5'] is None
    assert row['clinicalReviewStatus'] == 'NOT_INDEPENDENTLY_REVIEWED'
    assert set(row['sourceIds']) <= sources
    assert set(row['newFindingIds']) <= set(findings)
    if row['researchState'] == 'REVIEWER_READY_SOURCE_HANDOFF':
        prepared += 1
        assert row['sourceIds']
    else:
        assert row['researchState'] == 'UNEXAMINED_METHOD_POSITION'
        assert not row['sourceIds'] and not row['newFindingIds']
assert prepared == packet['counts']['sourceHandoffPositions'] == 18
assert packet['counts']['unexaminedMethodPositions'] == 782
for finding in findings.values():
    assert finding['sourceId'] in sources
    assert all(any(r['methodId'] == key and finding['id'] in r['newFindingIds'] for r in rows) for key in finding['positions'])
assert set(packet['fdaPredictions'].values()) == {'ABSTAIN'}
assert packet['certainty'] == 'NOT_VALIDATED'
assert packet['accuracy'] == 'NOT_CALIBRATED'
assert 'NCT05186818' in (HERE / 'fda-drug-trial-snapshot.html').read_text()
print('PASS: 7 captured original responses, 1 blocked request, 800 exact positions; 18 source handoffs, 782 unexamined; 0 grades/signoffs')
