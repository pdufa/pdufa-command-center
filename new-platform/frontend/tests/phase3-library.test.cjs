const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const { create, act } = require('react-test-renderer');
const { renderToStaticMarkup } = require('react-dom/server');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, filename) => module._compile(
  ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText, filename);
const { NextRequest } = require('next/server');
const auth = require('../lib/auth.ts');
const { catalogQuery, relayPhase3Catalog } = require('../lib/phase3-trials.ts');
const { relayLatestNctRun } = require('../lib/nct-latest-proxy.ts');
const { relayNctRun } = require('../lib/nct-stream-proxy.ts');
const { default: Phase3TrialLibrary, parseCatalog } = require('../app/Phase3TrialLibrary.tsx');
const { default: NctLiveStream } = require('../app/NctLiveStream.tsx');
global.IS_REACT_ACT_ENVIRONMENT = true;
const NCT = 'NCT01234567';
const RUN = 'cb4c2bcc-5309-4226-93cd-2a1f01876258';
const pointer = { nct_id: NCT, run_id: RUN };
const fixture = (period = 'CURRENT', changes = {}) => ({
  period, trials: [{ nct_id: NCT, company: 'Synthetic Test Sponsor', ticker: null, drug: 'Synthetic test product',
    indication: 'Test indication', trial_title: 'Synthetic test trial', phase3_status: 'COMPLETED', results_available: true,
    primary_endpoint_result: 'Posted results; endpoint interpretation pending.', actual_decision: 'PENDING',
    scientific_readiness: 'NOT READY', latest_run_id: RUN, last_verified: '2026-10-30T13:00:00+00:00',
    evidence: [{ url: 'https://clinicaltrials.gov/api/v2/studies/' + NCT, verification_status: 'VERIFIED' }], predictions: [] }],
  total: 50, page: 1, page_size: 25, pages: 2, counts: { APPROVED: 7, CRL: 2, EXTENDED: 1, PENDING: 40 },
  source_status: 'VERIFIED', last_updated: '2026-10-30T13:00:00+00:00', ingestion: { status: 'RUNNING', processed: 50, expected_total: 5000 },
  ...changes,
});
function configured() {
  const keys = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const before = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  Object.assign(process.env, { DASHBOARD_PASSWORD: 'test-password-not-production', SESSION_SIGNING_KEY: 'test-only-signing-key-that-is-long-enough',
    PDUFA_API_BASE_URL: 'https://backend.example/', PDUFA_INTERNAL_API_KEY: 'test-only-internal-key' });
  return () => { for (const [key, value] of Object.entries(before)) { if (value === undefined) delete process.env[key]; else process.env[key] = value; } };
}
function req(path) { return new NextRequest('https://dashboard.example' + path, { headers: { cookie: auth.COOKIE_NAME + '=' + auth.makeSession() } }); }
async function settle(ms = 300) { await act(async () => { await new Promise(resolve => setTimeout(resolve, ms)); }); }
function button(view, label) { return view.root.findAllByType('button').find(node => node.props['aria-label'] === label || node.children.filter(value => typeof value === 'string').join('') === label); }
function renderText(view) { return JSON.stringify(view.toJSON()); }
function storage() {
  const entries = new Map();
  return { entries, getItem: key => entries.get(key) || null, setItem: (key, value) => entries.set(key, value), removeItem: key => entries.delete(key) };
}

