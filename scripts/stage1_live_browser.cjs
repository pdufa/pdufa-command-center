'use strict';

// Uses a normal application login. No cookies, browser state, source values,
// screenshots, traces, HARs or credentials are written to artifacts or logs.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');

const NCT = 'NCT00116805';
const BASE = 'https://pdufa-new-dashboard.vercel.app';
const POINTER_KEY = 'pdufa_nct_processing_run_v1';
const outputPath = process.env.STAGE1_RESULT_PATH || path.join(process.cwd(), 'stage1-live-browser-result.json');
const summaryPath = process.env.GITHUB_STEP_SUMMARY;
const result = {
  status: 'INCOMPLETE', started_at: new Date().toISOString(), nct_id: NCT,
  checks: {}, counts: {}, source_sha256: [], failure_code: null,
};
let phase = 'preflight';

function record() {
  result.finished_at = new Date().toISOString();
  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, JSON.stringify(result, null, 2) + '\n', { mode: 0o600 });
  if (summaryPath) {
    const lines = [
      'Stage 1 authorized live browser verification: **' + result.status + '**',
      '', 'NCT: `' + NCT + '`',
      result.run_id ? 'Run: `' + result.run_id + '`' : 'No authenticated run ID established.',
      result.failure_code ? 'Blocker/check ID: `' + result.failure_code + '`' : 'All required live checks passed.',
      '', 'No credentials, session state, source values, screenshots, traces or HARs were retained.',
    ];
    fs.appendFileSync(summaryPath, lines.join('\n') + '\n');
  }
  // A fixed status and check identifier cannot expose a password or page content.
  console.log('Stage 1 live browser: ' + result.status + (result.failure_code ? ' [' + result.failure_code + ']' : ''));
}

function requireCheck(value, code) {
  result.checks[code] = Boolean(value);
  if (!value) {
    const error = new Error(code);
    error.checkId = code;
    throw error;
  }
}

function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort().map(k => JSON.stringify(k) + ':' + canonical(value[k])).join(',') + '}';
  return JSON.stringify(value);
}

function summarizeSnapshot(snapshot, runId) {
  requireCheck(snapshot && snapshot.run_id === runId && snapshot.nct_id === NCT && typeof snapshot.dossier_id === 'string', 'snapshot_identity');
  requireCheck(Array.isArray(snapshot.events) && snapshot.events.length > 0 && snapshot.terminal === true, 'persisted_terminal_snapshot');
  const latest = new Map();
  const children = {
    trial_identity: ['nct_identifier', 'sponsor', 'products', 'indication', 'phase'],
    trial_design: ['primary_endpoints', 'study_completion_status'],
    clinical_results: ['primary_endpoint_results', 'statistical_significance', 'clinical_effect_size', 'safety_findings', 'serious_adverse_events'],
    regulatory: ['fda_regulatory_pathway', 'special_designations', 'regulatory_submission_evidence', 'pdufa_date'],
    trial: ['trial_identity', 'trial_design', 'clinical_results', 'regulatory'],
  };
  const terminal = new Set(['VERIFIED', 'FAILED', 'INSUFFICIENT_EVIDENCE']);
  let previous = 0, parentChecks = 0, completeSeen = false;
  const hashes = new Set();
  for (const event of snapshot.events) {
    requireCheck(event.nct_id === NCT && event.run_id === runId && Number.isSafeInteger(event.sequence) && event.sequence === previous + 1, 'persisted_event_identity_and_order');
    previous = event.sequence;
    if (event.source && /^[a-f0-9]{64}$/i.test(event.source.sha256 || '')) hashes.add(event.source.sha256.toLowerCase());
    if (event.kind === 'node') {
      if (children[event.node_id] && terminal.has(event.status)) {
        const states = children[event.node_id].map(id => latest.get(id)?.status);
        requireCheck(states.every(state => terminal.has(state)), 'parent_follows_terminal_children');
        if (event.status === 'VERIFIED') requireCheck(states.every(state => state === 'VERIFIED'), 'verified_parent_requires_verified_children');
        parentChecks += 1;
      }
      if (event.node_id === 'main') requireCheck(event.value?.decision === 'ABSTAIN', 'main_abstains');
      latest.set(event.node_id, event);
    }
    if (event.kind === 'complete') {
      requireCheck(event.terminal === true && event.sequence === snapshot.events.length, 'terminal_event_is_last');
      requireCheck(event.value?.decision === 'ABSTAIN', 'completion_abstains');
      completeSeen = true;
    }
  }
  requireCheck(completeSeen && parentChecks > 0, 'persisted_bottom_up_completion');
  const leaves = [...latest.values()].filter(event => event.level === 4);
  const verified = leaves.filter(event => event.status === 'VERIFIED');
  requireCheck(verified.length > 0, 'verified_source_leaves_present');
  requireCheck(latest.get('nct_identifier')?.value === NCT, 'source_nct_matches_request');
  requireCheck(hashes.size > 0, 'source_hashes_present');
  result.counts.persisted_events = snapshot.events.length;
  result.counts.final_nodes = latest.size;
  result.counts.final_leaves = leaves.length;
  result.counts.verified_leaves = verified.length;
  result.counts.parent_dependency_checks = parentChecks;
  result.source_sha256 = [...hashes].sort();
  result.dossier_id = snapshot.dossier_id;
  result.checks.actual_workflow_source_verified = true;
  return latest;
}

