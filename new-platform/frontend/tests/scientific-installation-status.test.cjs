const test = require('node:test'), assert = require('node:assert/strict'), fs = require('node:fs'), ts = require('typescript');
require.extensions['.ts'] = (m, f) => m._compile(ts.transpileModule(fs.readFileSync(f, 'utf8'), {
  compilerOptions: {target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, esModuleInterop: true}
}).outputText, f);
const {validateMedicalInstallation, MAIN_RESEARCH_CHECKPOINT, researchCheckpointEvidenceUrl} = require('../lib/medical-installation-status.ts');
const {NextRequest} = require('next/server');
const {GET} = require('../app/api/predictions/medical-installation/route.ts');
const auth = require('../lib/auth.ts');
function unknown() {
  return {schemaVersion: 1, observedAt: '2026-11-08T18:00:00Z', storage: {state: 'BLOCKED', kind: 'postgresql'},
    medicalInstallation: {state: 'BLOCKED', reason: 'Storage unavailable', counts: null, tasks: [], currentTaskId: null,
      definitions: {UNKNOWN: 'No observation is inferred'}, clinicalSignoff: 'NOT_VERIFIED',
      fdaPredictions: {APPROVAL: 'ABSTAIN', CRL: 'ABSTAIN', REVIEW_DELAY: 'ABSTAIN'}, certainty: 'NOT_VALIDATED'}};
}
function observed() {
  const root = unknown(); root.storage.state = 'READY';
  Object.assign(root.medicalInstallation, {state: 'OBSERVED', counts: {canonicalTrials: 29, observedTrialLedgers: 29,
    sourceCompleteTrials: 29, sourceStages: 348, phaseVerifiedTrials: 0, potentialMethodPositions: 23200,
    recordedCurrentPhaseGrades: 0, excludedMethods: 0, pendingObservedMethods: 23200, unobservedMethodPositions: 0,
    completedAssessments: 0, historicalReviewEvents: 0, recordedGapEvents: 0, independentlySignedClinicalReviews: null,
    methodStates: {SCORED: 0, NOT_APPLICABLE: 0, RETRACTED: 0, STALE_PHASE: 0, UNREVIEWED: 0, VERIFY_PHASE: 23200}},
    tasks: [{id: 'medical.phase-verification', title: 'Verify current phase', status: 'ACTIVE', completed: 0, remaining: 29,
      dependency: 'Independent original registry review', evidence: 'Phase event ledger'}], currentTaskId: 'medical.phase-verification',
    taskCounts: {VERIFIED: 0, ACTIVE: 1, BLOCKED: 0, UNKNOWN: 0},
    sourceCollectionDates: {oldest: '2026-11-08T18:00:00Z', newest: '2026-11-08T18:00:00Z', freshnessValidation: 'NOT_ADJUDICATED'}});
  return root;
}
test('Revision 36 documentary checkpoint traces exact original captures without promoting clinical counts', () => {
  const path = require('node:path'), crypto = require('node:crypto');
  const packetDir = path.resolve(__dirname, '../../../docs/medical-review-pilot-20261108');
  const receipt = JSON.parse(fs.readFileSync(path.join(packetDir, 'revision36-original-history/public_browser_receipt.json')));
  const comparison = JSON.parse(fs.readFileSync(path.join(packetDir, 'revision36-original-history/validated_comparison.json')));
  const checkpoint = MAIN_RESEARCH_CHECKPOINT;
  assert.equal(checkpoint.nct, receipt.nct);
  assert.equal(checkpoint.candidateMethodPositions, 18);
  assert.equal(checkpoint.unexaminedMethodPositions, 782);
  assert.equal(checkpoint.officialMethodGrades, 0);
  assert.equal(checkpoint.candidateMethodPositions + checkpoint.unexaminedMethodPositions, 800);
  assert.equal(checkpoint.tasks.find(task => task.id === checkpoint.currentTaskId).status, 'ACTIVE');
  assert.equal(new Set(checkpoint.tasks.map(task => task.id)).size, checkpoint.tasks.length);
  for (const capture of receipt.versions) {
    const bytes = fs.readFileSync(path.join(packetDir, 'revision36-original-history', capture.artifact));
    const original = JSON.parse(bytes);
    assert.equal(capture.httpStatus, 200);
    assert.equal(original.studyVersion, capture.apiIndex);
    assert.equal(crypto.createHash('sha256').update(bytes).digest('hex'), capture.sha256);
    assert.equal(comparison.versionData['v' + capture.version].sourceSha256, capture.sha256);
  }
  for (const task of checkpoint.tasks.filter(task => task.status === 'VERIFIED')) {
    assert.ok(task.evidencePath);
    assert.ok(fs.existsSync(path.join(packetDir, task.evidencePath)));
    assert.ok(researchCheckpointEvidenceUrl(task.evidencePath).startsWith('https://github.com/pdufa/pdufa-command-center/blob/'));
  }
  assert.match(checkpoint.tasks.find(task => task.id === 'r36.source-reconciliation').acceptance, /does not resolve 516 versus 517/);
  assert.equal(checkpoint.tasks.find(task => task.id === 'r36.independent-grading').status, 'BLOCKED');
  assert.equal(checkpoint.tasks.find(task => task.id === 'r36.preview-runtime').status, 'VERIFIED');
  assert.equal(checkpoint.tasks.find(task => task.id === 'r36.backend-rollout').status, 'VERIFIED');
  assert.equal(validateMedicalInstallation(unknown()).installation.counts, null);
});
test('missing ledger observations remain unknown counts, never zeros', () => {
  const value = unknown();
  assert.equal(validateMedicalInstallation(value).installation.counts, null);
  value.medicalInstallation.counts = {};
  assert.throws(() => validateMedicalInstallation(value), /UNKNOWN_INSTALLATION_COUNTS/);
});
test('current task and methods reconcile with the actual potential positions', () => {
  assert.equal(validateMedicalInstallation(observed()).installation.currentTaskId, 'medical.phase-verification');
  for (const change of [
    x => x.medicalInstallation.counts.recordedCurrentPhaseGrades = 348,
    x => x.medicalInstallation.counts.unobservedMethodPositions = 1,
    x => x.medicalInstallation.currentTaskId = 'medical.fake-task',
    x => x.medicalInstallation.counts.independentlySignedClinicalReviews = 0,
    x => x.storage.kind = 'sqlite',
    x => x.medicalInstallation.fdaPredictions.APPROVAL = 0.8
  ]) {const value = observed(); change(value); assert.throws(() => validateMedicalInstallation(value));}
});
test('isolated monitor proxy authenticates, refuses production fallback, and withholds malformed observations', async () => {
  const names = ['DASHBOARD_PASSWORD', 'SESSION_SIGNING_KEY', 'PDUFA_MEDICAL_REVIEW_API_BASE_URL', 'PDUFA_API_BASE_URL', 'PDUFA_INTERNAL_API_KEY', 'PDUFA_MEDICAL_REVIEW_READ_KEY'];
  const saved = Object.fromEntries(names.map(k => [k, process.env[k]])), fetchBefore = global.fetch;
  try {
    process.env.DASHBOARD_PASSWORD = 'local-fixture-password'; process.env.SESSION_SIGNING_KEY = 'x'.repeat(32);
    process.env.PDUFA_INTERNAL_API_KEY = 'local-fixture-key'; process.env.PDUFA_MEDICAL_REVIEW_READ_KEY = 'local-scoped-read-only-key'; process.env.PDUFA_API_BASE_URL = 'https://production.example';
    delete process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL;
    const url = 'http://localhost/api/predictions/medical-installation';
    let calls = 0;
    global.fetch = async () => {calls++; throw Error('must not fetch');};
    assert.equal((await GET(new NextRequest(url))).status, 401);
    const headers = {cookie: auth.COOKIE_NAME + '=' + auth.makeSession()};
    assert.equal((await GET(new NextRequest(url, {headers}))).status, 503); assert.equal(calls, 0);
    process.env.PDUFA_MEDICAL_REVIEW_API_BASE_URL = 'https://isolated.example/';
    global.fetch = async (target, init) => {
      assert.equal(target, 'https://isolated.example/api/internal/installation-monitor');
      assert.equal(init.headers['x-pdufa-internal-key'], 'local-scoped-read-only-key');
      assert.equal(init.redirect, 'error'); assert.equal(init.cache, 'no-store');
      return Response.json(observed());
    };
    const success = await GET(new NextRequest(url, {headers}));
    assert.equal(success.status, 200); assert.equal(success.headers.get('cache-control'), 'private, no-store');
    assert.equal((await success.json()).installation.counts.recordedCurrentPhaseGrades, 0);
    global.fetch = async () => {const invalid = observed(); invalid.medicalInstallation.certainty = 'VALIDATED'; return Response.json(invalid);};
    assert.equal((await GET(new NextRequest(url, {headers}))).status, 503);
    global.fetch = async () => Response.json(unknown());
    assert.equal((await (await GET(new NextRequest(url, {headers}))).json()).installation.counts, null);
  } finally {
    global.fetch = fetchBefore;
    for (const [key, value] of Object.entries(saved)) {if (value === undefined) delete process.env[key]; else process.env[key] = value;}
  }
});
