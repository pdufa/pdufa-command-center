"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, file
);
const { scienceInstallationGates } = require("../lib/scientific-installation-gates.ts");

const checked = "CHECKED_IN_SESSION";
const unchecked = "NOT_CHECKED_IN_SESSION";
const blocked = "INDEPENDENT_VERIFICATION_REQUIRED";
const states = (gates) => gates.map(g => g.status);

test("without user-triggered reads no installation gate can claim verification", () => {
  const gates = scienceInstallationGates(null, false);
  assert.equal(gates.length, 7);
  assert.deepEqual(states(gates), [unchecked, unchecked, blocked, blocked, blocked, blocked, blocked]);
});

test("stale or unavailable published source cannot pass even with pilot connection", () => {
  const gates = scienceInstallationGates({ status: "SOURCE_NOT_FRESHLY_VERIFIED" }, true);
  assert.deepEqual(states(gates), [unchecked, checked, blocked, blocked, blocked, blocked, blocked]);
});

test("two limited browser checks never promote scientific or release authority", () => {
  const gates = scienceInstallationGates({ status: "PUBLISHED_SNAPSHOT_AUDIT" }, true);
  assert.deepEqual(states(gates), [checked, checked, blocked, blocked, blocked, blocked, blocked]);
  assert.equal(gates.filter(g => g.status === checked).length, 2);
  assert.ok(gates.every(g => !/APPROVED|READY_TO_RELEASE|SCIENTIFIC_SUCCESS/.test(g.status)));
});

test("checklist is collapsible, read-only, and not a background scanner", () => {
  const page = fs.readFileSync(path.join(__dirname, "../app/science/coverage/page.tsx"), "utf8");
  assert.match(page, /Science installation release checklist/);
  assert.match(page, /<details[\s>]/);
  assert.match(page, /scienceInstallationGates\(data, connectionSucceeded\)/);
  assert.match(page, /Independent verification required/);
  assert.doesNotMatch(page, /startScan\(|placeOrder\(|approveEvidence\(|startBatchImport\(/);
});
