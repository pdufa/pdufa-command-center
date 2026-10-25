"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const SCOPED_READ_ROUTES = [
  "../app/api/scientific-assessment/route.ts",
  "../app/api/scientific-assessment/connection/route.ts",
  "../app/api/scientific-assessment/pilot/keynote024/route.ts",
  "../app/api/scientific-assessment/archived/[nctId]/route.ts",
];

test("all scientific evidence proxy reads use isolated preview credentials, never ordinary API key", () => {
  for (const relative of SCOPED_READ_ROUTES) {
    const source = fs.readFileSync(path.join(__dirname, relative), "utf8");
    assert.match(source, /const key = process.env.PDUFA_SCIENTIFIC_PREVIEW_READ_KEY;/,
      relative + " must require a branch-scoped scientific key");
    assert.doesNotMatch(source, /process.env.PDUFA_INTERNAL_API_KEY/,
      relative + " must not fall back to the ordinary dashboard internal key");
    assert.match(source, /process.env.PDUFA_SCIENTIFIC_API_BASE_URL/,
      relative + " must never use the ordinary dashboard API base");
    assert.match(source, /authConfigured\(\).*hasSession/s,
      relative + " must require a signed-in dashboard user");
    assert.match(source, /"x-pdufa-internal-key": key/,
      relative + " must pass its dedicated key only as a request header");
    assert.match(source, /cache: "no-store"/);
    assert.doesNotMatch(source, /method:\s*["'](?:POST|PUT|PATCH|DELETE)["']/);
  }
});
