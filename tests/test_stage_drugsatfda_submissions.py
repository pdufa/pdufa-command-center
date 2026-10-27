import csv
import tempfile
import unittest
import zipfile
from pathlib import Path
from scripts.stage_drugsatfda_submissions import stage


class DrugsAtFDAStageTests(unittest.TestCase):
    def test_stage_submissions_without_promotion(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "drugsatfda.zip"
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("Submissions.txt",
                    "ApplNo\tSubmissionType\tSubmissionNo\tSubmissionStatus\tSubmissionStatusDate\n"
                    "221276\tORIG\t1\tAP\t2026-10-20\n")
                archive.writestr("ApplicationDocs.txt",
                    "ApplNo\tSubmissionType\tSubmissionNo\tApplicationDocsTitle\tApplicationDocsURL\tApplicationDocsDate\n"
                    "221276\tORIG\t1\tApproval letter\thttps://www.accessdata.fda.gov/a.pdf\t2026-10-20\n")
            report = stage(path)
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(len(report["candidates"][0]["source_documents"]), 1)
            self.assertFalse(report["candidates"][0]["model_eligible"])
            self.assertEqual(report["status_code_counts"]["AP"], 1)
