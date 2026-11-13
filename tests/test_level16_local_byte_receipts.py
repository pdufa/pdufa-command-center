"""Tests for offline byte matching, bounded paths, and non-promotion of reviews."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts/medical" / file)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


matcher = load("level16_local_byte_receipts", "level16_local_byte_receipts.py")
reporter = load("phase_first_levels_1_6", "phase_first_levels_1_6.py")


def manifest(records):
    return {"schemaVersion": 1, "kind": "FOCUS_LEVELS_1_6_LOCAL_BYTE_RECEIPTS",
            "records": records}


class LocalByteReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bytes = b"synthetic source content; not an actual clinical publication"
        self.digest = hashlib.sha256(self.bytes).hexdigest()
        self.nct = "NCT05507203"
        self.submit_id = "source-1"
        self.submissions = {
            self.nct: [{"submissionId": self.submit_id,
                         "submittedDigestUnverified": self.digest}],
        }

    def receipt(self, relative="clinical/source.txt"):
        return manifest([{"submissionId": self.submit_id, "relativePath": relative}])

    def write(self, value=None):
        path = self.root / "clinical" / "source.txt"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(self.bytes if value is None else value)
        return path

    def test_matching_exact_local_bytes_never_authenticates_publication_or_review(self):
        self.write()
        report = matcher.match_local_bytes(self.submissions, self.receipt(), self.root)
        item = report["receipts"][self.submit_id]
        self.assertEqual(item["byteMatchStatus"], "LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY")
        self.assertEqual(item["bytesRead"], len(self.bytes))
        self.assertEqual(item["computedSha256"], self.digest)
        self.assertEqual(report["summary"]["localByteMatches"], 1)
        self.assertEqual(report["summary"]["originalSourceAuthenticated"], 0)
        self.assertEqual(report["summary"]["independentScientificReviews"], 0)

    def test_detects_modified_content_without_upgrading_source(self):
        self.write(b"other bytes")
        report = matcher.match_local_bytes(self.submissions, self.receipt(), self.root)
        self.assertEqual(report["receipts"][self.submit_id]["byteMatchStatus"],
                         "LOCAL_DIGEST_MISMATCH")
        self.assertEqual(report["summary"]["localDigestMismatches"], 1)
        self.assertEqual(report["summary"]["originalSourceAuthenticated"], 0)

    def test_missing_or_unlisted_local_file_is_never_counted(self):
        missing = matcher.match_local_bytes(self.submissions, self.receipt(), self.root)
        self.assertEqual(missing["summary"]["localFilesNotPresent"], 1)
        self.assertEqual(missing["summary"]["localByteMatches"], 0)
        none = matcher.match_local_bytes(self.submissions, manifest([]), self.root)
        self.assertEqual(none["summary"]["sourcesWithoutLocalReceipt"], 1)
        self.assertEqual(none["summary"]["receiptEntries"], 0)

    def test_rejects_unknown_duplicate_and_forged_approval_fields(self):
        self.write()
        for rows in (
            [{"submissionId": "not-in-queue", "relativePath": "clinical/source.txt"}],
            [self.receipt()["records"][0], self.receipt()["records"][0]],
            [{"submissionId": self.submit_id, "relativePath": "clinical/source.txt",
              "independentlyReviewed": True}],
        ):
            with self.subTest(rows=rows):
                with self.assertRaises(ValueError):
                    matcher.match_local_bytes(self.submissions, manifest(rows), self.root)

    def test_rejects_absolute_traversal_and_backslash_paths(self):
        self.write()
        for path in ("../private.txt", "clinical/../../private.txt", "/etc/passwd",
                     "clinical\\source.txt", "clinical//source.txt",
                     "clinical/./source.txt", "C:/Windows/win.ini"):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    matcher.match_local_bytes(self.submissions, self.receipt(path), self.root)

    def test_rejects_symlink_to_file_outside_root(self):
        self.write()
        link = self.root / "clinical" / "linked.txt"
        outside = self.root.parent / ("not-really-clinical-" + self.root.name)
        outside.write_text("private text", encoding="utf-8")
        self.addCleanup(lambda: outside.unlink(missing_ok=True))
        try:
            link.symlink_to(outside)
        except (OSError, NotImplementedError):
            self.skipTest("OS does not permit symlink creation")
        with self.assertRaises(ValueError):
            matcher.match_local_bytes(self.submissions, self.receipt("clinical/linked.txt"),
                                      self.root)

    def test_rejects_oversize_file_without_hashing_full_contents(self):
        self.write(b"12345")
        with patch.object(matcher, "MAX_SOURCE_BYTES", 4):
            with self.assertRaises(ValueError):
                matcher.match_local_bytes(self.submissions, self.receipt(), self.root)

    def test_report_pipeline_attaches_receipts_but_not_assessment_or_probability(self):
        self.write()
        roster, apps, definitions = [json.loads(path.read_text(encoding="utf-8"))
                                     for path in (
                                         reporter.ROSTER_PATH,
                                         reporter.APPLICATIONS_PATH,
                                         reporter.DEFINITION_PATH,
                                     )]
        submission = {
            "submissionId": self.submit_id, "nct": self.nct, "level": 3,
            "sourceKind": "JOURNAL_PUBLICATION",
            "sourceUrl": "https://example.org/synthetic-report",
            "sourceDate": "2026-11-08", "accessedDate": "2026-11-10",
            "documentSha256": self.digest, "locator": "synthetic paragraph",
            "claim": "Example only, no clinical finding",
            "role": "CONTEXT", "submittedBy": "test-user",
        }
        submitted = {"schemaVersion": 1, "kind": "FOCUS_LEVELS_1_6_SOURCE_SUBMISSIONS",
                     "cutoffDate": "2026-11-11", "records": [submission]}
        report = reporter.build(roster, apps, {"results": {}}, definitions,
                                submissions=submitted, local_receipts=self.receipt(),
                                evidence_root=self.root)
        self.assertEqual(report["focusTrialCount"], 32)
        self.assertEqual(report["localByteConsistency"]["localByteMatches"], 1)
        self.assertEqual(report["scientificallyAdjudicatedLevels"], 0)
        source = report["trials"][0]["levels"][2]["submittedEvidenceLeads"][0]
        self.assertEqual(source["localByteReceipt"]["byteMatchStatus"],
                         "LOCAL_BYTES_MATCH_SUBMITTED_DIGEST_ONLY")
        self.assertEqual(source["authenticationStatus"],
                         "SUBMITTED_SOURCE_NOT_INDEPENDENTLY_AUTHENTICATED")
        self.assertFalse(report["trials"][0]["levels"][2]["assessmentCompleted"])
        self.assertIsNone(report["trials"][0]["levels"][2]["score"])
        self.assertIsNone(report["trials"][0]["fdaOutcomeJudgment"])

    def test_requires_both_receipt_manifest_and_root_plus_valid_submissions(self):
        roster, apps, definitions = [json.loads(path.read_text(encoding="utf-8"))
                                     for path in (
                                         reporter.ROSTER_PATH,
                                         reporter.APPLICATIONS_PATH,
                                         reporter.DEFINITION_PATH,
                                     )]
        for kwargs in (
            {"local_receipts": self.receipt()},
            {"evidence_root": self.root},
            {"local_receipts": self.receipt(), "evidence_root": self.root},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    reporter.build(roster, apps, {"results": {}}, definitions, **kwargs)


if __name__ == "__main__":
    unittest.main()
