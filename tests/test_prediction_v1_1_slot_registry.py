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

    def test_truthy_verification_values_cannot_claim_independent_review(self):
        first = next(iter(self.fields))
        for value in ("false", "true", 1, 0, None, [], {}):
            for state in ("VERIFIED", "UNVERIFIED"):
                with self.subTest(value=value, state=state), self.assertRaises(ValueError):
                    summarize_registry(self.fields, {first: SlotStatus(first, state, 1, value)})

    def test_noninteger_or_negative_source_counts_are_rejected(self):
        first = next(iter(self.fields))
        for value in (True, False, 1.0, "1", -1, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                summarize_registry(self.fields, {first: SlotStatus(first, "UNVERIFIED", value, False)})

    def test_malformed_statuses_are_rejected_without_attribute_or_hash_errors(self):
        first = next(iter(self.fields))
        for status in (None, {}, [], "VERIFIED", SlotStatus(first, [], 1, False)):
            with self.subTest(status=status), self.assertRaises(ValueError):
                summarize_registry(self.fields, {first: status})

    def test_nonmapping_collections_and_nontext_keys_are_rejected(self):
        for fields, observations in (([], None), (self.fields, []), (self.fields, {1: None})):
            with self.subTest(fields=fields, observations=observations), self.assertRaises(ValueError):
                summarize_registry(fields, observations)

    def test_structurally_verified_state_never_promotes_prediction_readiness(self):
        first = next(iter(self.fields))
        result = summarize_registry(self.fields, {first: SlotStatus(first, "VERIFIED", 1, True)})
        self.assertEqual(result["evidence_states"]["VERIFIED"], 1)
        self.assertFalse(result["scientific_catalog_validated"])
        self.assertEqual(result["prediction_readiness"], "NOT_READY")
        self.assertEqual(result["prediction_action"], "ABSTAIN")


if __name__ == "__main__":
    unittest.main()
