import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_phase3_marketcap_snapshot_freshness import audit

class DatedMarketCapAuditTests(unittest.TestCase):
    def test_130_original_issuer_snapshots_are_not_live_verification(self):
        report = audit(datetime.now(timezone.utc))
        self.assertEqual(report["saved_issuer_snapshots_examined"], 130)
        self.assertEqual(report["original_census_trials"], 741)
        self.assertEqual(len(report["issuers"]), 130)
        self.assertEqual(sum(report["saved_snapshot_range_counts"].values()), 130)
        self.assertEqual(sum(report["freshness_dispositions"].values()), 130)
        self.assertEqual(report["live_market_cap_verified_count"], 0)
        self.assertIsNone(report["qualified_pipeline_count"])
        self.assertTrue(all(x["live_market_cap_verified"] is False and x["qualified_pipeline"] is None for x in report["issuers"]))
    def test_saved_snapshot_older_than_day_is_not_current(self):
        report = audit(datetime.now(timezone.utc) + timedelta(days=5))
        self.assertEqual(report["freshness_dispositions"]["STALE_SNAPSHOT_RECHECK_REQUIRED"], 130)

if __name__ == "__main__":
    unittest.main()
