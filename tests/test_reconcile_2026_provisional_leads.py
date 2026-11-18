import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/reconcile_2026_provisional_leads.py"
spec = importlib.util.spec_from_file_location("provisional_reconciliation", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def ledger():
    return [{"record_id": "2026-L1-076", "classification": "UNRESOLVED"}]

def sidecar():
    return [{
        "lead_id": "2026-L1-076",
        "application_id": "NDA220936",
        "cohort_status": "PROVISIONAL_MATCH_AWAITING_PRIMARY_APPLICATION_ID",
        "application_id_source": "https://example.org/fda-derived",
    }]

class ProvisionalReconciliationTests(unittest.TestCase):
    def test_does_not_promote_secondary_application_id(self):
        result = mod.reconcile(ledger(), sidecar())
        self.assertEqual(len(result), 1)
        self.assertFalse(result[0]["promoted"])
        self.assertEqual(result[0]["ledger_classification"], "UNRESOLVED")

    def test_unknown_lead_rejected(self):
        row = sidecar()[0]
        row["lead_id"] = "2026-L1-999"
        with self.assertRaisesRegex(ValueError, "Unknown lead"):
            mod.reconcile(ledger(), [row])

    def test_duplicate_authoritative_leads_rejected(self):
        with self.assertRaisesRegex(ValueError, "Duplicate record_id"):
            mod.reconcile(ledger() * 2, sidecar())

    def test_unexpected_promotion_rejected(self):
        row = sidecar()[0]
        row["cohort_status"] = "VERIFIED"
        with self.assertRaisesRegex(ValueError, "Unexpected sidecar"):
            mod.reconcile(ledger(), [row])

    def test_missing_source_rejected(self):
        row = sidecar()[0]
        row["application_id_source"] = ""
        with self.assertRaisesRegex(ValueError, "Missing application-ID source"):
            mod.reconcile(ledger(), [row])

if __name__ == "__main__":
    unittest.main()
