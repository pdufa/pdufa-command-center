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


    def test_month_only_completion_is_research_never_verified(self):
        text = ("In July 2026, we completed an underwritten public offering "
                "of 21,045,000 shares of common stock. The net proceeds from "
                "the offering were approximately $405.0 million.")
        found = mod.monthly_completed_clauses(text, date(2026, 10, 15))
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][0], "2026-07")
        self.assertIn("$405.0 million", found[0][1])
        self.assertEqual(mod.monthly_completed_clauses(
            text.replace("completed", "expect to complete"),
            date(2026, 10, 15)), [])
        self.assertEqual(mod.monthly_completed_clauses(
            text.replace("July", "December"),
            date(2026, 10, 15)), [])

        class MonthOnly(FakeVerifier):
            def document(self, url):
                return "", text if url.endswith("quarterly.htm") else ""
            def financing(self, event):
                self.probes.append(event)
                raise AssertionError("A month-only description cannot run exact-day verification")
        v = MonthOnly()
        rows = mod.discover(v, [issue(EVENT_A["event_key"])],
                            [EVENT_A], sleep=lambda _: None)
        research = [r for r in rows if r["discovery_status"] == "MONTH_ONLY_FINANCING_REVIEW"]
        self.assertEqual(len(research), 1)
        self.assertEqual(research[0]["candidate_close_date"], "")
        self.assertEqual(research[0]["period_hint"], "2026-07")
        self.assertEqual(research[0]["date_precision"], "MONTH_ONLY")
        self.assertEqual(research[0]["trade_entry_authorized"], "NO")
        self.assertEqual(v.probes, [])

    def test_same_exact_close_repeated_in_multiple_filings_is_one_research_row(self):
        class RepeatedVerifier(FakeVerifier):
            def document(self, url):
                return "", ("On June 1, 2026, the Company closed an "
                            "underwritten public offering of common stock "
                            "with net proceeds of $125.0 million.")
            def financing(self, event):
                self.probes.append(event)
                return {"verification_status": "VERIFIED",
                        "source_url": event["financing_evidence_url"],
                        "source_sha256": "c" * 64,
                        "evidence": "On June 1, 2026, closed $125m offering",
                        "reason": "Exact completed transaction only"}
        rows = mod.discover(RepeatedVerifier(),
                            [issue(EVENT_A["event_key"]), issue(EVENT_B["event_key"])],
                            [EVENT_A, EVENT_B], sleep=lambda _: None)
        self.assertEqual(len(rows), 2)
        self.assertEqual({r["candidate_close_date"] for r in rows}, {"2026-06-01"})
        self.assertTrue(all(r["discovery_status"] == "VERIFIED_TRANSACTION_ONLY"
                            for r in rows))
        self.assertTrue(all(r["date_precision"] == "EXACT_DAY"
                            for r in rows))



if __name__ == "__main__":
    unittest.main()
