"""Extract reviewed primary financial statement layouts without saved values.

This fallback verifies dated statements when Companyfacts omits interim facts.
Currency is retained without conversion. Layout mappings contain labels and
columns only, never numeric balances.
"""
import html
import math
import re
from datetime import date
from html.parser import HTMLParser


class Tables(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.tables = [], []

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.stack.append({'rows': [], 'row': None, 'cell': None})
        elif self.stack:
            t = self.stack[-1]
            if tag == 'tr': t['row'] = []
            elif tag in {'td', 'th'}: t['cell'] = []

    def handle_data(self, text):
        if self.stack and self.stack[-1]['cell'] is not None:
            self.stack[-1]['cell'].append(text)

    def handle_endtag(self, tag):
        if not self.stack: return
        t = self.stack[-1]
        if tag in {'td', 'th'} and t['cell'] is not None:
            if t['row'] is not None:
                t['row'].append(re.sub(r'\s+', ' ', ''.join(t['cell'])).strip())
            t['cell'] = None
        elif tag == 'tr' and t['row'] is not None:
            t['rows'].append(t['row']); t['row'] = None
        elif tag == 'table': self.tables.append(self.stack.pop()['rows'])


def norm(text):
    return re.sub(r'\s+', ' ', text).strip().casefold()


def report_snapshot(raw, spec, as_of):
    start, end = date.fromisoformat(spec['start']), date.fromisoformat(spec['end'])
    days = (end - start).days + 1
    if not 0 <= (as_of - end).days <= 180 or not 60 <= days <= 380:
        raise ValueError('Reviewed statement is future, stale or has an invalid period')
    if spec['scale'] not in {1, 1000, 1000000}:
        raise ValueError('Unsupported financial unit scale')
    plain = html.unescape(re.sub(r'<[^>]+>', ' ', raw))
    if norm(spec['period_text']) not in norm(plain):
        raise ValueError('Reviewed statement period is absent')
    currency_markers = {
        'USD': {'US$', 'USD', 'US Dollars', 'U.S. dollars'},
        'EUR': {'€', 'EUR', 'euros'},
    }
    markers = {norm(value) for value in currency_markers.get(spec['currency'], set())}
    if (norm(spec['currency_text']) not in markers
            or norm(spec['currency_text']) not in norm(plain)):
        raise ValueError('Statement currency must match explicit reviewed units; no currency conversion')
    parser = Tables(); parser.feed(raw)
    found = []
    for table in parser.tables:
        heading = norm(' '.join(' '.join(row) for row in table[:5]))
        cursor = 0
        for token in spec['ordered_headers']:
            position = heading.find(norm(token), cursor)
            if position < 0: break
            cursor = position + len(norm(token))
        else:
            values = {}
            for kind in ('cash', 'flow'):
                mapping = spec[kind]
                matches = [row for row in table if row and norm(row[0]) == norm(mapping['label'])]
                if len(matches) != 1: break
                tail = ' '.join(matches[0][1:])
                numbers = re.findall(r'\(\s*[\d,]+(?:\.\d+)?\s*\)|-?[\d,]+(?:\.\d+)?', tail)
                try:
                    token = numbers[mapping['number_index']]
                    val = float(re.sub(r'[(),\s]', '', token)) * spec['scale']
                    values[kind] = -val if '(' in token else val
                except (IndexError, ValueError): break
            else:
                if values['cash'] >= 0 and all(math.isfinite(v) for v in values.values()):
                    found.append(values)
    if len(found) != 1:
        raise ValueError('No unique cash-flow statement with reviewed rows and current/prior columns')
    return {**found[0], 'currency': spec['currency'], 'start': start.isoformat(), 'end': end.isoformat(), 'flow_days': days}
