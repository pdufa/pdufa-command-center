"""Check that the committed source-only FOCUS outputs replay faithfully."""

import csv
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports/scientific-levels1-6"
RECEIPTS = REPORTS / "focus-level16-registry-receipts-20261119.json.gz"
STEM = "focus-level16-current-evidence-20261119"
SPEC = importlib.util.spec_from_file_location(
    "review_focus_level16", ROOT / "scripts/medical/review_focus_level16.py"
)
review = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(review)


class FocusCurrentEvidenceTests(unittest.TestCase):
    def test_reproducible_exact_roster_results_and_abstentions(self):
        with TemporaryDirectory() as directory:
            path = Path(directory)
            output = review.export(review.read(RECEIPTS), path)
            for suffix in (".json", ".csv"):
                self.assertEqual((path / (STEM + suffix)).read_bytes(),
                                 (REPORTS / (STEM + suffix)).read_bytes())
            with (path / (STEM + ".csv")).open(encoding="utf-8", newline="") as file:
                rows = list(csv.DictReader(file))
        self.assertEqual(len(output["trials"]), 32)
        self.assertEqual(len(rows), 192)
        self.assertEqual(len({(row["nct"], row["level"]) for row in rows}), 192)
        self.assertEqual({row["fda_direction"] for row in rows}, {"ABSTAIN"})
        self.assertEqual({row["scientific_validation"] for row in rows}, {"NOT_VERIFIED"})
        self.assertEqual({row["owner_review"] for row in rows}, {"OWNER_NOT_REVIEWED"})
        self.assertFalse(output["historicalPredictionInputPermitted"])

    def test_registry_digest_mismatch_refuses_to_export(self):
        receipts = review.read(RECEIPTS)
        next(iter(receipts.values()))["input_sha256"] = "0" * 64
        with TemporaryDirectory() as directory, self.assertRaisesRegex(ValueError, "digest mismatch"):
            review.export(receipts, Path(directory))
