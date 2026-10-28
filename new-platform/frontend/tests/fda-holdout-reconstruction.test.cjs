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
  assert.match(html, /twenty-level research protocol defines the required analysis/);
  assert.match(html, /Twenty-level investigation protocol · 0\/20 independently completed/);
  assert.match(html, /Completion artifacts required/);
  for (const depth of snapshot.caseReports[0].scientific_dossier.depth_framework.levels) {
    assert.ok(html.includes(depth.title));
  }
  for (const ticker of ['NVAX', 'UNCY', 'TNXP', 'BCRX', 'CORT', 'VNDA']) assert.match(html, new RegExp(ticker));
  const bad = copy(); bad.validatedCases = 6;
  const rejected = renderToStaticMarkup(React.createElement(Panel, {value:bad}));
  assert.match(rejected, /Evidence counts and predictions withheld/);
  assert.doesNotMatch(rejected, /Six priority cases|NVAX|0\/40/);
});


test('twenty-level research protocol cannot self-certify completed investigation or predictive value', () => {
  const framework = snapshot.caseReports[0].scientific_dossier.depth_framework;
  assert.equal(framework.catalog_version, 'science-investigation-depth-catalog-v1');
  assert.equal(framework.levels.length, 20);
  assert.equal(framework.predictive_value_validated, false);
  assert.equal(framework.completion_policy.automatic_completion_enabled, false);
  assert.equal(framework.completion_policy.source_leads_complete_levels, false);
  for (const [index, level] of framework.levels.entries()) {
    assert.equal(level.depth_level, index + 1);
    assert.ok(level.title && level.objective);
    assert.ok(level.requirements.length && level.completion_artifacts.length);
    assert.equal(level.independently_completed, false);
    assert.equal(level.ready_for_independent_certification, false);
    assert.deepEqual(level.independently_reviewed_question_ids, []);
  }
  const outcome = snapshot.caseReports[0].source_classification.find(source => source.source_role === 'OUTCOME_ONLY');
  for (const mutate of [
    f => f.catalog_version = 'UNREVIEWED_VERSION',
    f => f.predictive_value_validated = true,
    f => f.completion_policy.automatic_completion_enabled = true,
    f => f.completion_policy.source_leads_complete_levels = true,
    f => f.completion_policy.missing_evidence_is_unknown = false,
    f => f.levels.pop(),
    f => f.levels[0].title = '',
    f => f.levels[0].objective = '',
    f => f.levels[0].requirements = [],
    f => f.levels[0].completion_artifacts = [],
    f => f.levels[0].level_id = 'D20',
    f => f.levels[0].status = 'CERTIFIED',
    f => f.levels[0].independently_completed = true,
    f => f.levels[0].ready_for_independent_certification = true,
    f => f.levels[0].independently_reviewed_question_ids = ['S01'],
    f => f.levels[0].question_ids = ['S99'],
    f => f.levels[0].source_lead_ids = [outcome.source_id],
    f => f.levels[0].question_ids_with_source_leads = ['S99'],
    f => f.levels[0].prerequisite_levels = [20],
    f => f.levels[0].blocking_prerequisite_levels = [20],
  ]) {
    const bad = copy(); mutate(bad.caseReports[0].scientific_dossier.depth_framework);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
});
