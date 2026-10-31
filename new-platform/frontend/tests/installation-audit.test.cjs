const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const tracker = fs.readFileSync(path.join(__dirname, "..", "app", "installation-audit", "page.tsx"), "utf8");
const required = [
  "Core Platform", "Pipeline", "POOL / PIPELINE", "Scientific Assessment",
  "Historical Trial Database", "Prediction Engine", "Evidence Verification",
  "Regulatory Intelligence", "Investment Analysis", "Nightly Scanning",
  "Results & Reporting", "Automation", "Backup & Recovery",
  "Prediction Validation", "Final Acceptance",
];

test("SYSTEM STATUS has all 15 distinct installation sections", () => {
  const names = [...tracker.matchAll(/component: "([^"]+)"/g)].map(m => m[1]);
  assert.deepEqual(names, required);
  assert.equal(new Set(names).size, 15);
});

test("installation checks retain independent code, deployment, runtime and evidence gates", () => {
  const rows = tracker.split("\n").filter(line => line.trim().startsWith("{ component: "));
  assert.equal(rows.length, 15);
  for (const row of rows) {
    for (const key of ["requirement", "code", "deployment", "runtime", "evidence", "blocker", "lastVerified", "source", "sourceLabel"]) {
      assert.match(row, new RegExp("\\b" + key + ": "));
    }
    assert.match(row, /runtime: "(Not verified|Partial|Verified)"/);
    assert.doesNotMatch(row, /evidence: "Evidence verified"/);
  }
  const core = rows.find(row => row.includes('component: "Core Platform"'));
  assert.match(core, /runtime: "Partial"/);
  assert.equal(rows.filter(row => /runtime: "Partial"/.test(row)).length, 4);
});

test("dated, incomplete source audit is not misrepresented as qualified Pipeline or full scientific readiness", () => {
  assert.match(tracker, /Latest saved RESULTS:<\/strong> October 25, 2026/);
  assert.match(tracker, /run 40263199452/);
  assert.match(tracker, /0 tracked records changed/);
  assert.match(tracker, /Qualified Pipeline and FDA special-designation totals remain unknown/);
  assert.match(tracker, /995\/1121 verified/);
  assert.match(tracker, /21 unresolved, 2 conflicted, 93 unavailable and 10 not applicable/);
  assert.match(tracker, /995 \+ 21 \+ 2 \+ 93 \+ 10 = 1,121/);
  assert.match(tracker, /required SEC and FINANCIAL verification is still missing/);
  assert.match(tracker, /sourceAudit/);
  assert.match(tracker, /two conflicted checks are omitted from that short note/);
  assert.match(tracker, /Same-run source reconciliation/);
  assert.doesNotMatch(tracker, /Latest saved RESULTS:<\/strong> October 24, 2026/);
  assert.match(tracker, /not Pipeline qualified/);
  assert.match(tracker, /FDA-labelled historical outcomes/);
  assert.match(tracker, /40 assessments/);
  assert.match(tracker, /Implementation-stage counts are reported separately from verified acceptance/);
  assert.match(tracker, /Full acceptance requires runtime verification and applicable evidence verification/);
});

test("tracker stays read-only and never triggers scans, trades or scoring", () => {
  assert.doesNotMatch(tracker, /\bonClick=|\bonSubmit=|\bfetch\(|\buseEffect\(/);
  assert.match(tracker, /this page does not trigger scans, rescoring, notifications, orders or trades/);
});

test("OUTCOME connection success is documented without claiming validated FDA predictions", () => {
  assert.match(tracker, /OUTCOME source connection verified on October 25, 2026 at 6:37 PM Pacific/);
  assert.match(tracker, /authenticated production evidence request returned HTTP 200/);
  assert.match(tracker, /0 independently verified review-cycle outcomes/);
  assert.match(tracker, /incomplete approval\/nonapproval decision denominator/);
  assert.match(tracker, /no established time-forward calibration/);
  assert.match(tracker, /FDA approval probabilities remain unavailable/);
  assert.doesNotMatch(tracker, /blocked by an authenticated source-connection failure/);
  // Read-only HOP connectivity is not itself prediction validation.
  const row = tracker.split(String.fromCharCode(10)).find(x => x.includes('component: "Prediction Validation"'));
  assert.match(row, /runtime: "Not verified"/);
  assert.match(row, /evidence: "Partial"/);
});

test("technical installation does not require a human reviewer or encryption-key handoff", () => {
  assert.match(tracker, /No mandatory human reviewer enrollment, reviewer keys or reviewer handoff is required/);
  assert.match(tracker, /Scientific evidence and prediction validation remain a separate research requirement/);
  assert.match(tracker, /reproducible source-level validation/);
  assert.match(tracker, /These data-validation tasks do not require reviewer enrollment as an installation prerequisite/);
  assert.doesNotMatch(tracker, /independent reviewer signoffs must be verified/);
  assert.doesNotMatch(tracker, /with independently authenticated reviewers/);
  assert.match(tracker, /FDA approval probabilities remain unavailable/);
  const rows = [...tracker.matchAll(/component: "([^"]+)"/g)].map(m => m[1]);
  assert.equal(rows.length, 15);
});

test("MAIN final acceptance consistently follows the independent technical scope",()=>{
  const final=tracker.split("\n").find(line=>line.includes('component: "Final Acceptance"'));
  assert.match(final,/Technical MAIN production verification/);
  assert.match(final,/SCIENCE and OUTCOME readiness are tracked separately/);
  assert.match(final,/main-technical-installation-scope-20261025\.md/);
  assert.doesNotMatch(final,/complete science evidence|validated outcomes/);
  assert.match(final,/runtime: "Not verified", evidence: "Not verified"/);
  assert.match(tracker,/mainTechnicalAcceptance\(checks\)/);
  assert.match(tracker,/SCIENCE and OUTCOME research completion is not required for technical acceptance/);
});

test("nightly and results runtime use observed evidence without clearing source gates", () => {
  const lines = tracker.split("\n").filter(x => x.trim().startsWith("{ component: "));
  const nightly = lines.find(x => x.includes('component: "Nightly Scanning"'));
  const results = lines.find(x => x.includes('component: "Results & Reporting"'));
  assert.match(nightly, /runtime: "Partial", evidence: "Partial"/);
  assert.match(nightly, /20:15 PDT/);
  assert.match(nightly, /40263199452/);
  assert.match(nightly, /schedule punctuality and all regulatory\/financial source coverage are not certified/);
  assert.match(results, /runtime: "Partial", evidence: "Partial"/);
  assert.match(results, /qualified Pipeline and FDA designation counts remain unknown/);
  assert.doesNotMatch(nightly, /runtime: "Verified"/);
  assert.doesNotMatch(results, /runtime: "Verified"/);
});

test("outdated public ticker identities are visibly held with dated Nasdaq corporate-action sources", () => {
  assert.match(tracker,/Company-identity exceptions — source research, October 26/);
  assert.match(tracker,/2 recorded SEC FILINGS_INVENTORY conflicts remain OPEN/);
  assert.match(tracker,/QNCX to IRLA effective October 12, 2026/);
  assert.match(tracker,/ECA2026-724/);
  assert.match(tracker,/TBPH trading was suspended effective September 24, 2026/);
  assert.match(tracker,/ECA2026-668/);
  assert.match(tracker,/before qualification/);
  assert.match(tracker,/current ticker validity and public-company eligibility remain unverified/);
  assert.match(tracker,/does not alter research restrictions or historical records/);
  assert.doesNotMatch(tracker,/No new listing, trade approval or source verification is inferred\.\s*\{false\}/);
});
