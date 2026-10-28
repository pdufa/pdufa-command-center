"""KEYNOTE-024 pilot remains an unscored, exact-trial evidence inventory."""
import unittest

from app.scientific_dossier import DOMAINS
from app.scientific_pilot_keynote024 import keynote024_pilot_manifest


class Keynote024PilotTests(unittest.TestCase):
    def test_exact_registry_and_publication_links(self):
        pilot = keynote024_pilot_manifest()
        self.assertEqual(pilot["nct_id"], "NCT02142738")
        self.assertEqual(pilot["phase"], "PHASE3")
        self.assertEqual(pilot["enrollment"], 305)
        self.assertEqual(pilot["registry"], "https://clinicaltrials.gov/study/NCT02142738")
        self.assertEqual({x["source_id"] for x in pilot["source_references"]},
                         {"NCT02142738", "27718847", "29129441"})
        self.assertEqual(set(pilot["domains"]), set(DOMAINS))

    def test_pilot_never_generates_approval_probability_or_score(self):
        pilot = keynote024_pilot_manifest()
        self.assertIsNone(pilot["overall_score"])
        self.assertIsNone(pilot["fda_approval_probability"])
        self.assertFalse(pilot["live_system_writes"])
        self.assertEqual(pilot["assessment_status"], "pilot_evidence_inventory_only")
        self.assertTrue(all(x["status"] != "completed" for x in pilot["domains"].values()))

    def test_mutating_returned_manifest_does_not_change_reference(self):
        pilot = keynote024_pilot_manifest()
        pilot["source_references"].clear()
        self.assertEqual(len(keynote024_pilot_manifest()["source_references"]), 3)


if __name__ == "__main__":
    unittest.main()
