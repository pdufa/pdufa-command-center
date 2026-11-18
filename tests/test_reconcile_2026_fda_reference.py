import importlib.util
import pathlib
import unittest

SCRIPT = pathlib.Path(__file__).resolve().parents[1] / "scripts/reconcile_2026_fda_reference.py"
spec = importlib.util.spec_from_file_location("reconcile_2026_fda_reference", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReferenceReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.reference = [{
            "drug_name": "ExampleDrug",
            "approval_date": "2026-11-13",
            "pdufa_date_verified": "false",
            "level1_prediction": "",
        }]
        self.batch = [{
            "drug_name": "ExampleDrug",
            "approval_date": "2026-11-13",
            "active_ingredient": "example-ingredient",
            "source_url": "https://www.fda.gov/drugs/example",
            "pdufa_date": "",
            "level1_prediction": "",
        }]

    def test_valid_reference_batch(self):
        self.assertEqual(module.audit(self.reference, self.batch), [])

    def test_duplicate_reference_name(self):
        self.assertTrue(any("duplicate" in x for x in module.audit(self.reference * 2, self.batch)))

    def test_unlisted_drug(self):
        self.batch[0]["drug_name"] = "Unknown"
        self.assertTrue(any("absent" in x for x in module.audit(self.reference, self.batch)))

    def test_approval_date_mismatch(self):
        self.batch[0]["approval_date"] = "2026-11-12"
        self.assertTrue(any("approval-date disagreement" in x for x in module.audit(self.reference, self.batch)))

    def test_unverified_pdufa_date_cannot_be_populated(self):
        self.batch[0]["pdufa_date"] = "2026-11-13"
        self.assertTrue(any("unverified PDUFA" in x for x in module.audit(self.reference, self.batch)))

    def test_unverified_prediction_cannot_be_populated(self):
        self.batch[0]["level1_prediction"] = "APPROVE"
        self.assertTrue(any("unverified PDUFA" in x for x in module.audit(self.reference, self.batch)))

    def test_reference_prediction_cannot_be_populated(self):
        self.reference[0]["level1_prediction"] = "APPROVE"
        self.assertTrue(any("cannot contain L1" in x for x in module.audit(self.reference, self.batch)))

    def test_missing_fda_source(self):
        self.batch[0]["source_url"] = ""
        self.assertTrue(any("missing ingredient" in x for x in module.audit(self.reference, self.batch)))


if __name__ == "__main__":
    unittest.main()