async function inspectRenderedNodes(page, latest, checkPrefix) {
  // Values remain in memory solely for equality checks; never log or serialize them.
  const actual = await page.locator('#nct-live-processing').evaluate(section => {
    const rows = {};
    for (const article of section.querySelectorAll('article[data-node-id]')) {
      const value = article.querySelector(':scope > div');
      rows[article.getAttribute('data-node-id')] = {
        status: article.getAttribute('data-state'), value: value?.textContent ?? null,
        source_url: article.querySelector('a')?.href ?? null,
        source_sha256: article.querySelector('code')?.textContent ?? null,
      };
    }
    return rows;
  });
  requireCheck(Object.keys(actual).length === latest.size, checkPrefix + '_node_count_matches_snapshot');
  for (const [id, expected] of latest.entries()) {
    const row = actual[id];
    requireCheck(row && row.status === expected.status, checkPrefix + '_statuses_match_snapshot');
    if (expected.value === null || expected.value === undefined) {
      requireCheck(row.value === null, checkPrefix + '_missing_values_not_invented');
    } else if (typeof expected.value === 'string') {
      requireCheck(row.value === expected.value, checkPrefix + '_values_match_snapshot');
    } else {
      let parsed;
      try { parsed = JSON.parse(row.value); } catch { requireCheck(false, checkPrefix + '_values_match_snapshot'); }
      requireCheck(canonical(parsed) === canonical(expected.value), checkPrefix + '_values_match_snapshot');
    }
    if (expected.source) {
      requireCheck(row.source_url === expected.source.url && row.source_sha256 === expected.source.sha256, checkPrefix + '_citations_and_hashes_match_snapshot');
    }
  }
}

