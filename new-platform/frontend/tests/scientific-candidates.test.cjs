const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, filename) => module._compile(
  ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText, filename);
const { NextRequest } = require('next/server');
const auth = require('../lib/auth.ts');
const route = require('../app/api/scientific-candidates/route.ts');
const detail = require('../app/api/scientific-candidates/[nct_id]/route.ts');
const { isScientificCandidates, scientificCount, sourceUrl } = require('../lib/scientific-candidates.ts');
const Panel = require('../app/ScientificCandidateReadiness.tsx').default;
const candidate = { nct_id: 'NCT01234567', sponsor: 'Test sponsor', products: ['Investigational product'],
  indications: ['Test indication'], readiness: 'RELUCTANT', explanation: 'FDA pathway remains unverified.', last_verified: '2026-10-30T13:35:21Z' };
const report = { status: 'COMPLETE', candidates_identified: 1, candidates_independently_checked: 1,
  ready: 0, reluctant: 1, not_ready: 0, regulatory_identifiers_verified: 0, regulatory_identifiers_unresolved: 1,
  full_scientific_investigations_completed: 0, scientific_dossiers_created: 1, last_verified: '2026-10-30T13:35:21Z', candidates: [candidate],
  regulatory_identifiers: [{ associated_nct_id: 'NCT01234567', identifier: 'IND 12345', status: 'UNRESOLVED', sponsor: 'Test sponsor', products: ['Investigational product'], evidence: [], verified_at: null }] };

test('persisted counts must reconcile; unverified is distinct from zero', () => {
  assert.equal(scientificCount(null), 'Unverified');
  assert.equal(scientificCount(0), '0');
  assert.equal(isScientificCandidates(report), true);
  assert.equal(isScientificCandidates({ ...report, candidates_independently_checked: 2 }), false);
  assert.equal(isScientificCandidates({ ...report, ready: 1 }), false);
  assert.equal(isScientificCandidates({ ...report, candidates: [candidate, candidate] }), false);
  assert.equal(isScientificCandidates({ ...report, candidates: [{ ...candidate, readiness: 'PASS' }] }), false);
  assert.equal(isScientificCandidates({ ...report, last_verified: 'not a timestamp' }), false);
  assert.equal(isScientificCandidates({ ...report, ready: -1 }), false);
  assert.equal(isScientificCandidates({ ...report, candidates_independently_checked: 0 }), true);
  assert.equal(isScientificCandidates({ ...report, ready: 1, reluctant: 0 }), false);
  assert.equal(isScientificCandidates({ ...report, scientific_dossiers_created: 0 }), false);
  assert.equal(isScientificCandidates({ ...report, full_scientific_investigations_completed: 1 }), false);
  assert.equal(isScientificCandidates({ ...report, candidates_identified: null, candidates_independently_checked: null,
    ready: null, reluctant: null, not_ready: null, scientific_dossiers_created: null, candidates: [], last_verified: null }), true);
});

test('evidence links reject unsafe or credential-bearing URLs', () => {
  assert.equal(sourceUrl('https://clinicaltrials.gov/study/NCT01234567'), 'https://clinicaltrials.gov/study/NCT01234567');
  for (const url of ['javascript:alert(1)', 'data:text/html,unsafe', 'http://example.test', 'https://user:password@example.test/', null]) assert.equal(sourceUrl(url), null);
});

test('list and dossier authenticate before any outbound request', async () => {
  const previous = global.fetch;
  global.fetch = async () => assert.fail('Unauthenticated request reached backend');
  try {
    const req = new NextRequest('https://dashboard.example/api/scientific-candidates');
    assert.equal((await route.GET(req)).status, 401);
    assert.equal((await detail.GET(req, { params: Promise.resolve({ nct_id: 'NCT01234567' }) })).status, 401);
    assert.equal(route.POST, undefined); assert.equal(detail.POST, undefined);
  } finally { global.fetch = previous; }
});

test('authenticated list/dossier use exact read-only backend paths and never reveal keys', async () => {
  const previousFetch = global.fetch;
  const keys = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const previous = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  Object.assign(process.env, { DASHBOARD_PASSWORD: 'scientific-test-password', SESSION_SIGNING_KEY: 'scientific-test-signing-key-long-enough',
    PDUFA_API_BASE_URL: 'https://backend.example/', PDUFA_INTERNAL_API_KEY: 'scientific-test-internal-key' });
  let good = true; const urls = [];
  global.fetch = async (url, options) => {
    urls.push(url); assert.equal(options.headers['x-pdufa-internal-key'], 'scientific-test-internal-key');
    assert.equal(options.method, undefined); assert.equal(options.cache, 'no-store');
    return { ok: good, status: good ? 200 : 500, json: async () => url.endsWith('/NCT01234567') ? { nct_id: 'NCT01234567', sources: [{ url: 'https://clinicaltrials.gov/study/NCT01234567' }] } : report };
  };
  try {
    const req = () => new NextRequest('https://dashboard.example/api/scientific-candidates', { headers: { cookie: auth.COOKIE_NAME + '=' + auth.makeSession() } });
    const list = await route.GET(req()); assert.equal(list.status, 200); assert.deepEqual(await list.json(), report);
    const dossier = await detail.GET(req(), { params: Promise.resolve({ nct_id: 'NCT01234567' }) }); assert.equal(dossier.status, 200);
    assert.deepEqual(urls, ['https://backend.example/api/scientific-candidates', 'https://backend.example/api/scientific-candidates/NCT01234567']);
    const invalid = await detail.GET(req(), { params: Promise.resolve({ nct_id: '../../state' }) }); assert.equal(invalid.status, 422); assert.equal(urls.length, 2);
    good = false; const failed = await route.GET(req()); assert.equal(failed.status, 503);
    assert.doesNotMatch(JSON.stringify(await failed.json()), /scientific-test-internal-key|READY|PASS/);
    assert.equal(failed.headers.get('cache-control'), 'private, no-store');
  } finally { global.fetch = previousFetch; for (const [key, value] of Object.entries(previous)) {
    if (value === undefined) delete process.env[key]; else process.env[key] = value;
  } }
});

test('initial semantic rendering has expandable section and no invented counts', () => {
  const previous = global.fetch; global.fetch = async () => assert.fail('Initial render fetched evidence');
  try {
    const html = renderToStaticMarkup(React.createElement(Panel));
    assert.match(html, /<details/); assert.match(html, /SCIENTIFIC CANDIDATE READINESS/); assert.match(html, /role="status"/);
    assert.match(html, /Expand to load persisted candidate investigations/); assert.doesNotMatch(html, /228|>READY<|>PASS<|NCT01234567/);
  } finally { global.fetch = previous; }
});

test('page adds readiness beside archive health without changing existing controls', () => {
  const page = fs.readFileSync(require.resolve('../app/page.tsx'), 'utf8');
  const components = ['<ArchiveHealthPanel', '<ScientificCandidateReadiness', '<NctLiveStream', '<Workspace'];
  let previous = -1;
  for (const component of components) {
    const position = page.indexOf(component);
    assert.ok(position >= 0, component + ' remains present');
    assert.ok(position > previous, component + ' retains its placement after prior evidence panels');
    previous = position;
  }
});

