import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from audit_2026_fda_action_candidates import approval_candidates, audit, letter_candidates


class FdaCandidateAuditTests(unittest.TestCase):
    def test_action_key_preserves_same_day_supplements(self):
        supplement = {
            "submission_type": "SUPPL",
            "submission_class_code": "EFFICACY",
            "submission_status": "AP",
            "submission_status_date": "20261118",
            "submission_number": "1",
        }
        eligible = [
            supplement,
            supplement,
            {**supplement, "submission_number": "2"},
            {**supplement, "submission_number": "3", "submission_class_code": "LABELING"},
            {**supplement, "submission_number": "4", "submission_status": "TA"},
            {**supplement, "submission_number": "5", "submission_status_date": "20261119"},
        ]
        rows, classes, duplicates = approval_candidates([
            {"application_number": "NDA123456", "submissions": eligible},
            {"application_number": "ANDA123456", "submissions": eligible},
        ])
        self.assertEqual({row["submission_number"] for row in rows}, {"1", "2"})
        self.assertEqual(duplicates, 1)
        self.assertEqual(sum(classes.values()), 5)

    def test_letter_must_have_a_file_and_application(self):
        current = {
            "letter_date": "01/01/2026",
            "file_name": "CRL_fixture.pdf",
            "application_number": ["NDA 123456", "NDA 123456/Original 2"],
            "letter_type": "COMPLETE RESPONSE",
        }
        index = {
            "meta": {"results": {"total": 3, "skip": 0}},
            "results": [current, current, {"letter_date": "01/02/2026"}],
        }
        records, unresolved, duplicates = letter_candidates(index)
        self.assertEqual(len(records), 1)
        self.assertEqual(len(records[0]["application_numbers_as_published"]), 2)
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(duplicates, 1)
        index["meta"]["results"]["total"] = 4
        with self.assertRaisesRegex(ValueError, "all pages"):
            letter_candidates(index)

    def test_quarantine_file_exclusive_and_private(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            drugs = root / "drugs.zip"
            crls = root / "crls.json"
            timing = root / "timing.csv"
            quarantine = root / "quarantine"
            with zipfile.ZipFile(drugs, "w") as archive:
                archive.writestr("snapshot.json", '{"results":[]}')
            crls.write_text(json.dumps({
                "meta": {"last_updated": "2026-11-18", "results": {"total": 0, "skip": 0}},
                "results": [],
            }))
            timing.write_text(
                "ticker,drug,goal_date,fda_action_date\n"
                "TEST,Fixture,2026-11-18,2026-11-18\n"
            )
            report = audit(drugs, crls, timing, quarantine, 196)
            self.assertFalse(report["case_count_verified"])
            self.assertIsNone(report["eligible_denominator"])
            self.assertEqual(report["timing_discovery_distinct_rows"], 1)
            output = quarantine / "fda-action-candidates.private.json"
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            with self.assertRaises(FileExistsError):
                audit(drugs, crls, timing, quarantine, 196)
