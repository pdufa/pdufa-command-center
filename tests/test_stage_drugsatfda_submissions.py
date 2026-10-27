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
                    "ApplNo\tSubmissionType\tSubmissionNo\tSubmissionStatus\tSubmissionStatusDate\tReviewPriority\tSubmissionsPublicNotes\tSubmissionClassCodeID\n"
                    " 221276 \tORIG\t1\tAP\t2026-10-20\tPriority\tOriginal application\t2\n")
                archive.writestr("ApplicationDocs.txt",
                    "ApplNo\tSubmissionType\tSubmissionNo\tApplicationDocsTitle\tApplicationDocsURL\tApplicationDocsDate\n"
                    "221276\tORIG\t1\tApproval letter\thttps://www.accessdata.fda.gov/a.pdf\t2026-10-20\n")
                archive.writestr("Join_Submission_ActionType_Lookup.txt",
                    "ApplNo\tSubmissionType\tSubmissionNo\tActionTypes_LookupID\n"
                    "221276\tORIG\t1\t7\n")
                archive.writestr("ActionTypes_Lookup.txt",
                    "ActionTypes_LookupID\tActionTypes_LookupDescription\n"
                    "7\tApproval\n")
            report = stage(path)
            self.assertEqual(report["candidate_count"], 1)
            self.assertEqual(report["submission_types"]["ORIG"], 1)
            self.assertEqual(report["review_priority_counts"]["Priority"], 1)
            self.assertEqual(report["candidates"][0]["submission_class_code_id"], "2")
            self.assertEqual(report["candidate_decisions_verified"], 0)
            self.assertEqual(report["with_source_documents"], 1)
            self.assertEqual(report["without_source_documents"], 0)
            self.assertEqual(report["with_action_descriptions"], 1)
            self.assertEqual(len(report["candidates"][0]["source_documents"]), 1)
            self.assertFalse(report["candidates"][0]["model_eligible"])
            self.assertEqual(report["status_code_counts"]["AP"], 1)
            self.assertEqual(report["candidates"][0]["action_descriptions"], ["Approval"])
