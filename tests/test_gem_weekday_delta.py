"""Previously supported financing evidence is reused only under immutable issuer index."""
import unittest
from datetime import date
from scripts.gem_two_close_recheck import recheck_records


EVENT = {"event_key": "ABC|STUDY", "ticker": "ABC",
         "phase3_date": "2026-01-05", "phase3_status": "POSITIVE",
         "nct_id": "NCT00000001", "trial_evidence_url": "https://clinicaltrials.gov/study/NCT00000001"}
FINANCE = {"event_key": "ABC|STUDY",
           "second_financing_audit_status": "VERIFIED_SECOND_POST_PHASE3_FINANCING",
           "first_financing_date": "2026-02-01",
           "second_financing_date": "2026-04-01",
           "first_financing_source": "https://www.sec.gov/first",
           "second_financing_source": "https://www.sec.gov/second"}
HASH = "c" * 64
PRIOR = {"event_key": "ABC|STUDY", "ticker": "ABC",
         "phase3_readout_date": "2026-01-05", "phase3_status": "POSITIVE",
         "nct_id": "NCT00000001",
         "first_close_date": "2026-02-01", "second_close_date": "2026-04-01",
         "first_sec_url": "https://www.sec.gov/first",
         "second_sec_url": "https://www.sec.gov/second",
         "first_sec_status": "VERIFIED", "second_sec_status": "VERIFIED",
         "first_sec_sha256": "a" * 64, "second_sec_sha256": "b" * 64,
         "issuer_sec_registry_sha256": HASH,
         "recheck_status": "TRANSACTIONS_RECHECKED_REVIEW",
         "checked_at_utc": "2026-10-14T12:00:00+00:00"}


class Fake:
    as_of = date(2026, 10, 15)

    def __init__(self, registry_hash=HASH, registry_status="VERIFIED"):
        self.registry_hash = registry_hash
        self.registry_status = registry_status
        self.document_checks = 0

    def registry(self, _):
        return {"verification_status": self.registry_status,
                "source_sha256": self.registry_hash}

    def financing(self, _):
        self.document_checks += 1
        return {"verification_status": "VERIFIED", "source_sha256": "e" * 64}


class RetainedPairTests(unittest.TestCase):
    def test_unchanged_issuer_keeps_historical_transaction_proof_without_refetch(self):
        v = Fake()
        result = recheck_records(v, [EVENT], [FINANCE], mode="DELTA", prior=[PRIOR])
        self.assertEqual(v.document_checks, 0)
        self.assertEqual(result[0]["recheck_status"], "TRANSACTIONS_RECHECKED_REVIEW")
        self.assertIn("CARRIED_FORWARD", result[0]["recheck_note"])
        self.assertEqual(result[0]["gem_entry_authorized"], "NO")

    def test_amendment_or_missing_sec_inventory_forces_recheck(self):
        for v in (Fake(registry_hash="d" * 64),
                  Fake(registry_status="TECHNICAL_FAILURE")):
            with self.subTest(v=v.registry_hash):
                result = recheck_records(v, [EVENT], [FINANCE], mode="DELTA", prior=[PRIOR])
                self.assertEqual(v.document_checks, 2)
                self.assertNotIn("CARRIED_FORWARD", result[0]["recheck_note"])
                self.assertEqual(result[0]["gem_entry_authorized"], "NO")

    def test_sunday_full_and_changed_trial_never_reuse(self):
        v = Fake()
        recheck_records(v, [EVENT], [FINANCE], mode="FULL", prior=[PRIOR])
        self.assertEqual(v.document_checks, 2)
        v = Fake()
        changed = {**EVENT, "nct_id": "NCT00000002"}
        recheck_records(v, [changed], [FINANCE], mode="DELTA", prior=[PRIOR])
        self.assertEqual(v.document_checks, 2)


if __name__ == "__main__":
    unittest.main()
