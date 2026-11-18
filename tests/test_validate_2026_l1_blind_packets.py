"""Unit tests for blind packet provenance gate; no outcome labels are loaded."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/validate_2026_l1_blind_packets.py"
spec = importlib.util.spec_from_file_location("validate_blind_packets", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

def packet(**changes):
    p = {
        "predecision_evidence_cutoff": "2026-01-08",
        "historical_source_urls": "https://example.org/2025-study",
        "source_publication_dates": "2025-08-01",
        "source_content_hashes": "a" * 64,
    }
    p.update(changes)
    return p

class ProvenanceGateTests(unittest.TestCase):
    def test_valid_dates_still_require_independent_review(self):
        self.assertEqual(module.inspect_packet(packet()),
                         "SOURCE_PACKET_DATE_CHECK_PASSED_REQUIRES_INDEPENDENT_BLIND_REVIEW")

    def test_postcutoff_source_is_blocked(self):
        self.assertEqual(module.inspect_packet(packet(source_publication_dates="2026-01-09")),
                         "BLOCKED_POSTCUTOFF_SOURCE")

    def test_missing_source_hash_is_blocked(self):
        self.assertIn("SOURCE_CONTENT_HASHES",
                      module.inspect_packet(packet(source_content_hashes="")))

    def test_invalid_hash_is_blocked(self):
        self.assertEqual(module.inspect_packet(packet(source_content_hashes="not-a-hash")),
                         "BLOCKED_INVALID_SOURCE_HASH")

    def test_source_count_mismatch_is_blocked(self):
        self.assertEqual(module.inspect_packet(packet(
            historical_source_urls="https://example.org/a;https://example.org/b")),
            "BLOCKED_SOURCE_PROVENANCE_MISMATCH")

if __name__ == "__main__":
    unittest.main()
