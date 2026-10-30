'use strict';

// Public, read-only source discovery. Never prints source bodies or credentials.
const crypto = require('node:crypto');
const fs = require('node:fs');
const SOURCES = [
  ['current_oncology_index', 'https://www.fda.gov/drugs/resources-information-approved-drugs/oncology-cancerhematologic-malignancies-approval-notifications'],
  ['resources_index', 'https://www.fda.gov/drugs/resources-information-approved-drugs'],
  ['alternate_oncology_index', 'https://www.fda.gov/drugs/resources-information-approved-drugs/oncology-cancer-hematologic-malignancies-approval-notifications'],
  ['drug_approvals_index', 'https://www.fda.gov/drugs/drug-approvals-and-databases'],
  ['drugsfda_api', 'https://api.fda.gov/drug/drugsfda.json?limit=1'],
];

function officialLinks(body, base) {
  const links = new Set();
  for (const match of body.matchAll(/href\s*=\s*["']([^"']+)["']/gi)) {
    try {
      const url = new URL(match[1].replaceAll('&amp;', '&'), base);
      if (url.protocol !== 'https:' || !['www.fda.gov', 'fda.gov'].includes(url.hostname)) continue;
      if (!/approval|approved-drugs|oncology|hematologic/i.test(url.pathname)) continue;
      url.hash = '';
      url.search = '';
      links.add(url.href);
    } catch { /* Malformed public links are ignored. */ }
  }
  return [...links].sort((a, b) => {
    const score = value => /approval-notifications/.test(value) ? 0 : /fda-approves/.test(value) ? 1 : /resources-information-approved-drugs/.test(value) ? 2 : 3;
    return score(a) - score(b) || a.localeCompare(b);
  }).slice(0, 10);
}

async function probe([name, url]) {
  const record = { name, url, status: null, final_url: null, bytes: 0, sha256: null, official_links: [], error_code: null };
  try {
    const response = await fetch(url, {
      signal: AbortSignal.timeout(25000), redirect: 'follow',
      headers: { 'User-Agent': 'PDUFA-Phase3-Library/1.0', Accept: name === 'drugsfda_api' ? 'application/json' : 'text/html' },
    });
    const final = new URL(response.url);
    if (!['www.fda.gov', 'fda.gov', 'api.fda.gov', 'www.accessdata.fda.gov'].includes(final.hostname)) {
      record.error_code = 'NON_FDA_REDIRECT';
      return record;
    }
    record.status = response.status;
    record.final_url = final.href;
    const chunks = [];
    for await (const chunk of response.body || []) {
      record.bytes += chunk.byteLength;
      if (record.bytes > 4 * 1024 * 1024) { record.error_code = 'SOURCE_TOO_LARGE'; return record; }
      chunks.push(Buffer.from(chunk));
    }
    const buffer = Buffer.concat(chunks);
    record.sha256 = crypto.createHash('sha256').update(buffer).digest('hex');
    if (name !== 'drugsfda_api') record.official_links = officialLinks(buffer.toString('utf8'), response.url);
  } catch (error) {
    record.error_code = error?.name === 'TimeoutError' ? 'SOURCE_TIMEOUT' : 'SOURCE_REQUEST_FAILED';
  }
  return record;
}

async function main() {
  const started_at = new Date().toISOString();
  const probes = await Promise.all(SOURCES.map(probe));
  const result = { started_at, finished_at: new Date().toISOString(), scope: 'public_read_only_source_diagnosis', probes };
  console.log('PDUFA_PHASE3_PUBLIC_SOURCE_PROBE ' + JSON.stringify(result));
  if (process.env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, [
      'Public Phase 3 source diagnosis', '',
      '| Source | HTTP status | Safe failure code |', '|---|---|---|',
      ...probes.map(value => '| ' + value.name + ' | ' + (value.status ?? 'unavailable') + ' | ' + (value.error_code ?? '') + ' |'),
      '', 'Source bodies and credentials are not retained. This probe makes no FDA decision claims.', '',
    ].join('\n'));
  }
}

void main();
