const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");

require.extensions[".ts"] = (module, filename) => module._compile(ts.transpileModule(
  fs.readFileSync(filename, "utf8"),
  { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true } },
).outputText, filename);

const { NextRequest } = require("next/server");
const auth = require("../lib/auth.ts");
const { normalizeHopReadiness } = require("../lib/hop-readiness.ts");
const { hopBackendBase } = require("../lib/hop-backend.ts");
const route = require("../app/api/hop/readiness/route.ts");

function sourceFixture() {
  return {
    status: "RESEARCH_ONLY",
    published_crl_source: { published_letter_records: 458, fda_export_date: "2026-10-21" },
    approved_registry_source: { application_records: 29416, source_export_date: "2026-10-23" },
    historical_staged: 1,
    historical_model_eligible: 0,
    historical_training_data_connected: false,
    model_validated: false,
    prediction_available: false,
    prediction_probability: null,
    fda_page_review_worksheet: { published_letter_review_rows: 154, independently_verified_review_cycle_outcomes: 0 },
  };
}

test("HOP source projection cannot become an approval probability or verified cohort", () => {
  const source = sourceFixture();
  const out = normalizeHopReadiness(source, "2026-10-25T20:00:00Z");
  assert.equal(out.publishedLetters, 458);
  assert.equal(out.approvedApplications, 29416);
  assert.equal(out.sourcePageReviewRows, 154);
  assert.equal(out.independentlyVerifiedReviewCycles, 0);
  assert.equal(out.modelEligibleReviewCycles, 0);
  assert.equal(out.probability, null);
  assert.equal(out.predictionAvailable, false);
  assert.equal(out.denominatorComplete, false);
  assert.equal(out.checkedAt, "2026-10-25T20:00:00Z");
  for (const mutate of [
    x => x.prediction_available = true,
    x => x.model_validated = true,
    x => x.prediction_probability = 0.8,
    x => x.historical_model_eligible = 7,
    x => x.historical_training_data_connected = true,
    x => x.approved_registry_source.application_records = -2,
    x => x.status = "READY",
  ]) {
    const invalid = structuredClone(source); mutate(invalid);
    assert.throws(() => normalizeHopReadiness(invalid));
  }
  const unavailable = normalizeHopReadiness({
    status: "SOURCE_UNAVAILABLE", model_validated: false, prediction_available: false, prediction_probability: null,
  });
  assert.equal(unavailable.publishedLetters, null);
  assert.equal(unavailable.modelEligibleReviewCycles, null);
});

test("Unauthenticated HOP requests never contact upstream sources", async () => {
  const original = global.fetch;
  global.fetch = async () => assert.fail("Authentication bypassed");
  try {
    const res = await route.GET(new NextRequest("https://dashboard.example/api/hop/readiness"));
    assert.equal(res.status, 401);
    assert.equal(route.POST, undefined);
  } finally { global.fetch = original; }
});

