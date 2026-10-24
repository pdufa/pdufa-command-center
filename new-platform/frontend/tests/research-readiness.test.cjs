const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (m, file) => m._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true}
}).outputText, file);
const {researchReadiness, evidenceSource} = require('../lib/research-readiness.ts');
const PID = 'PDUFA-000001', EXACT = 'TRIAL|NCT01234567|ABC';

function review(stage = 'GEM_JR', ready = false, programId = PID, exactKey = EXACT) {
  const id = {programId, exactKey};
  const boundary = {assessmentScoreChange: false, fsFaChange: false};
  const missingRequirements = ready ? [] : ['complete verified assessment', 'exact-program market evidence', 'verified catalyst', 'financing and dilution risk review'];
  return {...id, stage, researchOnly: true, ordersEnabled: false, fsFaChanges: false,
    marketDataStatus: ready ? 'OK' : 'ALPACA_AUTH_FAILED',
    assessmentEvidence: {status: ready ? 'COMPLETE' : 'ASSESSMENT_INCOMPLETE', assessment_score: ready ? 80 : null, assessment_coverage: ready ? 100 : 40},
    marketEvidenceReview: {...id, ...boundary, qualificationChange: false, recommendation: null, status: ready ? 'RESEARCH_ONLY' : 'INSUFFICIENT_EVIDENCE'},
    decisionReadiness: {...id, ...boundary, ordersEnabled: false, status: ready ? 'READY_FOR_HUMAN_RESEARCH_REVIEW' : 'NOT_READY',
      missingRequirements, tradeCall: null, entryPrice: null, targetPrice: null, stopLoss: null},
    riskEvidenceReview: {...id, ...boundary, stage, identityStatus: 'EXACT_IDENTITY_MATCH', researchOnly: true, ordersEnabled: false, qualificationChange: false,
      catalystVerified: ready, financingRiskReviewed: ready, riskFlags: ['Dilution remains a recorded risk'],
      checks: ['catalystTiming', 'cashRunway', 'dilutionRisk'].map(id => ({id, label: id, status: ready ? 'REVIEWED' : 'MISSING',
        reason: ready ? 'Existing source review retained' : 'Source review required for this program',
        source: 'https://www.sec.gov/Archives/edgar/example', sourceDate: '2026-10-20', checkedAt: '2026-10-23'}))},
  };
}

function withSources(data) {
  data.sourceEvidence = {programId: data.programId, exactKey: data.exactKey, ticker: 'ABC', researchOnly: true,
    ordersEnabled: false, assessmentScoreChange: false, fsFaChanges: false, financingRiskReviewed: false,
    clinical: {status: 'OBSERVED', note: 'Exact trial record', facts: [{label: 'Enrollment', value: '963 (ACTUAL)', source: 'https://clinicaltrials.gov/study/NCT01234567', sourceDate: '2026-03-25', checkedAt: '2026-10-23', status: 'OBSERVED'}]},
    financial: {status: 'OBSERVED', note: 'Company source; financing clearance still required', facts: []}};
  return data;
}

test('source facts cannot cross program identities or claim financing clearance', () => {
  const data = withSources(review());
  assert.equal(researchReadiness(data, PID, EXACT, 'GEM_JR'), data);
  for (const change of [r => r.sourceEvidence.exactKey = 'OTHER', r => r.sourceEvidence.financingRiskReviewed = true,
    r => r.sourceEvidence.assessmentScoreChange = true, r => r.sourceEvidence.clinical.facts[0].value = {unknown: true}]) {
    const bad = structuredClone(data); change(bad);
    assert.throws(() => researchReadiness(bad, PID, EXACT, 'GEM_JR'));
  }
});

test('readiness requires the exact program, selected assessment stage, and all source evidence', () => {
  for (const stage of ['GEM_JR', 'GEM']) {
    for (const ready of [false, true]) assert.equal(researchReadiness(review(stage, ready), PID, EXACT, stage).stage, stage);
  }
  for (const mutate of [
    r => r.programId = 'PDUFA-000002',
    r => r.exactKey = 'ANOTHER_TRIAL',
    r => r.riskEvidenceReview.stage = 'GEM',
    r => r.marketEvidenceReview.exactKey = 'ANOTHER_TRIAL',
    r => r.decisionReadiness.ordersEnabled = true,
    r => r.fsFaChanges = true,
    r => r.decisionReadiness.tradeCall = 'BUY',
    r => r.marketEvidenceReview.recommendation = 'BUY',
    r => r.decisionReadiness.status = 'READY_FOR_HUMAN_RESEARCH_REVIEW',
    r => r.decisionReadiness.missingRequirements = [],
    r => r.riskEvidenceReview.catalystVerified = true,
    r => r.riskEvidenceReview.checks[2] = r.riskEvidenceReview.checks[1],
    r => delete r.assessmentEvidence,
  ]) {
    const data = review(); mutate(data);
    assert.throws(() => researchReadiness(data, PID, EXACT, 'GEM_JR'));
  }
  const incomplete = review('GEM_JR', true);
  incomplete.assessmentEvidence.assessment_coverage = 40;
  assert.throws(() => researchReadiness(incomplete, PID, EXACT, 'GEM_JR'));
  assert.equal(evidenceSource('https://www.sec.gov/Archives/edgar/example'), 'https://www.sec.gov/Archives/edgar/example');
  for (const source of ['', 'javascript:alert(1)', 'https://user:secret@example.com']) assert.equal(evidenceSource(source), undefined);
});

