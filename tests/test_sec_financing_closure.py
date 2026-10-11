"""Offline safety tests for reviewed SEC financing-close evidence; no live SEC HTTP."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from sec_financing_closure import (
    _amounts, _closing_date_in_text, _document_url, candidates,
    fetch_sec_document, financing_gate, read_reviews, review_closure,
    save_review, visible_text,
)

CIK = "0001234567"
ACC = "0001234567-26-000012"
ASOF = "2026-10-10"
FILING = {
    "form": "8-K", "filed": "2026-10-06", "accession": ACC,
    "source_url": "https://www.sec.gov/Archives/edgar/data/1234567/"
                  "000123456726000012/company-8k.htm",
}
GOOD = (
    "On October 3, 2026, the Company completed its previously announced "
    "registered direct offering of common stock, resulting in gross proceeds "
    "of approximately $42.5 million and net proceeds of approximately "
    "$39.9 million."
)
CONFUSING = (
    "On October 4, 2026, the Company announced a public offering. "
    "The offering is expected to close on October 6, 2026, subject to conditions."
)
EVIDENCE_HTML = (
    "<html><head><title>SEC filing</title></head><body><p>FORM 8-K</p>"
    "<p>" + GOOD + "</p></body></html>"
)


class Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, count):
        return self.payload[:count]


def opener(req, timeout):
    if not req.full_url.startswith("https://www.sec.gov/Archives/edgar/data/1234567/"):
        raise AssertionError("Unsafe SEC URL")
    return Response(EVIDENCE_HTML.encode())


def make_doc(text=EVIDENCE_HTML):
    def fake(req, timeout):
        return Response(text.encode())
    doc = fetch_sec_document(FILING, CIK, ASOF, "PDUFA Research contact@example.org",
                             opener=fake)
    doc["ticker"] = "ABCD"
    doc["company"] = "Example Biotech"
    return doc


def event_for(doc=None, closing="2026-10-03", label="October 2026 direct offering"):
    doc = doc or make_doc()
    found = candidates(doc)
    if not found:
        raise AssertionError("Fixture has no potential completion clause")
    return review_closure(doc, found[0]["id"], closing, label,
                          reviewer_confirmed=True, as_of=ASOF)


class FinancingClosureTests(unittest.TestCase):
    def test_explicit_completed_deal_and_identifiable_amounts(self):
        doc = make_doc()
        found = candidates(doc)
        self.assertEqual(len(found), 1)
        self.assertIn("completed", found[0]["excerpt"])
        event = event_for(doc)
        self.assertEqual(event["closing_date"], "2026-10-03")
        self.assertEqual(event["gross_proceeds_usd"], 42_500_000)
        self.assertEqual(event["net_proceeds_usd"], 39_900_000)
        self.assertEqual(event["financing_type"], "REGISTERED_DIRECT")
        self.assertTrue(event["reviewed_by_user"])
        self.assertFalse(event["eligible_for_automatic_entry"])
        self.assertEqual(event["atm_status"][:12], "NOT VERIFIED")

    def test_public_offering_detected_without_atm(self):
        text = (
            "On September 30, 2026, we closed our public offering "
            "of common stock for gross proceeds of $15 million."
        )
        event = event_for(make_doc(text), closing="2026-09-30")
        self.assertEqual(event["financing_type"], "PUBLIC_OFFERING")
        self.assertEqual(event["gross_proceeds_usd"], 15_000_000)

    def test_expected_close_is_not_past_close(self):
        for text in (
            CONFUSING,
            "On October 4, 2026, the Company expects to complete its public offering.",
            "On October 4, 2026, a public offering is scheduled to close tomorrow.",
            "On October 4, 2026, the Company has not completed its private placement.",
            "On October 4, 2026, the Company will close its registered direct offering.",
            "On October 4, 2026, the Company completed an at-the-market offering.",
            "The Company's private placement of common stock closed successfully.",
            "On October 4, 2026, the Company filed an S-3 to register $50 million.",
        ):
            self.assertEqual(candidates({"text": text}), [], text)

    def test_negative_and_prospective_in_same_clause_are_rejected(self):
        s = "On October 5, 2026, the public offering would be completed if approved."
        self.assertEqual(candidates({"text": s}), [])
        s = "On October 5, 2026, the Company completed its public offering subject to customary conditions."
        self.assertEqual(candidates({"text": s}), [])

    def test_no_human_confirmation_no_record(self):
        doc = make_doc()
        with self.assertRaisesRegex(ValueError, "explicitly confirm"):
            review_closure(doc, candidates(doc)[0]["id"], "2026-10-03",
                           "October 2026 direct offering", as_of=ASOF)

    def test_date_must_match_actual_text_not_filing_date(self):
        doc = make_doc()
        with self.assertRaisesRegex(ValueError, "not explicitly stated"):
            review_closure(doc, candidates(doc)[0]["id"], "2026-10-06",
                           "October 2026 direct offering", reviewer_confirmed=True, as_of=ASOF)
        self.assertTrue(_closing_date_in_text(GOOD, "2026-10-03"))
        self.assertFalse(_closing_date_in_text(GOOD, "2026-10-06"))

    def test_no_lookahead_closing_after_filing_or_as_of(self):
        doc = make_doc()
        with self.assertRaisesRegex(ValueError, "Closure date"):
            review_closure(doc, candidates(doc)[0]["id"], "2026-10-15",
                           "October 2026 direct offering", reviewer_confirmed=True, as_of=ASOF)
        with self.assertRaisesRegex(ValueError, "Closure date"):
            review_closure(doc, candidates(doc)[0]["id"], "2026-10-03",
                           "October 2026 direct offering", reviewer_confirmed=True,
                           as_of="2026-09-01")

    def test_src_8k_issuer_path_is_enforced(self):
        info, url = _document_url(FILING, CIK, ASOF)
        self.assertEqual(info["cik"], CIK)
        self.assertEqual(url, FILING["source_url"])
        with self.assertRaises(ValueError):
            _document_url(FILING, "0002222222", ASOF)
        with self.assertRaises(ValueError):
            _document_url({**FILING, "form": "424B5"}, CIK, ASOF)
        with self.assertRaises(ValueError):
            _document_url({**FILING, "filed": "2026-11-20"}, CIK, ASOF)
        with self.assertRaises(ValueError):
            _document_url({**FILING, "source_url": "https://evil.org/Archives/file"}, CIK, ASOF)

    def test_exhibit_filename_limited_to_same_filing_archive(self):
        _, url = _document_url(FILING, CIK, ASOF, "ex99-1.htm")
        self.assertTrue(url.endswith("/ex99-1.htm"))
        for invalid in ("../../bad.htm", "https://evil.org/x.htm", "bad.pdf",
                        "ex%2f99-1.htm", "x.htm?evil=1", "bad.js"):
            with self.assertRaises(ValueError, msg=invalid):
                _document_url(FILING, CIK, ASOF, invalid)

    def test_sec_403_and_missing_identity_do_not_verify(self):
        def blocked(req, timeout):
            raise HTTPError(req.full_url, 403, "Forbidden", None, None)
        with self.assertRaisesRegex(RuntimeError, "HTTP 403"):
            fetch_sec_document(FILING, CIK, ASOF,
                "PDUFA Research contact@example.org", opener=blocked)
        with self.assertRaises(ValueError):
            fetch_sec_document(FILING, CIK, ASOF, "", opener=opener)

    def test_fake_or_tampered_claim_cannot_be_saved(self):
        doc = make_doc()
        with self.assertRaisesRegex(ValueError, "not present"):
            review_closure(doc, "badbadbad", "2026-10-03",
                           "October 2026 direct offering", reviewer_confirmed=True, as_of=ASOF)
        doc["source_kind"] = "USER-PASTED"
        with self.assertRaisesRegex(ValueError, "proof"):
            review_closure(doc, candidates(doc)[0]["id"], "2026-10-03",
                           "October 2026 direct offering", reviewer_confirmed=True, as_of=ASOF)

    def test_event_ledger_and_named_financing_gate(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "sec" / "finance.sqlite3"
            self.assertEqual(read_reviews("ABCD", path), [])
            pending = financing_gate("ABCD", "October 2026 direct offering", ASOF, path, cik=CIK)
            self.assertFalse(pending["closure_verified"])
            event = event_for()
            id1 = save_review(event, path)
            self.assertEqual(save_review(event, path), id1)
            self.assertEqual(len(read_reviews("ABCD", path)), 1)
            self.assertEqual(len(read_reviews("EFGH", path)), 0)
            self.assertFalse(financing_gate("ABCD", None, ASOF, path, cik=CIK)["closure_verified"])
            self.assertFalse(financing_gate("ABCD", "different deal", ASOF, path, cik=CIK)["closure_verified"])
            self.assertFalse(financing_gate("ABCD", event["deal_label"], "2026-10-01", path, cik=CIK)["closure_verified"])
            self.assertFalse(financing_gate("ABCD", event["deal_label"], ASOF, path)["closure_verified"])
            self.assertFalse(financing_gate("ABCD", event["deal_label"], ASOF, path,
                                               cik="0009999999")["closure_verified"])
            gate = financing_gate("ABCD", event["deal_label"], ASOF, path, cik=CIK)
            self.assertTrue(gate["closure_verified"])
            self.assertFalse(gate["entry_ready"])
            self.assertIn("REVIEW", gate["status"])

    def test_record_requires_proper_status_and_attestation(self):
        with tempfile.TemporaryDirectory() as d:
            event = event_for()
            event["status"] = "ANNOUNCED"
            with self.assertRaises(ValueError):
                save_review(event, Path(d) / "db.sqlite")
            event = event_for()
            event["reviewed_by_user"] = False
            with self.assertRaises(ValueError):
                save_review(event, Path(d) / "db.sqlite")

    def test_html_parser_removes_script_and_navigation(self):
        markup = ("<html><head><title>Bad fake completed public offering</title></head>"
                  "<body><script>On October 3, 2026, the public offering completed.</script>"
                  "<p>" + GOOD + "</p></body></html>")
        visible = visible_text(markup)
        self.assertIn(GOOD, visible)
        self.assertNotIn("Bad fake", visible)
        self.assertEqual(len(candidates({"text": visible})), 1)

    def test_proceeds_without_source_remain_missing(self):
        event = event_for(make_doc(
            "On October 3, 2026, the Company completed a private placement of its common stock."),
            closing="2026-10-03")
        self.assertIsNone(event["gross_proceeds_usd"])
        self.assertIsNone(event["net_proceeds_usd"])
        self.assertEqual(_amounts("gross proceeds of $1.5 billion")["gross_proceeds_usd"],
                         1_500_000_000)


if __name__ == "__main__":
    unittest.main()
