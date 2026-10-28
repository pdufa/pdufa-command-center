import json
import tempfile
import unittest
from pathlib import Path

from research.fda_crl_intake_cli import main


class FDAIntakeCLITests(unittest.TestCase):
    def test_writes_unverified_manifest_without_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            pdf = Path(directory) / "original.pdf"
            pdf.write_bytes(b"%PDF-1.4\n%%EOF\n")
            output = Path(directory) / "intake.json"
            args = ["--pdf", str(pdf), "--application", "NDA218607",
                    "--action-date", "2025-06-27",
                    "--source-url", "https://example.test/letter.pdf",
                    "--output", str(output)]
            self.assertEqual(main(args), 0)
            result = json.loads(output.read_text())
            self.assertEqual(result["status"], "HASHED_UNVERIFIED_SOURCE")
            self.assertFalse(result["eligible_for_predictive_training"])
            with self.assertRaises(SystemExit):
                main(args)
            self.assertEqual(json.loads(output.read_text()), result)

    def test_missing_pdf_does_not_create_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "intake.json"
            with self.assertRaises(FileNotFoundError):
                main(["--pdf", str(Path(directory) / "missing.pdf"),
                      "--application", "NDA218607", "--action-date", "2025-06-27",
                      "--source-url", "https://example.test/letter.pdf",
                      "--output", str(output)])
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
