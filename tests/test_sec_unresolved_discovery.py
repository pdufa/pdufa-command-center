"""SEC search is research only: no missing source or snippet can approve GEM."""
import json
import unittest
from datetime import date

from scripts import sec_unresolved_discovery as mod

CIK = "0001234567"
ACC = "0001234567-26-000111"
BASE = "https://www.sec.gov/Archives/edgar/data/1234567/000123456726000111/"
EVENT_A = {"event_key": "ABC|TRIAL_ONE", "ticker": "ABC",
           "company": "Example Bio"}
EVENT_B = {"event_key": "ABC|TRIAL_TWO", "ticker": "ABC",
           "company": "Example Bio"}


def issue(key):
    return {"event_key": key, "ticker": "ABC", "category": "SEC",
            "claim": "FINANCING_CLOSURE"}


class FakeVerifier:
    as_of = date(2026, 10, 15)

    def __init__(self, close=True, denied=False):
        self.close = close
        self.denied = denied
        self.probes = []

    def cik(self, event):
        return CIK if event.get("ticker") == "ABC" else ""

    def submissions(self, event):
        if self.denied:
            raise RuntimeError("SEC blocked")
        return "submissions", {}, {
            "form": ["8-K", "10-Q", "8-K"],
            "filingDate": ["2026-06-01", "2026-08-12", "2026-10-16"],
            "accessionNumber": [ACC, ACC, ACC],
            "primaryDocument": ["form8k.htm", "quarterly.htm", "tomorrow.htm"],
        }

    def body(self, url):
        if url.endswith("index.json"):
            return json.dumps({"directory": {"item": [
                {"name": "ex99_1.htm"}, {"name": "../not-a-document.htm"}
            ]}}).encode()
        raise AssertionError(url)

    def document(self, url):
        if url.endswith("quarterly.htm"):
            return "", ("On June 1, 2026, the Company closed an underwritten public "
                        "offering of common stock with net proceeds of $125.0 million.")
        return "", "On May 10, 2026, the Company expects to close an offering."

    def financing(self, event):
        self.probes.append(dict(event))
        if self.close and event["financing_evidence_url"].endswith("quarterly.htm"):
            return {"verification_status": "VERIFIED",
                    "source_url": event["financing_evidence_url"],
                    "source_sha256": "a" * 64,
                    "reason": "Dated exact transaction verified",
                    "evidence": "Closed June 1, 2026 with $125m net"}
        return {"verification_status": "REVIEW_REQUIRED",
                "source_url": event["financing_evidence_url"],
                "source_sha256": "",
                "reason": "No dated funded closing in SEC filing"}


class SECDiscoveryTests(unittest.TestCase):
    def test_selects_periodic_filing_and_rejects_future(self):
        filings = mod.recent_documents(FakeVerifier(), EVENT_A)
        self.assertEqual({x[3] for x in filings},
                         {"form8k.htm", "quarterly.htm"})

    def test_issuer_index_exhibits_only_safe_documents(self):
        urls = mod.indexed_documents(FakeVerifier(), CIK, "8-K", ACC, "form8k.htm")
        self.assertIn(BASE + "form8k.htm", urls)
        self.assertIn(BASE + "ex99_1.htm", urls)
        self.assertFalse(any(".." in url for url in urls))

    def test_discovery_candidates_are_not_automatic_proof(self):
        completed = ("On June 1, 2026, the Company closed an underwritten "
                     "public offering of shares with net proceeds of $125 million.")
        hints = mod.candidate_clauses(completed, date(2026, 10, 15))
        self.assertTrue(any(h[0] == "2026-06-01" for h in hints))
        future = ("The public offering is expected to close on October 27, 2026 "
                  "with anticipated net proceeds of $150 million.")
        self.assertFalse(mod.candidate_clauses(future, date(2026, 10, 15)))

    def test_requires_strict_verified_source_and_never_grants_entry(self):
        v = FakeVerifier()
        rows = mod.discover(v, [issue(EVENT_A["event_key"]),
                                issue(EVENT_B["event_key"])],
                            [EVENT_A, EVENT_B], sleep=lambda _: None)
        supported = [r for r in rows
                     if r["discovery_status"] == "VERIFIED_TRANSACTION_ONLY"]
        self.assertEqual(len(supported), 2)
        self.assertEqual({r["event_key"] for r in supported},
                         {EVENT_A["event_key"], EVENT_B["event_key"]})
        self.assertTrue(all(r["trade_entry_authorized"] == "NO"
                            and r["second_post_phase3_verified"] == "NO"
                            for r in rows))
        self.assertTrue(all(p["_recheck_exact_sec_url"] for p in v.probes))

    def test_date_keyword_only_and_blocked_source_remain_unverified(self):
        rows = mod.discover(FakeVerifier(close=False),
                            [issue(EVENT_A["event_key"])],
                            [EVENT_A], sleep=lambda _: None)
        self.assertFalse(any(r["discovery_status"] == "VERIFIED_TRANSACTION_ONLY"
                             for r in rows))
        blocked = mod.discover(FakeVerifier(denied=True),
                               [issue(EVENT_A["event_key"])],
                               [EVENT_A], sleep=lambda _: None)
        self.assertEqual(blocked[0]["discovery_status"], "SEC_SOURCE_UNAVAILABLE")
        self.assertEqual(blocked[0]["trade_entry_authorized"], "NO")

    def test_search_link_cannot_validate_filing(self):
        url = mod.google_link("Example Bio", CIK)
        self.assertIn("google.com/search", url)
        self.assertIn("1234567", url)


if __name__ == "__main__":
    unittest.main()
