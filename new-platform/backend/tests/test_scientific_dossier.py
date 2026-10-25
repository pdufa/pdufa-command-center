"""Identity, provenance and no-fabricated-score contract for Trial Science."""
import unittest
from app.scientific_dossier import DOMAINS, build_scientific_dossier


class ScientificDossierTests(unittest.TestCase):
    def setUp(self):
        self.registry = {"protocolSection": {
            "identificationModule": {"nctId": "NCT12345678"},
            "designModule": {"designInfo": {
                "allocation": "RANDOMIZED",
                "interventionModel": "PARALLEL",
                "maskingInfo": {"masking": "DOUBLE"}},
                "enrollmentInfo": {"count": 250}},
            "outcomesModule": {"primaryOutcomes": [{"measure": "Overall survival"}]},
        }}

    def test_registry_facts_only_never_claim_scientific_verification(self):
        dossier = build_scientific_dossier("PROGRAM-123", "NCT12345678", self.registry)
        self.assertEqual(set(dossier["domains"]), set(DOMAINS))
        self.assertEqual(len(DOMAINS), 8)
        self.assertEqual(dossier["assessment_status"], "incomplete")
        self.assertIsNone(dossier["overall_score"])
        self.assertIsNone(dossier["fda_approval_probability"])
        design = dossier["domains"]["clinical_design"]
        self.assertEqual(design["status"], "source_record_only")
        self.assertTrue(all(c["scientifically_verified"] is False for c in design["claims"]))
        self.assertTrue(all(c["source_url"] == "https://clinicaltrials.gov/study/NCT12345678" for c in design["claims"]))
        self.assertTrue(all(dossier["domains"][domain]["score"] is None for domain in DOMAINS))

    def test_identity_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            build_scientific_dossier("PROGRAM-123", "NCT87654321", self.registry)

    def test_missing_fields_are_not_fabricated(self):
        registry = {"protocolSection": {"identificationModule": {"nctId": "NCT12345678"}}}
        dossier = build_scientific_dossier("PROGRAM-123", "NCT12345678", registry)
        self.assertEqual(dossier["domains"]["clinical_design"]["status"], "not_assessed")
        self.assertEqual(dossier["domains"]["clinical_design"]["claims"], [])

    def test_source_snapshot_checksum_reproducible(self):
        a = build_scientific_dossier("PROGRAM-123", "NCT12345678", self.registry)
        b = build_scientific_dossier("PROGRAM-123", "NCT12345678", self.registry)
        self.assertEqual(a["source_sha256"], b["source_sha256"])
        self.assertEqual(a, b)

    def test_invalid_identity_and_schema(self):
        for exact, nct, source in [
            ("", "NCT12345678", self.registry),
            ("PROGRAM-123", "invalid", self.registry),
            ("PROGRAM-123", "NCT12345678", {"protocolSection": []}),
        ]:
            with self.subTest(exact=exact, nct=nct):
                with self.assertRaises(ValueError):
                    build_scientific_dossier(exact, nct, source)


if __name__ == "__main__":
    unittest.main()
