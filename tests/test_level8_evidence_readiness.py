import unittest
from level7_evidence import make_record
from level8_evidence_readiness import assess_evidence_readiness

def record(source, status="verified", version="v1", stamp="2026-11-17T00:00:00+00:00"):
    return make_record(
        trial_id="NCT00000001", source_id=source,
        source_url="https://example.org/" + source, publisher="source",
        source_version=version,
        content=None if status in ("missing", "inaccessible") else b"published",
        status=status, retrieved_at=stamp,
    )

class Level8EvidenceReadinessTests(unittest.TestCase):
    def test_two_verified_independent_sources_are_ready(self):
        result = assess_evidence_readiness("NCT00000001", [record("registry"), record("publication")])
        self.assertEqual(result.status, "READY_FOR_SCIENTIFIC_REVIEW")
        self.assertEqual(result.verified_sources, 2)

    def test_single_source_revisions_do_not_count_as_independent(self):
        result = assess_evidence_readiness("NCT00000001", [
            record("registry"), record("registry", version="v2"),
        ])
        self.assertEqual(result.status, "EVIDENCE_INCOMPLETE")
        self.assertEqual(result.verified_sources, 1)

    def test_conflict_blocks_readiness(self):
        result = assess_evidence_readiness("NCT00000001", [
            record("registry"), record("publication"), record("company", "conflicting"),
        ])
        self.assertEqual(result.status, "CONFLICT_REVIEW")

    def test_missing_is_not_a_negative_outcome(self):
        result = assess_evidence_readiness("NCT00000001", [record("registry", "missing")])
        self.assertEqual(result.status, "EVIDENCE_INCOMPLETE")
        self.assertTrue(any("not negative clinical evidence" in reason for reason in result.reasons))

    def test_cross_trial_record_rejected(self):
        with self.assertRaisesRegex(ValueError, "Cross-trial"):
            assess_evidence_readiness("NCT00000002", [record("registry")])

if __name__ == "__main__":
    unittest.main()
