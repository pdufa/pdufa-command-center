"""Offline safety tests for the first-ten financing research audit."""
import csv
import hashlib
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError

from scripts.financing_first10_audit import (
    audit, closing_context, retrieve, valid_identity, validate_source,
)


class First10AuditTests(unittest.TestCase):
    def test_identity_must_have_real_contact_format(self):
        self.assertFalse(valid_identity('Mozilla'))
        self.assertFalse(valid_identity('PDUFA Research'))
        self.assertTrue(valid_identity('PDUFA Research research@example.org'))

    def test_url_is_issuer_scoped_and_not_arbitrary_domain(self):
        url = 'https://www.sec.gov/Archives/edgar/data/1234567/000123456726000001/closing.htm'
        self.assertTrue(validate_source(url, '0001234567'))
        self.assertFalse(validate_source(url, '0007654321'))
        self.assertFalse(validate_source(url.replace('www.sec.gov', 'evil.org'), '0001234567'))
        self.assertFalse(validate_source(url+'?file=bad', '0001234567'))

    def test_403_fails_closed(self):
        url = 'https://www.sec.gov/Archives/edgar/data/1234567/000123456726000001/closing.htm'
        def deny(req, timeout):
            raise HTTPError(req.full_url, 403, 'Forbidden', {}, None)
        with self.assertRaisesRegex(RuntimeError, 'SEC_403'):
            retrieve(url, 'PDUFA Research contact@example.org', opener=deny)

    def test_match_is_only_a_candidate(self):
        text = 'On October 3, 2026, the Company completed a registered direct offering of securities.'
        self.assertTrue(closing_context(text, '2026-10-03'))
        self.assertEqual(closing_context(text, '2026-10-05'), '')
        self.assertEqual(closing_context('The offering is expected to close on October 3, 2026.', '2026-10-03'), '')

    def test_no_automated_closed_or_entry_ready(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            (p/'registry.csv').write_text('ticker,company,cik10\nABCD,Test,0001234567\n', encoding='utf-8')
            source = 'https://www.sec.gov/Archives/edgar/data/1234567/000123456726000001/closing.htm'
            with (p/'ledger.csv').open('w', newline='', encoding='utf-8') as f:
                w=csv.DictWriter(f, fieldnames=['event_key', 'second_financing_status', 'second_financing_audit_status', 'second_financing_date', 'second_financing_source'])
                w.writeheader()
                w.writerow({'event_key':'ABCD|EVENT', 'second_financing_status':'CLOSED', 'second_financing_audit_status':'VERIFIED_SECOND_POST_PHASE3_FINANCING', 'second_financing_date':'2026-10-03', 'second_financing_source':source})
                w.writerow({'event_key':'ABCD|OTHER', 'second_financing_status':'', 'second_financing_audit_status':'NO_SECOND_POST_PHASE3_CLOSE_VERIFIED', 'second_financing_date':'', 'second_financing_source':''})
            def fetcher(url, agent):
                return hashlib.sha256(b'file').hexdigest(), 'On October 3, 2026, the Company completed its public offering.'
            rows = audit(p/'ledger.csv', p/'registry.csv', live=True,
                         agent='PDUFA Research contact@example.org', fetcher=fetcher, sleep=lambda x:None)
            self.assertEqual(rows[0]['sec_retrieval'], 'FETCHED_CANDIDATE_HUMAN_REVIEW_REQUIRED')
            self.assertEqual(rows[1]['sec_retrieval'], 'NO_SECOND_CLOSE_SOURCE_TO_CHECK')
            self.assertTrue(all(r['independent_closure_verified']=='NO' and r['entry_ready']=='NO' for r in rows))
            offline=audit(p/'ledger.csv', p/'registry.csv')
            self.assertEqual(offline[0]['sec_retrieval'], 'OFFLINE_PENDING_SEC_CHECK')
            self.assertEqual(offline[1]['sec_retrieval'], 'NO_SECOND_CLOSE_SOURCE_TO_CHECK')


if __name__ == '__main__':
    unittest.main()
