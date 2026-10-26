const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const page = fs.readFileSync(path.join(__dirname, "..", "app", "installation-audit", "page.tsx"), "utf8");
const lane = fs.readFileSync(path.join(__dirname, "..", "app", "installation-audit", "IndependentInstallationLane.tsx"), "utf8");

test("main installation audit exposes a separate owner-deferred key lane", () => {
  assert.match(page, /import IndependentInstallationLane from ".\/IndependentInstallationLane"/);
  assert.match(page, /<IndependentInstallationLane \/>/);
  assert.match(lane, /deferred by the owner, not completed/);
  assert.match(lane, /independent custody keyholder/);
  assert.match(lane, /not live probes/);
});

test("key-independent installation checkpoint cites bounded, pinned technical proof", () => {
  assert.match(lane, /16 of 16 GitHub Actions workflows passed/);
  assert.match(lane, /ec48768d69ce5548c5edf770ebba04cc492f4568/);
  assert.match(lane, /Vercel reported READY/);
  assert.match(lane, /not production SCIENCE release authorization/);
  assert.match(lane, /complete 8 PM Pacific scan execution and notifications/);
  assert.match(lane, /No FDA approval probability or completed scientific readiness is asserted/);
});

test("key pause section makes no reviewer, trading, scan or status mutations", () => {
  assert.doesNotMatch(lane, /\\bonClick=|\\bonSubmit=|\\bfetch\\(|\\buseEffect\\(|\\bPOST\\b|\\bPUT\\b/);
  assert.doesNotMatch(lane, /private[_-]key[_-]file|BEGIN PRIVATE KEY|@gmail\\.com/);
  assert.match(lane, /This section is read-only and does not promote any acceptance gate/);
  assert.match(lane, /GEM JR\/GEM FS\/FA associations/);
});
