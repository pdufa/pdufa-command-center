import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from unittest.mock import patch
from xml.sax.saxutils import escape

from scripts import focus_telegram_news as news
from scripts.telegram_scan_alert import message


class FocusTelegramNewsTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 10, 18, 0, tzinfo=timezone.utc)
        self.roster = {"CYTK": {"company": "Cytokinetics, Inc.", "ncts": {"NCT06081894"}}}

    def _rss(self, title, when=None, url="https://news.google.com/rss/articles/abc"):
        when = when or self.now
        return (f"<rss version='2.0'><channel><item><title>{escape(title)}</title>"
                f"<description>{escape(title)}</description><link>{url}</link>"
                f"<pubDate>{format_datetime(when)}</pubDate></item></channel></rss>").encode()

    def _candidate(self, title="Cytokinetics reports Phase 3 clinical trial results"):
        return {"key": "media:CYTK:https://news.google.com/rss/articles/abc",
                "ticker": "CYTK", "kind": "UNVERIFIED_MEDIA_HEADLINE",
                "title": title, "description": title, "url": "https://news.google.com/rss/articles/abc",
                "published": self.now.isoformat(), "drug": "", "ncts": [],
                "priority": "HIGH — verify source"}

    def test_canonical_ticker_accepts_legal_suffix_but_not_different_issuer(self):
        with tempfile.TemporaryDirectory() as temp:
            rfile = Path(temp) / "focus.json"
            records = [
                {"ticker": "CYTK", "nct": "NCT06081894", "company": "Cytokinetics"},
                {"ticker": "CYTK", "nct": "NCT00000001", "company": "Cytokinetics, Inc."},
            ]
            rfile.write_text(json.dumps({"records": records}))
            with patch.object(news, "ROSTER", rfile):
                self.assertEqual(len(news.roster()["CYTK"]["ncts"]), 2)
                records[-1]["company"] = "Different Biopharma Inc."
                rfile.write_text(json.dumps({"records": records}))
                with self.assertRaises(ValueError):
                    news.roster()

    def test_ticker_specific_media_lead_never_becomes_verified_fda_news(self):
        items = news.google_rss_candidates("CYTK", "Cytokinetics, Inc.",
                                           self._rss("Cytokinetics reports Phase 3 results"), self.now)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["kind"], "UNVERIFIED_MEDIA_HEADLINE")
        self.assertIn("verify", items[0]["priority"])

    def test_unrelated_and_old_news_does_not_alert(self):
        not_company = news.google_rss_candidates("CYTK", "Cytokinetics, Inc.",
                                                 self._rss("AXSM FDA trial news"), self.now)
        stale = news.google_rss_candidates(
            "CYTK", "Cytokinetics, Inc.",
            self._rss("Cytokinetics Phase 3 results", self.now - timedelta(days=8)),
            self.now)
        self.assertEqual(not_company, [])
        self.assertEqual(stale, [])

    def test_exact_fda_crosswalk_does_not_invent_verified_action(self):
        base = {"feedStatus": "LIVE_FDA_RSS", "articles": [{
            "ticker": "CYTK", "ncts": ["NCT06081894"], "kind": "FDA_ARTICLE",
            "verification": "OFFICIAL_FDA_PUBLICATION",
            "matchStatus": "UNREVIEWED_EXACT_DRUG_MENTION",
            "title": "Aficamten FDA update", "description": "FDA publication",
            "sourceUrl": "https://www.fda.gov/news-events/aficamten",
            "publishedAt": self.now.isoformat(), "drug": "aficamten"
        }]}
        found = news.fda_candidates(base, self.roster, self.now)
        self.assertEqual(len(found), 1)
        self.assertIn("UNREVIEWED", found[0]["kind"])
        self.assertIn("not proof", news.alert_details(found[0], False).lower())
        base["articles"][0]["ncts"] = ["NCT99999999"]
        self.assertFalse(news.fda_candidates(base, self.roster, self.now))

    def test_baseline_deduplication_and_amendment_realert(self):
        delivered = []
        with tempfile.TemporaryDirectory() as temp:
            state = str(Path(temp) / "state.json")
            first = self._candidate()
            newer = self._candidate("Cytokinetics reports AMENDED Phase 3 clinical trial results")
            sample = [first]
            def load(_roster, _now):
                return {a["key"]: a for a in sample}, []
            def sender(args):
                delivered.append(args)
                return 0
            with patch.object(news, "roster", return_value=self.roster):
                news.check_and_send(state, self.now, load=load, sender=sender)
                self.assertEqual(delivered, [])
                news.check_and_send(state, self.now, load=load, sender=sender)
                self.assertEqual(delivered, [])
                sample[:] = [newer]
                news.check_and_send(state, self.now, load=load, sender=sender)
                self.assertEqual(len(delivered), 1)
                self.assertIn("AMENDED", delivered[0][-1])
                news.check_and_send(state, self.now, load=load, sender=sender)
                self.assertEqual(len(delivered), 1)

    def test_failed_delivery_retries_and_outage_does_not_destroy_state(self):
        with tempfile.TemporaryDirectory() as temp:
            state = str(Path(temp) / "state.json")
            one, two = self._candidate(), self._candidate("Cytokinetics FDA trial delay")
            latest = [one]
            def load(_roster, _now):
                return {n["key"]: n for n in latest}, []
            sends = []
            def fail_then_pass(args):
                sends.append(args)
                return 1 if len(sends) == 1 else 0
            with patch.object(news, "roster", return_value=self.roster):
                news.check_and_send(state, self.now, load=load, sender=fail_then_pass)
                latest[:] = [two]
                news.check_and_send(state, self.now, load=load, sender=fail_then_pass)
                saved = json.loads(Path(state).read_text())
                self.assertEqual(saved["seen"][one["key"]]["fingerprint"], news.fingerprint(one))
                news.check_and_send(state, self.now, load=load, sender=fail_then_pass)
                self.assertEqual(len(sends), 2)
                with self.assertRaises(RuntimeError):
                    news.check_and_send(state, self.now,
                                        load=lambda *_: ({}, ["unavailable"] * 2),
                                        sender=fail_then_pass)

    def test_focus_event_is_scoped_and_normal_test_still_works(self):
        text = message("focus-news", details="CYTK | New clinical source")
        self.assertIn("FOCUS", text)
        self.assertIn("CYTK", text)
        self.assertIn("TELEGRAM TEST", message("test"))


if __name__ == "__main__":
    unittest.main()
