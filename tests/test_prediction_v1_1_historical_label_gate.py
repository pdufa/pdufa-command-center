"""Fail-closed regression checks for historical FDA outcome label gate."""
import unittest
from research.prediction_v1_1_historical_label_gate import (
    validate_historical_label, historical_label_receipt,
)

BASE = {
    "program_id": "TEST-DRUG",
    "outcome": "CRL",
    "decision_at": "2025-02-15T12:00:00Z",
    "source_published_at": "2025-02-16T12:00:00Z",
    "source_url": "https://www.fda.gov/example",
    "source_document_sha256": "a" * 64,
    "decision_document_id": "TEST-DOC-1",
}


class HistoricalLabelGateTests(unittest.TestCase):
    def test_structurally_valid_label_is_still_unverified(self):
        receipt = historical_label_receipt(BASE, evidence_cutoff="2025-02-01T00:00:00Z")
        self.assertTrue(receipt["accepted_for_research_review"])
        self.assertFalse(receipt["independently_verified"])
        self.assertEqual(receipt["prediction_action"], "ABSTAIN")

    def test_missed_target_cannot_be_a_decision(self):
        candidate = dict(BASE, outcome="MISSED_TARGET")
        self.assertTrue(validate_historical_label(candidate))

    def test_unresolved_outcome_rejected(self):
        self.assertTrue(validate_historical_label(dict(BASE, outcome="UNKNOWN")))

    def test_future_outcome_cannot_leak_into_past_cutoff(self):
        self.assertTrue(validate_historical_label(BASE, evidence_cutoff="2025-03-01T00:00:00Z"))

    def test_publication_must_not_precede_decision(self):
        candidate = dict(BASE, source_published_at="2025-02-14T12:00:00Z")
        self.assertTrue(validate_historical_label(candidate))

    def test_unattributed_outcome_rejected(self):
        candidate = dict(BASE, decision_document_id="")
        self.assertTrue(validate_historical_label(candidate))

    def test_unsafe_source_rejected(self):
        candidate = dict(BASE, source_url="http://example.com/outcome")
        self.assertTrue(validate_historical_label(candidate))

    def test_missing_cutoff_rejected_when_requested(self):
        self.assertTrue(validate_historical_label(BASE, evidence_cutoff="not-a-date"))

    def test_malformed_outcome_values_return_errors_instead_of_raising(self):
        for outcome in (None, [], {}, ["PASS"], True, 1):
            with self.subTest(outcome=outcome):
                receipt = historical_label_receipt(dict(BASE, outcome=outcome))
                self.assertFalse(receipt["accepted_for_research_review"])
                self.assertFalse(receipt["independently_verified"])
                self.assertEqual(receipt["prediction_action"], "ABSTAIN")

    def test_malformed_nested_identity_source_and_digest_values_fail_closed(self):
        for key in ("program_id", "decision_document_id", "source_url", "source_document_sha256"):
            for value in (None, [], {}, True, 42):
                with self.subTest(key=key, value=value):
                    self.assertTrue(validate_historical_label(dict(BASE, **{key: value})))

    def test_timestamp_claims_require_explicit_aware_instants(self):
        values = (None, [], {}, True, "2025-02-15", "2025-02-15T12:00:00",
                  "2025-02-15 12:00:00Z", " 2025-02-15T12:00:00Z", "2025-99-15T12:00:00Z")
        for key in ("decision_at", "source_published_at"):
            for value in values:
                with self.subTest(key=key, value=value):
                    self.assertTrue(validate_historical_label(dict(BASE, **{key: value})))
        for cutoff in values:
            if cutoff is not None:  # None means that no cutoff check was requested.
                with self.subTest(cutoff=cutoff):
                    self.assertTrue(validate_historical_label(BASE, evidence_cutoff=cutoff))

    def test_dirty_identity_or_source_reference_is_not_attributable(self):
        for key, value in (("program_id", " TEST-DRUG"), ("decision_document_id", "DOC\n1"),
                           ("source_url", "https://www.fda.gov/doc\nument"),
                           ("source_url", "https://user:secret@www.fda.gov/document"),
                           ("source_url", "https://www.fda.gov/document#claim")):
            with self.subTest(key=key, value=value):
                self.assertTrue(validate_historical_label(dict(BASE, **{key: value})))

    def test_offset_equivalent_known_outcome_is_rejected_at_cutoff(self):
        self.assertTrue(validate_historical_label(
            BASE, evidence_cutoff="2025-02-15T04:00:00-08:00"))


if __name__ == "__main__":
    unittest.main()
