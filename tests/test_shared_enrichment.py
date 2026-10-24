"""Evidence isolation, missingness, financial and market calculation acceptance."""
import copy
import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import shared_enrichment as shared
from scripts import collect_shared_enrichment as collector

ROOT = Path(__file__).resolve().parents[1]
TODAY = date(2026, 10, 23)
URL = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000000123.json'


def financial(cash=60, flow=-30, months=3):
    meta = dict(form='10-Q', accession='0000000123-26-000001', filed='2026-08-01', period_end='2026-06-30')
    return dict(ticker='ABC', cik='0000000123', as_of='2026-10-22', cash_usd=cash,
                operating_cash_flow_usd=flow, operating_cash_flow_months=months,
                cash_includes_restricted=False, review_flags=[], shares_outstanding=0,
                current_debt_usd=0, noncurrent_debt_usd=0,
                evidence=dict(companyfacts_url=URL, cash=meta, operating_cash_flow=meta,
                              shares=meta, current_debt=meta, noncurrent_debt=meta))


class CalculationTests(unittest.TestCase):
    def test_cash_only_runway_and_explicit_reported_zero(self):
        issuer = shared.Issuer('ABC', TODAY)
        shared.financial_fields(issuer, financial(), '123')
        self.assertEqual(issuer.company['monthly_burn'][:2], [10, 'CALCULATED'])
        self.assertEqual(issuer.company['cash_runway'][:2], [6, 'CALCULATED'])
        self.assertEqual(issuer.company['debt'][:2], [0, 'OBSERVED'])
        self.assertEqual(issuer.company['shares'][0], 0)
        self.assertEqual(issuer.company['cash_runway'][4], '2026-10-22')
        self.assertNotIn('approved_sales', issuer.company)

    def test_unusable_financial_inputs_never_become_current_runway(self):
        for change in ({'cash_includes_restricted': True}, {'operating_cash_flow_usd': 0},
                       {'operating_cash_flow_usd': 30}, {'operating_cash_flow_months': 6},
                       {'cik': '999'}):
            with self.subTest(change=change):
                issuer = shared.Issuer('ABC', TODAY)
                shared.financial_fields(issuer, {**financial(), **change}, '123')
                self.assertNotIn('cash_runway', issuer.company)
        for stamp, expected in [('2026-10-01', 'STALE'), ('2026-10-24', 'REVIEW')]:
            issuer = shared.Issuer('ABC', TODAY)
            shared.financial_fields(issuer, {**financial(), 'as_of': stamp}, '123')
            self.assertEqual(issuer.company['cash_runway'][1], expected)
        issuer = shared.Issuer('ABC', TODAY)
        source = financial()
        source['evidence']['operating_cash_flow'] = {**source['evidence']['operating_cash_flow'], 'period_end': '2026-03-31'}
        shared.financial_fields(issuer, source, '123')
        self.assertNotIn('cash_runway', issuer.company)

    def test_market_indicator_reference_values_and_no_short_history_fabrication(self):
        from datetime import timedelta
        days = [TODAY-timedelta(days=i) for i in range(350)]
        days = sorted(d for d in days if d.weekday() < 5)[-220:]
        bars = [dict(date=d.isoformat(), close=100, volume=10, high=101, low=99) for d in days]
        result = shared.market_metrics(bars)
        self.assertEqual(result['sma200'], 100)
        self.assertEqual(result['rsi14'], 50)
        self.assertEqual(result['atr14'], 2)
        self.assertEqual(result['relative_volume'], 1)
        self.assertEqual(result['volatility20'], 0)
        self.assertEqual(result['macd'], dict(line=0, signal=0, histogram=0))
        short = [{k: v for k, v in b.items() if k not in ('high', 'low')} for b in bars[-35:]]
        result = shared.market_metrics(short)
        self.assertNotIn('atr14', result)
        self.assertNotIn('sma50', result)
        self.assertNotIn('sma200', result)
        short[-1]['volume'] = 20
        self.assertEqual(shared.market_metrics(short)['relative_volume'], 2)
        for invalid in (short+[short[-1]], [dict(short[0], close=float('nan'))]):
            with self.assertRaises(ValueError):
                shared.market_metrics(invalid)


class PublicationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/'data').glob('*') if p.is_file()}
        cls.index, cls.shards = shared.build(ROOT/'data', today=TODAY, now='2026-10-23T10:00:00Z')

    def test_all_fifty_fields_reconcile_on_all_three_lists_without_mutating_sources(self):
        self.assertEqual(len(self.index['fields']), 50)
        draft = json.loads((ROOT/'new-platform/backend/config/enrichment_field_registry.json').read_text())
        self.assertEqual([f['id'] for f in self.index['fields']], [f['key'] for f in draft['fields']])
        for stage, counts in self.index['lists'].items():
            self.assertGreater(counts['records'], 0)
            for states in counts['fields'].values():
                self.assertEqual(sum(states.values()), counts['records'])
        for path, digest in self.before.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
        for shard in self.shards.values():
            for key, record in shard['records'].items():
                self.assertTrue(key.startswith(('TRIAL|', 'APPLICATION|', 'RESULT|')))
                self.assertNotIn('programId', record)
                self.assertEqual(record['ticker'], shard['ticker'])

    def test_company_facts_are_shared_but_closings_and_fda_facts_never_spread_to_other_programs(self):
        for shard in self.shards.values():
            self.assertNotIn('pdufa_date', shard['company'])
            self.assertNotIn('financing_event', shard['company'])
            for key, record in shard['records'].items():
                if not key.startswith('APPLICATION|'):
                    self.assertNotIn('pdufa_date', record['fields'])
                    self.assertNotIn('financing_event', record['fields'])
                if 'financing_event' in record['fields']:
                    self.assertEqual(record['fields']['financing_event'][1], 'REVIEW')
        self.assertEqual(self.index['lists']['PIPELINE']['fields']['regulatory_probability']['MISSING'], self.index['lists']['PIPELINE']['records'])

    def test_failed_optional_collection_reports_missing_configuration_and_keeps_original_dates(self):
        from scripts import shared_enrichment
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with (root/'company_registry.csv').open('w') as f:
                f.write('ticker,cik10,company\nABC,123,Example\n')
            (root/'gem_runway_evidence.json').write_text(json.dumps({'snapshots': [financial()]}))
            with patch.object(collector, 'build', return_value=({}, {'ABC': {}})), patch.object(collector, '_credentials', return_value=None), patch.dict('os.environ', {'SEC_USER_AGENT': ''}):
                result = collector.collect(root, now=datetime(2026, 10, 23, 20, tzinfo=timezone.utc), scanner=lambda *a, **k: self.fail('No SEC request without contact identity'))
            self.assertEqual(result['market']['configuration'], 'ALPACA_NOT_CONFIGURED')
            self.assertEqual(result['financial']['attempted'], 0)
            saved = json.loads((root/'shared_financials.json').read_text())
            self.assertEqual(saved['snapshots'][0]['as_of'], '2026-10-22')

    def test_rotation_moves_failed_issuers_behind_untouched_issuers(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root/'company_registry.csv').write_text('ticker,cik10,company\nAAA,123,A\nBBB,124,B\n')
            attempted = []
            def scanner(symbol, **kwargs):
                attempted.append(symbol)
                raise RuntimeError('source blocked')
            with patch.object(collector, 'build', return_value=({}, {'AAA': {}, 'BBB': {}})), patch.object(collector, '_credentials', return_value=None), patch.dict('os.environ', {'SEC_USER_AGENT': 'Research contact@example.com'}):
                for _ in range(2):
                    collector.collect(root, limit=1, now=datetime(2026, 10, 23, 20, tzinfo=timezone.utc), scanner=scanner)
            self.assertEqual(attempted, ['AAA', 'BBB'])


if __name__ == '__main__':
    unittest.main()
