"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

const source = fs.readFileSync(
  path.join(__dirname, "../app/api/scientific-assessment/route.ts"), "utf8",
);
const js = ts.transpileModule(source, { compilerOptions: {
  module: ts.ModuleKind.CommonJS,
  target: ts.ScriptTarget.ES2022,
}}).outputText;

const ID = "TRIAL|NCT12345678";
function makeRoute({ loggedIn = true, code = "science-integrated-v1",
                     upstreamStatus = 200, sample = null } = {}) {
  const calls = [];
  const instance = { exports: {} };
  const mockRequire = name => {
    if (name === "next/server") return {
      NextResponse: { json: (value, config = {}) => ({
        body: value, status: config.status ?? 200, headers: config.headers ?? {},
      }) },
    };
    if (name.endsWith("/lib/auth")) return {
      COOKIE_NAME: "test_session", authConfigured: () => true,
      hasSession: cookie => loggedIn && cookie === "session_token",
    };
    if (name.endsWith("/lib/read-only-warm-retry")) return {
      fetchReadOnlyWithWarmRetry: async (url, opts) => {
        calls.push({ url, opts });
        return {
          ok: upstreamStatus === 200,
          status: upstreamStatus,
          headers: { get: key =>
            key === "x-pdufa-scientific-api-contract" ? code : null },
          json: async () => sample ?? {
            exactId: ID, assessment: { overall_score: null },
            readinessGrades: null, investigation20: null,
          },
        };
      },
    };
    throw new Error("Unexpected module " + name);
  };
  new Function("require", "module", "exports", js)(
    mockRequire, instance, instance.exports,
  );
  return {
    calls,
    async request(exactId = ID, cookie = "session_token") {
      const url = new URL("https://preview.example/api/scientific-assessment");
      url.searchParams.set("exact_id", exactId);
      return instance.exports.GET({
        nextUrl: url,
        cookies: { get: () => cookie ? { value: cookie } : undefined },
      });
    },
  };
}

async function withEnv(fn, scienceBase = "https://science-review.example.org") {
  const old = {
    PDUFA_SCIENTIFIC_API_BASE_URL: process.env.PDUFA_SCIENTIFIC_API_BASE_URL,
    PDUFA_INTERNAL_API_KEY: process.env.PDUFA_INTERNAL_API_KEY,
    PDUFA_API_BASE_URL: process.env.PDUFA_API_BASE_URL,
  };
  if (scienceBase) process.env.PDUFA_SCIENTIFIC_API_BASE_URL = scienceBase;
  else delete process.env.PDUFA_SCIENTIFIC_API_BASE_URL;
  process.env.PDUFA_INTERNAL_API_KEY = "FAKE_TEST_KEY_DO_NOT_SHARE";
  process.env.PDUFA_API_BASE_URL = "https://normal-staging.example.org";
  try { await fn(); }
  finally {
    for (const [key, value] of Object.entries(old)) {
      if (value === undefined) delete process.env[key];
      else process.env[key] = value;
    }
  }
}

test("authenticated scientific preview GET requires matching integrated backend version", () => withEnv(async () => {
  const route = makeRoute();
  const result = await route.request();
  assert.equal(result.status, 200);
  assert.equal(result.body.exactId, ID);
  assert.equal(result.body.assessment.overall_score, null);
  assert.equal(result.headers["Cache-Control"], "private, no-store");
  assert.equal(route.calls.length, 1);
  assert.equal(route.calls[0].url,
    "https://science-review.example.org/api/scientific-assessment?exact_id=TRIAL%7CNCT12345678");
  assert.equal(route.calls[0].opts.cache, "no-store");
  assert.equal(route.calls[0].opts.headers["x-pdufa-internal-key"],
    process.env.PDUFA_INTERNAL_API_KEY);
  assert.doesNotMatch(JSON.stringify(result.body), /FAKE_TEST_KEY/);
}));

test("old Render science backend cannot inject unverified scores into trial UI", () => withEnv(async () => {
  const route = makeRoute({
    code: null,
    sample: { exactId: ID, assessment: { overall_score: 99 }, fdaApprovalProbability: 95 },
  });
  const result = await route.request();
  assert.equal(result.status, 503);
  assert.equal(result.body.error, "Integrated scientific backend release not deployed");
  assert.doesNotMatch(JSON.stringify(result.body), /\b95\b|\b99\b/);
}));

test("unknown backend version is rejected even if still live", () => withEnv(async () => {
  const route = makeRoute({ code: "science-integrated-v0" });
  const result = await route.request();
  assert.equal(result.status, 503);
  assert.equal(result.body.error, "Integrated scientific backend release not deployed");
}));

test("anonymous access blocked before any backend request", () => withEnv(async () => {
  const route = makeRoute({ loggedIn: false });
  const result = await route.request();
  assert.equal(result.status, 401);
  assert.equal(route.calls.length, 0);
}));

test("normal staging backend never substitutes for unavailable isolated scientific backend", () => withEnv(async () => {
  const route = makeRoute();
  const result = await route.request();
  assert.equal(result.status, 503);
  assert.equal(route.calls.length, 0);
}, null));

test("upstream auth failure never claims release readiness", () => withEnv(async () => {
  const route = makeRoute({ upstreamStatus: 401 });
  const result = await route.request();
  assert.equal(result.status, 401);
  assert.deepEqual(result.body, { error: "Scientific assessment unavailable" });
}));
