"""Avoid false FDA source conflicts during independent PDUFA claim rechecks."""
import unittest

from scripts.targeted_verification_repair import fresh_result


class FakeVerifier:
    def __init__(self, expected="2026-11-01", status="VERIFIED"):
        self.expected = expected
        self.status = status

    def regulatory(self, event):
        return [{
            "event_key": event["event_key"],
            "ticker": event["ticker"],
            "category": "FDA",
            "claim": "PDUFA_TARGET",
            "verification_status": self.status,
            "expected": self.expected,
            "observed": self.expected,
            "reason": "Exact source verified",
            "source_url": "https://example.org/issuer-release",
            "source_sha256": "f" * 64,
            "checked_at": "2026-10-15T02:20:00+00:00",
            "evidence": "Verified program and matching date",
        }]


class TargetedFdaRecheckTests(unittest.TestCase):
    EVENT = {"event_key": "AGIO|MITAPIVAT_SCD_20261101", "ticker": "AGIO"}

    def row(self, expected, status="REVIEW_REQUIRED"):
        return {
            "event_key": self.EVENT["event_key"],
            "ticker": "AGIO",
            "category": "FDA",
            "claim": "PDUFA_TARGET",
            "expected": expected,
            "verification_status": status,
        }

    def test_disease_name_in_saved_expected_is_not_a_calendar_date_conflict(self):
        for previous in ("sickle cell disease", "Duchenne muscular dystrophy (DMD)",
                         "recurrent respiratory papillomatosis (RRP)", "UNVERIFIED", ""):
            with self.subTest(previous=previous):
                found = fresh_result(FakeVerifier(), self.EVENT, self.row(previous))
                self.assertEqual(found["verification_status"], "VERIFIED")

    def test_comparable_saved_date_mismatch_still_causes_conflict(self):
        different = fresh_result(FakeVerifier(), self.EVENT, self.row("2026-11-08"))
        self.assertEqual(different["verification_status"], "CONFLICT")
        same = fresh_result(FakeVerifier(), self.EVENT, self.row("2026-11-01"))
        self.assertEqual(same["verification_status"], "VERIFIED")

    def test_previous_primary_date_conflict_is_not_silently_removed(self):
        found = fresh_result(FakeVerifier(), self.EVENT,
                             self.row("sickle cell disease", status="CONFLICT"))
        self.assertEqual(found["verification_status"], "CONFLICT")
        self.assertIn("separate reconciliation", found["reason"])

    def test_fresh_verifier_conflict_is_not_suppressed(self):
        found = fresh_result(FakeVerifier(status="CONFLICT"), self.EVENT,
                             self.row("sickle cell disease"))
        self.assertEqual(found["verification_status"], "CONFLICT")


if __name__ == "__main__":
    unittest.main()
