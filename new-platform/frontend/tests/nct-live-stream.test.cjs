const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');
const { create, act } = require('react-test-renderer');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, filename) => module._compile(
  ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022,
    jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  } }).outputText, filename);
const { NextRequest } = require('next/server');
const auth = require('../lib/auth.ts');
const parser = require('../lib/nct-live-stream.ts');
const { relayNctRun } = require('../lib/nct-stream-proxy.ts');
const { ProcessingNode, default: NctLiveStream } = require('../app/NctLiveStream.tsx');
global.IS_REACT_ACT_ENVIRONMENT = true;
const nct = 'NCT01234567';
const run = 'cb4c2bcc-5309-4226-93cd-2a1f01876258';
const pointer = { nct_id: nct, run_id: run };
const source = { url: 'https://clinicaltrials.gov/study/' + nct, sha256: 'a'.repeat(64), verified_at: '2026-10-30T13:00:00+00:00' };
const event = (sequence, changes = {}) => ({ ...pointer, sequence, node_id: 'sponsor', level: 4, status: 'PENDING', value: null, parent_id: 'trial_identity', kind: 'node', ...changes });
const frames = events => events.map(e => `id: ${run}:${e.sequence}\nevent: ${e.kind}\ndata: ${JSON.stringify(e)}\n\n`).join('');
const requestKey = '0fde6231-08bc-4f69-ae98-7c8f145ce4f4';

function configured() {
  const keys = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const before = Object.fromEntries(keys.map(k => [k, process.env[k]]));
  Object.assign(process.env, { DASHBOARD_PASSWORD: 'test-password-not-production', SESSION_SIGNING_KEY: 'test-only-signing-key-that-is-long-enough',
    PDUFA_API_BASE_URL: 'https://backend.example/', PDUFA_INTERNAL_API_KEY: 'test-only-internal-key' });
  return () => { for (const [k, v] of Object.entries(before)) { if (v === undefined) delete process.env[k]; else process.env[k] = v; } };
}
function req(path, options = {}) {
  return new NextRequest('https://dashboard.example' + path, { ...options, headers: {
    cookie: auth.COOKIE_NAME + '=' + auth.makeSession(), ...options.headers,
  } });
}

test('source events retain sequence ordering, pending/loading/verified states and parent dependencies', () => {
  let state = parser.initialRun(run, nct, 'dossier-1');
  for (const e of [event(1), event(2, { status: 'LOADING' }), event(3, { status: 'VERIFIED', value: { name: 'Sponsor A' }, source })]) state = parser.reduceNctEvent(state, e);
  assert.equal(state.nodes.sponsor.status, 'VERIFIED');
  assert.equal(state.nodes.trial_identity, undefined, 'client must not invent a parent completion');
  state = parser.reduceNctEvent(state, event(4, { node_id: 'trial_identity', level: 3, status: 'VERIFIED', source: null }));
  assert.equal(state.nodes.trial_identity.status, 'VERIFIED');
  const previous = state;
  assert.equal(parser.reduceNctEvent(state, event(3, { status: 'VERIFIED', value: 'duplicate', source })), previous);
  assert.throws(() => parser.reduceNctEvent(state, event(6)), /sequence gap/);
  assert.throws(() => parser.reduceNctEvent(state, event(5, { run_id: 'another-run-id' })), /identity mismatch/);
  assert.throws(() => parser.reduceNctEvent(state, event(5, { nct_id: 'NCT99999999' })), /identity mismatch/);
});

test('VERIFIED source leaves require a valid source URL, document digest and timestamp', () => {
  assert.equal(parser.isNctEvent(event(1, { status: 'VERIFIED', source })), true);
  assert.equal(parser.isNctEvent(event(1, { status: 'VERIFIED', source: null })), false);
  for (const changed of [{ url: 'javascript:alert(1)' }, { sha256: 'bad' }, { verified_at: '2026-10-30' }]) {
    assert.equal(parser.isNctEvent(event(1, { status: 'VERIFIED', source: { ...source, ...changed } })), false);
  }
});