test('Analyze reuse option is forwarded only as a validated boolean while manual runs remain unchanged', async () => {
  const restore = configured(), original = global.fetch;
  const bodies = [];
  global.fetch = async (_url, options) => {
    bodies.push(JSON.parse(options.body));
    return new Response(JSON.stringify({ ...pointer, dossier_id: 'test-dossier' }), { headers: { 'content-type': 'application/json' } });
  };
  const request = body => new NextRequest('https://dashboard.example/api/nct-stream/' + NCT + '/runs', {
    method: 'POST', headers: { origin: 'https://dashboard.example', cookie: auth.COOKIE_NAME + '=' + auth.makeSession(), 'content-type': 'application/json' }, body: JSON.stringify(body),
  });
  try {
    assert.equal((await relayNctRun(request({ request_key: RUN, reuse_existing: true }), NCT)).status, 200);
    assert.deepEqual(bodies[0], { request_key: RUN, reuse_existing: true });
    assert.equal((await relayNctRun(request({ request_key: RUN }), NCT)).status, 200);
    assert.deepEqual(bodies[1], { request_key: RUN });
    assert.equal((await relayNctRun(request({ request_key: RUN, reuse_existing: 'yes' }), NCT)).status, 422);
    assert.equal(bodies.length, 2);
  } finally { restore(); global.fetch = original; }
});

test('catalog filters validate server-side pagination/search/sorting without interpolating SQL', () => {
  const query = catalogQuery(new URLSearchParams({ period: 'PREVIOUS', q: 'Sponsor & test', decision: 'CRL', page: '2', page_size: '100', sort: 'company', dir: 'asc' }));
  assert.equal(query.get('q'), 'Sponsor & test');
  assert.equal(query.get('page'), '2');
  for (const bad of [{ period: 'FUTURE' }, { sort: 'company;DROP TABLE trials' }, { page: '0' }, { page_size: '101' }, { decision: 'PASS' }, { dir: 'sideways' }, { q: 'x'.repeat(201) }]) {
    assert.equal(catalogQuery(new URLSearchParams(bad)), null);
  }
});

test('catalog rejects malformed identities/counts and never fabricates records or outcomes', () => {
  assert.equal(parseCatalog(fixture(), 'CURRENT').trials.length, 1);
  assert.equal(parseCatalog(fixture('CURRENT', { trials: [], total: 0, pages: 0 }), 'CURRENT').trials.length, 0);
  assert.throws(() => parseCatalog(fixture('PREVIOUS'), 'CURRENT'), /Invalid trial catalog totals/);
  assert.throws(() => parseCatalog(fixture('CURRENT', { counts: { APPROVED: -1 } }), 'CURRENT'), /totals/);
  assert.throws(() => parseCatalog(fixture('CURRENT', { trials: [{ ...fixture().trials[0], nct_id: 'NCT123' }] }), 'CURRENT'), /evidence/);
  assert.throws(() => parseCatalog(fixture('CURRENT', { trials: [{ ...fixture().trials[0], actual_decision: 'PASS' }] }), 'CURRENT'), /evidence/);
});

test('catalog and latest-run proxies authenticate before any outbound network access', async () => {
  const restore = configured(), original = global.fetch;
  global.fetch = async () => assert.fail('Unauthenticated network request');
  try {
    const anonymous = new NextRequest('https://dashboard.example/api/phase3-trials?period=CURRENT');
    assert.equal((await relayPhase3Catalog(anonymous)).status, 401);
    assert.equal((await relayLatestNctRun(anonymous, NCT)).status, 401);
    assert.equal((await relayPhase3Catalog(req('/api/phase3-trials?period=INVALID'))).status, 422);
    assert.equal((await relayLatestNctRun(req('/api/nct-stream/bad/runs/latest'), 'bad')).status, 422);
  } finally { restore(); global.fetch = original; }
});

