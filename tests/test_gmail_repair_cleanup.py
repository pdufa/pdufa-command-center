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


class PrioritizedCleanupTests(unittest.TestCase):
    def test_explicit_operational_severity(self):
        from scripts.gmail_repair_cleanup import workflow_priority
        self.assertEqual(workflow_priority("PDUFA Overnight Sequential Scans"), 1)
        self.assertEqual(workflow_priority("PIPELINE Early Clinical Live Acceptance"), 1)
        self.assertEqual(workflow_priority("GEM Research Quality"), 1)
        self.assertEqual(workflow_priority("GEM JR Phase 3 Readout"), 1)
        self.assertEqual(workflow_priority("PDUFA SEC Filing Verification"), 2)
        self.assertEqual(workflow_priority("PDUFA FDA Source Evidence"), 2)
        self.assertEqual(workflow_priority("PDUFA Gmail Authentication Failure"), 3)
        self.assertEqual(workflow_priority("PDUFA Email Delivery Test"), 3)
        self.assertEqual(workflow_priority("PDUFA Command Center CI"), 4)
        self.assertEqual(workflow_priority("PDUFA New Platform Bootstrap Checks"), 4)
        self.assertEqual(workflow_priority("An Unrecognized Old Alert"), 5)

    def test_verified_old_and_fixed_runs_processed_last(self):
        from scripts.gmail_repair_cleanup import notice_priority, prioritized_queue
        fixed = {**BASE, "head_branch": "main", "head_sha": "latest"}
        old = {**BASE, "run_attempt": 1, "conclusion": "failure", "head_branch": "main",
               "head_sha": "superseded", "name": "PDUFA Overnight Sequential Scans"}
        current = {**old, "head_sha": "latest"}
        self.assertEqual(notice_priority(fixed, "latest"), 5)
        self.assertEqual(notice_priority(old, "latest"), 5)
        self.assertEqual(notice_priority(current, "latest"), 1)
        queue = [(b"500", 500, fixed, 5), (b"1", 1, current, 1), (b"99", 99, old, 5)]
        self.assertEqual([x[1] for x in prioritized_queue(queue)], [1, 500, 99])

    def test_every_header_batch_scanned_before_highest_priority_repairs(self):
        from unittest.mock import patch
        from scripts import gmail_repair_cleanup as m

        subjects = {
            2: "[pdufa/pdufa-command-center] Run failed: PDUFA Command Center CI - main (abc)",
            10: "[pdufa/pdufa-command-center] Run failed: PDUFA Gmail Authentication - main (abc)",
            101: "[pdufa/pdufa-command-center] Run failed: PDUFA SEC Evidence Scan - main (abc)",
            201: "[pdufa/pdufa-command-center] Run failed: PDUFA Overnight Sequential Scans - main (abc)",
            205: "[pdufa/pdufa-command-center] Run failed: Historical Status - main (abc)",
        }
        names = {
            2: "PDUFA Command Center CI",
            10: "PDUFA Gmail Authentication",
            101: "PDUFA SEC Evidence Scan",
            201: "PDUFA Overnight Sequential Scans",
            205: "Historical Status",
        }
        events = []

        class FakeIMAP:
            def __init__(self, *args, **kwargs):
                pass

            def login(self, user, password):
                return "OK", []

            def select(self, folder, readonly=False):
                return "OK", []

            def uid(self, operation, *args):
                if operation == "SEARCH":
                    return "OK", [b" ".join(str(i).encode() for i in range(1, 206))]
                if operation == "MOVE":
                    events.append(("trash", int(args[0])))
                    return "OK", [b"OK"]
                raise AssertionError("Unexpected IMAP command: " + operation)

            def logout(self):
                return "BYE", []

        def parse_headers(client, batch):
            events.append(("header_batch", len(batch)))
            return [(str(i).encode(), subjects[i]) for i in subjects if str(i).encode() in batch], True

        def github_json(path, token):
            if path == "/commits/main":
                return {"sha": "latest"}
            run_id = int(path.rsplit("/", 1)[1])
            uid = run_id - 1000
            return {
                "id": run_id,
                "head_repository": {"full_name": "pdufa/pdufa-command-center"},
                "name": names[uid],
                "status": "completed",
                "conclusion": "failure",
                "run_attempt": 1,
                "head_branch": "main",
                "head_sha": "latest",
                "html_url": f"https://github.com/pdufa/pdufa-command-center/actions/runs/{run_id}",
                "created_at": "2026-10-17T12:00:00Z",
            }

        def retrieve(client, uid):
            return f"https://github.com/pdufa/pdufa-command-center/actions/runs/{1000 + int(uid)}"

        def safe_repair(run_id, run, token, main_sha):
            events.append(("repair", run["name"]))
            return "RERUN_REQUESTED_NOT_YET_FIXED"

        with patch.dict("os.environ", {"PDUFA_GMAIL_USER": "tester@gmail.com",
                                      "PDUFA_GMAIL_APP_PASSWORD": "dummy"}), \
             patch.object(m.imaplib, "IMAP4_SSL", FakeIMAP), \
             patch.object(m, "parse_headers", parse_headers), \
             patch.object(m, "retrieve_message", retrieve), \
             patch.object(m, "github_json", github_json), \
             patch.object(m, "safe_repair", safe_repair):
            result = m.process_section("ALL", "not-a-real-token")

        self.assertEqual(result["status"], "CHECKED")
        self.assertEqual(result["headers_checked"], 205)
        self.assertEqual(result["failure_notifications"], 5)
        self.assertEqual(result["repair_requests"], 3)
        self.assertEqual(result["confirmed_resolved_trashed"], 0)
        self.assertEqual(events[:3], [("header_batch", 100), ("header_batch", 100),
                                      ("header_batch", 5)])
        repairs = [x[1] for x in events if x[0] == "repair"]
        self.assertEqual(repairs, ["PDUFA Overnight Sequential Scans",
                                   "PDUFA SEC Evidence Scan",
                                   "PDUFA Gmail Authentication"])
        self.assertEqual(result["priority_stats"]["1"]["repair_requests"], 1)
        self.assertEqual(result["priority_stats"]["2"]["repair_requests"], 1)
        self.assertEqual(result["priority_stats"]["3"]["repair_requests"], 1)

    def test_resolved_mail_goes_to_trash_after_critical_issue_handling(self):
        from unittest.mock import patch
        from scripts import gmail_repair_cleanup as m
        events = []

        class FakeIMAP:
            def __init__(self, *args, **kwargs): pass
            def login(self, user, password): pass
            def select(self, name, readonly=False): return "OK", []
            def uid(self, operation, *args):
                if operation == "SEARCH":
                    return "OK", [b"10 20"]
                if operation == "MOVE":
                    events.append("trash_" + args[0].decode())
                    return "OK", [b"OK"]
                raise AssertionError(operation)
            def logout(self): pass

        def github_json(path, token):
            if path == "/commits/main": return {"sha": "latest"}
            run_id = int(path.rsplit("/", 1)[1])
            return {
                "id": run_id, "head_repository": {"full_name": "pdufa/pdufa-command-center"},
                "name": "PDUFA Overnight Sequential Scans" if run_id == 1010 else "PDUFA Command Center CI",
                "status": "completed", "conclusion": "failure" if run_id == 1010 else "success",
                "run_attempt": 1 if run_id == 1010 else 2, "head_branch": "main", "head_sha": "latest",
                "html_url": f"https://github.com/pdufa/pdufa-command-center/actions/runs/{run_id}",
            }

        def safe_repair(*args):
            events.append("repair_critical")
            return "RERUN_REQUESTED_NOT_YET_FIXED"

        with patch.dict("os.environ", {"PDUFA_GMAIL_USER": "tester@gmail.com",
                                      "PDUFA_GMAIL_APP_PASSWORD": "dummy"}), \
             patch.object(m.imaplib, "IMAP4_SSL", FakeIMAP), \
             patch.object(m, "parse_headers", lambda client, batch: (
                 [(uid, "PDUFA Alert") for uid in batch], True)), \
             patch.object(m, "retrieve_message", lambda client, uid:
                 f"https://github.com/pdufa/pdufa-command-center/actions/runs/{1000 + int(uid)}"), \
             patch.object(m, "github_json", github_json), \
             patch.object(m, "safe_repair", safe_repair):
            result = m.process_section("ALL", "fake")

        self.assertEqual(events, ["repair_critical", "trash_20"])
        self.assertEqual(result["confirmed_resolved_trashed"], 1)
        self.assertEqual(result["priority_stats"]["5"]["confirmed_resolved_trashed"], 1)
        self.assertEqual(result["priority_stats"]["1"]["manual_review_or_pending"], 1)


if __name__ == "__main__":
    unittest.main()
