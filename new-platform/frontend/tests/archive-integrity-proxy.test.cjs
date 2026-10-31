const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (module, filename) => module._compile(
  ts.transpileModule(fs.readFileSync(filename, 'utf8'), { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  } }).outputText, filename);
const { NextRequest } = require('next/server');
const auth = require('../lib/auth.ts');
const routes = {
  'archive-health': require('../app/api/archive-health/route.ts'),
  'archive-manifest': require('../app/api/archive-manifest/route.ts'),
};
const health = { status: 'REVIEW_REQUIRED', archived_trials: 2, manifest_verification: 'PASS', verification_overdue: true, checks: { physical_records: 2 } };
const manifest = { manifest: { records: [{ nct_id: 'NCT00116805', sha256: 'a'.repeat(64) }], expected_nct_ids: ['NCT00116805'] }, manifest_sha256: 'b'.repeat(64), checksum_valid: true };
function setup() {
  const keys = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const before = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  const fetch = global.fetch;
  Object.assign(process.env, { DASHBOARD_PASSWORD: 'isolated-test-password', SESSION_SIGNING_KEY: 'isolated-test-signing-key-at-least-32-characters',
    PDUFA_API_BASE_URL: 'https://backend.example/', PDUFA_INTERNAL_API_KEY: 'isolated-internal-key-not-production' });
  return () => { global.fetch = fetch; for (const [key, value] of Object.entries(before)) { if (value === undefined) delete process.env[key]; else process.env[key] = value; } };
}
function request(resource, authenticated = true) {
  return new NextRequest('https://dashboard.example/api/' + resource + '?upstream=https://untrusted.example/', {
    headers: authenticated ? { cookie: auth.COOKIE_NAME + '=' + auth.makeSession() } : {},
  });
}
for (const [resource, route] of Object.entries(routes)) {
  test(resource + ': unauthenticated or invalid sessions cannot contact Render', async () => {
    const restore = setup();
    global.fetch = async () => assert.fail('Authentication must precede network');
    try {
      assert.equal((await route.GET(request(resource, false))).status, 401);
      const invalid = new NextRequest('https://dashboard.example/api/' + resource, { headers: { cookie: auth.COOKIE_NAME + '=invalid' } });
      assert.equal((await route.GET(invalid)).status, 401);
      delete process.env.DASHBOARD_PASSWORD;
      assert.equal((await route.GET(request(resource, false))).status, 401);
    } finally { restore(); }
  });
  test(resource + ': relays only existing GET report and preserves actual evidence status', async () => {
    const restore = setup(), expected = resource === 'archive-health' ? health : manifest;
    const calls = [];
    global.fetch = async (url, options) => {
      calls.push({ url, options });
      return new Response(JSON.stringify(expected), { headers: { 'content-type': 'application/json; charset=utf-8' } });
    };
    try {
      const response = await route.GET(request(resource));
      assert.equal(response.status, 200);
      assert.deepEqual(await response.json(), expected);
      assert.equal(response.headers.get('cache-control'), 'private, no-store');
      assert.equal(calls.length, 1);
      assert.equal(calls[0].url, 'https://backend.example/api/' + resource);
      assert.equal(calls[0].options.method, 'GET');
      assert.equal(calls[0].options.body, undefined);
      assert.equal(calls[0].options.cache, 'no-store');
      assert.equal(calls[0].options.redirect, 'error');
      assert.ok(calls[0].options.signal instanceof AbortSignal);
      assert.deepEqual(calls[0].options.headers, { 'X-Pdufa-Internal-Key': 'isolated-internal-key-not-production', Accept: 'application/json' });
      assert.equal(route.POST, undefined);
      assert.equal(route.PUT, undefined);
      assert.equal(route.DELETE, undefined);
    } finally { restore(); }
  });
  test(resource + ': missing or insecure backend configuration fails closed', async () => {
    const restore = setup();
    global.fetch = async () => assert.fail('Invalid configuration cannot make outbound requests');
    try {
      delete process.env.PDUFA_INTERNAL_API_KEY;
      assert.equal((await route.GET(request(resource))).status, 503);
      process.env.PDUFA_INTERNAL_API_KEY = 'isolated-internal-key-not-production';
      for (const base of ['', 'http://backend.example', 'https://user:pass@backend.example', 'invalid-url']) {
        process.env.PDUFA_API_BASE_URL = base;
        const result = await route.GET(request(resource));
        assert.equal(result.status, 503);
        assert.deepEqual(await result.json(), { error: 'Archive verification unavailable' });
      }
    } finally { restore(); }
  });
  test(resource + ': upstream failure details and credentials never reach browser', async () => {
    const restore = setup();
    try {
      for (const status of [401, 403, 404, 500, 503]) {
        global.fetch = async () => new Response('private upstream diagnostic', { status, headers: { 'content-type': 'application/json', 'X-Pdufa-Internal-Key': process.env.PDUFA_INTERNAL_API_KEY } });
        const result = await route.GET(request(resource));
        assert.equal(result.status, 503);
        assert.deepEqual(await result.json(), { error: 'Archive verification unavailable' });
        assert.equal(result.headers.get('X-Pdufa-Internal-Key'), null);
      }
      global.fetch = async () => new Response(JSON.stringify({ debug_key: process.env.PDUFA_INTERNAL_API_KEY }), { headers: { 'content-type': 'application/json' } });
      const echoed = await route.GET(request(resource));
      assert.equal(echoed.status, 503);
      assert.doesNotMatch(await echoed.text(), /isolated-internal-key/);
    } finally { restore(); }
  });
  test(resource + ': invalid JSON, HTML, nonobjects, timeout and redirects fail closed', async () => {
    const restore = setup();
    try {
      for (const [body, contentType] of [['<html>Login</html>', 'text/html'], ['{', 'application/json'], ['[]', 'application/json'], ['null', 'application/json'], ['"PASS"', 'application/json']]) {
        global.fetch = async () => new Response(body, { headers: { 'content-type': contentType } });
        assert.equal((await route.GET(request(resource))).status, 503);
      }
      for (const error of [new DOMException('private timeout diagnostic', 'TimeoutError'), new TypeError('private redirect diagnostic')]) {
        global.fetch = async () => { throw error; };
        const result = await route.GET(request(resource));
        assert.equal(result.status, 503);
        assert.deepEqual(await result.json(), { error: 'Archive verification unavailable' });
      }
    } finally { restore(); }
  });
}
