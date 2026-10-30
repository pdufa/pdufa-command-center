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
const route = require('../app/api/archive-health/route.ts');
const { isArchiveHealth, archiveCount } = require('../lib/archive-health.ts');
const Panel = require('../app/ArchiveHealthPanel.tsx').default;
const report = {
  archived_trials: 11622, archive_integrity: 'PASS', manifest_verification: 'PASS',
  last_verified: '2026-10-30T13:14:26Z', next_scheduled_verification: '2026-10-31T03:00:00Z',
  scientific_ready_trials: 0, trials_needing_additional_evidence: 11622,
  trials_with_regulatory_outcome_evidence: 0,
  inventory: { statistical_analyses: { present: 40, missing: 11582 } },
  checks: { sha256_mismatches: 0 }, scheduler: { time_zone: 'America/Los_Angeles' },
  definitions: { statistical_analyses: 'Reported statistical analysis; not proof of clinical benefit.' },
  scientific_readiness_scope: 'Evidence screening only; independent validation required.',
};

test('unverified counts never become zero; malformed backend reports are rejected', () => {
  assert.equal(archiveCount(null), 'Unverified');
  assert.equal(archiveCount(0), '0');
  assert.equal(isArchiveHealth(report), true);
  assert.equal(isArchiveHealth({ ...report, archived_trials: -1 }), false);
  assert.equal(isArchiveHealth({ ...report, last_verified: 'invalid' }), false);
  assert.equal(isArchiveHealth({ ...report, inventory: { efficacy: { present: null, missing: 1 } } }), false);
});

test('archive endpoint authenticates before contacting backend and remains read-only', async () => {
  const previous = global.fetch;
  global.fetch = async () => assert.fail('Unauthenticated outbound request');
  try {
    const response = await route.GET(new NextRequest('https://dashboard.example/api/archive-health'));
    assert.equal(response.status, 401);
    assert.equal(response.headers.get('cache-control'), 'private, no-store');
    assert.equal(route.POST, undefined);
  } finally { global.fetch = previous; }
});

test('authenticated proxy uses existing secret only server-side and rejects backend failure', async () => {
  const previousFetch = global.fetch;
  const keys = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const previous = Object.fromEntries(keys.map(key => [key, process.env[key]]));
  Object.assign(process.env, { DASHBOARD_PASSWORD: 'archive-test-password',
    SESSION_SIGNING_KEY: 'archive-test-signing-key-long-enough',
    PDUFA_API_BASE_URL: 'https://backend.example/', PDUFA_INTERNAL_API_KEY: 'test-internal-key' });
  let good = true;
  global.fetch = async (url, options) => {
    assert.equal(url, 'https://backend.example/api/archive-health');
    assert.equal(options.headers['x-pdufa-internal-key'], 'test-internal-key');
    assert.equal(options.method, undefined);
    assert.equal(options.cache, 'no-store');
    return { ok: good, json: async () => report };
  };
  try {
    const request = () => new NextRequest('https://dashboard.example/api/archive-health', {
      headers: { cookie: auth.COOKIE_NAME + '=' + auth.makeSession() },
    });
    const response = await route.GET(request());
    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), report);
    good = false;
    const failed = await route.GET(request());
    assert.equal(failed.status, 503);
    assert.doesNotMatch(JSON.stringify(await failed.json()), /PASS|test-internal-key/);
  } finally {
    global.fetch = previousFetch;
    for (const [key, value] of Object.entries(previous)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
});

test('initial archive panel is expandable and displays no invented verified results', () => {
  const previousFetch = global.fetch;
  global.fetch = async () => assert.fail('Server rendering must not fetch archive data');
  try {
    const html = renderToStaticMarkup(React.createElement(Panel));
    assert.match(html, /<details/);
    assert.match(html, /<summary[^>]*>ARCHIVE HEALTH &amp; SCIENTIFIC READINESS<\/summary>/);
    assert.match(html, /role="status"/);
    assert.match(html, /Expand to load the saved verification report/);
    assert.doesNotMatch(html, /11,622|>PASS<|<table/);
  } finally {
    global.fetch = previousFetch;
  }
});
