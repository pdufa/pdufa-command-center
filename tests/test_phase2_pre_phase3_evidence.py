"""PRE PHASE 3 Phase 2 primary p-value provenance and identity tests."""
import unittest
from datetime import datetime, timezone, timedelta

from phase2_pre_phase3_evidence import primary_evidence_index, phase2_linked_summary

NOW = datetime(2026, 10, 10, 20, tzinfo=timezone.utc)


def observation(**changes):
    row = {
        "ticker": "TEST", "nct_id": "NCT11112222",
        "observation_id": "first-comparison",
        "primary_endpoint": "Change from baseline",
        "comparison": "control vs treatment",
        "p_value": "0.004",
        "observed_at_utc": "2026-10-10T18:00:00+00:00",
        "results_first_posted": "2026-09-15",
        "source_url": "https://clinicaltrials.gov/study/NCT11112222",
    }
    row.update(changes)
    return row


class Phase2EvidenceTests(unittest.TestCase):
    def test_exact_ticker_and_link_required(self):
        index = primary_evidence_index([observation()], NOW)
        match = phase2_linked_summary(index, "TEST", "NCT11112222 | NCT33334444")
        self.assertEqual(match["Phase 2 PRIMARY evidence count"], 1)
        self.assertIn("NCT11112222 p=0.004", match["Linked Phase 2 PRIMARY p"])
        self.assertEqual(phase2_linked_summary(index, "OTHER", "NCT11112222")["Phase 2 PRIMARY evidence count"], 0)
        self.assertEqual(phase2_linked_summary(index, "TEST", "NCT33334444")["Phase 2 PRIMARY evidence count"], 0)

    def test_future_or_unattributed_data_never_leaks(self):
        for change in (
            {"observed_at_utc": "2026-10-11T01:00:00Z"},
            {"observed_at_utc": ""},
            {"results_first_posted": "2026-10-11"},
            {"source_url": "https://example.org/study/NCT11112222"},
            {"source_url": "https://clinicaltrials.gov/study/NCT33334444"},
            {"primary_endpoint": ""},
            {"p_value": ""},
            {"p_value": "1.1"},
            {"p_value": "not-p"},
            {"p_value_modifier": "approx"},
            {"results_first_posted": "2026-10-11"},
            {"nct_id": "INVALID"},
            {"ticker": ""},
        ):
            self.assertEqual(primary_evidence_index([observation(**change)], NOW), {}, change)

    def test_deduplicates_same_observation_id_not_distinct_comparisons(self):
        same = observation()
        other = observation(observation_id="second-comparison", comparison="active vs treatment", p_value="0.0000")
        result = primary_evidence_index([same, same, other], NOW)
        self.assertEqual(phase2_linked_summary(result, "TEST", "NCT11112222")["Phase 2 PRIMARY evidence count"], 2)

    def test_p_less_than_qualifier_is_preserved(self):
        idx = primary_evidence_index([observation(p_value_modifier="<", p_value="0.001")], NOW)
        summary = phase2_linked_summary(idx, "TEST", "NCT11112222")
        self.assertIn("p<0.001", summary["Linked Phase 2 PRIMARY p"])

    def test_missing_evidence_is_explicit_and_non_diagnostic(self):
        empty = phase2_linked_summary({}, "TEST", "NCT11112222")
        self.assertEqual(empty["Phase 2 PRIMARY evidence count"], 0)
        self.assertIn("NOT VERIFIED", empty["Linked Phase 2 PRIMARY p"])

    def test_timezone_is_required(self):
        with self.assertRaises(ValueError):
            primary_evidence_index([observation()], datetime(2026, 10, 10, 20))
        future = observation(observed_at_utc=(NOW+timedelta(seconds=1)).isoformat())
        self.assertEqual(primary_evidence_index([future], NOW), {})


if __name__ == "__main__":
    unittest.main()
