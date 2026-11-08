const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const app = path.resolve(__dirname, "../app");
const page = fs.readFileSync(path.join(app, "medical-intelligence-preview/page.tsx"), "utf8");
const client = fs.readFileSync(path.join(app, "medical-intelligence-preview/OnDemandRegistryResearch.tsx"), "utf8");
const api = fs.readFileSync(path.join(app, "api/medical-intelligence-preview/run/route.ts"), "utf8");

test("opening a Deep Medical Intelligence page never fetches live registry data", () => {
  assert.doesNotMatch(page, /await\s+(fetch|getRegistryStudy)\s*\(/);
  assert.match(page, /View saved research/);
  assert.match(page, /<OnDemandRegistryResearch/);
});
test("user click is the only live lookup trigger in the client component", () => {
  assert.match(client, /onClick=\{run\}/);
  assert.match(client, /method:\s*"POST"/);
  assert.match(client, /Run External Source Check/);
  assert.match(client, /"IDLE"/);
});
test("registry collection endpoint is POST-only, exact NCT and non-predictive", () => {
  assert.match(api, /export async function POST/);
  assert.doesNotMatch(api, /export async function GET/);
  assert.match(api, /focus.records.some/);
  assert.match(api, /cache:\s*"no-store"/);
  assert.match(api, /decision:\s*"INSUFFICIENT_EVIDENCE"/);
});
