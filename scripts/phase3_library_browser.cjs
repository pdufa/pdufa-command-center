'use strict';

// Uses the normal application password form. This script retains no source
// values, credentials, browser state, screenshots, traces, HARs or cookies.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const BASE = 'https://pdufa-new-dashboard.vercel.app';
const POINTER_KEY = 'pdufa_nct_processing_run_v1';
const DECISIONS = ['APPROVED', 'CRL', 'EXTENDED', 'PENDING'];
const result = { status: 'INCOMPLETE', started_at: new Date().toISOString(), checks: {}, counts: {}, failure_code: null };
let phase = 'preflight';

function requireCheck(value, code) {
  result.checks[code] = Boolean(value);
  if (!value) { const error = new Error(code); error.checkId = code; throw error; }
}
function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  return JSON.stringify(value);
}
function sanitized() {
  const safe = { status: result.status === 'PASS' ? 'PASS' : 'INCOMPLETE', started_at: result.started_at, finished_at: result.finished_at, checks: {}, counts: {}, failure_code: null };
  for (const [key, value] of Object.entries(result.checks)) if (/^[a-z0-9_]{1,120}$/.test(key) && typeof value === 'boolean') safe.checks[key] = value;
  for (const [key, value] of Object.entries(result.counts)) if (/^[a-z0-9_]{1,120}$/.test(key) && Number.isSafeInteger(value) && value >= 0) safe.counts[key] = value;
  for (const key of ['nct_id', 'run_id', 'dossier_id']) if (typeof result[key] === 'string' && /^[A-Za-z0-9:._/-]{1,250}$/.test(result[key])) safe[key] = result[key];
  for (const key of ['saved_dossier_sha256', 'persisted_events_sha256']) if (/^[a-f0-9]{64}$/.test(result[key] || '')) safe[key] = result[key];
  if (typeof result.failure_code === 'string' && /^[A-Za-z0-9_]{1,160}$/.test(result.failure_code)) safe.failure_code = result.failure_code;
  if (['RUNNING', 'COMPLETE', 'FAILED', 'PAUSED', 'NOT_STARTED', 'IDLE'].includes(result.ingestion_state)) safe.ingestion_state = result.ingestion_state;
  return safe;
}
function record() {
  result.finished_at = new Date().toISOString();
  const safe = sanitized();
  const destination = process.env.PHASE3_RESULT_PATH || path.join(process.cwd(), 'phase3-library-browser-result.json');
  fs.mkdirSync(path.dirname(destination), { recursive: true });
  fs.writeFileSync(destination, JSON.stringify(safe, null, 2) + '\n', { mode: 0o600 });
  console.log('PDUFA_PHASE3_BROWSER_VERIFICATION ' + JSON.stringify(safe));
  if (process.env.GITHUB_STEP_SUMMARY) fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY,
    'Phase 3 library browser verification: **' + safe.status + '**\n\n' +
    (safe.nct_id ? 'Trial: \x60' + safe.nct_id + '\x60\n\n' : '') +
    (safe.failure_code ? 'Check: \x60' + safe.failure_code + '\x60\n\n' : '') +
    'Only sanitized identifiers, hashes, counts, timestamps and assertion booleans were retained.\n');
}
function validCatalog(value, period, code) {
  requireCheck(value && value.period === period && Array.isArray(value.trials) && Number.isSafeInteger(value.total) && value.total >= 0 &&
    Number.isSafeInteger(value.page) && value.page > 0 && Number.isSafeInteger(value.page_size) && value.page_size > 0 &&
    value.counts && DECISIONS.every(key => Number.isSafeInteger(value.counts[key]) && value.counts[key] >= 0), code + '_catalog_schema');
  requireCheck(value.trials.length <= value.page_size && new Set(value.trials.map(row => row.nct_id)).size === value.trials.length, code + '_unique_trial_identifiers');
  for (const row of value.trials) {
    requireCheck(/^NCT[0-9]{8}$/.test(row.nct_id || '') && row.results_available === true && typeof row.company === 'string' &&
      typeof row.drug === 'string' && typeof row.indication === 'string' && typeof row.trial_title === 'string' &&
      DECISIONS.includes(row.actual_decision), code + '_actual_phase3_records');
    requireCheck(Array.isArray(row.evidence) && row.evidence.some(source => source.verification_status === 'VERIFIED' &&
      source.url === 'https://clinicaltrials.gov/api/v2/studies/' + row.nct_id && /^[a-f0-9]{64}$/.test(source.sha256 || '') &&
      Number.isFinite(Date.parse(source.retrieved_at))), code + '_authoritative_source_provenance');
    if (row.actual_decision !== 'PENDING') requireCheck(Array.isArray(row.regulatory_application_ids) && row.regulatory_application_ids.length > 0 &&
      row.evidence.some(source => source.verification_status === 'VERIFIED' && !source.url.startsWith('https://clinicaltrials.gov/')), code + '_regulatory_decisions_have_linked_primary_evidence');
  }
  return value;
}
async function catalog(context, period, changes = {}, code = 'api') {
  const params = new URLSearchParams({ period, q: '', decision: 'ALL', sort: 'nct_id', dir: 'asc', page: '1', page_size: '25', ...changes });
  const response = await context.request.get(BASE + '/api/phase3-trials?' + params, { timeout: 30000, maxRedirects: 0 });
  requireCheck(response.status() === 200, code + '_authenticated_catalog_200');
  requireCheck((response.headers()['cache-control'] || '').includes('no-store'), code + '_catalog_private_no_store');
  return validCatalog(await response.json(), period, code);
}
async function warmCatalog(context, period) {
  const deadline = Date.now() + 180000;
  while (true) {
    const data = await catalog(context, period, {}, period.toLowerCase());
    if (data.total > 0 && data.trials.length > 0) return data;
    if (Date.now() >= deadline) { requireCheck(false, period.toLowerCase() + '_catalog_populated_with_real_trials'); }
    await new Promise(resolve => setTimeout(resolve, 3000));
  }
}
function responseFor(page, filters) {
  return page.waitForResponse(response => {
    const url = new URL(response.url());
    return url.pathname === '/api/phase3-trials' && response.request().method() === 'GET' &&
      Object.entries(filters).every(([key, value]) => url.searchParams.get(key) === String(value));
  }, { timeout: 45000 });
}
async function visibleMatches(page, data, prefix) {
  const expected = data.trials.map(row => row.nct_id);
  await page.waitForFunction(ids => {
    const actual = [...document.querySelectorAll('#phase3-trial-library tbody tr[data-nct-id]')].map(row => row.getAttribute('data-nct-id'));
    return JSON.stringify(actual) === JSON.stringify(ids);
  }, expected, { timeout: 30000 });
  const displayed = await page.locator('#phase3-trial-library tbody tr[data-nct-id]').evaluateAll(rows => rows.map(row => [...row.querySelectorAll('td')].map(cell => cell.textContent.trim())));
  for (const [index, row] of data.trials.entries()) {
    const cells = displayed[index];
    requireCheck(cells?.length === 15 && cells[0] === row.company && cells[1] === (row.ticker || 'Not verified') &&
      cells[2] === row.drug && cells[3] === row.indication && cells[4] === row.trial_title && cells[5] === row.nct_id &&
      cells[6] === row.phase3_status && cells[7] === (row.primary_endpoint_result || 'Posted results require endpoint interpretation') &&
      cells[8] === 'Posted results verified' && cells[9] === (row.fda_submission_status || 'UNKNOWN') &&
      cells[12] === (row.scientific_readiness || 'NOT READY'), prefix + '_rendered_values_match_verified_database_response');
  }
  const names = { APPROVED: '🟢', CRL: '🔴', EXTENDED: '🟠', PENDING: '⚪' };
  for (const decision of DECISIONS) {
    const button = page.locator('#phase3-trial-library').getByRole('button', { name: new RegExp('^' + names[decision] + ' ' + decision + ' ·') });
    requireCheck((await button.textContent()).trim() === names[decision] + ' ' + decision + ' · ' + data.counts[decision].toLocaleString('en-US'), prefix + '_decision_counts_match_server');
  }
}
async function readUiResponse(response, period, prefix, page) {
  requireCheck(response.status() === 200, prefix + '_ui_catalog_200');
  const data = validCatalog(await response.json(), period, prefix);
  await visibleMatches(page, data, prefix);
  return data;
}
async function selectPeriod(page, period, code) {
  const select = page.getByLabel('Search period', { exact: true });
  const response = responseFor(page, { period, decision: 'ALL', page: '1' });
  if (await select.inputValue() === period) {
    await page.locator('#phase3-trial-library').getByRole('button', { name: 'Refresh verified trials', exact: true }).click();
  } else await select.selectOption(period);
  return readUiResponse(await response, period, code, page);
}
function checkSnapshot(snapshot, nct, runId) {
  requireCheck(snapshot?.nct_id === nct && snapshot?.run_id === runId && snapshot.terminal === true && snapshot.status === 'COMPLETE' &&
    Array.isArray(snapshot.events) && snapshot.events.length > 0, 'selected_trial_terminal_snapshot');
  const states = new Map(), dependencies = {
    trial_identity: ['nct_identifier', 'sponsor', 'products', 'indication', 'phase'],
    trial_design: ['primary_endpoints', 'study_completion_status'],
    clinical_results: ['primary_endpoint_results', 'statistical_significance', 'clinical_effect_size', 'safety_findings', 'serious_adverse_events'],
    regulatory: ['fda_regulatory_pathway', 'special_designations', 'regulatory_submission_evidence', 'pdufa_date'],
    trial: ['trial_identity', 'trial_design', 'clinical_results', 'regulatory'],
  };
  const terminal = new Set(['VERIFIED', 'FAILED', 'INSUFFICIENT_EVIDENCE']);
  let dependencyChecks = 0;
  for (const [index, event] of snapshot.events.entries()) {
    requireCheck(event.nct_id === nct && event.run_id === runId && event.sequence === index + 1 && event.status !== 'FAILED', 'selected_trial_persisted_events_ordered_without_failures');
    if (event.source) requireCheck(event.source.url === 'https://clinicaltrials.gov/api/v2/studies/' + nct &&
      /^[a-f0-9]{64}$/.test(event.source.sha256 || '') && Number.isFinite(Date.parse(event.source.verified_at)), 'selected_trial_live_source_provenance');
    if (event.kind === 'node') {
      if (dependencies[event.node_id] && terminal.has(event.status)) {
        requireCheck(dependencies[event.node_id].every(child => terminal.has(states.get(child)?.status)), 'selected_trial_parent_follows_subordinate_completion');
        dependencyChecks += 1;
      }
      if (event.node_id === 'main') requireCheck(event.value?.decision === 'ABSTAIN', 'analysis_preserves_main_abstention');
      states.set(event.node_id, event);
    }
  }
  requireCheck(states.get('nct_identifier')?.value === nct && states.get('nct_identifier')?.source, 'selected_trial_normalized_nct_identity');
  requireCheck(dependencyChecks > 0 && snapshot.events.at(-1)?.terminal === true, 'selected_trial_bottom_up_processing_completed');
  result.counts.selected_trial_persisted_events = snapshot.events.length;
  result.counts.selected_trial_parent_dependency_checks = dependencyChecks;
  result.persisted_events_sha256 = crypto.createHash('sha256').update(canonical(snapshot.events)).digest('hex');
}
async function readSnapshot(context, nct, runId) {
  const response = await context.request.get(BASE + '/api/nct-stream/' + nct + '/runs/' + runId, { timeout: 30000 });
  requireCheck(response.status() === 200, 'selected_trial_authenticated_snapshot_200');
  return response.json();
}
async function dossierProof(context, nct, runId, expected) {
  const response = await context.request.get(BASE + '/api/nct-stream/' + nct + '/runs/' + runId + '/dossier-integrity', { timeout: 30000 });
  requireCheck(response.status() === 200, 'saved_dossier_read_only_integrity_endpoint_200');
  const proof = await response.json();
  requireCheck(proof.nct_id === nct && proof.run_id === runId && proof.unchanged === true &&
    typeof proof.dossier_id === 'string' && /^[a-f0-9]{64}$/.test(proof.database_sha256 || '') &&
    proof.database_sha256 === proof.run_original_sha256, 'saved_dossier_database_checksum_matches_original');
  if (expected) requireCheck(proof.dossier_id === expected.dossier_id && proof.database_sha256 === expected.database_sha256, 'saved_dossier_unchanged_after_processing_and_refresh');
  result.dossier_id = proof.dossier_id; result.saved_dossier_sha256 = proof.database_sha256;
  return proof;
}

