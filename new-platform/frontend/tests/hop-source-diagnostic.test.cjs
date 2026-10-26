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
const { safeHopDiagnostic } = require("../lib/hop-source-diagnostic.ts");

test("authenticated HOP credential failure maps to safe resolution, never to claim of success", () => {
  const result = safeHopDiagnostic(503, { reason: "SOURCE_AUTHENTICATION_FAILED" });
  assert.match(result, /server-to-server credential/);
  assert.match(result, /production/);
  assert.match(result, /NOT VERIFIED/);
  assert.doesNotMatch(result, /credentials are valid|prediction enabled/);
});

test("known 503 reason codes have bounded actionable messages", () => {
  for (const reason of [
    "SOURCE_UNREACHABLE", "SOURCE_ROUTE_MISSING", "SOURCE_HTTP_ERROR",
    "SOURCE_INVALID_RESPONSE", "SOURCE_AUTHENTICATION_FAILED",
  ]) {
    const message = safeHopDiagnostic(503, { reason });
    assert.ok(message.length > 70);
    assert.match(message, /NOT VERIFIED/);
    assert.match(message, /no FDA prediction is enabled/);
  }
});

test("arbitrary upstream secrets and unexpected response fields never escape to users", () => {
  const secret = "SECRET_DO_NOT_LEAK_123456";
  for (const x of [
    null, "", [], { error: secret }, { reason: secret }, { reason: { value: secret } },
    { reason: "SOURCE_AUTHENTICATION_FAILED", error: secret, debug: secret },
    { reason: "__proto__", message: secret }, { reason: "constructor", message: secret },
  ]) {
    assert.doesNotMatch(safeHopDiagnostic(503, x), /SECRET_DO_NOT_LEAK/);
  }
  assert.doesNotMatch(safeHopDiagnostic(200, { reason: "SOURCE_UNREACHABLE", message: secret }), /SECRET_DO_NOT_LEAK/);
  assert.doesNotMatch(safeHopDiagnostic(502, { error: secret }), /SECRET_DO_NOT_LEAK/);
});

test("non-503 responses and unauthenticated requests stay independently classified", () => {
  assert.match(safeHopDiagnostic(401, { reason: "SOURCE_AUTHENTICATION_FAILED" }), /Sign in/);
  assert.match(safeHopDiagnostic(403, { reason: "SOURCE_AUTHENTICATION_FAILED" }), /permission/);
  assert.match(safeHopDiagnostic(502, { reason: "SOURCE_AUTHENTICATION_FAILED" }), /HTTP 502/);
  assert.match(safeHopDiagnostic(-7, {}), /HTTP unknown/);
  assert.match(safeHopDiagnostic(503, { reason: "INVALID" }), /not verified/);
});

test("installed tracker fetches authenticated read-only OUTCOME once and shows only sanitized reason", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/installation-audit/ScientificOutcomeLive.tsx"), "utf8");
  assert.match(ui, /safeHopDiagnostic\(response.status, payload\)/);
  assert.match(ui, /read\("\/api\/hop\/readiness", true\)\.then\(auditOutcomeStatus\)/);
  assert.match(ui, /cache:"no-store"/);
  assert.match(ui, /Certification: NOT VALIDATED/);
  assert.match(ui, /Historical verification counts are withheld/);
  assert.doesNotMatch(ui, /PDUFA_INTERNAL_API_KEY|PDUFA_HOP_INTERNAL_API_KEY|placeTrade|saveGrade|runScan/);
});
