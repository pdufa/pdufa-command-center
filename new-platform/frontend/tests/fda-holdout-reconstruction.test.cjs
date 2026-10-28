const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (m, file) => m._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true}
}).outputText, file);
const {auditHoldoutReconstruction, holdoutSourceUrl} = require('../lib/fda-holdout-reconstruction.ts');
const snapshot = require('../lib/fda-holdout-reconstruction-snapshot.json');
const React = require('react');
const {renderToStaticMarkup} = require('react-dom/server');
const Panel = require('../app/installation-audit/HistoricalHoldoutReconstruction.tsx').default;
const copy = () => structuredClone(snapshot);

test('real dated reconstruction preserves six exact cases and all abstention boundaries', () => {
  assert.equal(auditHoldoutReconstruction(snapshot), snapshot);
  assert.equal(snapshot.caseReports.length, 6);
  assert.equal(snapshot.validatedCases, 0);
  for (const c of snapshot.caseReports) {
    assert.equal(c.science_worklist.length, 40);
    assert.equal(c.depth_worklist.length, 20);
    assert.equal(c.outcome.pass_probability, null);
    assert.equal(c.independently_certified_assessments, 0);
  }
});

test('identity, dates, unsupported probabilities and self-certification fail closed', () => {
  for (const mutate of [
    r => r.researchOnly = false,
    r => r.validatedCases = 1,
    r => r.tradingAuthorized = true,
    r => r.caseReports[0].application_id = 'NDA218607',
    r => r.caseReports[0].action_document.source_bytes_retained = true,
    r => r.caseReports[0].event_key = 'UNRECOGNIZED|2025-04-01',
    r => r.caseReports[1] = r.caseReports[0],
    r => r.asOf = '2025-02-30',
    r => r.caseReports[0].reconstruction_cutoff = '2025-04-01',
    r => r.caseReports[0].original_prediction_cutoff = '2025-03-31',
    r => r.caseReports[0].frozen_prediction_source_count = 1,
    r => r.caseReports[0].independently_certified_assessments = 1,
    r => r.caseReports[0].eligible_for_validation = true,
    r => r.caseReports[0].outcome.pass_probability = 0.8,
    r => r.caseReports[0].main.status = 'PASS',
    r => r.caseReports[0].depth_worklist[0].status = 'CERTIFIED',
    r => r.caseReports[0].science_worklist[0].scientific_score = 80,
    r => r.caseReports[0].related_precedents[0].eligible_for_training = true,
    r => r.caseReports[0].scientific_dossier.summary.independently_completed_assessments = 40,
    r => r.caseReports[0].scientific_dossier.event_key = 'OTHER',
    r => r.caseReports[0].scientific_dossier.layers[0].questions[0].question_id = 'S40',
    r => r.caseReports[0].scientific_dossier.depth_framework.independently_reviewed_levels = [1],
  ]) {
    const bad = copy(); mutate(bad);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
});

test('late, outcome-only or unindexed observations cannot appear as question evidence', () => {
  const outcome = snapshot.caseReports[0].source_classification.find(s => s.source_role === 'OUTCOME_ONLY');
  for (const mutate of [
    r => r.caseReports[0].science_worklist[0].source_ids = [outcome.source_id],
    r => r.caseReports[0].source_classification.find(s => s.source_id === outcome.source_id).classification = 'PREDECISION_RESEARCH_CANDIDATE',
    r => r.caseReports[0].source_classification[0].available_on = '2025-04-02',
    r => r.caseReports[0].source_classification[0].availability_source_url = null,
    r => r.caseReports[0].source_classification[0].availability_source_url = 'https://www.sec.gov/Archives/edgar/data/1000694/000100069425000005/0001000694-25-000005-index.htm',
    r => r.caseReports[0].source_classification[0].availability_basis = 'UNKNOWN',
    r => r.caseReports[0].predecision_research_candidate_count += 1,
    r => r.caseReports[0].source_classification[0].independently_reviewed = true,
  ]) {
    const bad = copy(); mutate(bad);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
});

test('source links require official hosts and reject executable, credential and port variants', () => {
  for (const url of ['javascript:alert(1)', 'https://www.sec.gov.evil.example/doc', 'https://user:secret@www.sec.gov/doc',
    'https://www.sec.gov:443/doc', 'https://www.sec.gov:444/doc', 'https://www.sec.gov/doc#fragment', 'https://www.sec.gov/']) {
    assert.equal(holdoutSourceUrl(url), undefined);
    const bad = copy(); bad.caseReports[0].source_classification[0].source_url = url;
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
  assert.equal(holdoutSourceUrl('https://www.fda.gov/media/186545/download?stream=top'), 'https://www.fda.gov/media/186545/download?stream=top');
});

test('MAIN panel renders source-backed details and withholds all counts on invalid payloads', () => {
  const html = renderToStaticMarkup(React.createElement(Panel));
  assert.match(html, /Six priority cases/);
  assert.match(html, /OUTCOME and MAIN abstain/);
  assert.match(html, /Independently certified assessments: 0\/40/);
  assert.match(html, /not independently certified/);
  assert.match(html, /Original prediction cutoff/);
  assert.match(html, /PARTIAL TEXT FIRST PAGE VISUAL REVIEW REQUIRED/);
  assert.match(html, /CORRECTED DOCUMENT ONLY ORIGINAL NOT RETRIEVED/);
  assert.match(html, /Required documents: protocol and efficacy results/);
  assert.match(html, /No semantic definitions or completion is inferred/);
  for (const ticker of ['NVAX', 'UNCY', 'TNXP', 'BCRX', 'CORT', 'VNDA']) assert.match(html, new RegExp(ticker));
  const bad = copy(); bad.validatedCases = 6;
  const rejected = renderToStaticMarkup(React.createElement(Panel, {value:bad}));
  assert.match(rejected, /Evidence counts and predictions withheld/);
  assert.doesNotMatch(rejected, /Six priority cases|NVAX|0\/40/);
});
