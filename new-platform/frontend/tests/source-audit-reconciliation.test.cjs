const test = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");

const report = JSON.parse(fs.readFileSync(path.join(__dirname, "..", "..", "..", "data", "pdufa_source_report.json"), "utf8"));

test("source verification accounting preserves conflicts and reconciles to due", () => {
  const fields = ["findings_verified", "findings_unresolved", "findings_conflicted", "findings_unavailable", "findings_not_applicable"];
  for (const key of ["findings_due", ...fields]) {
    assert.equal(Number.isSafeInteger(report[key]) && report[key] >= 0, true, key);
  }
  assert.equal(fields.reduce((sum, key) => sum + report[key], 0), report.findings_due,
    "Count all conflicted claims separately; never silently omit or reclassify source findings");
});

test("incomplete source families cannot silently produce a full coverage certificate", () => {
  assert.equal(typeof report.full_coverage_verified, "boolean");
  assert.ok(Array.isArray(report.missing_required_source_families));
  if (report.missing_required_source_families.length > 0) {
    assert.equal(report.full_coverage_verified, false);
  }
  if (report.full_coverage_verified) {
    assert.equal(report.missing_required_source_families.length, 0);
    assert.equal(report.findings_unresolved + report.findings_conflicted, 0);
  }
});
