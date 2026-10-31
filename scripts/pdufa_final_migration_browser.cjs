'use strict';

// Authorized production verification. Normal dashboard form login only.
// Read-only browser/API requests; no scanner dispatch, restriction writes,
// new processing runs, session exports, traces, HARs or source payload artifacts.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const BASE = 'https://pdufa-new-dashboard.vercel.app';
const NCT = 'NCT00116805';
const ORIGINAL = 'c7c1d08244597084152238853c3d8357b892218aee1c48db97e83f63216c54de';
const output = process.env.MIGRATION_RESULT_PATH || path.join(process.cwd(), 'final-migration-result.json');
const result = {
  technical_completion: 'INCOMPLETE', verification_execution: 'INCOMPLETE',
  started_at: new Date().toISOString(), commit_sha: process.env.GITHUB_SHA || null,
  workflow_run_id: process.env.GITHUB_RUN_ID || null, nct_id: NCT,
  checks: {}, counts: {}, gates: [], hashes: {}, artifacts: [],
};
const failures = [];
const runtime = { pageErrors: 0, apiServerErrors: 0, streamlitRequests: 0, blockedMutations: 0 };
let saved = null;
let pool = null;
let reports = null;
let control = null;

function assert(value, code) {
  result.checks[code] = Boolean(value);
  if (!value) { const error = new Error(code); error.code = code; throw error; }
}
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}
const hash = value => crypto.createHash('sha256').update(canonical(value)).digest('hex');
const integer = value => Number.isSafeInteger(value) && value >= 0;
async function gate(id, code, work) {
  const row = { id, code, status: 'NOT_VERIFIED', checked_at: new Date().toISOString(), checks: [] };
  const previous = new Set(Object.keys(result.checks));
  try {
    const outcome = await work();
    row.status = outcome && outcome.blocked ? 'BLOCKED' : 'VERIFIED';
    if (outcome && outcome.blocker) row.blocker = outcome.blocker;
  } catch (error) {
    row.status = 'FAILED';
    row.failure_code = typeof error.code === 'string' && /^[a-z0-9_]+$/.test(error.code) ? error.code : code + '_execution_failed';
    failures.push(row.failure_code);
  }
  row.checks = Object.keys(result.checks).filter(key => !previous.has(key));
  result.gates.push(row);
}
async function json(context, pathname, code, expected = 200) {
  // A research-source freshness 503 remains a failure if persistent. Retry
  // the protected, read-only workspace twice after a cold-start/deploy,
  // without ever retrying writes, authentication failures or corrupt data.
  const scopeRead = expected === 200 && pathname.startsWith('/api/scope-funnel?');
  let response;
  for (let attempt = 0; attempt < (scopeRead ? 3 : 1); attempt++) {
    response = await context.request.get(BASE + pathname, { timeout: 65000, maxRedirects: 0 });
    if (!(scopeRead && response.status() === 503 && attempt < 2)) break;
    console.log('PDUFA_SCOPE_RETRY ' + JSON.stringify({code, attempt:attempt+1, httpStatus:503}));
    await new Promise(resolve => setTimeout(resolve, 4000));
  }
  if (response.status() !== expected) {
    // Never log clinical data or arbitrary server errors. Only permit finite
    // diagnostic enums from the authenticated, protected scope endpoint.
    let reasonCode = 'NOT_AVAILABLE';
    if (pathname.startsWith('/api/scope-funnel') && response.status() === 503) {
      try {
        const body = await response.json();
        if (typeof body.reasonCode === 'string' && /^[A-Z_]{4,64}$/.test(body.reasonCode))
          reasonCode = body.reasonCode;
      } catch {}
    }
    console.error('PDUFA_ACCEPTANCE_HTTP_MISMATCH ' +
      JSON.stringify({check:code, expectedStatus:expected, actualStatus:response.status(), reasonCode}));
  }
  assert(response.status() === expected, code + '_http_' + expected);
  if (expected !== 200) return null;
  assert((response.headers()['content-type'] || '').includes('application/json'), code + '_json');
  return response.json();
}
async function goto(page, pathname, code) {
  const response = await page.goto(BASE + pathname, { waitUntil: 'domcontentloaded', timeout: 65000 });
  assert(response && response.status() === 200, code + '_page_http_200');
  await page.locator('main').first().waitFor({ state: 'visible', timeout: 30000 });
}
async function login(page, password, prefix) {
  await goto(page, '/', prefix);
  await page.locator('#password').waitFor({ state: 'visible', timeout: 30000 });
  await page.locator('#password').fill(password);
  const completed = page.waitForResponse(r => new URL(r.url()).pathname === '/api/auth' && r.request().method() === 'POST', { timeout: 40000 });
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  assert((await completed).status() === 200, prefix + '_normal_password_login');
  await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor({ state: 'visible', timeout: 45000 });
  assert(await page.locator('#password').count() === 0, prefix + '_login_form_removed');
}
function watch(page) {
  page.on('pageerror', error => {
    runtime.pageErrors += 1;
    // Only finite diagnostic categories and the current same-site page path:
    // never leak exception text, URLs with query strings, cookies or source rows.
    const name = error?.name === 'TypeError' ? 'TypeError'
      : error?.name === 'ReferenceError' ? 'ReferenceError'
      : error?.name === 'SyntaxError' ? 'SyntaxError' : 'Other';
    const message = typeof error?.message === 'string' ? error.message : '';
    const category = /hydrat/i.test(message) ? 'HYDRATION'
      : /chunk|loading css|dynamically imported module/i.test(message) ? 'CHUNK_LOADING'
      : /network|fetch|load failed/i.test(message) ? 'NETWORK'
      : /undefined|null|not a function/i.test(message) ? 'APPLICATION_STATE' : 'UNCLASSIFIED';
    const pathname = (() => { try { const u = new URL(page.url()); return u.origin === BASE ? u.pathname : 'OTHER_ORIGIN'; } catch { return 'UNKNOWN'; } })();
    console.error('PDUFA_BROWSER_PAGEERROR ' + JSON.stringify({name, category, pathname}));
  });
  page.on('request', request => {
    try { if (/(^|\.)(?:streamlit\.app|streamlit\.io)$/.test(new URL(request.url()).hostname)) runtime.streamlitRequests += 1; } catch {}
  });
  page.on('response', response => {
    try { const u = new URL(response.url()); if (u.origin === BASE && u.pathname.startsWith('/api/') && response.status() >= 500) runtime.apiServerErrors += 1; } catch {}
  });
}
async function safeContext(browser, options = {}) {
  const context = await browser.newContext(options);
  await context.route('**/*', route => {
    const request = route.request();
    const method = request.method();
    const u = new URL(request.url());
    if (!['GET', 'HEAD', 'OPTIONS'].includes(method) && !(u.origin === BASE && u.pathname === '/api/auth' && method === 'POST')) {
      runtime.blockedMutations += 1;
      return route.abort('blockedbyclient');
    }
    return route.continue();
  });
  return context;
}
async function checkNavigation(page, prefix) {
  const nav = page.getByRole('navigation', { name: 'Site navigation', exact: true });
  assert(await nav.isVisible(), prefix + '_native_navigation_visible');
  const links = await nav.getByRole('link').evaluateAll(items => items.map(item => ({ text: item.textContent.trim(), href: item.getAttribute('href') })));
  const required = ['/', '/pool', '/pipeline', '/patient-population', '/goal', '/scans', '/results', '/restrictions', '/predictions'];
  assert(required.every(href => links.some(item => item.href === href)), prefix + '_all_native_routes_linked');
  assert(links.every(item => !/GEM|WT|STREAMLIT/i.test(item.text) && !/streamlit\.(app|io)/i.test(item.href)), prefix + '_retired_lists_absent_from_active_navigation');
}
async function waitRows(page, code) {
  await page.waitForFunction(() => document.querySelector('tbody tr') !== null, null, { timeout: 65000 });
  assert(await page.locator('tbody tr').count() > 0, code + '_rows_render');
  // Next.js' route announcer uses role=alert outside <main>; only inspect actual application errors.
  const alerts = page.locator('main [role="alert"]');
  if (await alerts.count() > 0) {
    const contexts = await alerts.evaluateAll(nodes => nodes.map(n => n.closest('[aria-label]')?.getAttribute('aria-label') || n.parentElement?.tagName || 'unknown'));
    console.log('PDUFA_ACCEPTANCE_ALERT_CONTEXT ' + JSON.stringify({code, count:contexts.length, contexts:contexts.slice(0,4)}));
  }
  assert(await alerts.count() === 0, code + '_no_visible_alert');
}
async function testPool(context, page) {
  pool = await json(context, '/api/scope-funnel?view=pool&limit=50&offset=0', 'pool');
  assert(pool.view === 'pool' && integer(pool.total) && pool.total > 0 && Array.isArray(pool.rows) && pool.rows.length > 0 && pool.rows.length <= 50, 'pool_actual_inventory_response');
  assert(pool.overview && pool.overview.poolRecords === pool.total, 'pool_count_matches_overview');
  assert(new Set(pool.rows.map(row => row.id)).size === pool.rows.length, 'pool_page_identity_unique');
  assert(pool.rows.every(row => typeof row.id === 'string' && row.id.length && typeof row.ticker === 'string'), 'pool_source_identities_present');
  result.counts.pool_records = pool.total;
  result.counts.pool_first_page = pool.rows.length;
  result.hashes.pool_first_page = hash(pool.rows);
  if (pool.nextOffset !== null) {
    const second = await json(context, '/api/scope-funnel?view=pool&limit=50&offset=' + pool.nextOffset, 'pool_second_page');
    assert(second.offset === pool.nextOffset && second.total === pool.total && Array.isArray(second.rows) && second.rows.length > 0, 'pool_server_pagination');
    assert(second.rows.every(row => !pool.rows.some(first => first.id === row.id)), 'pool_page_boundaries_no_duplicates');
  }
  const first = pool.rows[0];
  const query = first.ticker || first.nctId || first.id;
  const searched = await json(context, '/api/scope-funnel?view=pool&limit=50&offset=0&query=' + encodeURIComponent(query), 'pool_search');
  assert(searched.total > 0 && searched.rows.some(row => row.id === first.id), 'pool_server_search_exact_record');
  await goto(page, '/pool', 'pool_ui');
  await waitRows(page, 'pool_ui');
  const input = page.getByRole('searchbox', { name: 'Search ticker, trial, company, drug or indication', exact: true });
  await input.fill(query);
  const response = page.waitForResponse(r => new URL(r.url()).pathname === '/api/scope-funnel' && new URL(r.url()).searchParams.get('query') === query, { timeout: 65000 });
  await page.getByRole('button', { name: 'Search', exact: true }).click();
  assert((await response).status() === 200, 'pool_search_ui_reaches_real_api');
  const resetResponse = page.waitForResponse(r => {
    const u = new URL(r.url());
    return u.pathname === '/api/scope-funnel' && u.searchParams.get('view') === 'pool'
      && !u.searchParams.has('query') && u.searchParams.get('offset') === '0';
  }, { timeout: 65000 });
  await page.getByRole('button', { name: 'Clear', exact: true }).click();
  assert((await resetResponse).status() === 200, 'pool_clear_search_fetches_first_unfiltered_page');
  await page.waitForFunction(total => {
    const main = document.querySelector('main');
    const states = main ? [...main.querySelectorAll('[role="status"]')] : [];
    return states.some(item => item.textContent.includes('Showing 1') && item.textContent.includes('of ' + total.toLocaleString()));
  }, pool.total, { timeout: 65000 });
  const next = page.getByRole('button', { name: 'Next', exact: true });
  if (pool.total > 50) {
    assert(await next.isEnabled(), 'pool_next_page_enabled');
    await next.click();
    await page.waitForFunction(() => [...document.querySelectorAll('[role="status"]')].some(item => /Showing 51/.test(item.textContent)), null, { timeout: 65000 });
    await page.getByRole('button', { name: 'Previous', exact: true }).click();
  }
  const scope = await json(context, '/api/archive-scope', 'pool_archive_scope');
  assert(scope.status === 'VERIFIED' && scope.scopeType === 'SAVED_EXACT_NCT_IDENTITY_PRESERVATION_NOT_FULL_UNIVERSE', 'pool_current_physical_nct_scope_verified_not_scientific_qualification');
  assert(integer(scope.originalScopeRecords) && integer(scope.archivePhysicalRecords) && integer(scope.unionDistinctTrials) && integer(scope.missingPoolTrials), 'pool_canonical_archive_scope_union_counts_present');
  assert(scope.originalScopeRecords >= 11623 && scope.archivePhysicalRecords === scope.originalScopeRecords
    && scope.unionDistinctTrials >= scope.originalScopeRecords && scope.missingPoolTrials === 0
    && scope.missingExpectedArchiveRecords === 0
    && scope.missingDatedManifestRecords === 0
    && scope.publishedOutsideArchive === 0, 'pool_full_preserved_current_archive_scope_represents_original_11623_ncts');
  assert(scope.currentScopeSha256 === scope.physicalArchiveSha256
    && scope.currentScopeSha256 === scope.publishedPoolSha256, 'pool_current_archived_and_published_id_sets_identical');
  result.counts.original_scope_ncts = scope.originalScopeRecords;
  result.counts.dated_manifest_ncts = scope.datedManifestRecords;
}
async function testPipeline(context, page) {
  const data = await json(context, '/api/scope-funnel?view=pipeline&limit=50&offset=0', 'pipeline');
  const review = await json(context, '/api/scope-funnel?view=readout-review&limit=50&offset=0', 'pipeline_review');
  assert(data.view === 'pipeline' && integer(data.total) && Array.isArray(data.rows) && data.overview, 'pipeline_real_queue_response');
  assert(data.rows.every(row => row.censusStatus === 'COMPLETED' && row.poolStatus === 'EXACT_MATCH' && row.postPhase3Evidence === 'REGISTRY_COMPLETED'), 'pipeline_requires_completed_exact_identity');
  assert(data.rows.every(row => row.capUsd >= 300000000 && row.capUsd <= 10000000000 && row.qualification === 'NEEDS_REVIEW'), 'pipeline_historical_cap_range_and_uncertainty');
  assert(data.qualifiedProgramCount === null && data.overview.qualifiedPrograms === null, 'pipeline_no_invented_qualified_count');
  assert(data.total === data.overview.matchedCompletedRecords && data.total + review.total === data.overview.historicalPhase3Records, 'pipeline_review_and_completed_counts_reconcile');
  result.counts.pipeline_research_queue = data.total;
  result.counts.pipeline_unresolved_queue = review.total;
  result.counts.historical_phase3_records = data.overview.historicalPhase3Records;
  await goto(page, '/pipeline', 'pipeline_ui');
  await page.getByRole('button', { name: 'Unmatched / verify final readout', exact: true }).waitFor();
  await page.getByRole('button', { name: 'Unmatched / verify final readout', exact: true }).click();
  await page.waitForFunction(() => document.querySelector('button[aria-pressed="true"]')?.textContent.includes('Unmatched'), null, { timeout: 30000 });
  await page.getByRole('button', { name: 'Completed & exact-linked (research queue)', exact: true }).click();
  const detail = page.locator('tbody details').first();
  if (await detail.count()) { await detail.locator('summary').click(); assert(await detail.getAttribute('open') !== null, 'pipeline_evidence_reasons_expand'); }
  return { blocked: true, blocker: 'current_listing_cap_final_readout_rights_qualification_not_established' };
}
async function testPopulation(page) {
  await goto(page, '/patient-population', 'population_ui');
  await waitRows(page, 'population');
  const rowCount = await page.locator('tbody tr').count();
  result.counts.population_visible_rows = rowCount;
  const firstTrial = await page.locator('tbody tr').first().innerText();
  const nct = firstTrial.match(/NCT\d{8}/)?.[0];
  assert(Boolean(nct), 'population_exact_nct_identity');
  const query = page.getByRole('searchbox', { name: 'Search ticker, company, NCT or loaded registry details', exact: true });
  await query.fill(nct);
  await page.waitForFunction(() => document.querySelectorAll('tbody tr').length === 1, null, { timeout: 30000 });
  assert((await page.locator('tbody').innerText()).includes(nct), 'population_search_preserves_exact_trial');
  await page.getByRole('button', { name: 'View ▾', exact: true }).first().click();
  assert(await page.getByRole('button', { name: 'Review exact NCT source', exact: true }).isVisible(), 'population_source_drilldown_available');
  assert(await page.locator('details').count() >= 1, 'population_investigation_sections_exist');
  await page.locator('details summary').first().click();
  assert(await page.locator('details').first().getAttribute('open') !== null, 'population_investigation_expands');
  await page.getByRole('button', { name: 'Clear all filters', exact: true }).click();
  return { blocked: true, blocker: 'population_estimates_and_current_pipeline_eligibility_not_independently_adjudicated' };
}
async function testScans(context, page) {
  reports = await json(context, '/api/published-scans', 'published_scans');
  assert(reports.clinical && reports.sources && reports.daily && Array.isArray(reports.daily.days), 'published_source_and_daily_reports_available');
  control = await json(context, '/api/scans/control', 'scan_control_read_only');
  assert(typeof control.dispatchEnabled === 'boolean' && Array.isArray(control.manual) && Array.isArray(control.overnight), 'existing_scan_control_status_identity');
  await goto(page, '/scans', 'scans_ui');
  const published = page.getByRole('button', { name: 'REFRESH PUBLISHED SCAN STATUS', exact: true });
  await published.waitFor({ state: 'visible', timeout: 30000 });
  await published.click();
  // Select the actual scan control. Accessible-name "Stage" can match a
  // screen-reader/summary element that is not a <select> and has no options.
  const stage = page.locator('.scans-actions-grid label').filter({ hasText: /^Stage/ }).locator('select').first();
  await stage.waitFor({ state: 'visible', timeout: 30000 });
  const options = await stage.locator('option').evaluateAll(items => items.map(item => item.value));
  console.log('PDUFA_ACCEPTANCE_SCAN_OPTIONS ' + JSON.stringify(options.slice(0,20)));
  assert(options.includes('PIPELINE') && options.includes('PHASE3_RESULTS') && !options.some(v => /GEM|WT/.test(v)), 'scan_targets_native_pool_pipeline_only');
  await stage.selectOption('PIPELINE');
  await stage.selectOption('ALL');
  assert(runtime.blockedMutations === 0, 'scan_controls_inspected_without_dispatch');
  result.counts.source_findings_verified = integer(reports.sources.findings_verified) ? reports.sources.findings_verified : null;
  result.counts.source_findings_unresolved = integer(reports.sources.required_findings_unresolved) ? reports.sources.required_findings_unresolved : null;
  assert(typeof reports.sources.status === 'string', 'scans_actual_source_status_is_present');
  if (reports.sources.required_findings_unresolved > 0) {
    // SCANS fetches published reports on the client. Ensure the source evidence
    // has rendered before inspecting its unresolved findings, not just the page shell.
    await page.waitForFunction(count => {
      const main = document.querySelector('main');
      return main && main.textContent.includes(String(count) + ' required findings');
    }, reports.sources.required_findings_unresolved, { timeout: 65000 });
    assert((await page.locator('main').innerText()).includes('unresolved'), 'scans_unresolved_sources_remain_explicit');
  }
}
async function testResults(context, page) {
  reports = reports || await json(context, '/api/published-scans', 'results_report');
  assert(reports.daily && reports.daily.schema_version === 1 && Array.isArray(reports.daily.days) && reports.daily.days.length > 0, 'saved_results_history_exists');
  const days = reports.daily.days;
  assert(days.every(day => /^\d{4}-\d{2}-\d{2}$/.test(day.date_pacific) && day.sections && typeof day.status === 'string'), 'saved_results_dates_and_sections_valid');
  assert(new Set(days.map(day => day.date_pacific)).size === days.length, 'results_dates_unique');
  assert(days.every(day => Object.values(day.sections).every(section => ['previous', 'new', 'updated', 'removed', 'total'].every(key => section[key] === null || integer(section[key])))), 'unknown_results_remain_null_not_fabricated_zero');
  result.counts.saved_results_days = days.length;
  result.hashes.saved_results_history = hash(days);
  await goto(page, '/results', 'results_ui');
  const dates = page.getByLabel('Report date (Pacific)', { exact: true });
  await dates.waitFor();
  // Wait for the asynchronous published-scan fetch before checking the calendar.
  // Merely finding the select isn't evidence that its saved dates have loaded.
  await page.waitForFunction(count => {
    const control = document.querySelector('select#daily-results-day');
    return control instanceof HTMLSelectElement && control.options.length >= count;
  }, days.length, { timeout: 65000 });
  const options = await dates.locator('option').evaluateAll(items => items.map(item => item.value));
  assert(options.length >= days.length, 'results_all_saved_dates_visible');
  await dates.selectOption(days[days.length - 1].date_pacific);
  const detail = page.locator('details').first();
  await detail.locator('summary').click();
  assert(await detail.getAttribute('open') !== null, 'results_saved_evidence_expands');
  await page.getByRole('button', { name: 'Refresh reports', exact: true }).click();
}
async function testDatabase(context) {
  const health = await json(context, '/api/site-health', 'site_health');
  assert(Array.isArray(health.checks), 'health_returns_dated_checks');
  assert(health.checks.some(check => check.id === 'backend' && check.state === 'good'), 'render_backend_reports_persistent_storage_ready');
  const latest = await json(context, '/api/nct-stream/' + NCT + '/runs/latest', 'saved_run');
  assert(latest.nct_id === NCT && /^[A-Za-z0-9_-]{8,100}$/.test(latest.run_id || '') && Array.isArray(latest.events) && latest.events.length > 0, 'fresh_database_saved_dossier_identity');
  const runPath = '/api/nct-stream/' + NCT + '/runs/' + latest.run_id;
  const proof = await json(context, runPath + '/dossier-integrity', 'saved_integrity');
  assert(proof.nct_id === NCT && proof.run_id === latest.run_id && proof.unchanged === true && proof.database_sha256 === ORIGINAL && proof.run_original_sha256 === ORIGINAL, 'fresh_database_payload_matches_original_saved_dossier');
  assert(latest.events.every((event, index) => event.sequence === index + 1 && event.nct_id === NCT), 'persisted_stream_sequence_is_complete_and_scoped');
  saved = { latest, runPath, proof };
  result.hashes.saved_dossier_sha256 = proof.database_sha256;
  result.hashes.saved_event_prefix_sha256 = hash(latest.events);
  result.counts.saved_stream_events = latest.events.length;
  result.saved_run_id = latest.run_id;
}
async function testPredictions(context, page) {
  const data = await json(context, '/api/phase3-trials/' + NCT + '/predictions', 'prediction');
  assert(data.nct_id === NCT && data.decision === 'ABSTAIN' && data.validated_decision_available === false, 'unvalidated_operational_prediction_is_abstain');
  assert(data.decision_explanation && data.decision_explanation.requires_independent_adjudication === true && data.decision_explanation.requires_outcome_calibration === true, 'abstain_explains_validation_gates');
  const readiness = await json(context, '/api/phase3-trials/' + NCT + '/readiness', 'readiness');
  assert(readiness.nct_id === NCT && readiness.decision === 'ABSTAIN' && Array.isArray(readiness.decision_pipeline), 'science_outcome_main_readiness_abstains');
  const consistency = await json(context, '/api/phase3-trials/' + NCT + '/statistical-consistency', 'protocol_sap');
  assert(consistency.nct_id === NCT && consistency.decision === 'ABSTAIN' && consistency.adjudication_status === 'NOT_ADJUDICATED', 'protocol_sap_comparison_not_misrepresented_as_adjudication');
  await goto(page, '/predictions', 'predictions_ui');
  assert(await page.getByText(/ABSTAIN/).count() > 0, 'predictions_page_prominently_exposes_abstention');
}
async function preserved(context) {
  if (!saved) return { blocked: true, blocker: 'fresh_database_dossier_evidence_unavailable' };
  const after = await json(context, saved.runPath, 'saved_run_after');
  const proof = await json(context, saved.runPath + '/dossier-integrity', 'saved_integrity_after');
  assert(after.nct_id === NCT && after.run_id === saved.latest.run_id && Array.isArray(after.events) && after.events.length >= saved.latest.events.length, 'saved_run_identity_preserved');
  assert(hash(after.events.slice(0, saved.latest.events.length)) === hash(saved.latest.events), 'original_saved_events_unchanged');
  assert(proof.unchanged === true && proof.database_sha256 === ORIGINAL, 'original_saved_dossier_unchanged_after_navigation');
  const fresh = await json(context, '/api/scope-funnel?view=pool&limit=50&offset=0', 'pool_preservation');
  const scope = await json(context, '/api/archive-scope', 'saved_archive_scope');
  assert(scope.status === 'VERIFIED', 'current_archive_and_pool_identity_sets_verified');
  assert(['originalScopeRecords', 'archivePhysicalRecords', 'catalogDistinctTrials', 'publishedDistinctTrials', 'unionDistinctTrials', 'missingExpectedArchiveRecords', 'archiveOutsideOriginalScope', 'catalogOutsideArchive', 'publishedOutsideArchive', 'missingPoolTrials', 'datedManifestRecords', 'missingDatedManifestRecords'].every(key => integer(scope[key])), 'original_scope_reconciliation_counts_are_actual');
  for (const key of ['originalScopeRecords', 'archivePhysicalRecords', 'unionDistinctTrials', 'missingExpectedArchiveRecords', 'missingPoolTrials', 'datedManifestRecords']) result.counts[key] = scope[key];
  assert(scope.originalScopeRecords >= 11623 && scope.archivePhysicalRecords === scope.originalScopeRecords
    && scope.missingExpectedArchiveRecords === 0 && scope.archiveOutsideOriginalScope === 0
    && scope.missingPoolTrials === 0 && scope.publishedOutsideArchive === 0
    && scope.missingDatedManifestRecords === 0, 'all_saved_original_and_current_nct_identities_preserved');
  assert(scope.currentScopeSha256 === scope.physicalArchiveSha256
    && scope.currentScopeSha256 === scope.publishedPoolSha256, 'current_scope_physical_and_published_full_sets_reconcile');
}
async function mobile(browser, password) {
  const context = await safeContext(browser, { viewport: { width: 375, height: 812 }, deviceScaleFactor: 2, isMobile: true, hasTouch: true });
  const page = await context.newPage(); watch(page);
  await login(page, password, 'webkit_mobile');
  await checkNavigation(page, 'webkit_mobile');
  for (const pathname of ['/pool', '/pipeline', '/patient-population', '/goal', '/scans', '/results', '/restrictions', '/predictions']) {
    await goto(page, pathname, 'webkit_' + pathname.slice(1).replaceAll('-', '_'));
    const nav = page.getByRole('navigation', { name: 'Site navigation', exact: true });
    assert(await nav.isVisible(), 'webkit_native_navigation_persists');
    assert(await page.locator('h1').first().isVisible(), 'webkit_route_heading_visible');
    const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 3);
    assert(overflow, 'webkit_' + pathname.slice(1).replaceAll('-', '_') + '_no_document_horizontal_overflow');
  }
  await context.close();
}
function finish() {
  result.finished_at = new Date().toISOString();
  result.counts.acceptance_gates = 14;
  for (const status of ['VERIFIED', 'BLOCKED', 'FAILED', 'NOT_VERIFIED']) result.counts['gates_' + status.toLowerCase()] = result.gates.filter(gate => gate.status === status).length;
  result.completion_percentage = Math.round(result.counts.gates_verified / 14 * 10000) / 100;
  result.runtime = runtime;
  result.failure_codes = [...new Set(failures.map(code => typeof code === 'string' && /^[a-z0-9_]+$/.test(code) ? code : 'browser_execution_failed'))];
  result.gates.sort((a, b) => a.id - b.id);
  result.verification_execution = failures.length || runtime.pageErrors || runtime.apiServerErrors || runtime.streamlitRequests || runtime.blockedMutations ? 'FAIL' : 'PASS';
  result.technical_completion = result.gates.length === 14 && result.gates.every(gate => gate.status === 'VERIFIED') && result.verification_execution === 'PASS' ? 'VERIFIED COMPLETE' : 'INCOMPLETE';
  fs.mkdirSync(path.dirname(output), { recursive: true });
  fs.writeFileSync(output, JSON.stringify(result, null, 2) + '\n', { mode: 0o600 });
  console.log('PDUFA_FINAL_MIGRATION_VERIFICATION ' + JSON.stringify(result));
  if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, [
    'Final migration acceptance: **' + result.technical_completion + '**',
    '', 'Verification execution: **' + result.verification_execution + '**',
    '', 'Verified: ' + result.counts.gates_verified + '/14; blocked: ' + result.counts.gates_blocked + '; failed: ' + result.counts.gates_failed,
    '', ...result.gates.map(row => '- ' + row.id + ' ' + row.code + ': **' + row.status + '**' + (row.blocker ? ' (' + row.blocker + ')' : row.failure_code ? ' (' + row.failure_code + ')' : '')),
    '', 'No credential, cookie, source payload, protected clinical screenshot, trace or HAR retained.', '',
  ].join('\n'));
}
(async () => {
  const password = process.env.DASHBOARD_PASSWORD;
  if (!password) { result.failure_code = 'missing_dashboard_password_secret'; failures.push(result.failure_code); finish(); process.exitCode = 1; return; }
  const { chromium, webkit } = require('playwright');
  let desktopBrowser; let mobileBrowser; let context;
  try {
    desktopBrowser = await chromium.launch();
    context = await safeContext(desktopBrowser, { viewport: { width: 1440, height: 1000 } });
    for (const pathname of ['/api/scope-funnel', '/api/site-health', '/api/published-scans', '/api/scans/control', '/api/assessments', '/api/nct-stream/' + NCT + '/runs/latest']) await json(context, pathname, 'anonymous_' + pathname.split('/').filter(Boolean).join('_').replaceAll('-', '_'), 401);
    const page = await context.newPage(); watch(page);
    await login(page, password, 'desktop');
    await gate(10, 'authentication_and_authorization', async () => {
      assert((await json(context, '/api/auth', 'authenticated_state')).authenticated === true, 'authenticated_cookie_accepted_by_application');
      assert(result.checks.desktop_normal_password_login, 'authorized_existing_password_normal_form_login');
    });
    await gate(1, 'homepage_and_native_navigation', async () => {
      await checkNavigation(page, 'desktop');
      assert(await page.getByRole('heading', { name: 'PDUFA Command Center', exact: true }).isVisible(), 'native_homepage_heading');
      const artifactDirectory = process.env.MIGRATION_ARTIFACT_DIR;
      if (artifactDirectory) {
        fs.mkdirSync(artifactDirectory, { recursive: true });
        await page.getByRole('navigation', { name: 'Site navigation', exact: true }).screenshot({ path: path.join(artifactDirectory, 'native-navigation-desktop.png') });
        result.artifacts.push('native-navigation-desktop.png');
      }
    });
    await gate(2, 'pool_inventory_search_pagination', () => testPool(context, page));
    await gate(3, 'restricted_pipeline_qualification', () => testPipeline(context, page));
    await gate(4, 'patient_population_research', () => testPopulation(page));
    await gate(5, 'scans_status_and_controls_read_only', () => testScans(context, page));
    await gate(6, 'results_dates_and_saved_history', () => testResults(context, page));
    await gate(1.5, 'goal_operations_supporting_observation', async () => {
      await goto(page, '/goal', 'goal_ui');
      await page.getByRole('heading', { name: 'Research Operations', exact: true }).waitFor();
      await page.waitForFunction(() => [...document.querySelectorAll('p')].some(item => /Source state:/.test(item.textContent)), null, { timeout: 65000 });
      assert((await page.locator('main').innerText()).includes('Not established'), 'goal_does_not_invent_qualified_program_count');
    });
    const goalObservation = result.gates.pop();
    const homeGate = result.gates.find(row => row.id === 1);
    homeGate.checks.push(...goalObservation.checks);
    if (goalObservation.status === 'FAILED') { homeGate.status = 'FAILED'; homeGate.failure_code = goalObservation.failure_code; }
    await gate(7, 'restrictions_rules_read_only', async () => {
      await goto(page, '/restrictions', 'restrictions_ui');
      const before = await page.locator('main').innerText();
      assert(/\$300 million–\$10 billion inclusive/.test(before) && /Current public listing/.test(before) && /pivotal Phase 3/.test(before), 'restrictions_all_three_independent_rules_visible');
      assert(await page.locator('main input, main select, main button').count() === 0, 'restrictions_are_read_only');
      result.hashes.restriction_rules = hash(before);
      await page.reload({ waitUntil: 'domcontentloaded' });
      assert(hash(await page.locator('main').innerText()) === result.hashes.restriction_rules, 'restriction_rules_unchanged_after_refresh');
    });
    await gate(8, 'prediction_abstention_and_readiness', () => testPredictions(context, page));
    await gate(9, 'backend_and_fresh_postgresql_reads', () => testDatabase(context));
    await gate(11, 'original_source_and_dossier_preservation', () => preserved(context));
    await gate(12, 'scheduled_execution_and_source_dependencies', async () => {
      control = control || await json(context, '/api/scans/control', 'schedule_control');
      assert(Array.isArray(control.overnight), 'existing_overnight_runs_readable');
      result.counts.visible_overnight_runs = control.overnight.length;
      result.counts.successful_visible_overnight_runs = control.overnight.filter(run => run.status === 'completed' && run.conclusion === 'success').length;
      return { blocked: true, blocker: 'scheduled_8pm_execution_and_all_required_source_success_require_independent_run_audit' };
    });
    await gate(13, 'legacy_retirement', async () => {
      assert(runtime.streamlitRequests === 0, 'native_pages_make_no_streamlit_requests');
      assert(runtime.blockedMutations === 0, 'verification_started_no_scans_and_modified_no_controls');
      return { blocked: true, blocker: 'external_streamlit_administrative_shutdown_not_verified' };
    });
    await gate(14, 'backup_and_actual_restore', async () => ({ blocked: true, blocker: 'no_authorized_isolated_postgresql_restore_target_or_actual_restore_evidence' }));
    mobileBrowser = await webkit.launch();
    try { await mobile(mobileBrowser, password); result.checks.mobile_webkit_all_nine_routes = true; }
    catch (error) { result.checks.mobile_webkit_all_nine_routes = false; failures.push(error.code || 'mobile_webkit_execution_failed'); }
    await gatePostPreservation(context);
  } catch (error) {
    result.failure_code = typeof error.code === 'string' && /^[a-z0-9_]+$/.test(error.code) ? error.code : 'authorized_browser_execution_failed';
    failures.push(result.failure_code);
  } finally {
    if (context) await context.close().catch(() => {});
    if (desktopBrowser) await desktopBrowser.close().catch(() => {});
    if (mobileBrowser) await mobileBrowser.close().catch(() => {});
    finish();
    if (result.verification_execution !== 'PASS') process.exitCode = 1;
  }
})();
async function gatePostPreservation(context) {
  if (!saved) return;
  const proof = await json(context, saved.runPath + '/dossier-integrity', 'final_saved_integrity');
  assert(proof.unchanged === true && proof.database_sha256 === ORIGINAL, 'final_mobile_and_desktop_dossier_unchanged');
}

