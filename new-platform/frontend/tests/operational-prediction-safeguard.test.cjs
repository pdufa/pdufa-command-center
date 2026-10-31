const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const { create, act } = require('react-test-renderer');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, filename) => module._compile(
  ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText, filename);
const { NextRequest } = require('next/server');
const auth = require('../lib/auth.ts');
const { GET } = require('../app/api/phase3-trials/[nct_id]/predictions/route.ts');
const { default: NctLiveStream } = require('../app/NctLiveStream.tsx');
const { default: Pilot } = require('../app/prediction-pilot/page.tsx');
global.IS_REACT_ACT_ENVIRONMENT = true;
const nct = 'NCT00116805', run = 'cb4c2bcc-5309-4226-93cd-2a1f01876258';
function text(value) {
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (Array.isArray(value)) return value.map(text).join('');
  return value && typeof value === 'object' ? text(value.children) : '';
}
function configured() {
  const keys = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const before = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  Object.assign(process.env, { DASHBOARD_PASSWORD: 'isolated-test-password', SESSION_SIGNING_KEY: 'isolated-test-signing-key-long-enough',
    PDUFA_API_BASE_URL: 'https://backend.example', PDUFA_INTERNAL_API_KEY: 'isolated-internal-key' });
  return () => { for (const [key, value] of Object.entries(before)) { if (value === undefined) delete process.env[key]; else process.env[key] = value; } };
}

for (const decision of ['PASS', 'CRL', 'EXTENSION']) test('READY saved ' + decision + ' cannot become an operational forecast', async () => {
  const restore = configured(), original = global.fetch;
  const saved = { decision, scientific_readiness: 'READY', created_at: '2025-01-01T00:00:00Z', evidence_ids: ['isolated-evidence'] };
  global.fetch = async () => new Response(JSON.stringify({ nct_id: nct, decision, latest_prediction: saved, predictions: [saved], status: 'RECORDED' }), { headers: { 'content-type': 'application/json' } });
  try {
    const request = new NextRequest('https://dashboard.example/api/phase3-trials/' + nct + '/predictions', { headers: { cookie: auth.COOKIE_NAME + '=' + auth.makeSession() } });
    const result = await GET(request, { params: Promise.resolve({ nct_id: nct }) });
    assert.equal(result.status, 200);
    const record = await result.json();
    assert.equal(record.decision, 'ABSTAIN');
    assert.equal(record.status, 'NOT_READY');
    assert.equal(record.validated_decision_available, false);
    assert.deepEqual(record.latest_prediction, saved, 'immutable saved research record is retained');
    assert.deepEqual(record.predictions, [saved]);
  } finally { restore(); global.fetch = original; }
});

test('prediction proxy authenticates before network and rejects cross-trial records', async () => {
  const restore = configured(), original = global.fetch;
  try {
    global.fetch = async () => assert.fail('Anonymous outbound request');
    const anonymous = new NextRequest('https://dashboard.example/api/phase3-trials/' + nct + '/predictions');
    assert.equal((await GET(anonymous, { params: Promise.resolve({ nct_id: nct }) })).status, 401);
    global.fetch = async () => new Response(JSON.stringify({ nct_id: 'NCT99999999', decision: 'PASS' }), { headers: { 'content-type': 'application/json' } });
    const request = new NextRequest(anonymous.url, { headers: { cookie: auth.COOKIE_NAME + '=' + auth.makeSession() } });
    const result = await GET(request, { params: Promise.resolve({ nct_id: nct }) });
    assert.equal(result.status, 503);
    assert.equal((await result.json()).decision, 'ABSTAIN');
  } finally { restore(); global.fetch = original; }
});

test('frozen pilot prominently abstains and retains its sourced clinical observations', async () => {
  let view;
  try {
    await act(async () => { view = create(React.createElement(Pilot)); });
    const safeguard = view.root.findByProps({ 'aria-label': 'Operational prediction safeguard' });
    assert.match(text(safeguard.children), /ABSTAIN/);
    assert.match(text(safeguard.children), /NOT ADJUDICATED/);
    assert.match(text(view.toJSON()), /NCT05208047/);
    assert.match(text(view.toJSON()), /0.50/);
    assert.match(text(view.toJSON()), /Frozen research observations/);
  } finally { if (view) await act(async () => view.unmount()); }
});

for (const decision of ['PASS', 'CRL', 'EXTENSION']) test('rendered MAIN abstains while saved ' + decision + ' remains a closed historical record', async () => {
  const original = { fetch: global.fetch, localStorage: global.localStorage, window: global.window };
  global.localStorage = { getItem: key => key === 'pdufa_nct_processing_run_v1' ? JSON.stringify({ nct_id: nct, run_id: run }) : null, setItem() {}, removeItem() {} };
  global.window = new EventTarget();
  global.fetch = async url => {
    let data;
    if (String(url).startsWith('/api/nct-stream/')) data = { nct_id: nct, run_id: run, dossier_id: 'isolated-dossier', terminal: true,
      events: [{ nct_id: nct, run_id: run, sequence: 1, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE', value: { decision: 'ABSTAIN' }, parent_id: null, kind: 'complete', terminal: true }] };
    else if (String(url).endsWith('/predictions')) data = { nct_id: nct, decision, status: 'RECORDED', latest_prediction: { decision, scientific_readiness: 'READY', created_at: '2025-01-01T00:00:00Z' } };
    else if (String(url).endsWith('/readiness')) data = { nct_id: nct, decision: 'ABSTAIN', checks_available: 0, checks_total: 7, assessments: [], decision_pipeline: [] };
    else if (String(url).endsWith('/statistical-consistency')) data = { nct_id: nct, comparisons: [], comparison_ready: false, integrity_matched_document_counts: { PROTOCOL: 0, SAP: 0 }, readiness_blockers: ['MISSING_DOCUMENTS'] };
    else if (String(url).endsWith('/source-inventory')) data = { nct_id: nct, sources: [] };
    else assert.fail('Unexpected isolated fixture request: ' + url);
    return new Response(JSON.stringify(data), { headers: { 'content-type': 'application/json' } });
  };
  let view;
  try {
    await act(async () => { view = create(React.createElement(NctLiveStream)); await new Promise(resolve => setTimeout(resolve, 20)); });
    await act(async () => { await new Promise(resolve => setTimeout(resolve, 20)); });
    const headings = view.root.findAllByType('strong').map(node => text(node.children));
    assert.ok(headings.includes('FDA prediction: ABSTAIN'));
    assert.ok(headings.includes('FDA decision prediction: ABSTAIN — NOT READY.'));
    assert.ok(!headings.some(value => /^FDA (?:decision )?prediction: (?:PASS|CRL|EXTENSION)/.test(value)));
    const history = view.root.findByProps({ 'data-unvalidated-prediction-record': 'true' });
    assert.equal(history.type, 'details');
    assert.equal(history.props.open, undefined);
    assert.match(text(history.children), new RegExp('Recorded class: ' + decision));
    assert.match(text(history.children), /operational decision remains ABSTAIN/);
  } finally {
    if (view) await act(async () => view.unmount());
    for (const [key, value] of Object.entries(original)) { if (value === undefined) delete global[key]; else global[key] = value; }
  }
});