test('SSE parser handles byte splits, UTF-8, CRLF, heartbeat comments and exact cursor identity', () => {
  const events = [event(1, { value: 'Médicament' }), event(2, { status: 'LOADING' })];
  const encoded = new TextEncoder().encode(': heartbeat\r\n\r\n' + frames(events).replaceAll('\n', '\r\n'));
  const reader = new parser.NctSseParser(pointer);
  const result = [];
  for (const byte of encoded) result.push(...reader.feed(Uint8Array.of(byte)));
  result.push(...reader.feed(new Uint8Array(), true));
  assert.deepEqual(result, events);
  assert.throws(() => {
    new parser.NctSseParser(pointer).feed(new TextEncoder().encode(frames([event(1)]).replace(`id: ${run}:1`, `id: ${run}:2`)));
  }, /cursor mismatch/);
  assert.throws(() => {
    new parser.NctSseParser(pointer).feed(new TextEncoder().encode(frames([event(1, { nct_id: 'NCT99999999' })])));
  }, /identity mismatch/);
});

test('truncated or malformed streams cannot become completed', () => {
  const reader = new parser.NctSseParser(pointer);
  reader.feed(new TextEncoder().encode(`id: ${run}:1\ndata: {"run_id":`));
  assert.throws(() => reader.feed(new Uint8Array(), true), /ended mid-event/);
  assert.throws(() => new parser.NctSseParser(pointer).feed(new TextEncoder().encode(`id: ${run}:1\ndata: not-json\n\n`)), SyntaxError);
  assert.equal(parser.initialRun(run, nct).terminal, false);
});