async function installRealReconnectProbe(page) {
  // Deliberately closes one real HTTP stream; never fabricates/changes data.
  await page.addInitScript(() => {
    const nativeFetch = window.fetch.bind(window);
    const probe = { connections: [], delivered: [], interrupted: false, protocol_errors: 0 };
    window.__phase3Transport = probe;
    window.fetch = async (input, options) => {
      const response = await nativeFetch(input, options);
      const url = new URL(typeof input === 'string' || input instanceof URL ? String(input) : input.url, location.href);
      if (!url.pathname.startsWith('/api/nct-stream/') || !url.pathname.endsWith('/events') || !response.ok || !response.body) return response;
      const headers = new Headers(options?.headers || (input instanceof Request ? input.headers : undefined));
      const connection = { after: Number(url.searchParams.get('after') || '0'), cursor: headers.get('Last-Event-ID'), delivered: 0 };
      probe.connections.push(connection);
      const interrupt = !probe.interrupted && probe.connections.length === 1;
      const reader = response.body.getReader(), decoder = new TextDecoder(), encoder = new TextEncoder();
      const body = new ReadableStream({
        async start(controller) {
          let buffer = '';
          try {
            while (true) {
              const next = await reader.read();
              buffer += decoder.decode(next.value || new Uint8Array(), { stream: !next.done });
              let boundary;
              while ((boundary = buffer.match(/\r?\n\r?\n/))) {
                const end = boundary.index + boundary[0].length;
                const frame = buffer.slice(0, end); buffer = buffer.slice(end);
                const lines = frame.replace(/\r\n/g, '\n').split('\n');
                const data = lines.filter(line => line.startsWith('data:')).map(line => line.slice(5).replace(/^ /, '')).join('\n');
                if (data) {
                  try {
                    const event = JSON.parse(data);
                    const id = lines.find(line => line.startsWith('id:'))?.slice(3).trim();
                    if (id !== event.run_id + ':' + event.sequence) probe.protocol_errors += 1;
                    probe.delivered.push({ id, run_id: event.run_id, nct_id: event.nct_id, sequence: event.sequence });
                    connection.delivered += 1;
                  } catch { probe.protocol_errors += 1; }
                }
                controller.enqueue(encoder.encode(frame));
                if (interrupt && connection.delivered === 3) {
                  probe.interrupted = true; controller.close();
                  await reader.cancel().catch(() => {}); return;
                }
              }
              if (next.done) { if (buffer) controller.enqueue(encoder.encode(buffer)); controller.close(); return; }
            }
          } catch { controller.error(new Error('Verification observed a stream interruption')); }
        },
        cancel() { return reader.cancel().catch(() => {}); },
      });
      return new Response(body, { status: response.status, statusText: response.statusText, headers: response.headers });
    };
  });
}

