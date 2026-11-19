import importlib.util
from pathlib import Path
import unittest

P = Path(__file__).resolve().parents[1] / "scripts/prepare_2026_l1_blind_reconstruction.py"
spec = importlib.util.spec_from_file_location("blind_reconstruction", P)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def sample(**changes):
    row = {
        "verification_status": "VERIFIED",
        "record_id": "2026-L1-001",
        "application_id": "BLA125745",
        "review_cycle": "INITIAL",
        "supplement": "NONE",
        "drug": "Example",
        "pdufa_date": "2026-01-10",
        "outcome_action_date": "2026-01-09",
        "evidence_cutoff_at": "",
        "prediction_frozen_at": "",
        "latest_evidence_published_at": "",
        "prediction_kind": "OUTCOME_AWARE",
        "assessment_kind": "OUTCOME_AWARE",
        "actual_outcome": "CRL",
        "assessment": "CRL",
        "rationale": "FDA issued a CRL",
    }
    row.update(changes)
    return row

class BlindReconstructionTests(unittest.TestCase):
    def test_outcome_never_exposed_in_queue(self):
        result = mod.queue_rows([sample()])
        self.assertEqual(len(result), 1)
        self.assertNotIn("actual_outcome", result[0])
        self.assertNotIn("assessment", result[0])
        self.assertNotIn("rationale", result[0])
        self.assertEqual(result[0]["blind_reconstruction_status"],
                         "RECONSTRUCT_FROM_ARCHIVED_PREDECISION_SOURCES")

    def test_dates_require_independent_source_packet_audit(self):
        row = sample(evidence_cutoff_at="2026-01-01",
                     prediction_frozen_at="2026-01-02",
                     latest_evidence_published_at="2025-12-30")
        self.assertEqual(mod.queue_rows([row])[0]["blind_reconstruction_status"],
                         "AUDIT_FROZEN_SOURCE_PACKET")

    def test_postdecision_freeze_is_not_blind(self):
        row = sample(evidence_cutoff_at="2026-01-01",
                     prediction_frozen_at="2026-01-10",
                     latest_evidence_published_at="2025-12-30")
        self.assertEqual(mod.queue_rows([row])[0]["blind_reconstruction_status"],
                         "RECONSTRUCT_FROM_ARCHIVED_PREDECISION_SOURCES")

    def test_unverified_cycles_excluded(self):
        self.assertEqual(mod.queue_rows([sample(verification_status="UNRESOLVED")]), [])

if __name__ == "__main__":
    unittest.main()