test('saved snapshot restores exact ordered run state and rejects false terminal claims', () => {
  const complete = event(3, { kind: 'complete', terminal: true, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE', value: { decision: 'ABSTAIN' } });
  const snapshot = { ...pointer, dossier_id: 'dossier-1', events: [event(1), event(2, { status: 'LOADING' }), complete], terminal: true };
  const state = parser.parseSnapshot(snapshot, pointer);
  assert.equal(state.terminal, true);
  assert.equal(state.sequence, 3);
  assert.equal(parser.eventCursor(state), run + ':3');
  assert.throws(() => parser.parseSnapshot({ ...snapshot, terminal: false }, pointer), /completion mismatch/);
  assert.throws(() => parser.parseSnapshot({ ...snapshot, nct_id: 'NCT99999999' }, pointer), /identity/);
  assert.deepEqual(parser.savedPointer({ ...pointer, evidence: 'not stored', session: 'not stored' }), pointer);
});

test('proxy authenticates before network access; POST requires exact same origin and UUID', async () => {
  const restore = configured(), original = global.fetch;
  global.fetch = async () => assert.fail('No outbound request is authorized');
  try {
    const unauth = new NextRequest('https://dashboard.example/api/nct-stream/' + nct + '/runs', { method: 'POST' });
    assert.equal((await relayNctRun(unauth, nct)).status, 401);
    for (const origin of [undefined, 'https://other.example']) {
      const headers = { 'content-type': 'application/json', ...(origin ? { origin } : {}) };
      assert.equal((await relayNctRun(req('/api/nct-stream/' + nct + '/runs', { method: 'POST', headers, body: JSON.stringify({ request_key: requestKey }) }), nct)).status, 403);
    }
    assert.equal((await relayNctRun(req('/api/nct-stream/' + nct + '/runs', { method: 'POST', headers: { origin: 'https://dashboard.example' }, body: '{"request_key":"bad"}' }), nct)).status, 422);
  } finally { restore(); global.fetch = original; }
});

test('proxy keeps API credentials server-side, relays validated resume headers and rejects non-SSE responses', async () => {
  const restore = configured(), original = global.fetch;
  let kind = 'json', calls = 0;
  global.fetch = async (url, options) => {
    calls += 1;
    assert.equal(options.headers['X-Pdufa-Internal-Key'], 'test-only-internal-key');
    assert.ok(options.signal);
    if (options.method === 'POST') {
      assert.equal(url, 'https://backend.example/api/nct-stream/' + nct + '/runs');
      assert.deepEqual(JSON.parse(options.body), { request_key: requestKey });
      return new Response(JSON.stringify({ ...pointer, dossier_id: 'dossier-1', latest_sequence: 0 }), { headers: { 'content-type': 'application/json' } });
    }
    assert.equal(url, 'https://backend.example/api/nct-stream/' + nct + '/runs/' + run + '/events?after=2');
    assert.equal(options.headers['Last-Event-ID'], run + ':2');
    return new Response(kind === 'sse' ? frames([event(3)]) : '{}', { headers: { 'content-type': kind === 'sse' ? 'text/event-stream' : 'application/json' } });
  };
  try {
    const created = await relayNctRun(req('/api/nct-stream/' + nct + '/runs', { method: 'POST', headers: { origin: 'https://dashboard.example' }, body: JSON.stringify({ request_key: requestKey, ignored: true }) }), nct);
    assert.equal(created.status, 200);
    assert.doesNotMatch(JSON.stringify(await created.json()), /test-only-internal-key/);
    const streamReq = () => req('/api/nct-stream/' + nct + '/runs/' + run + '/events?after=2', { headers: { 'last-event-id': run + ':2' } });
    assert.equal((await relayNctRun(streamReq(), nct, run, true)).status, 502);
    kind = 'sse';
    const streamed = await relayNctRun(streamReq(), nct, run, true);
    assert.equal(streamed.status, 200);
    assert.equal(streamed.headers.get('content-type'), 'text/event-stream; charset=utf-8');
    assert.match(streamed.headers.get('cache-control'), /private, no-store, no-transform/);
    assert.match(await streamed.text(), /id:/);
    assert.equal((await relayNctRun(req('/api/nct-stream/' + nct + '/runs/' + run + '/events', { headers: { 'last-event-id': 'different-run:2' } }), nct, run, true)).status, 422);
    assert.equal(calls, 3);
  } finally { restore(); global.fetch = original; }
});

test('only LOADING renders an accessible rotating processing indicator', () => {
  const pending = renderToStaticMarkup(React.createElement(ProcessingNode, { event: event(1) }));
  const loading = renderToStaticMarkup(React.createElement(ProcessingNode, { event: event(1, { status: 'LOADING' }) }));
  const insufficient = renderToStaticMarkup(React.createElement(ProcessingNode, { event: event(1, { status: 'INSUFFICIENT_EVIDENCE' }) }));
  assert.doesNotMatch(pending, /class="nct-processing-spinner"/);
  assert.match(loading, /class="nct-processing-spinner" role="img" aria-label="Processing"/);
  assert.doesNotMatch(insufficient, /class="nct-processing-spinner"/);
});

test('client reconnects after incomplete EOF, deduplicates prior events and persists only run pointer', async () => {
  const originalFetch = global.fetch, originalStorage = global.localStorage;
  const entries = new Map();
  global.localStorage = { getItem: k => entries.get(k) || null, setItem: (k, v) => entries.set(k, v), removeItem: k => entries.delete(k) };
  let streams = 0;
  global.fetch = async (url, options = {}) => {
    if (options.method === 'POST') return new Response(JSON.stringify({ ...pointer, dossier_id: 'dossier-1', latest_sequence: 1 }), { headers: { 'content-type': 'application/json' } });
    streams += 1;
    if (streams === 1) return new Response(frames([event(1)]), { headers: { 'content-type': 'text/event-stream' } });
    assert.match(url, /after=1$/);
    assert.equal(options.headers['Last-Event-ID'], run + ':1');
    return new Response(frames([event(1), event(2, { status: 'LOADING' }), event(3, { kind: 'complete', terminal: true, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE', value: { decision: 'ABSTAIN' } })]), { headers: { 'content-type': 'text/event-stream' } });
  };
  let view;
  try {
    await act(async () => { view = create(React.createElement(NctLiveStream)); });
    await act(async () => { view.root.findByType('input').props.onChange({ target: { value: nct } }); });
    await act(async () => { view.root.findByType('form').props.onSubmit({ preventDefault() {} }); await new Promise(resolve => setTimeout(resolve, 700)); });
    const output = JSON.stringify(view.toJSON());
    assert.match(output, /Processing run completed/);
    assert.equal(streams, 2);
    assert.equal(view.root.findAllByProps({ 'data-node-id': 'sponsor' }).length, 1);
    assert.deepEqual(JSON.parse(entries.get('pdufa_nct_processing_run_v1')), pointer);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = originalFetch;
    if (originalStorage === undefined) delete global.localStorage; else global.localStorage = originalStorage;
  }
});

test('reload restores a completed persisted snapshot without creating a new run or replaying the stream', async () => {
  const originalFetch = global.fetch, originalStorage = global.localStorage;
  global.localStorage = { getItem: () => JSON.stringify(pointer), setItem() {}, removeItem() {} };
  let calls = 0;
  global.fetch = async (url, options = {}) => {
    calls += 1;
    assert.equal(options.method, undefined);
    assert.equal(url, '/api/nct-stream/' + nct + '/runs/' + run);
    return new Response(JSON.stringify({ ...pointer, dossier_id: 'dossier-1', terminal: true,
      events: [event(1), event(2, { kind: 'complete', terminal: true, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE' })] }),
      { headers: { 'content-type': 'application/json' } });
  };
  let view;
  try {
    await act(async () => { view = create(React.createElement(NctLiveStream)); await new Promise(resolve => setTimeout(resolve, 20)); });
    assert.match(JSON.stringify(view.toJSON()), /Saved completed processing run restored/);
    assert.equal(calls, 1);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = originalFetch;
    if (originalStorage === undefined) delete global.localStorage; else global.localStorage = originalStorage;
  }
});

test('changing NCT aborts the old stream and cannot mix its results into the new selection', async () => {
  const originalFetch = global.fetch, originalStorage = global.localStorage;
  global.localStorage = { getItem: () => null, setItem() {}, removeItem() {} };
  const nextNct = 'NCT76543210', nextRun = '18c17552-5365-4d3b-a3ed-42a13d8eaeb8';
  let oldSignal;
  global.fetch = async (url, options = {}) => {
    const second = url.includes(nextNct);
    if (options.method === 'POST') return new Response(JSON.stringify({ run_id: second ? nextRun : run, nct_id: second ? nextNct : nct, dossier_id: 'dossier-1', latest_sequence: 0 }), { headers: { 'content-type': 'application/json' } });
    if (!second) {
      oldSignal = options.signal;
      const stream = new ReadableStream({ start(body) {
        body.enqueue(new TextEncoder().encode(frames([event(1, { value: 'Old selection' })])));
        options.signal.addEventListener('abort', () => body.error(new DOMException('Aborted', 'AbortError')), { once: true });
      } });
      return new Response(stream, { headers: { 'content-type': 'text/event-stream' } });
    }
    const completed = event(2, { run_id: nextRun, nct_id: nextNct, kind: 'complete', terminal: true, node_id: 'main', level: 1, status: 'INSUFFICIENT_EVIDENCE' });
    const nextEvents = [event(1, { run_id: nextRun, nct_id: nextNct, value: 'New selection' }), completed];
    const body = nextEvents.map(e => `id: ${nextRun}:${e.sequence}\nevent: ${e.kind}\ndata: ${JSON.stringify(e)}\n\n`).join('');
    return new Response(body, { headers: { 'content-type': 'text/event-stream' } });
  };
  let view;
  try {
    await act(async () => { view = create(React.createElement(NctLiveStream)); });
    await act(async () => { view.root.findByType('input').props.onChange({ target: { value: nct } }); });
    await act(async () => { view.root.findByType('form').props.onSubmit({ preventDefault() {} }); await new Promise(resolve => setTimeout(resolve, 20)); });
    await act(async () => { view.root.findByType('input').props.onChange({ target: { value: nextNct } }); });
    await act(async () => { view.root.findByType('form').props.onSubmit({ preventDefault() {} }); await new Promise(resolve => setTimeout(resolve, 20)); });
    assert.equal(oldSignal.aborted, true);
    const output = JSON.stringify(view.toJSON());
    assert.match(output, /New selection/);
    assert.doesNotMatch(output, /Old selection/);
    assert.match(output, /NCT76543210/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = originalFetch;
    if (originalStorage === undefined) delete global.localStorage; else global.localStorage = originalStorage;
  }
});
