"""MAIN R76: public JAMA original supplement links, secure path and truthful receipts."""
from __future__ import annotations
import json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"/"scripts"))
from capture_launch_htn_jama_publisher_pdfs_r76 import (
    extract_public_cdn_links,validate_candidate_url,process
)
try:
 from pypdf import PdfWriter
except ImportError:
 PdfWriter=None

def fixtures():
 return (
    json.loads((ROOT/"frontend"/"data"/"focus-r73-launch-htn-original-document-index.json").read_text()),
    json.loads((ROOT/"frontend"/"data"/"focus-r71-five-main-publication-source-review.json").read_text())
 )

def url(n):
 return f"https://cdn.jamanetwork.com/ama/content_public/journal/jama/939665/joi250041supp{n}_prod_1767895070.42223.pdf?Expires=1797137344&Signature=test-token-{n}"

class SourceIndex(unittest.TestCase):
 def test_exact_public_cdn_links_indexed_in_html(self):
  s="<html>"+''.join(f'<a href="{url(i).replace("&","&amp;")}">Supplement {i}</a>' for i in range(1,8))+"</html>"
  out=extract_public_cdn_links(s)
  self.assertEqual(set(out),set(range(1,8)))
  self.assertTrue(all(validate_candidate_url(out[i]) is not None for i in range(1,8)))

 def test_deny_unsafe_hosts_missing_signature_and_duplicate_sources(self):
  for u in [
   "http://cdn.jamanetwork.com/ama/content_public/journal/jama/939665/joi250041supp1_prod_x.pdf",
   "https://cdn.jamanetwork.com.evil.example/ama/content_public/journal/jama/939665/joi250041supp1_prod_x.pdf?Expires=1&Signature=x",
   "https://evil.example/ama/content_public/journal/jama/939665/joi250041supp1_prod_x.pdf?Expires=1&Signature=x",
   "https://cdn.jamanetwork.com/ama/content_public/journal/jama/939665/joi250041supp8_prod_x.pdf?Expires=1&Signature=x",
   "https://cdn.jamanetwork.com/ama/content_public/journal/jama/939665/joi250041supp1_prod_x.pdf"
  ]:self.assertIsNone(validate_candidate_url(u))
  with self.assertRaisesRegex(ValueError,"AMBIGUOUS"):
   extract_public_cdn_links(f'<a href="{url(1)}"></a><a href="{url(1).replace("test-token-1","test-token-2")}"></a>')

 def test_publisher_html_without_source_pdf_does_not_create_forecast(self):
  m,r=fixtures()
  report=process(m,r,links_getter=lambda:"<html>Content only, no links</html>",
      pdf_getter=lambda _:(_ for _ in ()).throw(AssertionError("no pdf allowed")))
  self.assertEqual(report["sourceLinksInPublicArticle"],0)
  self.assertEqual(report["pdfSourceByteHashReceipts"],0)
  self.assertEqual(report["unverifiedPdfSources"],7)
  self.assertEqual(report["futureFDAOutcome"],"ABSTAIN")
  self.assertFalse(report["signedCdnUrlsRetained"])
  self.assertFalse(report["copyrightedPdfBytesArchived"])

 @unittest.skipUnless(PdfWriter is not None,"Dedicated R76 workflow installs pypdf; not required for production")
 def test_mock_signed_source_bytes_hash_without_publishing_signed_url(self):
  from io import BytesIO
  writer=PdfWriter();writer.add_blank_page(width=612,height=792)
  b=BytesIO();writer.write(b);pdf=b.getvalue()
  html="<html>"+''.join(f'<a href="{url(i)}">PDF</a>' for i in range(1,8))+"</html>"
  m,r=fixtures()
  report=process(m,r,links_getter=lambda:html,pdf_getter=lambda _:pdf)
  self.assertEqual(report["pdfSourceByteHashReceipts"],7)
  self.assertEqual(report["sourceLinksInPublicArticle"],7)
  self.assertEqual(report["authenticatedPreUnblindingSapLocks"],0)
  self.assertEqual(report["validatedFDAForecasts"],0)
  self.assertEqual(report["futureFDAOutcome"],"ABSTAIN")
  self.assertTrue(all(d["pdfPageCount"]==1 for d in report["records"]))
  self.assertFalse(any("Signature" in str(d) or "Expires" in str(d) for d in report["records"]))

if __name__=="__main__":unittest.main()
