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
    assert.match(row, /runtime: "Not verified"/);
    assert.doesNotMatch(row, /evidence: "Evidence verified"/);
  }
});

test("dated, incomplete source audit is not misrepresented as qualified Pipeline or full scientific readiness", () => {
  assert.match(tracker, /993\/1121 verified/);
  assert.match(tracker, /two checks have no separately stated classification/);
  assert.match(tracker, /not Pipeline qualified/);
  assert.match(tracker, /FDA-labelled historical outcomes/);
  assert.match(tracker, /40 assessments/);
  assert.match(tracker, /No numerical installation percentage is asserted/);
});

test("tracker stays read-only and never triggers scans, trades or scoring", () => {
  assert.doesNotMatch(tracker, /\bonClick=|\bonSubmit=|\bfetch\(|\buseEffect\(/);
  assert.match(tracker, /this page does not trigger scans, rescoring, notifications, orders or trades/);
});
