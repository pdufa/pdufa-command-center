"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const fs = require("node:fs");
const ts = require("typescript");

const routeFile = path.join(__dirname, "../app/api/scientific-assessment/connection/route.ts");
const compiled = ts.transpileModule(fs.readFileSync(routeFile, "utf8"), {
  compilerOptions: {
    module: ts.ModuleKind.CommonJS,
    target: ts.ScriptTarget.ES2022,
    esModuleInterop: true,
  },
}).outputText;
const ID = "TRIAL|NCT02142738";

function makeRoute({ authenticated = true, configured = true, response, rejectFetch = false } = {}) {
  const calls = [];
  const mod = { exports: {} };
  const sandboxRequire = name => {
    if (name === "next/server") return {
      NextResponse: { json: (payload, opts = {}) => ({
        body: payload,
        status: opts.status ?? 200,
        headers: opts.headers ?? {},
      }) },
    };
    if (name.endsWith("/lib/auth")) return {
      COOKIE_NAME: "test_session",
      authConfigured: () => configured,
      hasSession: token => authenticated && token === "active-test-cookie",
    };
    if (name.endsWith("/lib/read-only-warm-retry")) return {
      fetchReadOnlyWithWarmRetry: async (url, init) => {
        calls.push({ url, init });
        if (rejectFetch) throw new Error("network unavailable");
        return response ?? {
          ok: true, status: 200,
          json: async () => ({
            exactId: ID,
            independentOfQualificationPresets: true,
            assessment: { overall_score: null },
            registryEvidence: { source: "checksum_verified_registry_only" },
          }),
        };
      },
    };
    throw new Error("Unrecognized route dependency: " + name);
  };
  new Function("require", "module", "exports", compiled)(
    sandboxRequire, mod, mod.exports,
  );
  const GET = mod.exports.GET;
  async function request(exactId = ID, cookie = "active-test-cookie") {
    const url = new URL("https://preview.example/api/scientific-assessment/connection");
    url.searchParams.set("exact_id", exactId);
    return GET({ nextUrl: url, cookies: { get: () => cookie ? { value: cookie } : undefined } });
  }
  return { request, calls };
}

async function withEnv(run, base = "https://isolated-science.example.org") {
  const before = {
    PDUFA_SCIENTIFIC_API_BASE_URL: process.env.PDUFA_SCIENTIFIC_API_BASE_URL,
    PDUFA_INTERNAL_API_KEY: process.env.PDUFA_INTERNAL_API_KEY,
    PDUFA_API_BASE_URL: process.env.PDUFA_API_BASE_URL,
  };
  if (base === null) delete process.env.PDUFA_SCIENTIFIC_API_BASE_URL;
  else process.env.PDUFA_SCIENTIFIC_API_BASE_URL = base;
  process.env.PDUFA_INTERNAL_API_KEY = "TEST_INTERNAL_KEY_NOT_A_REAL_SECRET";
  process.env.PDUFA_API_BASE_URL = "https://ordinary-dashboard.example.org";
  try { return await run(); }
  finally {
    for (const [key, value] of Object.entries(before)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
}

test("anonymous request is rejected before reaching the isolated service", async () => withEnv(async () => {
  const route = makeRoute({ authenticated: false });
  const result = await route.request();
  assert.equal(result.status, 401);
  assert.equal(result.body.connection, "authentication_required");
  assert.equal(route.calls.length, 0);
  assert.equal(result.headers["Cache-Control"], "private, no-store");
}));

test("only exact TRIAL|NCT######## identifiers may trigger the remote GET", async () => withEnv(async () => {
  const route = makeRoute();
  for (const malformed of ["", "TRIAL|INVALID", "TRIAL|NCT02142738?admin=true", "PDUFA|ABC", "https://example.test"]) {
    const result = await route.request(malformed);
    assert.equal(result.status, 422);
  }
  assert.equal(route.calls.length, 0);
}));

test("ordinary dashboard API can never replace absent isolated scientific base", async () => withEnv(async () => {
  const route = makeRoute();
  const result = await route.request();
  assert.equal(result.status, 503);
  assert.equal(result.body.connection, "scientific_backend_not_configured");
  assert.equal(route.calls.length, 0);
}, null));

test("authenticated isolated GET proves exact-trial connection without publishing scores", async () => withEnv(async () => {
  const route = makeRoute();
  const result = await route.request();
  assert.equal(route.calls.length, 1);
  assert.equal(route.calls[0].url,
    "https://isolated-science.example.org/api/scientific-assessment?exact_id=TRIAL%7CNCT02142738");
  assert.equal(route.calls[0].init.headers["x-pdufa-internal-key"], process.env.PDUFA_INTERNAL_API_KEY);
  assert.equal(route.calls[0].init.cache, "no-store");
  assert.equal(result.status, 200);
  assert.equal(result.body.connection, "connected");
  assert.equal(result.body.exactTrialIdentityMatched, true);
  assert.equal(result.body.archivedRecordPresent, true);
  assert.equal(result.body.approvalProbability, null);
  assert.equal(result.body.scoresAssignedByConnectionTest, false);
  assert.equal(result.headers["Cache-Control"], "private, no-store");
  assert.doesNotMatch(JSON.stringify(result.body), /TEST_INTERNAL_KEY|checksum_verified_registry_only/);
}));

test("an upstream internal credential failure does not count as connectivity success", async () => withEnv(async () => {
  const route = makeRoute({ response: { ok: false, status: 401 } });
  const result = await route.request();
  assert.equal(result.status, 502);
  assert.equal(result.body.connection, "scientific_backend_authorization_failed");
}));

test("a forged trial identity or missing preset-isolation contract fails closed", async () => withEnv(async () => {
  for (const body of [
    { exactId: "TRIAL|NCT04280705", independentOfQualificationPresets: true, assessment: {} },
    { exactId: ID, independentOfQualificationPresets: false, assessment: {} },
    { exactId: ID, independentOfQualificationPresets: true, assessment: null },
  ]) {
    const route = makeRoute({ response: { ok: true, status: 200, json: async () => body } });
    const result = await route.request();
    assert.equal(result.status, 503);
    assert.equal(result.body.connection, "scientific_backend_identity_mismatch");
  }
}));

test("a network failure is unavailable, not a negative clinical assessment", async () => withEnv(async () => {
  const route = makeRoute({ rejectFetch: true });
  const result = await route.request();
  assert.equal(result.status, 503);
  assert.equal(result.body.connection, "scientific_backend_unreachable");
  assert.ok(!Object.prototype.hasOwnProperty.call(result.body, "fdaApprovalProbability"));
}));
