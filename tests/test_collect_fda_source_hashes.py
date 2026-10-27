import unittest
from scripts.collect_fda_source_hashes import collect, permitted_fda_pdf


class FakeResponse:
    status = 200
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def read(self, n): return b"%PDF-1.7\n" + b"safe source bytes"


class FakeOpener:
    def open(self, req, timeout): return FakeResponse()


class SourceHashTests(unittest.TestCase):
    def test_only_official_pdf_urls_allowed(self):
        self.assertTrue(permitted_fda_pdf("https://www.accessdata.fda.gov/drugsatfda_docs/appletter/2026/a.pdf"))
        self.assertFalse(permitted_fda_pdf("https://www.accessdata.fda.gov.evil.example/a.pdf"))
        self.assertFalse(permitted_fda_pdf("http://www.fda.gov/a.pdf"))
        self.assertFalse(permitted_fda_pdf("https://www.fda.gov/a.html"))

    def test_hash_never_promotes_candidate(self):
        row = {"application_id": "NDA221276", "official_source_url": "https://www.fda.gov/a.pdf"}
        result = collect([row], opener=FakeOpener())
        self.assertEqual(result["records"][0]["status"], "BYTES_HASHED_NOT_ADJUDICATED")
        self.assertEqual(len(result["records"][0]["sha256"]), 64)
        self.assertEqual(result["model_eligible"], 0)
        self.assertFalse(result["records"][0]["independently_verified"])

    def test_nonofficial_source_blocked(self):
        result = collect([{"official_source_url": "https://example.org/a.pdf"}], opener=FakeOpener())
        self.assertEqual(result["records"][0]["status"], "BLOCKED_NOT_ALLOWLISTED_FDA_PDF")


if __name__ == "__main__":
    unittest.main()