test('proxies forward bounded filters/private credentials only server-side and reject wrong content type', async () => {
  const restore = configured(), original = global.fetch;
  const calls = [];
  global.fetch = async (url, options) => {
    calls.push(url);
    assert.equal(options.headers['X-Pdufa-Internal-Key'], 'test-only-internal-key');
    assert.equal(options.cache, 'no-store');
    assert.ok(options.signal);
    return new Response(JSON.stringify(url.endsWith('/runs/latest') ? { ...pointer, dossier_id: 'test-dossier' } : fixture()), { headers: { 'content-type': 'application/json' } });
  };
  try {
    const result = await relayPhase3Catalog(req('/api/phase3-trials?period=CURRENT&q=NCT01234567&page=2&decision=PENDING'));
    assert.equal(result.status, 200);
    assert.match(result.headers.get('cache-control'), /private, no-store/);
    assert.doesNotMatch(JSON.stringify(await result.json()), /test-only-internal-key/);
    assert.equal(new URL(calls[0]).searchParams.get('page'), '2');
    assert.equal(new URL(calls[0]).searchParams.get('decision'), 'PENDING');
    assert.equal((await relayLatestNctRun(req('/api/nct-stream/' + NCT + '/runs/latest'), NCT)).status, 200);
    assert.equal(calls[1], 'https://backend.example/api/nct-stream/' + NCT + '/runs/latest');
    global.fetch = async () => new Response('<html>unavailable</html>', { headers: { 'content-type': 'text/html' } });
    assert.equal((await relayPhase3Catalog(req('/api/phase3-trials?period=CURRENT'))).status, 502);
    assert.equal((await relayLatestNctRun(req('/api/nct-stream/' + NCT + '/runs/latest'), NCT)).status, 502);
  } finally { restore(); global.fetch = original; }
});

test('library displays all fifteen columns with mobile scrolling and honest unknown outcome/prediction states', () => {
  const markup = renderToStaticMarkup(React.createElement(Phase3TrialLibrary, { onAnalyze() {} }));
  for (const label of ['Company', 'Stock ticker', 'Drug', 'Indication', 'Trial title', 'NCT number', 'Phase 3 status', 'Primary endpoint result', 'Results availability', 'FDA submission status', 'PDUFA date', 'Actual FDA decision', 'Scientific readiness', 'Last verified date', 'Analyze']) assert.match(markup, new RegExp(label));
  assert.match(markup, /overflow:auto/);
  assert.match(markup, /min-width:2400px/);
  assert.match(markup, /PREDICTED FDA DECISION vs. ACTUAL FDA DECISION/);
  assert.match(markup, /No eligible saved prospective predictions/);
  assert.doesNotMatch(markup, /Synthetic Test Sponsor/);
});

test('library uses server counts, period/search/decision filters, sorting and pagination; Analyze passes exact NCT and saved run', async () => {
  const originalFetch = global.fetch, originalStorage = global.localStorage;
  global.localStorage = storage();
  const calls = [], analyzed = [];
  global.fetch = async url => {
    calls.push(url);
    const params = new URL(url, 'https://dashboard.example').searchParams;
    return new Response(JSON.stringify(fixture(params.get('period'), { page: Number(params.get('page') || 1) })), { headers: { 'content-type': 'application/json' } });
  };
  let view;
  try {
    await act(async () => { view = create(React.createElement(Phase3TrialLibrary, { onAnalyze: (...args) => analyzed.push(args) })); });
    await settle();
    assert.match(renderText(view), /APPROVED/);
    assert.match(renderText(view), /50 matching trials/);
    assert.match(renderText(view), /Posted results verified/);
    assert.match(renderText(view), /PENDING \/ UNKNOWN/);
    assert.match(renderText(view), /50 imported/);
    const approved = view.root.findAllByType('button').find(node => node.children.includes('APPROVED'));
    assert.ok(approved, 'decision box rendered');
    assert.ok(approved.children.includes('7'), 'box count comes from server total, not one displayed row');
    await act(async () => approved.props.onClick()); await settle();
    assert.equal(new URL(calls.at(-1), 'https://dashboard.example').searchParams.get('decision'), 'APPROVED');
    await act(async () => view.root.findByProps({ 'aria-label': 'Search trials' }).props.onChange({ target: { value: 'Synthetic' } })); await settle();
    assert.equal(new URL(calls.at(-1), 'https://dashboard.example').searchParams.get('q'), 'Synthetic');
    await act(async () => button(view, 'Next page').props.onClick()); await settle();
    assert.equal(new URL(calls.at(-1), 'https://dashboard.example').searchParams.get('page'), '2');
    await act(async () => view.root.findByProps({ 'aria-label': 'Search period' }).props.onChange({ target: { value: 'PREVIOUS' } })); await settle();
    const previous = new URL(calls.at(-1), 'https://dashboard.example').searchParams;
    assert.equal(previous.get('period'), 'PREVIOUS'); assert.equal(previous.get('page'), '1'); assert.equal(previous.get('decision'), 'ALL');
    await act(async () => button(view, 'Sort by Company').props.onClick()); await settle();
    assert.equal(new URL(calls.at(-1), 'https://dashboard.example').searchParams.get('sort'), 'company');
    await act(async () => button(view, 'Analyze ' + NCT).props.onClick());
    assert.deepEqual(analyzed, [[NCT, RUN]]);
    assert.match(renderText(view), /Selected trial/);
    const preferences = JSON.parse(global.localStorage.entries.get('pdufa_phase3_library_filters_v1'));
    assert.equal(preferences.period, 'PREVIOUS'); assert.equal(preferences.sort, 'company');
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = originalFetch;
    if (originalStorage === undefined) delete global.localStorage; else global.localStorage = originalStorage;
  }
});

