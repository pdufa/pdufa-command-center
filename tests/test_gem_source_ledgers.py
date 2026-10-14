"""Prevent silent GEM search corruption and false Phase 3 financing promotions."""
from __future__ import annotations

import csv
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_gem_source_ledgers import validate


ROOT = Path(__file__).resolve().parents[1] / "data"


class GEMSearchLedgerValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for file in ("pdufa_candidates.csv", "second_financing_status.csv"):
            shutil.copy(ROOT / file, self.root / file)

    def rewrite(self, file, transform):
        path = self.root / file
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        transform(rows)
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=rows[0])
            writer.writeheader()
            writer.writerows(rows)

    def test_current_ledgers_have_no_shifted_rows_or_unqualified_finances(self):
        result = validate(ROOT)
        self.assertGreaterEqual(result["regulatory_programs"], 45)
        self.assertGreaterEqual(result["financing_block_programs"], 38)
        self.assertEqual(result["core_source_audited_programs"], 6)
        self.assertFalse(result["manual_entry_authorized"])

    def test_malformed_pdufa_field_cannot_enter_search(self):
        def corrupt(rows):
            next(x for x in rows if x["ticker"] == "NTLA")["pdufa_date"] = "presbyopia"
        self.rewrite("pdufa_candidates.csv", corrupt)
        with self.assertRaisesRegex(ValueError, "pdufa_date"):
            validate(self.root)

    def test_shifted_company_cell_cannot_enter_search(self):
        def corrupt(rows):
            next(x for x in rows if x["ticker"] == "MLYS")["company"] = '"Mineralys Therapeutics'
        self.rewrite("pdufa_candidates.csv", corrupt)
        with self.assertRaisesRegex(ValueError, "broken CSV quote"):
            validate(self.root)

    def test_phase2_sumit_cannot_be_promoted_as_gem(self):
        def corrupt(rows):
            row = next(x for x in rows if "NONADVSM" in x["event_key"])
            row.update(
                second_financing_status="CLOSED", second_financing_closed="YES",
                second_financing_audit_status="VERIFIED_SECOND_POST_PHASE3_FINANCING"
            )
        self.rewrite("second_financing_status.csv", corrupt)
        with self.assertRaisesRegex(ValueError, "premature GEM financing promotion"):
            validate(self.root)


if __name__ == "__main__":
    unittest.main()
