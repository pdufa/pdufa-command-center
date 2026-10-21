const test = require('node:test');
const assert = require('node:assert/strict');
const { overallHealth, savedCheck, emailHealth, scoringHealth, clinicalHealth, sourceHealth } = require('../lib/site-health.ts');
const now = Date.parse('2026-10-21T13:00:00Z');
const dated = { checked_at_utc: '2026-10-21T05:00:00Z' };
const check = state => ({state});
test('Combined color never averages failure or unknown checks into green', () => {
  assert.equal(overallHealth(['good','good'].map(check)), 'good');
  assert.equal(overallHealth(['good','warning'].map(check)), 'warning');
  assert.equal(overallHealth(['good','unknown'].map(check)), 'warning');
  assert.equal(overallHealth([...Array(20).fill(check('good')), check('failed')]), 'failed');
  assert.equal(overallHealth([check('unknown')]), 'unknown');
  assert.equal(overallHealth([]), 'unknown');
});
test('PDUFA verified zero differs from missing counts or unsafe email scope', () => {
  const mail = {...dated, scope:'PDUFA_ONLY_EXCLUDING_INBOX_TRASH_SPAM', status:'CHECKED', total_count:0, unread_count:0};
  assert.equal(savedCheck('email','PDUFA',mail,now,emailHealth).state,'good');
  assert.match(emailHealth(mail).summary,/0 emails/);
  for (const patch of [{scope:'ALL'}, {status:'UNAVAILABLE'}, {total_count:null}, {unread_count:1}, {total_count:-1}]) {
    assert.equal(emailHealth({...mail,...patch}).state,'unknown');
  }
  assert.equal(savedCheck('email','PDUFA',null,now,emailHealth).state,'unknown');
});
test('Stale reports cannot retain a green state', () => {
  const mail = {scope:'PDUFA_ONLY_EXCLUDING_INBOX_TRASH_SPAM',status:'CHECKED',total_count:5,unread_count:1};
  for (const checked_at_utc of ['2026-10-19T01:00:00Z','2026-10-23T01:00:00Z']) {
    assert.equal(savedCheck('email','PDUFA',{...mail,checked_at_utc},now,emailHealth).state,'warning');
  }
});
test('Clinical job completion is independent of full source coverage and scoring', () => {
  assert.equal(clinicalHealth({scans:Array(3).fill({collector_status:'COMPLETE'})}).state,'good');
  assert.equal(clinicalHealth({scans:[{collector_status:'FAILED'}]}).state,'failed');
  assert.equal(sourceHealth({status:'PARTIAL',full_coverage_verified:false,required_findings_unresolved:23}).state,'warning');
  assert.equal(scoringHealth({status:'REVIEW_REQUIRED',counts:{data_gaps:4}}).state,'warning');
  assert.equal(scoringHealth({status:'COMPLETE',counts:{data_gaps:0}}).state,'good');
});
