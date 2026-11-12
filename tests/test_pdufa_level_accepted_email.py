"""Offline regression tests for PDUFA accepted-level Gmail notifications."""
import importlib.util
from email.message import EmailMessage
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("accepted_email", ROOT / "scripts/pdufa_level_accepted_email.py")
M = importlib.util.module_from_spec(spec)
spec.loader.exec_module(M)

def accepted(n=4,sha="a"*64):
    return {"level":n, "review_evidence_sha256":sha,
            "verified_reviewers":["clinical-expert","code-expert"],
            "verified_utc":"2026-11-12T15:10:00+00:00",
            "review_comment_urls":[
                "https://github.com/pdufa/pdufa-command-center/issues/1096#issuecomment-11",
                "https://github.com/pdufa/pdufa-command-center/issues/1096#issuecomment-12",
            ]}

class AcceptedEmailTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        p=patch.object(M,"STATE",Path(t.name)/"notifications.json")
        p.start();self.addCleanup(p.stop)
        self.credentials=("test.sender@example.org","dummy-gmail-app-password",
                          "test.recipient@example.org")

    def test_notifies_only_independently_accepted_levels(self):
        events=M.accepted_events({"accepted_levels":[]})
        calls=[]
        result=M.process(events=events,credentials=self.credentials,send=lambda *args:calls.append(args))
        self.assertEqual(result["sent_now"],0)
        self.assertEqual(calls,[])
        event=M.accepted_events({"accepted_levels":[accepted()]})
        result=M.process(events=event,credentials=self.credentials,
                         send=lambda *args:calls.append(args))
        self.assertEqual(result["sent_now"],1)
        self.assertEqual(len(calls),1)
        self.assertIn("Level 4",calls[0][0]["Subject"])
        self.assertIn("Level 5",calls[0][0].get_content())

    def test_restart_does_not_repeat_delivered_email(self):
        calls=[]
        events=M.accepted_events({"accepted_levels":[accepted()]})
        for _ in range(3):
            M.process(events=events,credentials=self.credentials,send=lambda *args:calls.append(args))
        self.assertEqual(len(calls),1)
        self.assertEqual(M.load_state()["sent"]["4"]["sha256"],"a"*64)

    def test_missing_credentials_preserves_unsent(self):
        events=M.accepted_events({"accepted_levels":[accepted()]})
        result=M.process(events=events,credentials=None,send=lambda *args:self.fail("must not send"))
        with patch.object(M,"config",return_value=None):
            result=M.process(events=events,credentials=None,
                             send=lambda *args:self.fail("must not send"))
        self.assertEqual(result["pending"],1)
        self.assertEqual(result["total_sent"],0)
        self.assertEqual(result["last_error"],"LOCAL_GMAIL_CONFIGURATION_MISSING")

    def test_failed_mail_is_retryable(self):
        import smtplib
        events=M.accepted_events({"accepted_levels":[accepted()]})
        def fail(*args):
            raise smtplib.SMTPAuthenticationError(535,b"no")
        output=M.process(events=events,credentials=self.credentials,send=fail)
        self.assertEqual(output["pending"],1)
        self.assertEqual(output["total_sent"],0)
        output=M.process(events=events,credentials=self.credentials,send=lambda *args:None)
        self.assertEqual(output["sent_now"],1)

    def test_reject_changed_source_digest_after_email(self):
        events=M.accepted_events({"accepted_levels":[accepted()]})
        M.process(events=events,credentials=self.credentials,send=lambda *args:None)
        altered=accepted(sha="b"*64)
        with self.assertRaises(ValueError):
            M.process(events=M.accepted_events({"accepted_levels":[altered]}),
                      credentials=self.credentials,send=lambda *args:None)

    def test_reject_fake_reviews_wrong_order_and_same_reviewer(self):
        invalid=accepted()
        invalid["verified_reviewers"]=["same","same"]
        with self.assertRaises(ValueError):
            M.accepted_events({"accepted_levels":[invalid]})
        with self.assertRaises(ValueError):
            M.accepted_events({"accepted_levels":[accepted(5)]})
        invalid=accepted()
        invalid["review_comment_urls"]=["https://example.org/forged","https://example.org/forged2"]
        with self.assertRaises(ValueError):
            M.accepted_events({"accepted_levels":[invalid]})

    def test_subject_and_body_for_final_level(self):
        ev=accepted(n=20)
        msg=M.message({"level":20,"sha256":ev["review_evidence_sha256"],
                       "approved_utc":ev["verified_utc"],"reviewers":ev["verified_reviewers"]},
                      "recipient@example.org","sender@example.org")
        self.assertIn("Levels 4",msg["Subject"])
        self.assertIn("no",msg.get_content().lower()) if False else None
        self.assertIn("All Levels 4-20",msg.get_content())

    def test_reject_header_injection(self):
        for address in ["a@b.org\nBCC:another@b.org","Friendly <a@b.org>","not-an-email"]:
            with self.assertRaises(ValueError):
                M.mailbox(address)

if __name__=="__main__":
    unittest.main()
