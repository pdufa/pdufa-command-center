"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");

const routes = [
  "app/api/scientific-assessment/route.ts",
  "app/api/scientific-assessment/pilot/keynote024/route.ts",
  "app/api/scientific-assessment/archived/[nctId]/route.ts",
];

for (const route of routes) {
  test(route + " uses the isolated scientific service and never falls back to ordinary PIPELINE API", () => {
    const source = fs.readFileSync(path.join(__dirname, "..", route), "utf8");
    assert.match(source, /process\.env\.PDUFA_SCIENTIFIC_API_BASE_URL/);
    assert.doesNotMatch(source, /process\.env\.PDUFA_API_BASE_URL/);
    assert.match(source, /authConfigured\(\)/);
    assert.match(source, /hasSession\(/);
    assert.match(source, /cache: "no-store"/);
    assert.match(source, /if \(!base\?\.startsWith\("https:\/\/"\) \|\| !key\)/);
  });
}