test('library restores period/search after refresh and handles missing source responses without synthetic rows', async () => {
  const originalFetch = global.fetch, originalStorage = global.localStorage;
  const saved = storage(); saved.entries.set('pdufa_phase3_library_filters_v1', JSON.stringify({ period: 'PREVIOUS', query: 'NCT01234567', decision: 'ALL', sort: 'nct_id', direction: 'asc', page: 1 }));
  global.localStorage = saved;
  const calls = [];
  global.fetch = async url => { calls.push(url); return new Response('{}', { status: 503, headers: { 'content-type': 'application/json' } }); };
  let view;
  try {
    await act(async () => { view = create(React.createElement(Phase3TrialLibrary, { onAnalyze() {} })); }); await settle();
    const params = new URL(calls[0], 'https://dashboard.example').searchParams;
    assert.equal(params.get('period'), 'PREVIOUS'); assert.equal(params.get('q'), NCT);
    assert.match(renderText(view), /catalog unavailable \(503\)/);
    assert.equal(view.root.findAllByProps({ 'data-nct-id': NCT }).length, 0);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = originalFetch;
    if (originalStorage === undefined) delete global.localStorage; else global.localStorage = originalStorage;
  }
});

test('Analyze restores server saved analysis and repeated clicks do not create or duplicate processing runs', async () => {
  const originalFetch = global.fetch, originalStorage = global.localStorage, originalWindow = global.window;
  global.localStorage = storage(); global.window = new EventTarget();
  let lookups = 0, posts = 0;
  global.fetch = async (url, options = {}) => {
    if (options.method === 'POST') { posts += 1; assert.fail('Saved analysis must not be overwritten'); }
    assert.match(url, /\/runs\/latest$/); lookups += 1;
    await new Promise(resolve => setTimeout(resolve, 15));
    return new Response(JSON.stringify({ ...pointer, dossier_id: 'test-dossier', terminal: true,
      events: [{ ...pointer, sequence: 1, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE', value: { decision: 'ABSTAIN' }, kind: 'complete', terminal: true }] }),
      { headers: { 'content-type': 'application/json' } });
  };
  let view;
  try {
    await act(async () => { view = create(React.createElement(NctLiveStream)); });
    await act(async () => {
      global.window.dispatchEvent(new CustomEvent('pdufa:analyze-nct', { detail: NCT }));
      global.window.dispatchEvent(new CustomEvent('pdufa:analyze-nct', { detail: NCT }));
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    assert.equal(lookups, 1); assert.equal(posts, 0);
    assert.match(renderText(view), /Saved completed processing run restored/);
    assert.deepEqual(JSON.parse(global.localStorage.entries.get('pdufa_nct_processing_run_v1')), pointer);
    await act(async () => global.window.dispatchEvent(new CustomEvent('pdufa:analyze-nct', { detail: { ...pointer } })));
    assert.equal(lookups, 1);
    const newer = { nct_id: NCT, run_id: 'dc4c2bcc-5309-4226-93cd-2a1f01876258' };
    let newerReads = 0;
    global.fetch = async url => {
      assert.equal(url, '/api/nct-stream/' + NCT + '/runs/' + newer.run_id);
      newerReads += 1;
      return new Response(JSON.stringify({ ...newer, dossier_id: 'test-dossier', terminal: true,
        events: [{ ...newer, sequence: 1, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE', value: { decision: 'ABSTAIN' }, kind: 'complete', terminal: true }] }),
        { headers: { 'content-type': 'application/json' } });
    };
    await act(async () => {
      global.window.dispatchEvent(new CustomEvent('pdufa:analyze-nct', { detail: newer }));
      await new Promise(resolve => setTimeout(resolve, 20));
    });
    assert.equal(newerReads, 1, 'explicit latest saved-run selection must replace an older completed same-NCT run');
    assert.deepEqual(JSON.parse(global.localStorage.entries.get('pdufa_nct_processing_run_v1')), newer);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = originalFetch;
    if (originalStorage === undefined) delete global.localStorage; else global.localStorage = originalStorage;
    if (originalWindow === undefined) delete global.window; else global.window = originalWindow;
  }
});

test('Analyze creates a genuinely new run only after an authoritative missing-run response and deduplicates double clicks', async () => {
  const originalFetch = global.fetch, originalStorage = global.localStorage, originalWindow = global.window;
  global.localStorage = storage(); global.window = new EventTarget();
  let posts = 0, lookups = 0;
  global.fetch = async (url, options = {}) => {
    if (url.endsWith('/latest')) { lookups += 1; return new Response('{}', { status: 404 }); }
    if (options.method === 'POST') {
      posts += 1;
      const body = JSON.parse(options.body);
      assert.equal(body.reuse_existing, true); assert.match(body.request_key, /^[a-f0-9-]{36}$/);
      await new Promise(resolve => setTimeout(resolve, 15));
      return new Response(JSON.stringify({ ...pointer, dossier_id: 'test-dossier' }), { headers: { 'content-type': 'application/json' } });
    }
    const event = { ...pointer, sequence: 1, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE', value: { decision: 'ABSTAIN' }, kind: 'complete', terminal: true };
    return new Response('id: ' + RUN + ':1\nevent: complete\ndata: ' + JSON.stringify(event) + '\n\n', { headers: { 'content-type': 'text/event-stream' } });
  };
  let view;
  try {
    await act(async () => { view = create(React.createElement(NctLiveStream)); });
    await act(async () => {
      global.window.dispatchEvent(new CustomEvent('pdufa:analyze-nct', { detail: NCT }));
      global.window.dispatchEvent(new CustomEvent('pdufa:analyze-nct', { detail: NCT }));
      await new Promise(resolve => setTimeout(resolve, 50));
    });
    assert.equal(lookups, 1); assert.equal(posts, 1);
    assert.match(renderText(view), /Processing run completed/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = originalFetch;
    if (originalStorage === undefined) delete global.localStorage; else global.localStorage = originalStorage;
    if (originalWindow === undefined) delete global.window; else global.window = originalWindow;
  }
});

test('library is mounted inside the existing PREDICTION section and outside the live-stream component', () => {
  const workspace = fs.readFileSync(require.resolve('../app/Workspace.tsx'), 'utf8');
  const stream = fs.readFileSync(require.resolve('../app/NctLiveStream.tsx'), 'utf8');
  const prediction = workspace.indexOf('top==="PREDICTION" && <section');
  const library = workspace.indexOf('<Phase3TrialLibrary', prediction);
  const nextTab = workspace.indexOf('top==="RESTRICTIONS" && <div', prediction);
  assert.ok(prediction >= 0 && library > prediction && library < nextTab);
  assert.ok(workspace.indexOf('Historical comparators', prediction) < library, 'library follows existing analysis table');
  assert.doesNotMatch(stream, /<Phase3TrialLibrary/);
});