async function main() {
  const password = process.env.DASHBOARD_PASSWORD;
  delete process.env.DASHBOARD_PASSWORD;
  if (!password) {
    result.failure_code = 'MISSING_GITHUB_ACTIONS_SECRET_DASHBOARD_PASSWORD';
    record();
    console.error('INCOMPLETE: missing GitHub Actions secret DASHBOARD_PASSWORD');
    process.exitCode = 1;
    return;
  }
  let browser;
  try {
    phase = 'browser_launch';
    const { chromium } = require('playwright');
    browser = await chromium.launch({ headless: true });
    const context = await browser.newContext({ reducedMotion: 'no-preference' });
    phase = 'unauthenticated_api';
    const probe = await context.request.get(BASE + '/api/nct-stream/' + NCT + '/runs/00000000-0000-4000-8000-000000000000', { timeout: 30000, maxRedirects: 0 });
    requireCheck(probe.status() === 401, 'unauthenticated_snapshot_rejected_401');
    const page = await context.newPage();
    const network = { posts: 0, snapshots: 0, eventResponses: 0, badEventContentTypes: 0, nctConsoleErrors: 0, nctRuntimeErrors: 0, unexpectedNctNetworkErrors: 0 };
    page.on('console', message => {
      if (message.type() === 'error' && /nct-stream|nct-live-processing|NctLiveStream|Processing event/i.test(message.text())) network.nctConsoleErrors += 1;
    });
    page.on('pageerror', error => {
      if (/nct-stream|nct-live-processing|NctLiveStream|Processing event/i.test(String(error.stack || '') + String(error.message || ''))) network.nctRuntimeErrors += 1;
    });
    page.on('request', request => {
      const pathname = new URL(request.url()).pathname;
      if (!pathname.startsWith('/api/nct-stream/')) return;
      if (request.method() === 'POST') network.posts += 1;
      else if (!pathname.endsWith('/events')) network.snapshots += 1;
    });
    page.on('response', response => {
      const pathname = new URL(response.url()).pathname;
      if (!pathname.startsWith('/api/nct-stream/') || !pathname.endsWith('/events')) return;
      network.eventResponses += 1;
      if (!response.ok() || !(response.headers()['content-type'] || '').toLowerCase().startsWith('text/event-stream')) network.badEventContentTypes += 1;
    });
    page.on('requestfailed', request => {
      if (new URL(request.url()).pathname.startsWith('/api/nct-stream/') && !/ERR_ABORTED|NS_BINDING_ABORTED/.test(request.failure()?.errorText || '')) network.unexpectedNctNetworkErrors += 1;
    });
    phase = 'normal_application_login';
    await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('#password').waitFor({ state: 'visible', timeout: 30000 });
    await page.locator('#password').fill(password);
    const login = page.waitForResponse(response => new URL(response.url()).pathname === '/api/auth' && response.request().method() === 'POST', { timeout: 30000 });
    await page.getByRole('button', { name: 'Sign in', exact: true }).click();
    requireCheck((await login).status() === 200, 'normal_password_login_succeeded');
    const section = page.locator('#nct-live-processing');
    await section.waitFor({ state: 'visible', timeout: 45000 });
    // Explicitly verify the active dashboard section is on the PREDICTION surface.
    // Do not claim a tab click unless the deployed UI exposes a matching control.
    const predictionTab = page.getByRole('tab', { name: /prediction/i });
    const predictionLink = page.getByRole('link', { name: /^prediction$/i });
    const predictionButton = page.getByRole('button', { name: /^prediction$/i });
    if (await predictionTab.count()) {
      await predictionTab.first().click();
      requireCheck(await section.isVisible(), 'prediction_tab_live_panel_visible');
    } else if (await predictionButton.count()) {
      await predictionButton.first().click();
      await section.waitFor({ state: 'visible', timeout: 45000 });
      requireCheck(await section.isVisible(), 'prediction_tab_live_panel_visible');
    } else if (await predictionLink.count()) {
      await predictionLink.first().click();
      await section.waitFor({ state: 'visible', timeout: 45000 });
      requireCheck(await section.isVisible(), 'prediction_tab_live_panel_visible');
    } else {
      // Existing dashboard may render PREDICTION as a heading rather than a tab.
      requireCheck(false, 'prediction_tab_navigation_control_not_found');
    }
    requireCheck(await section.isVisible(), 'authenticated_component_rendered');
    await section.evaluate(section => {
      const observation = { loading_animation: false, pending_without_spinner: false, verified_leaf_before_terminal: false, verified_citation: false, verified_hash: false };
      const check = () => {
        const terminal = (section.querySelector('[role="status"]')?.textContent || '').includes('Processing run completed');
        const firstDetails = section.querySelector('details');
        for (const article of section.querySelectorAll('article[data-state="LOADING"]')) {
          const spinner = article.querySelector('.nct-processing-spinner');
          if (spinner && getComputedStyle(spinner).animationName !== 'none') observation.loading_animation = true;
        }
        if ([...section.querySelectorAll('article[data-state="PENDING"]')].some(article => !article.querySelector('.nct-processing-spinner'))) observation.pending_without_spinner = true;
        for (const article of firstDetails?.querySelectorAll('article[data-state="VERIFIED"]') || []) {
          if (!terminal) observation.verified_leaf_before_terminal = true;
          if (article.querySelector('a[href^="https://"]')) observation.verified_citation = true;
          if (/^[a-f0-9]{64}$/i.test(article.querySelector('code')?.textContent || '')) observation.verified_hash = true;
        }
      };
      const observer = new MutationObserver(check);
      observer.observe(section, { childList: true, subtree: true, attributes: true, characterData: true });
      window.__stage1LiveObservation = observation;
      check();
    });
    phase = 'live_trial_run';
    const createdResponse = page.waitForResponse(response => new URL(response.url()).pathname === '/api/nct-stream/' + NCT + '/runs' && response.request().method() === 'POST', { timeout: 45000 });
    await page.locator('#nct-live-input').fill(NCT);
    await section.getByRole('button', { name: 'Start processing', exact: true }).click();
    const created = await createdResponse;
    // Record only safe HTTP metadata on failure; never persist response bodies,
    // request headers, cookies, tokens, or other potentially sensitive data.
    if (!created.ok()) {
      result.counts.run_create_http_status = created.status();
      const retryAfter = created.headers()['retry-after'];
      result.checks.run_create_rate_limited = created.status() === 429;
      result.checks.run_create_auth_rejected = [401, 403].includes(created.status());
      result.checks.run_create_server_error = created.status() >= 500;
      result.checks.run_create_retry_after_present = typeof retryAfter === 'string';
      console.log('Stage 1 run creation HTTP status: ' + created.status());
    }
    requireCheck(created.ok(), 'run_created_through_authenticated_browser');
    const run = await created.json();
    requireCheck(run.nct_id === NCT && /^[A-Za-z0-9_-]{8,100}$/.test(run.run_id || '') && typeof run.dossier_id === 'string', 'new_run_identity');
    result.run_id = run.run_id;
    await section.locator('[role="status"]').filter({ hasText: 'Processing run completed.' }).waitFor({ state: 'visible', timeout: 150000 });
    const observed = await page.evaluate(() => window.__stage1LiveObservation);
    for (const [key, value] of Object.entries(observed || {})) requireCheck(value === true, 'observed_' + key);
    requireCheck(network.posts === 1 && network.eventResponses > 0 && network.badEventContentTypes === 0, 'browser_network_is_authenticated_sse');
    // Independently exercise browser-context SSE cursor resume against the same
    // authenticated persisted run. This verifies HTTP reconnection and dedupe;
    // it does not simulate a mid-stream UI network outage.
    phase = 'browser_context_sse_resume';
    const sseUrl = BASE + '/api/nct-stream/' + NCT + '/runs/' + run.run_id + '/events';
    const firstSse = await context.request.get(sseUrl, { timeout: 30000 });
    requireCheck(firstSse.status() === 200 && (firstSse.headers()['content-type'] || '').toLowerCase().includes('text/event-stream'), 'browser_context_sse_initial_200');
    const initialText = await firstSse.text();
    // SSE IDs are opaque cursor strings, not necessarily decimal integers.
    // Parse event blocks and compare replay to the original ordered suffix.
    const eventIds = body => body.split(/\\r?\\n\\r?\\n/).map(block => {
      const match = block.match(/^id:[ \\t]*(.+?)\\r?$/m);
      return match ? match[1].trim() : null;
    }).filter(Boolean);
    const ids = eventIds(initialText);
    result.counts.browser_context_initial_events = ids.length;
    requireCheck(ids.length > 1 && new Set(ids).size === ids.length, 'browser_context_sse_ordered_ids');
    const midpoint = Math.floor(ids.length / 2) - 1;
    const cursor = ids[midpoint];
    const resumedSse = await context.request.get(sseUrl, { headers: { 'Last-Event-ID': cursor }, timeout: 30000 });
    requireCheck(resumedSse.status() === 200, 'browser_context_sse_resume_200');
    const resumedText = await resumedSse.text();
    const resumedIds = eventIds(resumedText);
    requireCheck(resumedIds.length > 0 && new Set(resumedIds).size === resumedIds.length && !resumedIds.includes(cursor), 'browser_context_sse_resume_no_duplicate_ids');
    requireCheck(JSON.stringify(resumedIds) === JSON.stringify(ids.slice(midpoint + 1)), 'browser_context_sse_resume_reaches_terminal');
    result.counts.browser_context_resumed_events = resumedIds.length;

    phase = 'persisted_snapshot_comparison';
    const snapshotResponse = await context.request.get(BASE + '/api/nct-stream/' + NCT + '/runs/' + run.run_id, { timeout: 30000 });
    requireCheck(snapshotResponse.status() === 200, 'authenticated_snapshot_200');
    const snapshot = await snapshotResponse.json();
    const latest = summarizeSnapshot(snapshot, run.run_id);
    await inspectRenderedNodes(page, latest, 'initial_display');
    const pointer = await page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), POINTER_KEY);
    requireCheck(pointer && pointer.run_id === run.run_id && pointer.nct_id === NCT && Object.keys(pointer).sort().join(',') === 'nct_id,run_id', 'storage_contains_only_run_pointer');
    // Validate a fresh read-only dossier fingerprint if the snapshot exposes one.
    // This does not substitute for a direct persisted-dossier database checksum.
    if (typeof snapshot.dossier_sha256 === 'string') {
      requireCheck(/^[a-f0-9]{64}$/i.test(snapshot.dossier_sha256), 'snapshot_dossier_hash_format');
      result.checks.snapshot_dossier_hash_available = true;
    } else {
      result.checks.snapshot_dossier_hash_available = false;
    }
    const normalizedBefore = crypto.createHash('sha256').update(canonical(snapshot.events)).digest('hex');
    const postsBefore = network.posts;
    phase = 'reload_and_restore';
    await page.reload({ waitUntil: 'domcontentloaded', timeout: 60000 });
    await page.locator('#nct-live-processing [role="status"]').filter({ hasText: 'Saved completed processing run restored.' }).waitFor({ state: 'visible', timeout: 60000 });
    const restoredPointer = await page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), POINTER_KEY);
    requireCheck(restoredPointer?.run_id === run.run_id && restoredPointer?.nct_id === NCT, 'reload_uses_same_persisted_run');
    requireCheck(network.posts === postsBefore && network.snapshots > 0, 'reload_does_not_create_another_run');
    const restoredResponse = await context.request.get(BASE + '/api/nct-stream/' + NCT + '/runs/' + run.run_id, { timeout: 30000 });
    requireCheck(restoredResponse.status() === 200, 'restored_authenticated_snapshot_200');
    const restored = await restoredResponse.json();
    requireCheck(crypto.createHash('sha256').update(canonical(restored.events)).digest('hex') === normalizedBefore, 'persisted_events_unchanged_after_reload');
    await inspectRenderedNodes(page, latest, 'restored_display');
    result.counts.browser_run_posts = network.posts;
    result.counts.browser_snapshot_requests = network.snapshots;
    result.counts.browser_sse_responses = network.eventResponses;
    result.counts.nct_console_errors = network.nctConsoleErrors;
    result.counts.nct_runtime_errors = network.nctRuntimeErrors;
    result.counts.unexpected_nct_network_errors = network.unexpectedNctNetworkErrors;
    requireCheck(network.nctConsoleErrors === 0 && network.nctRuntimeErrors === 0 && network.unexpectedNctNetworkErrors === 0, 'no_unexpected_nct_runtime_errors');
    result.checks.no_prediction_or_trading_authorization = [...latest.values()].filter(e => e.node_id === 'main').every(e => e.value?.decision === 'ABSTAIN');
    result.status = 'PASS';
  } catch (error) {
    result.failure_code = error && typeof error.checkId === 'string' ? error.checkId : 'LIVE_CHECK_FAILED_AT_' + phase.toUpperCase();
    process.exitCode = 1;
  } finally {
    if (browser) await browser.close().catch(() => {});
    record();
  }
}

void main();
