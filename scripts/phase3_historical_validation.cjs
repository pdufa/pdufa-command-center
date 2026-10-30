'use strict';

// Read-only validation of persisted prospective predictions and verified outcomes.
// Normal login only; credentials and source contents are never retained.
const fs = require('node:fs');
const path = require('node:path');
const BASE = 'https://pdufa-new-dashboard.vercel.app';
const result = { status: 'INCOMPLETE', validation_status: 'NOT_VALIDATED', started_at: new Date().toISOString(), checks: {}, counts: {}, accuracy_by_decision: {}, calibration_metrics: null, failure_code: null };
let phase = 'preflight';
function check(value, code) {
  result.checks[code] = Boolean(value);
  if (!value) { const error = new Error(code); error.checkId = code; throw error; }
}
function record() {
  result.finished_at = new Date().toISOString();
  const safe = { status: result.status === 'PASS' ? 'PASS' : 'INCOMPLETE', validation_status: ['NOT_VALIDATED', 'REVIEW_REQUIRED', 'VALIDATED'].includes(result.validation_status) ? result.validation_status : 'NOT_VALIDATED',
    started_at: result.started_at, finished_at: result.finished_at, checks: {}, counts: {}, accuracy_by_decision: {}, calibration_metrics: null, failure_code: null };
  for (const [key, value] of Object.entries(result.checks)) if (/^[a-z0-9_]{1,120}$/.test(key) && typeof value === 'boolean') safe.checks[key] = value;
  for (const [key, value] of Object.entries(result.counts)) if (/^[a-z0-9_]{1,120}$/.test(key) && Number.isSafeInteger(value) && value >= 0) safe.counts[key] = value;
  for (const decision of ['PASS', 'CRL', 'EXTENSION']) {
    const row = result.accuracy_by_decision[decision];
    if (row && Number.isSafeInteger(row.evaluated) && Number.isSafeInteger(row.correct)) safe.accuracy_by_decision[decision] = {
      evaluated: row.evaluated, correct: row.correct, accuracy: typeof row.accuracy === 'number' && row.accuracy >= 0 && row.accuracy <= 1 ? row.accuracy : null };
  }
  if (typeof result.failure_code === 'string' && /^[A-Za-z0-9_]{1,160}$/.test(result.failure_code)) safe.failure_code = result.failure_code;
  const destination = process.env.PHASE3_VALIDATION_RESULT_PATH || path.join(process.cwd(), 'phase3-historical-validation-result.json');
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.writeFileSync(destination, JSON.stringify(safe, null, 2) + '\n', { mode: 0o600 });
  console.log('PDUFA_PHASE3_HISTORICAL_VALIDATION ' + JSON.stringify(safe));
  if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    'Historical validation workflow: **' + safe.status + '**\n\nScientific prediction validation: **' + safe.validation_status + '**\n\n' +
    'Workflow execution success does not establish validated prediction accuracy or trading authorization.\n');
}
async function main() {
  const password = process.env.DASHBOARD_PASSWORD;
  delete process.env.DASHBOARD_PASSWORD;
  if (!password) { result.failure_code = 'MISSING_GITHUB_ACTIONS_SECRET_DASHBOARD_PASSWORD'; process.exitCode = 1; record(); return; }
  let browser;
  try {
    const { chromium } = require('playwright');
    phase = 'launch';
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext();
    const anonymous = await context.request.get(BASE + '/api/phase3-trials/validation', { timeout: 30000, maxRedirects: 0 });
    check(anonymous.status() === 401, 'anonymous_validation_rejected');
    const page = await context.newPage();
    let runtimeErrors = 0;
    page.on('pageerror', () => { runtimeErrors += 1; });
    phase = 'normal_login';
    await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('#password').fill(password);
    const login = page.waitForResponse(response => new URL(response.url()).pathname === '/api/auth' && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    check((await login).status() === 200, 'normal_application_authentication');
    phase = 'read_only_persisted_validation';
    const response = await context.request.get(BASE + '/api/phase3-trials/validation', { timeout: 30000 });
    check(response.status() === 200, 'authenticated_persisted_validation_200');
    const data = await response.json();
    check(['NOT_VALIDATED', 'REVIEW_REQUIRED', 'VALIDATED'].includes(data.status), 'validation_status_reported');
    result.validation_status = data.status;
    for (const key of ['total_applications', 'eligible_applications', 'number_evaluated', 'number_abstained', 'number_with_known_outcomes', 'prediction_records', 'temporally_eligible_predictions', 'excluded_for_lookahead_or_missing_outcome', 'unresolved_outcomes']) {
      check(Number.isSafeInteger(data[key]) && data[key] >= 0, 'actual_' + key + '_reported');
      result.counts[key] = data[key];
    }
    check(data.number_evaluated <= data.eligible_applications && data.temporally_eligible_predictions <= data.prediction_records &&
      data.excluded_for_lookahead_or_missing_outcome + data.temporally_eligible_predictions === data.prediction_records, 'time_aware_eligibility_counts_consistent');
    check(data.number_with_known_outcomes <= data.total_applications && data.unresolved_outcomes <= data.total_applications, 'verified_outcome_counts_consistent');
    check(data.data_completeness && Number.isSafeInteger(data.data_completeness.applications) && Number.isSafeInteger(data.data_completeness.verified_outcomes), 'actual_data_completeness_reported');
    if (data.number_evaluated === 0) check(data.status === 'NOT_VALIDATED', 'no_predictions_means_no_accuracy_claim');
    for (const decision of ['PASS', 'CRL', 'EXTENSION']) {
      const row = data.accuracy_by_decision?.[decision];
      check(row && Number.isSafeInteger(row.evaluated) && Number.isSafeInteger(row.correct) && row.correct >= 0 && row.correct <= row.evaluated, 'actual_' + decision.toLowerCase() + '_category_counts');
      if (data.number_evaluated < 30 || row.evaluated < 10) check(row.accuracy === null, decision.toLowerCase() + '_insufficient_sample_has_no_accuracy');
      else check(typeof row.accuracy === 'number' && row.accuracy >= 0 && row.accuracy <= 1, decision.toLowerCase() + '_accuracy_is_bounded_observation');
      result.accuracy_by_decision[decision] = { evaluated: row.evaluated, correct: row.correct, accuracy: row.accuracy };
    }
    check(data.calibration_metrics === null, 'uncalibrated_model_does_not_invent_calibration');
    check(Number.isFinite(Date.parse(data.verified_at)) && typeof data.limitation === 'string' && data.limitation.length > 0, 'verification_timestamp_and_limitations_present');
    check(runtimeErrors === 0, 'no_authentication_runtime_errors');
    result.status = 'PASS';
  } catch (failure) {
    result.failure_code = typeof failure?.checkId === 'string' ? failure.checkId : 'VALIDATION_CHECK_FAILED_AT_' + phase.toUpperCase();
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close().catch(() => {});
    record();
  }
}
void main();
