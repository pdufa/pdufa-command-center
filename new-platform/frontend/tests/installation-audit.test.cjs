const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const tracker = fs.readFileSync(path.join(__dirname, "..", "app", "installation-audit", "page.tsx"), "utf8");
const required = [
  "Core Platform", "Pipeline", "GEM JR / GEM / WT", "Scientific Assessment",
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
  assert.equal(rows.filter(row => /runtime: "Partial"/.test(row)).length, 1);
});

test("dated, incomplete source audit is not misrepresented as qualified Pipeline or full scientific readiness", () => {
  assert.match(tracker, /993\/1121 verified/);
  assert.match(tracker, /995\/1121 verified/);
  assert.match(tracker, /21 unresolved, 2 conflicted, 93 unavailable and 10 not applicable/);
  assert.match(tracker, /995 \+ 21 \+ 2 \+ 93 \+ 10 = 1,121/);
  assert.match(tracker, /required SEC and FINANCIAL verification is still missing/);
  assert.match(tracker, /sourceAudit/);
  assert.match(tracker, /two checks have no separately stated classification/);
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
