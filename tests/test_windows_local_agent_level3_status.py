"""Scheduled Level 3 reports must match exactly captured, unadjudicated evidence."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from level3_focus_evidence_readiness import build_readiness
from windows_local_agent_level3_status import verify_level3_report
from windows_local_agent_live_focus_registry import make_envelope, atomic_json

NOW = datetime(2026, 11, 11, 23, 0, tzinfo=timezone.utc)
NCT = "NCT00000001"


class LevelThreeScheduledStatusTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.capture_dir = Path(temp.name)
        self.roster = {
            "schemaVersion": 1, "asOf": "2026-11-11",
            "records": [{"nct": f"NCT{i:08d}", "ticker": "TST"} for i in range(1, 30)],
        }
        self.raw = json.dumps(self.roster).encode()
        self.digest = hashlib.sha256(self.raw).hexdigest()

    def make_report(self):
        return build_readiness(self.raw, self.capture_dir, NOW)

    def put_receipt(self):
        record = {"protocolSection": {
            "identificationModule": {"nctId": NCT},
            "designModule": {"phases": ["PHASE3"]},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Endpoint"}]},
        }}
        metadata = {
            "nct": NCT,
            "source_url": "https://clinicaltrials.gov/api/v2/studies/" + NCT,
            "source_type": "PRIMARY_REGISTRY",
            "retrieved_at_utc": NOW.isoformat(),
            "sha256": "a" * 64,
            "scientific_adjudication": "NOT_ADJUDICATED",
            "fda_probability": None,
        }
        atomic_json(
            self.capture_dir / f"{NCT}.json",
            make_envelope(NCT, self.digest, record, metadata),
        )

    def test_valid_partial_unreviewed_report_can_pass(self):
        self.put_receipt()
        report = self.make_report()
        self.assertEqual(report["fresh_source_contexts"], 1)
        self.assertEqual(report["scientific_reviews_completed"], 0)
        self.assertTrue(verify_level3_report(
            report, self.raw, self.capture_dir, NOW + timedelta(seconds=20)
        ))

    def test_fake_scientific_review_or_prediction_cannot_pass(self):
        self.put_receipt()
        original = self.make_report()
        for field, value in (
            ("scientific_reviews_completed", 1),
            ("calibrated_fda_predictions_created", 29),
            ("production_modified", True),
        ):
            with self.subTest(field=field):
                report = copy.deepcopy(original)
                report[field] = value
                self.assertFalse(verify_level3_report(report, self.raw, self.capture_dir, NOW))
        changed = copy.deepcopy(original)
        changed["records"][0]["registry_evidence"]["clinical_efficacy_established"] = True
        self.assertFalse(verify_level3_report(changed, self.raw, self.capture_dir, NOW))

    def test_expired_or_future_report_never_stays_green(self):
        original = self.make_report()
        self.assertFalse(verify_level3_report(
            original, self.raw, self.capture_dir, NOW + timedelta(minutes=6)
        ))
        self.assertFalse(verify_level3_report(
            original, self.raw, self.capture_dir, NOW - timedelta(seconds=1)
        ))

    def test_different_source_snapshot_or_tampered_receipt_rejected(self):
        self.put_receipt()
        original = self.make_report()
        alternate = json.dumps({**self.roster, "asOf": "2026-11-10"}).encode()
        self.assertFalse(verify_level3_report(original, alternate, self.capture_dir, NOW))
        receipt_path = self.capture_dir / f"{NCT}.json"
        receipt = json.loads(receipt_path.read_text())
        receipt["record"]["protocolSection"]["identificationModule"]["nctId"] = "NCT00000002"
        receipt_path.write_text(json.dumps(receipt))
        self.assertFalse(verify_level3_report(original, self.raw, self.capture_dir, NOW))


if __name__ == "__main__":
    unittest.main()
