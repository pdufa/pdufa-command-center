const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (m, file) => m._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true}
}).outputText, file);
const shared = require('../lib/shared-enrichment.ts');
const root = path.join(__dirname, '../../../data/shared_enrichment');
const index = shared.validateEnrichmentIndex(JSON.parse(fs.readFileSync(path.join(root, 'index.json'), 'utf8')));
const shard = JSON.parse(fs.readFileSync(path.join(root, 'records/SVRA.json'), 'utf8'));
const key = Object.keys(shard.records).find(k => k.startsWith('APPLICATION|'));

test('all fifty coverage denominators reconcile and malformed publications are rejected', () => {
  for (const stage of Object.keys(index.lists)) for (const f of index.fields) assert.equal(Object.values(index.lists[stage].fields[f.id]).reduce((a,b) => a+b), index.lists[stage].records);
  const bad = structuredClone(index);
  bad.lists.PIPELINE.fields.cash_balance.MISSING++;
  assert.throws(() => shared.validateEnrichmentIndex(bad), /reconcile/);
  assert.throws(() => shared.validateEnrichmentIndex({...index, fields: index.fields.slice(1)}), /catalog/);
});

test('an exact company/program match is required and company views cannot leak application facts', () => {
  assert.ok(key);
  const program = shared.enrichmentDetail(index, shard, 'SVRA', key, '2026-10-23');
  assert.equal(program.fields.length, 50);
  assert.throws(() => shared.enrichmentDetail(index, shard, 'BCRX', key), /mismatch/);
  assert.throws(() => shared.enrichmentDetail(index, shard, 'SVRA', 'APPLICATION|OTHER'), /not found/);
  const company = shared.enrichmentDetail(index, shard, 'SVRA', '', '2026-10-23');
  assert.ok(company.fields.filter(f => f.scope === 'program' && f.id !== 'evidence_completeness').every(f => f.status === 'MISSING' && f.value === null));
  assert.equal(company.fields.find(f => f.id === 'cash_balance').value, 41800000);
  assert.equal(company.fields.find(f => f.id === 'regulatory_probability').value, null);
});

test('reopening an older publication expires source freshness and updates date distances', () => {
  const data = shared.enrichmentDetail(index, shard, 'SVRA', key, '2026-11-30');
  assert.equal(data.fields.find(f => f.id === 'cash_balance').status, 'STALE');
  const bad = structuredClone(shard);
  bad.company.cash_balance[4] = '2027-01-01';
  assert.equal(shared.enrichmentDetail(index, bad, 'SVRA', '', '2026-10-23').fields.find(f => f.id === 'cash_balance').status, 'REVIEW');
});

test('API authenticates before fetching, rejects unsafe identifiers and never returns a mismatched program', async () => {
  const {NextRequest} = require('next/server');
  const auth = require('../lib/auth.ts');
  const route = require('../app/api/shared-enrichment/route.ts');
  const prior = {password: process.env.DASHBOARD_PASSWORD, signing: process.env.SESSION_SIGNING_KEY, fetch: global.fetch};
  process.env.DASHBOARD_PASSWORD = 'test-only-password';
  process.env.SESSION_SIGNING_KEY = 'test-only-signing-key-that-is-long-enough';
  const cookie = auth.COOKIE_NAME+'='+auth.makeSession();
  let calls = 0;
  global.fetch = async url => {calls++; return {ok: true, text: async () => JSON.stringify(url.endsWith('index.json') ? index : shard)};};
  const request = (query = '', signed = true) => new NextRequest('http://localhost/api/shared-enrichment'+query, {headers: signed ? {cookie} : {}});
  try {
    assert.equal((await route.GET(request('', false))).status, 401);
    assert.equal((await route.GET(request('?ticker=../SVRA'))).status, 400);
    assert.equal((await route.GET(request('?id=TRIAL%7CNCT00000001'))).status, 400);
    assert.equal(calls, 0);
    assert.equal((await route.GET(request())).status, 200);
    const query = '?ticker=SVRA&id='+encodeURIComponent(key);
    assert.equal((await route.GET(request(query))).status, 200);
    assert.equal((await route.GET(request('?ticker=SVRA&id=APPLICATION%7CUNKNOWN'))).status, 404);
    global.fetch = async () => ({ok: false});
    assert.equal((await route.GET(request())).status, 503);
  } finally {
    global.fetch = prior.fetch;
    if (prior.password === undefined) delete process.env.DASHBOARD_PASSWORD; else process.env.DASHBOARD_PASSWORD = prior.password;
    if (prior.signing === undefined) delete process.env.SESSION_SIGNING_KEY; else process.env.SESSION_SIGNING_KEY = prior.signing;
  }
});

test('field DETAILS cancels an old company request and never displays its results for a new company', async () => {
  const React = require('react');
  const {create, act} = require('react-test-renderer');
  const View = require('../app/SharedEnrichment.tsx').SharedProgramFields;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const previousFetch = global.fetch, requests = [];
  global.fetch = (url, options) => new Promise(resolve => requests.push({url, options, resolve}));
  let view;
  try {
    await act(async () => {view = create(React.createElement(View, {ticker: 'SVRA', exactKey: key}));});
    assert.equal(requests.length, 0, 'collapsed evidence does not fetch');
    await act(async () => view.root.findByType('details').props.onToggle({currentTarget: {open: true}}));
    await act(async () => view.update(React.createElement(View, {ticker: 'BCRX'})));
    assert.equal(requests[0].options.signal.aborted, true);
    const old = shared.enrichmentDetail(index, shard, 'SVRA', key, '2026-10-23');
    await act(async () => requests[0].resolve({ok: true, json: async () => old}));
    assert.doesNotMatch(JSON.stringify(view.toJSON()), /41,800,000/);
    await act(async () => requests[1].resolve({ok: false, status: 503}));
    assert.match(JSON.stringify(view.toJSON()), /unavailable/);
    assert.equal(view.root.findAllByType('button').length, 1);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = previousFetch;
  }
});