test('authenticated proxy withholds cross-program or disabled review and keeps credentials server-side', async () => {
  const {NextRequest} = require('next/server');
  const auth = require('../lib/auth.ts');
  const route = require('../app/api/review/program-decision-readiness/[programId]/route.ts');
  const keys = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const previous = Object.fromEntries(keys.map(k => [k, process.env[k]])), previousFetch = global.fetch;
  Object.assign(process.env, {DASHBOARD_PASSWORD: 'test-only-password', SESSION_SIGNING_KEY: 'test-only-signing-key-that-is-long-enough',
    PDUFA_API_BASE_URL: 'https://isolated.example', PDUFA_INTERNAL_API_KEY: 'test-only-backend-secret'});
  const cookie = auth.COOKIE_NAME + '=' + auth.makeSession();
  const query = new URLSearchParams({stage: 'GEM_JR', identity: EXACT});
  const request = (params = query, signed = true) => new NextRequest('http://localhost/api/review/program-decision-readiness/' + PID + '?' + params,
    {headers: signed ? {cookie} : {}});
  const context = {params: Promise.resolve({programId: PID})};
  let calls = [];
  global.fetch = async (url, options) => {calls.push({url, options}); return {ok: true, json: async () => review()};};
  try {
    assert.equal((await route.GET(request(query, false), context)).status, 401);
    assert.equal((await route.GET(request(new URLSearchParams({stage: 'PIPELINE', identity: EXACT})), context)).status, 422);
    assert.equal((await route.GET(request(new URLSearchParams({stage: 'GEM_JR'})), context)).status, 422);
    assert.equal(calls.length, 0);
    const response = await route.GET(request(), context);
    assert.equal(response.status, 200);
    assert.equal(response.headers.get('cache-control'), 'private, no-store');
    assert.equal(calls[0].url, 'https://isolated.example/api/review/program-decision-readiness/' + PID + '?stage=GEM_JR');
    assert.equal(calls[0].options.redirect, 'error');
    assert.equal(calls[0].options.headers['x-pdufa-internal-key'], 'test-only-backend-secret');
    assert.doesNotMatch(JSON.stringify(await response.json()), /test-only-backend-secret/);
    global.fetch = async () => ({ok: true, json: async () => review('GEM')});
    assert.equal((await route.GET(request(), context)).status, 503);
    global.fetch = async () => ({ok: false, status: 404});
    assert.equal((await route.GET(request(), context)).status, 404);
    global.fetch = async () => ({ok: false, status: 401, json: async () => ({secret: 'never-return'})});
    const denied = await route.GET(request(), context);
    assert.equal(denied.status, 503);
    assert.doesNotMatch(JSON.stringify(await denied.json()), /never-return/);
  } finally {
    global.fetch = previousFetch;
    for (const key of keys) if (previous[key] === undefined) delete process.env[key]; else process.env[key] = previous[key];
  }
});

test('trial panel loads risk reviews independently of market failure and aborts old trial and stage requests', async () => {
  const React = require('react');
  const {create, act} = require('react-test-renderer');
  const View = require('../app/ProgramMarketEnrichment.tsx').default;
  global.IS_REACT_ACT_ENVIRONMENT = true;
  const previousFetch = global.fetch, requests = [];
  global.fetch = (url, options) => new Promise(resolve => requests.push({url, options, resolve}));
  let view;
  const props = {programId: PID, exactKey: EXACT, stage: 'GEM_JR'};
  try {
    await act(async () => {view = create(React.createElement(View, props));});
    assert.equal(requests.length, 2);
    assert.match(requests[1].url, /stage=GEM_JR/);
    await act(async () => view.update(React.createElement(View, {...props, stage: 'GEM'})));
    assert.ok(requests.slice(0, 2).every(r => r.options.signal.aborted));
    await act(async () => requests[1].resolve({ok: true, json: async () => review('GEM_JR', true)}));
    assert.doesNotMatch(JSON.stringify(view.toJSON()), /Ready for human review/);
    await act(async () => requests[2].resolve({ok: false, status: 503}));
    await act(async () => requests[3].resolve({ok: true, json: async () => withSources(review('GEM'))}));
    let rendered = JSON.stringify(view.toJSON());
    assert.match(rendered, /Alpaca rejected the configured API credentials/);
    assert.match(rendered, /Source review required for this program/);
    assert.match(rendered, /Dilution remains a recorded risk/);
    assert.equal(view.root.findAllByProps({'aria-label': 'Investment research readiness'}).length, 1);
    assert.equal(view.root.findAllByType('a').length, 4);
    assert.equal(view.root.findAllByType('details').length, 1);
    assert.notEqual(view.root.findByType('details').props.open, true);
    assert.match(rendered, /963 \(ACTUAL\)/);
    const second = {...props, programId: 'PDUFA-000002', exactKey: 'TRIAL|NCT00000002|DEF', stage: 'GEM'};
    await act(async () => view.update(React.createElement(View, second)));
    assert.ok(requests.slice(2, 4).every(r => r.options.signal.aborted));
    await act(async () => requests[5].resolve({ok: true, json: async () => review('GEM', true)}));
    rendered = JSON.stringify(view.toJSON());
    assert.doesNotMatch(rendered, /Ready for human review|Source review required for this program/);
    assert.match(rendered, /Research readiness is unavailable/);
  } finally {
    if (view) await act(async () => view.unmount());
    global.fetch = previousFetch;
  }
});
