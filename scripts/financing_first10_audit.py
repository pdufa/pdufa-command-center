#!/usr/bin/env python3
"""Audit ten existing PDUFA financing rows; never auto-certify a closing.

Offline is the safe default. --live requires SEC_USER_AGENT with a real
contact email. This tool neither modifies the prior research ledger nor
promotes a candidate into ENTRY READY.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / 'data/company_registry.csv'
LEDGER = ROOT / 'data/second_financing_status.csv'
ARCHIVE = re.compile(r'^/Archives/edgar/data/(\d{1,10})/(\d{18})/([A-Za-z0-9_.-]+)$')
MAX_BYTES = 6_000_000
FINANCE_WORDS = re.compile(r'\b(offering|financing|placement|securities|convertible notes|tranche)\b', re.I)
CLOSING_WORDS = re.compile(r'\b(closed|completed|consummated)\b', re.I)
NEGATIVE_WORDS = re.compile(r'\b(expects? to|will|would|subject to|not completed|not closed|proposed|upon closing)\b', re.I)


def valid_identity(agent):
    return bool(re.fullmatch(r'.{3,120}\s+[^\s@]+@[^\s@]+\.[^\s@]+', str(agent or '').strip()))


def validate_source(url, cik):
    """Enforce issuer identity before fetching; never trust ledger URL alone."""
    if not url:
        return False
    parsed = urlsplit(url)
    match = ARCHIVE.fullmatch(parsed.path)
    return bool(parsed.scheme == 'https' and parsed.netloc == 'www.sec.gov'
                and not parsed.query and not parsed.fragment and match
                and int(match.group(1)) == int(cik)
                and re.search(r'\.(?:htm|html|txt)$', match.group(3), re.I))


def closing_context(document_text, close_date):
    """Surface a *possible* dated clause, not independently verified proof."""
    if not close_date:
        return ''
    try:
        d = date.fromisoformat(close_date)
    except ValueError:
        return ''
    patterns = [d.isoformat(), f'{d.strftime("%B")} {d.day}, {d.year}',
                d.strftime('%B %d, %Y'), d.strftime('%m/%d/%Y')]
    for token in patterns:
        for m in re.finditer(re.escape(token), document_text, re.I):
            window = document_text[max(0, m.start()-230):m.end()+230]
            if (FINANCE_WORDS.search(window) and CLOSING_WORDS.search(window)
                    and not NEGATIVE_WORDS.search(window)):
                return re.sub(r'\s+', ' ', window).strip()[:500]
    return ''


def retrieve(url, agent, opener=urlopen):
    """A single compliant SEC request; never retry a 403 or disguise identity."""
    if not valid_identity(agent):
        raise ValueError('SEC_USER_AGENT must contain app name and genuine contact email')
    req = Request(url, headers={'User-Agent': agent, 'Accept': 'text/html,text/plain',
                                'Accept-Encoding': 'identity'})
    try:
        with opener(req, timeout=20) as response:
            if hasattr(response, 'geturl') and urlsplit(response.geturl()).netloc != 'www.sec.gov':
                raise RuntimeError('SEC_REDIRECT_OFF_HOST')
            blob = response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 403:
            raise RuntimeError('SEC_403_ACCESS_DENIED') from exc
        if exc.code == 429:
            raise RuntimeError('SEC_429_RATE_LIMITED') from exc
        raise RuntimeError(f'SEC_HTTP_{exc.code}') from exc
    except (URLError, OSError, TimeoutError) as exc:
        raise RuntimeError('SEC_NETWORK_UNAVAILABLE') from exc
    if len(blob) > MAX_BYTES:
        raise RuntimeError('SEC_DOCUMENT_TOO_LARGE')
    if not blob:
        raise RuntimeError('SEC_EMPTY_DOCUMENT')
    from sec_financing_closure import visible_text
    return hashlib.sha256(blob).hexdigest(), visible_text(blob)


def audit(ledger=LEDGER, registry=REGISTRY, limit=10, live=False,
          agent=None, fetcher=retrieve, sleep=time.sleep):
    if live and not valid_identity(agent):
        raise ValueError('Live SEC checks require SEC_USER_AGENT with a genuine contact email')
    with Path(registry).open(newline='', encoding='utf-8-sig') as f:
        index = {r['ticker'].upper(): r for r in csv.DictReader(f)
                 if r.get('ticker') and r.get('cik10', '').isdigit()}
    with Path(ledger).open(newline='', encoding='utf-8-sig') as f:
        records = list(csv.DictReader(f))[:limit]
    output = []
    for number, record in enumerate(records, start=1):
        key = record.get('event_key', '')
        ticker = key.split('|')[0].upper()
        issuer = index.get(ticker)
        cik = issuer['cik10'] if issuer else ''
        url = record.get('second_financing_source', '').strip()
        prior = record.get('second_financing_audit_status', '')
        row = {
            'batch_number': number, 'event_key': key, 'ticker': ticker, 'cik': cik,
            'prior_research_status': record.get('second_financing_status', ''),
            'prior_audit_label': prior, 'claimed_close_date': record.get('second_financing_date', ''),
            'source_url': url, 'sec_retrieval': 'NOT_ATTEMPTED',
            'document_sha256': '', 'candidate_closing_excerpt': '',
            'independent_closure_verified': 'NO', 'entry_ready': 'NO',
            'as_of_utc': datetime.now(timezone.utc).isoformat(),
        }
        if not issuer:
            row['sec_retrieval'] = 'REGISTRY_IDENTITY_MISSING'
        elif not url:
            row['sec_retrieval'] = 'NO_SECOND_CLOSE_SOURCE_TO_CHECK'
        elif not validate_source(url, cik):
            row['sec_retrieval'] = 'SOURCE_CIK_OR_URL_MISMATCH'
        elif not live:
            row['sec_retrieval'] = 'OFFLINE_PENDING_SEC_CHECK'
        else:
            try:
                digest, txt = fetcher(url, agent)
                row['document_sha256'] = digest
                row['candidate_closing_excerpt'] = closing_context(txt, row['claimed_close_date'])
                row['sec_retrieval'] = ('FETCHED_CANDIDATE_HUMAN_REVIEW_REQUIRED'
                                        if row['candidate_closing_excerpt'] else
                                        'FETCHED_NO_MATCHING_CLOSING_CLAUSE')
            except (RuntimeError, ValueError) as exc:
                row['sec_retrieval'] = str(exc)
            finally:
                sleep(0.5)
        output.append(row)
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, default=LEDGER)
    parser.add_argument('--registry', type=Path, default=REGISTRY)
    parser.add_argument('--output', type=Path, default=ROOT/'data/financing_first10_audit.csv')
    parser.add_argument('--live', action='store_true', help='Contact official SEC pages using SEC_USER_AGENT')
    args = parser.parse_args(argv)
    results = audit(args.ledger, args.registry, live=args.live, agent=os.environ.get('SEC_USER_AGENT'))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)
    print(json.dumps({'checked_rows': len(results), 'live': args.live,
                      'sec_retrieval_counts': {s: sum(r['sec_retrieval'] == s for r in results)
                                               for s in sorted(set(r['sec_retrieval'] for r in results))},
                      'independently_verified': 0, 'entry_ready': 0,
                      'report': str(args.output)}, indent=2))


if __name__ == '__main__':
    main()
