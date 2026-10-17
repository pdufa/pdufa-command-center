"""Guardrails for automated PDUFA Gmail issue repair / exact-notice cleanup."""
import unittest
from scripts.gmail_repair_cleanup import exact_run_ids, is_failure_notification, \
    source_run_valid, confirmed_fixed

RUN = "https://github.com/pdufa/pdufa-command-center/actions/runs/39042182664"
BASE = {
    "id": 39042182664,
    "head_repository": {"full_name": "pdufa/pdufa-command-center"},
    "name": "PDUFA New Platform Bootstrap Checks",
    "head_branch": "new-platform-bootstrap",
    "status": "completed",
    "conclusion": "success",
    "run_attempt": 2,
    "html_url": RUN,
}

class GmailResolvedCleanupTests(unittest.TestCase):
    def test_exact_github_link(self):
        self.assertEqual(exact_run_ids(f"[View workflow]({RUN}?email_source=notifications)"),
                         {39042182664})
        self.assertEqual(exact_run_ids("https://github.com/other/repo/actions/runs/39042182664"), set())
        self.assertEqual(exact_run_ids("unlinked error message"), set())

    def test_sender_and_subject_whitelist(self):
        subject = "[pdufa/pdufa-command-center] Run failed: PDUFA New Platform Bootstrap Checks - main (7a85571)"
        self.assertTrue(is_failure_notification(subject, "GitHub <notifications@github.com>"))
        self.assertFalse(is_failure_notification(subject, "An attacker <external@example.com>"))
        self.assertFalse(is_failure_notification("[PDUFA] Scan END - complete",
                                                 "notifications@github.com"))
        self.assertFalse(is_failure_notification(
            "[someone/repo] Run failed: PDUFA New Platform Bootstrap Checks",
            "notifications@github.com"))

    def test_same_run_successful_retry_may_be_trashed(self):
        self.assertTrue(confirmed_fixed(BASE, 39042182664))
        self.assertFalse(confirmed_fixed(BASE, 39042182665))

    def test_no_trash_if_first_attempt_success_or_failed_or_queued(self):
        self.assertFalse(confirmed_fixed({**BASE, "run_attempt": 1}, 39042182664))
        self.assertFalse(confirmed_fixed({**BASE, "conclusion": "failure"}, 39042182664))
        self.assertFalse(confirmed_fixed({**BASE, "status": "in_progress"}, 39042182664))

    def test_no_cross_repo_or_wrong_link_or_untrusted_url(self):
        self.assertFalse(source_run_valid({**BASE, "head_repository":
                                           {"full_name": "untrusted/repo"}}, 39042182664))
        self.assertFalse(source_run_valid({**BASE, "html_url":
                                           "https://evil.example/actions/runs/39042182664"},
                                          39042182664))
        self.assertFalse(confirmed_fixed({**BASE, "html_url": RUN + "-fake"}, 39042182664))


if __name__ == "__main__":
    unittest.main()
