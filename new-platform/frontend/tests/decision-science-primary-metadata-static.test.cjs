const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const parser = fs.readFileSync(path.join(__dirname, "../lib/decision-science-investigation.ts"), "utf8");
test("science parser recognizes primary trial metadata", () => {
  assert.match(parser, /primaryTrial/);
  assert.match(parser, /validatePrimaryTrialSourceIdentity/);
});
test("science parser preserves legacy source fields", () => {
  for (const field of ["url", "publishedAt", "observedAt", "independentlyReviewed"]) {
    assert.ok(parser.includes(field));
  }
});