async function main() {
  const password = process.env.DASHBOARD_PASSWORD;
  delete process.env.DASHBOARD_PASSWORD;
  if (!password) { result.failure_code = 'MISSING_GITHUB_ACTIONS_SECRET_DASHBOARD_PASSWORD'; process.exitCode = 1; record(); return; }
  let browser;
  try {
    phase = 'launch';
    const { chromium } = require('playwright');
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ reducedMotion: 'no-preference' });
    const probe = await context.request.get(BASE + '/api/phase3-trials?period=CURRENT', { timeout: 30000, maxRedirects: 0 });
    requireCheck(probe.status() === 401, 'anonymous_trial_catalog_rejected_401');
    const page = await context.newPage();
    await installRealReconnectProbe(page);
    const network = { runPosts: 0, eventResponses: 0, wrongSse: 0, runtimeErrors: 0, consoleErrors: 0, unexpectedApiFailures: 0 };
    page.on('pageerror', () => { network.runtimeErrors += 1; });
    page.on('console', message => {
      if (message.type() === 'error' && /phase3-trials|Phase3TrialLibrary|nct-stream|NctLiveStream|hydration|ChunkLoadError|ReferenceError|TypeError/i.test(message.text())) network.consoleErrors += 1;
    });
    page.on('request', request => { if (/^\/api\/nct-stream\/NCT[0-9]{8}\/runs$/.test(new URL(request.url()).pathname) && request.method() === 'POST') network.runPosts += 1; });
    page.on('response', response => {
      const url = new URL(response.url());
      if (url.pathname.startsWith('/api/nct-stream/') && url.pathname.endsWith('/events')) {
        network.eventResponses += 1;
        if (!response.ok() || !(response.headers()['content-type'] || '').startsWith('text/event-stream')) network.wrongSse += 1;
      }
    });
    page.on('requestfailed', request => {
      if (/^\/api\/(?:phase3-trials|nct-stream)/.test(new URL(request.url()).pathname) && !/ERR_ABORTED|NS_BINDING_ABORTED/.test(request.failure()?.errorText || '')) network.unexpectedApiFailures += 1;
    });
    phase = 'normal_login';
    await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('#password').fill(password);
    const login = page.waitForResponse(response => new URL(response.url()).pathname === '/api/auth' && response.request().method() === 'POST');
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    requireCheck((await login).status() === 200, 'normal_production_dashboard_authentication');
    await page.locator('#nct-live-processing').waitFor({ state: 'visible', timeout: 45000 });
    phase = 'catalog_warmup';
    const current = await warmCatalog(context, 'CURRENT');
    const historical = await warmCatalog(context, 'PREVIOUS');
    requireCheck(current.total > 0 && historical.total > 0, 'current_and_historical_catalogs_populated');
    result.counts.current_verified_trials = current.total; result.counts.historical_verified_trials = historical.total;
    phase = 'prediction_navigation';
    const nav = page.getByRole('button', { name: 'PREDICTION', exact: true });
    const initialResponse = responseFor(page, { period: 'CURRENT', page: '1' });
    await nav.click();
    requireCheck(await nav.getAttribute('aria-current') === 'page', 'prediction_tab_selected');
    const library = page.locator('#phase3-trial-library');
    await library.waitFor({ state: 'visible', timeout: 45000 });
    const uiCurrent = await readUiResponse(await initialResponse, 'CURRENT', 'initial_current', page);
    requireCheck(await page.getByRole('region', { name: 'PREDICTION — HOP', exact: true }).locator('#phase3-trial-library').count() === 1, 'library_inside_existing_prediction_tab');
    const placement = await library.evaluate(section => {
      const prediction = section.closest('section[aria-label="PREDICTION — HOP"]');
      if (!prediction) return false;
      const siblings = [...prediction.children];
      return siblings.indexOf(section) > siblings.findIndex(child => child.tagName === 'H2') && !document.querySelector('#nct-live-processing #phase3-trial-library');
    });
    requireCheck(placement, 'library_below_existing_prediction_analysis_content');
    const requiredHeaders = ['Company', 'Stock ticker', 'Drug', 'Indication', 'Trial title', 'NCT number', 'Phase 3 status', 'Primary endpoint result', 'Results availability', 'FDA submission status', 'PDUFA date', 'Actual FDA decision', 'Scientific readiness', 'Last verified date', 'Analyze'];
    requireCheck(await library.locator('thead th').count() === 15, 'library_has_fifteen_required_columns');
    for (const header of requiredHeaders) requireCheck(await library.getByRole('columnheader', { name: new RegExp(header.replace(/[.*+?^$()|[\]\\]/g, '\\$&'), 'i') }).count() === 1, 'required_column_present');
    const historicalResponse = await selectPeriod(page, 'PREVIOUS', 'historical_ui');
    requireCheck(historicalResponse.trials.length > 0, 'historical_ui_has_verified_records');
    await selectPeriod(page, 'CURRENT', 'restored_current_ui');
    phase = 'server_search';
    const sample = uiCurrent.trials[0];
    for (const field of ['nct_id', 'company', 'drug', 'indication']) {
      const term = String(sample[field] || '').slice(0, 100).trim();
      requireCheck(term.length > 0, 'verified_trial_has_searchable_' + field);
      const searched = await catalog(context, 'CURRENT', { q: term }, 'search_' + field);
      requireCheck(searched.trials.some(row => row.nct_id === sample.nct_id), 'server_search_' + field + '_finds_exact_saved_trial');
    }
    const searchInput = page.getByLabel('Search trials', { exact: true });
    let uiResponse = responseFor(page, { period: 'CURRENT', q: sample.nct_id, page: '1' });
    await searchInput.fill(sample.nct_id);
    const uiSearch = await readUiResponse(await uiResponse, 'CURRENT', 'nct_search_ui', page);
    requireCheck(uiSearch.trials.some(row => row.nct_id === sample.nct_id), 'nct_search_populates_correct_trial');
    uiResponse = responseFor(page, { period: 'CURRENT', q: '', page: '1' });
    await searchInput.fill('');
    await readUiResponse(await uiResponse, 'CURRENT', 'search_cleared', page);
    phase = 'sort_and_pagination';
    uiResponse = responseFor(page, { sort: 'nct_id', dir: 'asc', page: '1' });
    await page.getByRole('button', { name: 'Sort by NCT number', exact: true }).click();
    let firstPage = await readUiResponse(await uiResponse, 'CURRENT', 'sorted_page_one', page);
    requireCheck(firstPage.trials.every((row, index, rows) => index === 0 || rows[index - 1].nct_id.localeCompare(row.nct_id) <= 0), 'server_sort_nct_ascending');
    requireCheck(firstPage.total > 25 && firstPage.pages > 1, 'catalog_supports_multiple_server_pages');
    uiResponse = responseFor(page, { sort: 'nct_id', dir: 'asc', page: '2' });
    await library.getByRole('button', { name: 'Next page', exact: true }).click();
    const secondPage = await readUiResponse(await uiResponse, 'CURRENT', 'sorted_page_two', page);
    requireCheck(secondPage.page === 2 && secondPage.trials.length > 0 && !secondPage.trials.some(row => firstPage.trials.some(first => first.nct_id === row.nct_id)), 'pagination_returns_distinct_verified_trial_ids');
    result.counts.pagination_distinct_trials = new Set([...firstPage.trials, ...secondPage.trials].map(row => row.nct_id)).size;
    phase = 'decision_filters';
    for (const decision of DECISIONS) {
      const icon = { APPROVED: '🟢', CRL: '🔴', EXTENDED: '🟠', PENDING: '⚪' }[decision];
      const box = library.getByRole('button', { name: new RegExp('^' + icon + ' ' + decision + ' ·') });
      uiResponse = responseFor(page, { decision, page: '1' });
      await box.click();
      const filtered = await readUiResponse(await uiResponse, 'CURRENT', 'decision_' + decision.toLowerCase(), page);
      requireCheck(filtered.total === filtered.counts[decision] && filtered.trials.every(row => row.actual_decision === decision), 'decision_' + decision.toLowerCase() + '_matches_verified_records');
      requireCheck(await box.getAttribute('aria-pressed') === 'true', 'decision_' + decision.toLowerCase() + '_filter_selected');
    }
    uiResponse = responseFor(page, { decision: 'ALL', page: '1' });
    await library.getByRole('button', { name: /^All ·/ }).click();
    const all = await readUiResponse(await uiResponse, 'CURRENT', 'all_decisions_restored', page);
    const chosen = all.trials.find(row => !row.latest_run_id) || all.trials[0];
    requireCheck(chosen && /^NCT[0-9]{8}$/.test(chosen.nct_id), 'real_trial_selected_for_analysis');
    result.nct_id = chosen.nct_id;
    phase = 'analyze_selected_trial';
    const postsBefore = network.runPosts;
    await page.locator('#nct-live-processing').evaluate(section => {
      const observation = { loading_indicator: false, verified_while_processing: false, reconnect_notice: false };
      const check = () => {
        const status = section.querySelector('[role="status"]')?.textContent || '';
        const spinner = section.querySelector('article[data-state="LOADING"] .nct-processing-spinner');
        if (spinner && getComputedStyle(spinner).animationName !== 'none') observation.loading_indicator = true;
        if (section.querySelector('article[data-state="VERIFIED"]') && !status.includes('Processing run completed')) observation.verified_while_processing = true;
        if (status.includes('Connection interrupted. Reconnecting')) observation.reconnect_notice = true;
      };
      new MutationObserver(check).observe(section, { childList: true, subtree: true, attributes: true, characterData: true });
      window.__phase3AnalysisObservation = observation; check();
    });
    await library.getByRole('button', { name: 'Analyze ' + chosen.nct_id, exact: true }).dblclick();
    await page.waitForFunction(nct => {
      try { return JSON.parse(localStorage.getItem('pdufa_nct_processing_run_v1') || 'null')?.nct_id === nct; } catch { return false; }
    }, chosen.nct_id, { timeout: 60000 });
    const pointer = await page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), POINTER_KEY);
    requireCheck(pointer?.nct_id === chosen.nct_id && /^[A-Za-z0-9_-]{8,100}$/.test(pointer.run_id || ''), 'analyze_uses_exact_nct_and_persisted_run');
    result.run_id = pointer.run_id;
    const original = await dossierProof(context, chosen.nct_id, pointer.run_id);
    const processing = page.locator('#nct-live-processing');
    await processing.locator('[role="status"]').filter({ hasText: /Processing run completed\.|Saved completed processing run restored\./ }).waitFor({ state: 'visible', timeout: 150000 });
    requireCheck(network.runPosts - postsBefore <= 1, 'double_click_does_not_duplicate_processing_runs');
    if (!chosen.latest_run_id) requireCheck(network.runPosts - postsBefore === 1 && network.eventResponses > 0 && network.wrongSse === 0, 'new_library_trial_uses_authenticated_render_sse');
    else requireCheck(pointer.run_id === chosen.latest_run_id, 'analyze_restores_existing_saved_analysis');
    const snapshot = await readSnapshot(context, chosen.nct_id, pointer.run_id);
    checkSnapshot(snapshot, chosen.nct_id, pointer.run_id);
    if (!chosen.latest_run_id) {
      const visible = await page.evaluate(() => window.__phase3AnalysisObservation);
      requireCheck(visible?.loading_indicator && visible?.verified_while_processing && visible?.reconnect_notice, 'new_trial_visible_loading_incremental_population_and_reconnect_notice');
      const wire = await page.evaluate(() => window.__phase3Transport);
      requireCheck(wire?.interrupted === true && wire.connections.length >= 2 && wire.connections[1].after === 3 &&
        wire.connections[1].cursor === pointer.run_id + ':3', 'new_trial_forced_browser_reconnection_uses_actual_cursor');
      requireCheck(wire.protocol_errors === 0 && wire.delivered.length === snapshot.events.length &&
        wire.delivered.every((event, index) => event.id === pointer.run_id + ':' + (index + 1) && event.sequence === index + 1 &&
          event.nct_id === chosen.nct_id && event.run_id === pointer.run_id), 'new_trial_reconnection_preserves_order_without_duplicates');
      result.counts.selected_trial_browser_connections = wire.connections.length;
      result.counts.selected_trial_received_events = wire.delivered.length;
      result.counts.selected_trial_duplicate_events = wire.delivered.length - new Set(wire.delivered.map(event => event.id)).size;
    }
    await dossierProof(context, chosen.nct_id, pointer.run_id, original);
    const postsBeforeSecondClick = network.runPosts;
    await library.getByRole('button', { name: 'Analyze ' + chosen.nct_id, exact: true }).click();
    await page.waitForTimeout(500);
    requireCheck(network.runPosts === postsBeforeSecondClick, 'repeated_analyze_reuses_saved_analysis');
    requireCheck(await page.locator('#nct-live-input').inputValue() === chosen.nct_id, 'selected_trial_populates_existing_analysis_input');
    phase = 'refresh_persistence';
    const eventHash = result.persisted_events_sha256;
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('#nct-live-processing [role="status"]').filter({ hasText: 'Saved completed processing run restored.' }).waitFor({ state: 'visible', timeout: 60000 });
    const restored = await page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), POINTER_KEY);
    requireCheck(restored?.run_id === pointer.run_id && restored?.nct_id === chosen.nct_id && network.runPosts === postsBeforeSecondClick, 'refresh_preserves_selected_trial_without_new_run');
    const afterRefresh = await readSnapshot(context, chosen.nct_id, pointer.run_id);
    requireCheck(crypto.createHash('sha256').update(canonical(afterRefresh.events)).digest('hex') === eventHash, 'database_events_survive_refresh_unchanged');
    await dossierProof(context, chosen.nct_id, pointer.run_id, original);
    await page.getByRole('button', { name: 'PREDICTION', exact: true }).click();
    await library.waitFor({ state: 'visible', timeout: 30000 });
    await library.getByRole('status').filter({ hasText: 'Selected trial:' }).waitFor({ state: 'visible', timeout: 30000 });
    requireCheck((await library.textContent()).includes(chosen.nct_id), 'library_restores_current_trial_selection');
    requireCheck(await library.getByLabel('Search period', { exact: true }).inputValue() === 'CURRENT', 'library_filters_survive_refresh');
    phase = 'mobile_layout';
    await page.setViewportSize({ width: 375, height: 812 });
    await library.waitFor({ state: 'visible' });
    const mobile = await library.evaluate(section => {
      const area = section.querySelector('[aria-label="Scrollable Phase 3 trial table"]');
      const table = area?.querySelector('table');
      const before = area?.scrollLeft || 0;
      if (area) area.scrollLeft = area.scrollWidth;
      const rect = area?.getBoundingClientRect();
      return { scrollable: !!area && !!table && area.scrollWidth > area.clientWidth && area.scrollLeft > before,
        within_viewport: !!rect && rect.left >= -1 && rect.right <= window.innerWidth + 1,
        fifteen_headers: table?.querySelectorAll('thead th').length === 15,
        analyze_present: !!section.querySelector('button[aria-label^="Analyze NCT"]') };
    });
    requireCheck(mobile.scrollable && mobile.within_viewport && mobile.fifteen_headers && mobile.analyze_present, 'mobile_table_scrolls_with_all_columns_without_clipping');
    phase = 'final_metrics';
    for (const period of ['CURRENT', 'PREVIOUS']) {
      const final = await catalog(context, period, {}, 'final_' + period.toLowerCase());
      result.counts[period.toLowerCase() + '_verified_trials'] = final.total;
      for (const decision of DECISIONS) result.counts[period.toLowerCase() + '_' + decision.toLowerCase()] = final.counts[decision];
      if (period === 'CURRENT') {
        result.ingestion_state = final.ingestion?.state;
        result.checks.automatic_sync_execution_verified = final.ingestion?.scheduling?.verified_execution === true;
      }
    }
    result.counts.browser_analysis_posts = network.runPosts;
    result.counts.browser_sse_responses = network.eventResponses;
    result.counts.runtime_errors = network.runtimeErrors;
    result.counts.relevant_console_errors = network.consoleErrors;
    result.counts.unexpected_api_network_errors = network.unexpectedApiFailures;
    requireCheck(network.runtimeErrors === 0 && network.consoleErrors === 0 && network.unexpectedApiFailures === 0 && network.wrongSse === 0, 'no_relevant_runtime_errors');
    requireCheck(Object.entries(result.checks).every(([key, value]) => key === 'automatic_sync_execution_verified' || value === true), 'all_mandatory_phase3_browser_assertions_passed');
    result.status = 'PASS';
  } catch (failure) {
    result.failure_code = typeof failure?.checkId === 'string' ? failure.checkId : 'LIVE_CHECK_FAILED_AT_' + phase.toUpperCase();
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close().catch(() => {});
    record();
  }
}
void main();
