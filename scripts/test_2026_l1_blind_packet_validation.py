#!/usr/bin/env python3
"""Standard-library regression tests for fail-closed blind packet validation."""
import contextlib
import csv
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("validate_2026_l1_blind100_packets.py")
spec = importlib.util.spec_from_file_location("blind_validator", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class BlindPacketTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "evidence").mkdir()
        self.row = dict.fromkeys(mod.MANIFEST_COLUMNS, "")
        self.row.update(case_id="CASE-1", archive_position="1", ticker="TEST",
                        drug_or_event="Synthetic Test Drug",
                        application_identity_status="VERIFIED",
                        precutoff_evidence_status="VERIFIED",
                        blind_prediction="NOT_ISSUED",
                        prediction_lock_status="NOT_LOCKED")
        self.packet = dict(case_id="CASE-1", application_id="NDA 000001",
                           indication="synthetic indication",
                           original_pdufa_goal_date="2026-06-01",
                           evidence_cutoff="2026-05-31",
                           sources=[dict(url="https://example.org/old-study",
                                         publication_date="2026-05-01",
                                         sha256="a"*64)],
                           clinical_summary="synthetic clinical data",
                           safety_summary="synthetic safety data",
                           regulatory_summary="synthetic pre-decision data",
                           cmc_summary="synthetic CMC data")
        self.write()

    def write(self):
        with (self.root / "manifest.csv").open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=mod.MANIFEST_COLUMNS)
            w.writeheader()
            w.writerow(self.row)
        (self.root / "evidence" / "CASE-1.json").write_text(json.dumps(self.packet))

    def verify(self):
        with contextlib.redirect_stdout(io.StringIO()):
            mod.validate(self.root, 1)

    def test_one_case_valid(self):
        self.verify()

    def test_batch_size_mismatch_fails(self):
        with self.assertRaises(SystemExit):
            mod.validate(self.root, 20)

    def test_unverified_identity_fails(self):
        self.row["application_identity_status"] = "UNVERIFIED"
        self.write()
        with self.assertRaises(SystemExit):
            self.verify()

    def test_post_cutoff_source_fails(self):
        self.packet["sources"][0]["publication_date"] = "2026-06-02"
        self.write()
        with self.assertRaises(SystemExit):
            self.verify()

    def test_cutoff_on_goal_date_fails(self):
        self.packet["evidence_cutoff"] = "2026-06-01"
        self.write()
        with self.assertRaises(SystemExit):
            self.verify()

    def test_invalid_case_id_fails(self):
        self.row["case_id"] = "../leak"
        self.write()
        with self.assertRaises(SystemExit):
            self.verify()

    def test_outcome_phrase_fails(self):
        self.packet["clinical_summary"] = "FDA decision: approved"
        self.write()
        with self.assertRaises(SystemExit):
            self.verify()

if __name__ == "__main__":
    unittest.main()
