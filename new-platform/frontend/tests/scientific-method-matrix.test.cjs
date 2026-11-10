const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), ts = require('typescript');
require.extensions['.ts'] = (m, f) => m._compile(ts.transpileModule(fs.readFileSync(f, 'utf8'), {
  compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true}
}).outputText, f);
const {assertMatrixPhaseSnapshot, isolatedMedicalBackend, validateReviewMatrix} = require('../lib/medical-review-matrix.ts');
const {NextRequest} = require('next/server');
const {GET} = require('../app/api/predictions/medical-matrix/route.ts');
const auth = require('../lib/auth.ts');
const nct = 'NCT05507203';
function matrix() {
  return {nct, totalPositions: 800, verifiedPhase: null, phaseEventId: null,
    counts: {SCORED: 0, NOT_APPLICABLE: 0, RETRACTED: 0, STALE_PHASE: 0, UNREVIEWED: 0, VERIFY_PHASE: 800},
    assessments: Array.from({length: 40}, (_, i) => ({assessmentIndex: i + 1, status: 'VERIFY_PHASE', scoreOutOf100: null,
      reviewedMethods: 0, excludedMethods: 0, pendingMethods: 20, applicableMethods: 20})),
    selectedAssessment: null, historicalReviewEvents: 0, recordedGapEvents: 0, phaseHistory: [],
    fdaPredictions: {APPROVAL: 'ABSTAIN', CRL: 'ABSTAIN', REVIEW_DELAY: 'ABSTAIN'}, certainty: 'NOT_VALIDATED'};
}
function method(i, status = 'VERIFY_PHASE') {
  return {methodIndex: i + 1, status, grade: null, reviewEventId: null, revision: null,
    reviewedAt: null, reviewerId: null, rationale: null, sourceEvidence: [], history: [], evidenceGaps: []};
}
function reviewed() {
  const m = matrix();
  m.verifiedPhase = 'PHASE3'; m.phaseEventId = 'p1';
  m.phaseHistory = [{phase_event_id: 'p1', verified_phase: 'PHASE3', reviewer_id: 'phase-reviewer', verified_at: '2026-11-08'}];
  m.counts = {...m.counts, VERIFY_PHASE: 0, UNREVIEWED: 799, SCORED: 1};
  m.assessments.forEach(a => a.status = 'NOT_REVIEWED');
  Object.assign(m.assessments[0], {status: 'PROVISIONAL', reviewedMethods: 1, pendingMethods: 19, scoreOutOf100: 80});
  const r = {review_event_id: 'r1', verified_phase: 'PHASE3', phase_event_id: 'p1', assessment_index: 1, method_index: 1,
    reviewer_id: 'offline-fixture-reviewer', evidence_reviewed_at: '2026-11-08', rationale: 'Offline fixture', disposition: 'SCORED',
    revision: 1, grade: 4, evidence: [{sourceUrl: 'https://clinicaltrials.gov/study/' + nct, stageDocumentSha256: 'a'.repeat(64)}]};
  const first = {...method(0, 'SCORED'), grade: 4, reviewEventId: 'r1', revision: 1, reviewerId: r.reviewer_id,
    reviewedAt: r.evidence_reviewed_at, rationale: r.rationale, sourceEvidence: r.evidence, history: [r]};
  m.selectedAssessment = {...m.assessments[0], methods: Array.from({length:20}, (_, i) => i ? method(i, 'UNREVIEWED') : first)};
  m.historicalReviewEvents = 1;
  return m;
}
test('isolated backend accepts only an explicit HTTPS root', () => {
  assert.equal(isolatedMedicalBackend('https://isolated.example/'), 'https://isolated.example');
  for (const value of [undefined, '', 'http://isolated.example', 'https://user:secret@example.com', 'https://example.com/path', 'https://example.com/?key=value'])
    assert.equal(isolatedMedicalBackend(value), null);
});
test('800 unreviewed slots never become scores, exclusions, or FDA probabilities', () => {
  const m = matrix();
  assert.equal(validateReviewMatrix(m, nct).counts.SCORED, 0);
  for (const alter of [
    x => x.nct = 'NCT00000000', x => x.counts.SCORED = 1,
    x => x.assessments[0].scoreOutOf100 = 0,
    x => x.fdaPredictions.APPROVAL = 0.8,
    x => x.certainty = 'VALIDATED'
  ]) {
    const invalid = matrix(); alter(invalid); assert.throws(() => validateReviewMatrix(invalid, nct));
  }
});
test('method detail preserves retraction and earlier phase history without counting prior grades', () => {
  const m = reviewed(), first = m.selectedAssessment.methods[0], old = structuredClone(first.history[0]);
  old.phase_event_id = 'p0'; old.verified_phase = 'PHASE2'; old.review_event_id = 'old';
  m.phaseHistory.unshift({phase_event_id: 'p0', verified_phase: 'PHASE2', reviewer_id: 'prior-reviewer', verified_at: '2026-10-01'});
  first.history.unshift(old); m.historicalReviewEvents++;
  assert.equal(validateReviewMatrix(m, nct, 1).selectedAssessment.scoreOutOf100, 80);
  const retracted = {...first.history.at(-1), revision: 2, review_event_id: 'r2', disposition: 'RETRACTED', grade: null, evidence: []};
  first.history.push(retracted); m.historicalReviewEvents++;
  Object.assign(first, {status: 'RETRACTED', grade: null, reviewEventId: 'r2', revision: 2, sourceEvidence: []});
  Object.assign(m.assessments[0], {status: 'NOT_REVIEWED', reviewedMethods: 0, pendingMethods: 20, scoreOutOf100: null});
  Object.assign(m.selectedAssessment, m.assessments[0]);
  m.counts.SCORED = 0; m.counts.RETRACTED = 1;
  const detail = validateReviewMatrix(m, nct, 1).selectedAssessment.methods[0];
  assert.equal(detail.grade, null); assert.equal(detail.history[0].grade, 4);
});
test('reject incoherent summary, current phase, selected counts and method normalization', () => {
  for (const alter of [
    m => m.counts.SCORED = 0,
    m => m.assessments[0].status = 'NOT_REVIEWED',
    m => m.phaseEventId = null,
    m => m.selectedAssessment.reviewedMethods = 2,
    m => m.selectedAssessment.scoreOutOf100 = 99,
    m => {m.assessments[0].scoreOutOf100 = 99; m.selectedAssessment.scoreOutOf100 = 99;},
    m => m.selectedAssessment.methods[0].reviewEventId = 'different-event',
    m => m.selectedAssessment.methods[0].history[0].phase_event_id = 'p0',
    m => m.selectedAssessment.methods[0].history[0].assessment_index = 2,
    m => m.selectedAssessment.methods[0].sourceEvidence = []
  ]) {
    const m = reviewed(); alter(m); assert.throws(() => validateReviewMatrix(m, nct, 1));
  }
});
test('reject malformed historical grades, revisions, dispositions, identities and uncaptured sources', () => {
  for (const alter of [
    r => r.grade = 6, r => r.grade = 3.5, r => r.grade = null, r => r.revision = 0,
    r => r.revision = 1.5, r => r.disposition = 'MISSING', r => r.phase_event_id = '',
    r => r.review_event_id = '', r => r.evidence = [],
    r => r.evidence[0].stageDocumentSha256 = 'invalid', r => r.evidence[0].sourceUrl = 'http://source.example',
    r => r.disposition = 'NOT_APPLICABLE'
  ]) {
    const m = reviewed(); alter(m.selectedAssessment.methods[0].history[0]);
    assert.throws(() => validateReviewMatrix(m, nct, 1));
  }
});
test('catalog and review reads must share the same latest verified phase-event identity', () => {
  const m = reviewed();
  assert.doesNotThrow(() => assertMatrixPhaseSnapshot({phaseEvents: [{phase_event_id: 'p1', verified_phase: 'PHASE3'}]}, m));
  assert.throws(() => assertMatrixPhaseSnapshot({phaseEvents: [{phase_event_id: 'p2', verified_phase: 'PHASE3'}]}, m), /PHASE_CHANGED/);
  assert.throws(() => assertMatrixPhaseSnapshot({phaseEvents: []}, m), /PHASE_CHANGED/);
});
test('proxy authenticates, rejects missing isolated backend despite production URL, and is read-only', async () => {
  const names = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_MEDICAL_REVIEW_API_BASE_URL', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY'];
  const saved = Object.fromEntries(names.map(k => [k, process.env[k]]));
  try {
    process.env.DASHBOARD_PASSWORD = 'local-test-password'; process.env.SESSION_SIGNING_KEY = 'x'.repeat(32);
    process.env.PDUFA_INTERNAL_API_KEY = 'local-test-key'; process.env.PDUFA_API_BASE_URL = 'https://production.example';
    delete process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL;
    const url = 'http://localhost/api/predictions/medical-matrix?nct=' + nct;
    assert.equal((await GET(new NextRequest(url))).status, 401);
    const headers = {cookie: auth.COOKIE_NAME + '=' + auth.makeSession()};
    assert.equal((await GET(new NextRequest(url, {headers}))).status, 503);
    assert.equal((await GET(new NextRequest(url + '&assessmentIndex=41', {headers}))).status, 422);
  } finally {for (const [key, value] of Object.entries(saved)) {if (value === undefined) delete process.env[key]; else process.env[key] = value;}}
});
test('proxy uses only the configured isolated origin and keeps the internal credential server-side', async () => {
  const names = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_MEDICAL_REVIEW_API_BASE_URL', 'PDUFA_MEDICAL_INTERNAL_API_KEY', 'PDUFA_MEDICAL_REVIEW_READ_KEY'];
  const saved = Object.fromEntries(names.map(k => [k, process.env[k]])), previousFetch = global.fetch;
  try {
    process.env.DASHBOARD_PASSWORD = 'local-test-password'; process.env.SESSION_SIGNING_KEY = 'x'.repeat(32);
    process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL = 'https://isolated.example';
    process.env.PDUFA_MEDICAL_INTERNAL_API_KEY = 'local-test-medical-key';
    process.env.PDUFA_MEDICAL_REVIEW_READ_KEY = 'local-scoped-read-only-key';
    const m = matrix();
    m.selectedAssessment = {...m.assessments[0], methods: Array.from({length:20}, (_, i) => method(i))};
    let calls = 0;
    global.fetch = async (url, options) => {
      calls++; assert.equal(url, 'https://isolated.example/api/internal/medical-assessments/' + nct + '/matrix?assessmentIndex=1');
      assert.equal(options.headers['x-pdufa-internal-key'], 'local-scoped-read-only-key');
      assert.equal(options.redirect, 'error'); assert.equal(options.cache, 'no-store');
      return Response.json(m);
    };
    const response = await GET(new NextRequest('http://localhost/api/predictions/medical-matrix?nct=' + nct + '&assessmentIndex=1', {
      headers: {cookie: auth.COOKIE_NAME + '=' + auth.makeSession()}
    }));
    assert.equal(response.status, 200); assert.equal(calls, 1);
    const body = await response.text(); assert.ok(!body.includes('local-scoped-read-only-key'));
    assert.ok(!body.includes('local-test-medical-key'));
    assert.equal(JSON.parse(body).review.selectedAssessment.methods.length, 20);
  } finally {
    global.fetch = previousFetch;
    for (const [key, value] of Object.entries(saved)) {if (value === undefined) delete process.env[key]; else process.env[key] = value;}
  }
});
