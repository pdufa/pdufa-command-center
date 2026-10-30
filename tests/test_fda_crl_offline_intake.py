import hashlib
import tempfile
import unittest
from pathlib import Path

from research.fda_crl_offline_intake import inspect_fda_pdf


class OfflineCRLIntakeTests(unittest.TestCase):
    def test_hash_does_not_certify(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.pdf"
            payload = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
            path.write_bytes(payload)
            result = inspect_fda_pdf(path, application="NDA218607",
                                    action_date="2025-06-27",
                                    public_available_on="2025-07-01")
            self.assertEqual(result["sha256"], hashlib.sha256(payload).hexdigest())
            self.assertFalse(result["fda_authenticity_verified"])
            self.assertFalse(result["eligible_for_predecision_science"])
            self.assertFalse(result["trading_authorized"])

    def test_partial_file_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.pdf"
            path.write_bytes(b"%PDF-1.4\ntruncated")
            with self.assertRaises(ValueError):
                inspect_fda_pdf(path, application="NDA218607",
                               action_date="2025-06-27")

    def test_availability_before_action_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "source.pdf"
            path.write_bytes(b"%PDF-1.4\n%%EOF\n")
            with self.assertRaises(ValueError):
                inspect_fda_pdf(path, application="NDA218607",
                               action_date="2025-06-27",
                               public_available_on="2025-06-26")


if __name__ == "__main__":
    unittest.main()
