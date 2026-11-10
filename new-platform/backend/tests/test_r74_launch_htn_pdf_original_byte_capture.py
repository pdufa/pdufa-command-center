"""MAIN R74: fail-closed original PDF capture tests; all traffic mocked."""
from __future__ import annotations
import json
import sys
import unittest
from pathlib import Path
from pypdf import PdfWriter

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"/"scripts"))
from capture_launch_htn_original_pdf_bytes_r74 import (
    process,review_pdf,MAX_PDF_BYTES,RECEIPT_SCHEMA
)

def fixtures():
    return (
      json.loads((ROOT/"frontend"/"data"/"focus-r73-launch-htn-original-document-index.json").read_text()),
      json.loads((ROOT/"frontend"/"data"/"focus-r71-five-main-publication-source-review.json").read_text())
    )

def make_pdf():
    from io import BytesIO
    p=PdfWriter()
    p.add_blank_page(width=612,height=792)
    b=BytesIO(); p.write(b)
    return b.getvalue()

class PDFOriginalR74(unittest.TestCase):
    def test_mock_seven_pdfs_capture_hashes_not_original_signed_saps(self):
        man,r71=fixtures()
        pdf=make_pdf()
        def fetch(url):
            self.assertTrue(url.startswith("https://pmc.ncbi.nlm.nih.gov/articles/instance/12210145/bin/"))
            return pdf,url
        out=process(man,r71,fetch)
        self.assertEqual(out["schema"],RECEIPT_SCHEMA)
        self.assertEqual(out["originalIndexedSourceCount"],7)
        self.assertEqual(out["actualSourcePdfByteReceipts"],7)
        self.assertEqual(out["sourceDocumentsUnverified"],0)
        self.assertEqual(out["status"],"ALL_PDF_BYTES_CAPTURED_RESEARCH_ONLY")
        self.assertTrue(all(x["pdfPageCount"]==1 for x in out["records"]))
        self.assertTrue(all(len(x["sourcePdfSha256"])==64 for x in out["records"]))
        self.assertFalse(out["rawPdfBytesArchivedInPublicArtifact"])
        self.assertEqual(out["independentlyAuthenticatedHistoricalFirstPublicDates"],0)
        self.assertEqual(out["independentlyAuthenticatedProspectiveSapSignatures"],0)
        self.assertEqual(out["signedScientificReviews"],0)
        self.assertIsNone(out["clinicalGrade"])
        self.assertEqual(out["futureFDAOutcome"],"ABSTAIN")

    def test_non_pdf_html_truncation_and_excess_size_rejected(self):
        with self.assertRaisesRegex(ValueError,"RESPONSE_NOT_A_PDF"):
            review_pdf(b"<html>Preparing to download...</html>")
        with self.assertRaisesRegex(ValueError,"PDF_SIZE_INVALID"):
            review_pdf(b"%PDF-"+b"x"*10)
        with self.assertRaisesRegex(ValueError,"PDF_SIZE_INVALID"):
            review_pdf(b"%PDF-"+b"x"*MAX_PDF_BYTES)

    def test_html_interstitials_partial_and_network_failures_remain_unverified(self):
        man,r71=fixtures()
        good=make_pdf()
        def fetch(url):
            if url.endswith("s001.pdf"):return good,url
            if url.endswith("s002.pdf"):return b"<html>Preparing to download...</html>",url
            raise TimeoutError("timed out")
        out=process(man,r71,fetch)
        self.assertEqual(out["actualSourcePdfByteReceipts"],1)
        self.assertEqual(out["sourceDocumentsUnverified"],6)
        self.assertEqual(out["status"],"PARTIAL_SOURCE_CAPTURE")
        self.assertEqual(out["records"][1]["failureCode"],"RESPONSE_NOT_A_PDF")
        self.assertEqual(out["records"][2]["failureCode"],"SOURCE_ACCESS_FAILED")
        self.assertEqual(out["validatedFDAForecasts"],0)

    def test_tampered_roster_source_index_refused_before_network(self):
        man,r71=fixtures()
        man["documents"][0]["filename"]="modified.pdf"
        def no_network(url):
            raise AssertionError("must not reach network")
        with self.assertRaises(ValueError):
            process(man,r71,no_network)

if __name__=="__main__":unittest.main()