test("HOP readiness uses its installed service independently of both other backends", () => {
  const keys = ["PDUFA_HOP_API_BASE_URL", "PDUFA_API_BASE_URL", "PDUFA_RESEARCH_API_BASE_URL"];
  const saved = Object.fromEntries(keys.map(k => [k, process.env[k]]));
  try {
    delete process.env.PDUFA_HOP_API_BASE_URL;
    process.env.PDUFA_API_BASE_URL = "https://storage.example";
    process.env.PDUFA_RESEARCH_API_BASE_URL = "https://market.example";
    assert.equal(hopBackendBase(), "https://pdufa-hop-readonly-review.onrender.com");
    process.env.PDUFA_HOP_API_BASE_URL = " https://hop.example/ ";
    assert.equal(hopBackendBase(), "https://hop.example");
    for (const invalid of ["", "http://hop.example", "https://user:secret@hop.example",
      "https://hop.example/path", "https://hop.example?key=x", "https://hop.example/#x", "not a URL"]) {
      process.env.PDUFA_HOP_API_BASE_URL = invalid;
      assert.equal(hopBackendBase(), null, invalid);
    }
  } finally {
    for (const [key, value] of Object.entries(saved)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
});

test("Authenticated HOP proxy reads only approved backend endpoint and hides credentials", async () => {
  const keys = ["DASHBOARD_PASSWORD", "SESSION_SIGNING_KEY", "PDUFA_API_BASE_URL", "PDUFA_INTERNAL_API_KEY", "PDUFA_HOP_API_BASE_URL"];
  const originals = Object.fromEntries(keys.map(k => [k, process.env[k]]));
  const originalFetch = global.fetch;
  Object.assign(process.env, {
    DASHBOARD_PASSWORD: "test-only-hop-password",
    SESSION_SIGNING_KEY: "test-only-signing-key-long-enough-2026",
    PDUFA_API_BASE_URL: "https://storage.example",
    PDUFA_INTERNAL_API_KEY: "internal-hop-test-only-secret",
  });
  delete process.env.PDUFA_HOP_API_BASE_URL;
  let calls = 0;
  global.fetch = async (url, init) => {
    calls += 1;
    assert.equal(url, "https://pdufa-hop-readonly-review.onrender.com/api/hop/readiness");
    assert.equal(init.headers["x-pdufa-internal-key"], "internal-hop-test-only-secret");
    assert.ok(!init.method || init.method === "GET");
    assert.equal(init.redirect, "error");
    return new Response(JSON.stringify(sourceFixture()), { status: 200, headers: { "Content-Type": "application/json" } });
  };
  try {
    const cookie = auth.COOKIE_NAME + "=" + auth.makeSession();
    const request = new NextRequest("https://dashboard.example/api/hop/readiness", { headers: { cookie } });
    const response = await route.GET(request);
    const body = await response.json();
    assert.equal(response.status, 200);
    assert.equal(body.approvedApplications, 29416);
    assert.equal(body.modelEligibleReviewCycles, 0);
    assert.equal(body.probability, null);
    assert.equal(response.headers.get("cache-control"), "private, no-store");
    assert.equal(calls, 1);
    assert.ok(!JSON.stringify(body).includes("internal-hop-test-only-secret"));
    // A future model flag cannot silently activate an unreviewed UI prediction.
    global.fetch = async () => new Response(JSON.stringify({ ...sourceFixture(), prediction_available: true }));
    const denied = await route.GET(request);
    assert.equal(denied.status, 503);
    const invalidBody = await denied.json();
    assert.equal(invalidBody.reason, "SOURCE_INVALID_RESPONSE");
    assert.ok(!JSON.stringify(invalidBody).includes("internal-hop-test-only-secret"));
    // An explicitly configured source remains isolated; an auth error never
    // retries against the storage backend or exposes the upstream error body.
    process.env.PDUFA_HOP_API_BASE_URL = "https://hop.example";
    calls = 0;
    global.fetch = async (url) => {
      calls++;
      assert.equal(url, "https://hop.example/api/hop/readiness");
      return new Response(JSON.stringify({ detail: "private-upstream-message" }), { status: 401 });
    };
    const upstreamDenied = await route.GET(request);
    assert.equal(upstreamDenied.status, 503);
    assert.equal(calls, 1);
    const authBody = await upstreamDenied.json();
    assert.equal(authBody.reason, "SOURCE_AUTHENTICATION_FAILED");
    assert.doesNotMatch(JSON.stringify(authBody), /private-upstream-message|internal-hop-test-only-secret/);
    for (const [status, reason] of [[404, "SOURCE_ROUTE_MISSING"], [500, "SOURCE_HTTP_ERROR"]]) {
      global.fetch = async () => new Response("private-upstream-message", { status });
      assert.equal((await (await route.GET(request)).json()).reason, reason);
    }
    global.fetch = async () => { throw new Error("private-network-error"); };
    const networkBody = await (await route.GET(request)).json();
    assert.equal(networkBody.reason, "SOURCE_UNREACHABLE");
    assert.doesNotMatch(JSON.stringify(networkBody), /private-network-error/);
    // Invalid explicit configuration must fail before any credential-bearing request.
    process.env.PDUFA_HOP_API_BASE_URL = "https://hop.example/path";
    global.fetch = async () => assert.fail("Invalid HOP source must not fall back");
    assert.equal((await route.GET(request)).status, 503);
  } finally {
    global.fetch = originalFetch;
    for (const [key, value] of Object.entries(originals)) {
      if (value === undefined) delete process.env[key]; else process.env[key] = value;
    }
  }
});
