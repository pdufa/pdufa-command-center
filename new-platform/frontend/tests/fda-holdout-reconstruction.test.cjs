const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
for (const ext of ['.ts', '.tsx']) require.extensions[ext] = (m, file) => m._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {
  compilerOptions: {module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true}
}).outputText, file);
const {auditHoldoutReconstruction, holdoutSourceUrl, scientificIssueSourceUrl} = require('../lib/fda-holdout-reconstruction.ts');
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
  assert.match(html, /fifty-level research protocol preserves the twenty-level foundation/);
  assert.match(html, /Fifty-level investigation protocol · 0\/50 independently completed/);
  assert.match(html, /Preserved twenty-level foundation · 0\/20 independently completed/);
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


test('fifty-level extension preserves the foundation and cannot claim completed investigation', () => {
  const dossier = snapshot.caseReports[0].scientific_dossier;
  assert.equal(dossier.extended_investigation_framework.levels.length, 50);
  assert.deepEqual(dossier.extended_investigation_framework.levels.slice(0, 20), dossier.depth_framework.levels);
  for (const mutate of [
    f => f.levels.pop(),
    f => f.levels[49].level_id = 'D20',
    f => f.levels[0].title = 'Replaced legacy definition',
    f => f.independently_completed_level_count = 50,
    f => f.legacy_backend_review_boundary_changed = true,
    f => f.levels[49].independently_completed = true,
    f => f.levels[49].source_lead_ids = ['NONEXISTENT'],
  ]) {
    const bad = copy(); mutate(bad.caseReports[0].scientific_dossier.extended_investigation_framework);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
});

test('three-class research contract preserves extension semantics and withholds unsupported grades/probabilities', () => {
  for (const c of snapshot.caseReports) {
    assert.deepEqual(c.decision_contract.target_classes, ['PASS', 'CRL', 'EXTENSION']);
    assert.equal(c.decision_contract.predicted_decision, 'ABSTAIN');
    assert.deepEqual(c.decision_contract.probabilities, {PASS:null, CRL:null, EXTENSION:null});
  }
  for (const mutate of [
    c => c.predicted_decision = 'PASS',
    c => c.probabilities = {PASS:0.8, CRL:0.1, EXTENSION:0.1},
    c => c.probabilities.EXTENSION = 0,
    c => c.target_classes = ['PASS', 'FAIL'],
    c => c.extension_is_binary_nonapproval = true,
    c => c.science_readiness_grade = 'READY',
    c => c.prediction_confidence_grade = 'HIGH',
    c => c.eligible_for_validated_accuracy = true,
    c => c.trading_authorized = true,
    c => c.blockers = [],
  ]) {
    const bad = copy(); mutate(bad.caseReports[0].decision_contract);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
});

test('TNXP sponsor arithmetic cannot establish protocol compliance or a frozen historical feature', () => {
  const tnxp = snapshot.caseReports.find(c => c.event_key.startsWith('TNXP|'));
  const issue = tnxp.scientific_dossier.scientific_issues[0];
  assert.equal(issue.randomized_population.total, 457);
  assert.equal(issue.reported_efficacy_population.total, 456);
  assert.equal(issue.reported_safety_population.total, 457);
  assert.equal(issue.protocol_compliance_status, 'NOT_ESTABLISHED');
  for (const mutate of [
    i => i.protocol_compliance_status = 'COMPLIANT',
    i => i.reported_efficacy_population.total = 457,
    i => i.independently_adjudicated = true,
    i => i.eligible_for_predecision_features = true,
    i => i.approval_probability = 0.9,
    i => i.effect_on_proposed_fda_decision = 'PASS',
    i => i.sources[0].public_availability_verified = true,
    i => i.sources[0].url = 'https://www.tonixpharma.com.evil.example/doc',
    i => i.original_prediction_cutoff = '2025-08-14',
  ]) {
    const bad = copy(); mutate(bad.caseReports.find(c => c.event_key.startsWith('TNXP|')).scientific_dossier.scientific_issues[0]);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
  for (const url of ['javascript:alert(1)', 'https://cdn.clinicaltrials.gov.evil.example/doc', 'https://user:secret@doi.org/doc',
    'https://doi.org:443/doc', 'https://doi.org/doc#fragment']) assert.equal(scientificIssueSourceUrl(url), undefined);
});

test('both existing research views show fifty tasks, three withheld outcomes and unresolved TNXP compliance', () => {
  const FdaPage = require('../app/fda-research-status/page.tsx').default;
  for (const View of [Panel, FdaPage]) {
    const html = renderToStaticMarkup(React.createElement(View));
    assert.match(html, /Fifty-level investigation protocol · 0\/50 independently completed/);
    assert.match(html, /50 tasks in total, not 70/);
    assert.match(html, /PASS \/ CRL \/ EXTENSION probabilities: withheld/);
    assert.match(html, /Protocol compliance: <strong>NOT ESTABLISHED/);
    assert.match(html, /457 randomized versus 456 in reported efficacy analysis/);
    assert.match(html, /all-randomized analysis/);
    assert.match(html, /Document date:/);
    assert.match(html, /Original public availability:/);
    assert.match(html, /Original historical prediction cutoff: unverified/);
    assert.match(html, /https:\/\/cdn.clinicaltrials.gov\/large-docs\/49\/NCT05273749\/SAP_003.pdf/);
  }
});

test('both research views preserve TNXP primary failure, sensitivity roles and uncertain populations', () => {
  const matrix = snapshot.caseReports.find(c => c.event_key.startsWith('TNXP|')).scientific_dossier.tnxp_trial_comparison;
  assert.deepEqual(matrix.trials.map(t => t.name), ['RELIEF', 'RALLY', 'RESILIENT']);
  assert.equal(matrix.trials[1].primary_analysis.p_value, '0.115');
  assert.equal(matrix.trials[1].primary_analysis.source_reported_outcome, 'FAILED');
  assert.equal(matrix.trials[1].sensitivity_analyses[0].p_value, '0.014');
  assert.equal(matrix.trials[0].populations.randomized_total, null);
  const FdaPage = require('../app/fda-research-status/page.tsx').default;
  for (const View of [Panel, FdaPage]) {
    const html = renderToStaticMarkup(React.createElement(View));
    for (const pattern of [/TNXP RELIEF \/ RALLY \/ RESILIENT/, /RALLY remains a failed primary endpoint \(p=0.115\)/,
      /favorable sensitivity analysis \(p=0.014\) does not replace/, /No p values, treatment effects or safety rates are pooled/,
      /Adverse-event withdrawal does not by itself establish drug causality/, /Not recorded in this matrix; agreement or disagreement is unknown/]) assert.match(html, pattern);
  }
});

test('TNXP matrix rejects altered clinical roles, invented populations and forecast/certification claims', () => {
  for (const mutate of [
    m => m.application_id = 'NDA000001', m => m.original_prediction_cutoff = '2025-08-14',
    m => m.eligible_for_predecision_features = true, m => m.eligible_for_validated_accuracy = true,
    m => m.independently_completed_assessments = 3, m => m.sources[0].source_url = 'javascript:alert(1)',
    m => m.sources[0].public_availability_verified = true, m => m.sources[0].source_bytes_retained = true,
    m => m.sources[0].document_date = '2025-08-16', m => m.trials[1].primary_analysis.p_value = '0.014',
    m => m.trials[1].primary_analysis.source_reported_outcome = 'POSITIVE',
    m => m.trials[1].sensitivity_analyses[0].analysis_role = 'PRESPECIFIED_PRIMARY',
    m => m.trials[0].populations.randomized_total = 503, m => m.trials[2].populations.efficacy_total = 457,
    m => m.trials[1].safety.causality_status = 'DRUG_CAUSALITY_ESTABLISHED',
    m => m.trials[1].safety.source_reported_events[0].independently_adjudicated = true,
    m => m.comparison_summary.resilient_exclusion_compliance_status = 'COMPLIANT',
    m => m.comparison_summary.pooled_p_value = '0.01', m => m.comparison_summary.prediction_accuracy = 1,
    m => m.comparison_summary.probabilities.PASS = 0.9,
    m => m.comparison_summary.within_program_comparison_is_independent_fda_cohort = true,
  ]) {
    const bad = copy(); mutate(bad.caseReports.find(c => c.event_key.startsWith('TNXP|')).scientific_dossier.tnxp_trial_comparison);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
  const bad = copy();
  bad.caseReports[0].scientific_dossier.tnxp_trial_comparison = bad.caseReports.find(c => c.event_key.startsWith('TNXP|')).scientific_dossier.tnxp_trial_comparison;
  assert.throws(() => auditHoldoutReconstruction(bad));
});

test('FDA label denominator corroboration stays outcome-only and cannot establish SAP compliance', () => {
  const issue = snapshot.caseReports.find(c => c.event_key.startsWith('TNXP|')).scientific_dossier.scientific_issues[0];
  assert.equal(issue.postdecision_context.source_role, 'OUTCOME_ONLY');
  assert.equal(issue.postdecision_context.reported_efficacy_population.total, 456);
  const FdaPage = require('../app/fda-research-status/page.tsx').default;
  for (const View of [Panel, FdaPage]) {
    const html = renderToStaticMarkup(React.createElement(View));
    for (const pattern of [/FDA postdecision label corroboration · excluded from prediction inputs/,
      /225 placebo \+ 231 active = 456/, /corroborates the reported denominator, not authority for the exclusion/,
      /219428s000lbl.pdf/, /postdecision evidence cannot complete historical predecision features or establish SAP compliance/]) assert.match(html, pattern);
  }
  for (const mutate of [
    c => c.source_role = 'PREDECISION_RESEARCH', c => c.eligible_for_predecision_features = true,
    c => c.protocol_exclusion_authority_established = true, c => c.public_availability_verified = true,
    c => c.reported_efficacy_population.total = 457, c => c.source_url = 'https://www.accessdata.fda.gov.evil.example/label.pdf',
    c => c.application_index_url = 'javascript:alert(1)',
  ]) {
    const bad = copy(); mutate(bad.caseReports.find(c => c.event_key.startsWith('TNXP|')).scientific_dossier.scientific_issues[0].postdecision_context);
    assert.throws(() => auditHoldoutReconstruction(bad));
  }
});
