"""Regression tests for the research-only scientific slot registry."""
import unittest

from research.prediction_v1_1_slot_registry import (
    SlotStatus, load_defined_fields, summarize_registry,
)


class SlotRegistryTests(unittest.TestCase):
    def setUp(self):
        self.fields = load_defined_fields()

    def test_draft_inventory_is_explicitly_incomplete(self):
        summary = summarize_registry(self.fields)
        self.assertEqual(summary["proposed_slots"], 650)
        self.assertEqual(summary["defined_fields"], 8)
        self.assertEqual(summary["undefined_slots"], 642)
        self.assertEqual(summary["prediction_action"], "ABSTAIN")
        self.assertFalse(summary["scientific_catalog_validated"])

    def test_unverified_population_does_not_change_readiness(self):
        first = next(iter(self.fields))
        summary = summarize_registry(self.fields, {
            first: SlotStatus(first, "UNVERIFIED", 1, False)
        })
        self.assertEqual(summary["evidence_states"]["UNVERIFIED"], 1)
        self.assertEqual(summary["prediction_readiness"], "NOT_READY")

    def test_self_asserted_verified_is_rejected(self):
        first = next(iter(self.fields))
        with self.assertRaises(ValueError):
            summarize_registry(self.fields, {
                first: SlotStatus(first, "VERIFIED", 1, False)
            })

    def test_verified_without_source_is_rejected(self):
        first = next(iter(self.fields))
        with self.assertRaises(ValueError):
            summarize_registry(self.fields, {
                first: SlotStatus(first, "VERIFIED", 0, True)
            })

    def test_undefined_field_is_rejected(self):
        with self.assertRaises(ValueError):
            summarize_registry(self.fields, {
                "FAKE-999": SlotStatus("FAKE-999", "UNVERIFIED", 1, False)
            })

    def test_mismatched_field_id_is_rejected(self):
        first = next(iter(self.fields))
        with self.assertRaises(ValueError):
            summarize_registry(self.fields, {
                first: SlotStatus("FAKE-999", "UNVERIFIED", 1, False)
            })


if __name__ == "__main__":
    unittest.main()
