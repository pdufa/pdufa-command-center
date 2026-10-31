"""Exact original archive NCT identity acceptance, without candidate promotions."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "new-platform"))
from backend.app.archive_scope_reconciliation import evidence


class ArchiveScopeEvidenceTests(unittest.TestCase):
    def snapshot(self, scope=None, physical=None, published=None, complete="COMPLETE", source="CURRENT"):
        scope = scope if scope is not None else ["NCT00000001", "NCT00000002"]
        physical = physical if physical is not None else scope
        published = published if published is not None else scope
        return evidence(scope, scope, physical, ["NCT00000001", "NCT00000003"],
                        published, ["NCT00000001"], complete, source)

    def test_proves_current_scope_and_permits_extra_catalog_and_newer_archive_records(self):
        row = self.snapshot()
        self.assertEqual(row["status"], "VERIFIED")
        self.assertEqual(row["originalScopeRecords"], 2)
        self.assertEqual(row["archivePhysicalRecords"], 2)
        self.assertEqual(row["unionDistinctTrials"], 3)
        self.assertEqual(row["catalogOutsideArchive"], 1)
        self.assertEqual(row["laterArchiveRecordsOutsideDatedManifest"], 1)
        self.assertEqual(row["missingPoolTrials"], 0)
        self.assertEqual(row["currentScopeSha256"], row["physicalArchiveSha256"])
        self.assertEqual(row["publishedPoolSha256"], row["physicalArchiveSha256"])

    def test_missing_current_nct_in_archive_or_pool_blocks(self):
        for scope, physical, published in (
            (["NCT00000001", "NCT00000002"], ["NCT00000001"], ["NCT00000001", "NCT00000002"]),
            (["NCT00000001", "NCT00000002"], ["NCT00000001", "NCT00000002"], ["NCT00000001"]),
        ):
            with self.subTest(scope=scope, physical=physical, published=published):
                row = self.snapshot(scope=scope, physical=physical, published=published)
                self.assertEqual(row["status"], "REVIEW_REQUIRED")

    def test_incomplete_download_and_stale_source_never_certify(self):
        self.assertEqual(self.snapshot(complete="PARTIAL")["status"], "REVIEW_REQUIRED")
        self.assertEqual(self.snapshot(source="STALE")["status"], "REVIEW_REQUIRED")

    def test_duplicate_or_malformed_study_ids_cannot_qualify(self):
        for values in (["NCT00000001", "NCT00000001"], ["X123"], [""], [None]):
            with self.subTest(ids=values), self.assertRaises(ValueError):
                self.snapshot(scope=values)


if __name__ == "__main__":
    unittest.main()
