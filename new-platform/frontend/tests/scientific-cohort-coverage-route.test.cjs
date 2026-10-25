"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS,
      target: ts.ScriptTarget.ES2022,
      esModuleInterop: true,
    },
  }).outputText, file,
);

const compiled = ts.transpileModule(
  fs.readFileSync(path.join(__dirname, "../app/api/scientific-cohort/coverage/route.ts"), "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  },
).outputText;

function data() {
  return {
    asOf: new Date().toISOString().slice(0, 10), mode: "LIVE_READ_ONLY_GITHUB_SOURCE",
    pipeline: [
      { id: "TRIAL|NCT02142738", programId: "PDUFA-000101", nctId: "NCT02142738" },
      { id: "APPLICATION|DBVT|2020-08-03|viaskin-peanut", programId: "PDUFA-000071" },
    ],
    members: {
      GEM_JR: { rows: [{ id: "TRIAL|NCT02142738", programId: "PDUFA-000101" }] },
      GEM: { rows: [] },
    },
    sourceHealth: { state: "COMPLETE_PUBLISHED", pipelineSourceParity: { exactPrograms: 2 } },
  };
}
function audit(dataOverride = data()) {
  const keys = {};
  const calls = [];
  const mod = { exports: {} };
  const requireMock = name => {
    if (name === "next/server") return {
      NextResponse: { json: (value, options = {}) => ({
        status: options.status ?? 200,
        body: value, headers: options.headers ?? {},
      }) },
    };
    if (name.endsWith("/lib/auth")) return {
      COOKIE_NAME: "test_session",
      authConfigured: () => keys.configured !== false,
      hasSession: value => value === "valid-cookie",
    };
    if (name.endsWith("/lib/read-only-warm-retry")) return {
      fetchReadOnlyWithWarmRetry: async (url, init) => {
        calls.push({ url, init });
        const isWt = url.endsWith("/api/program-watch-trade");
        const response = isWt
          ? (keys.badWt ? { foo: "missing-tags" } : { watch: ["PDUFA-000071"], trade: [] })
          : dataOverride;
        return {
          ok: keys.failUpstream !== true,
          status: keys.failUpstream ? 503 : 200,
          json: async () => response,
        };
      },
    };
    if (name.endsWith("/lib/scientific-cohort-coverage")) return {
      computePublishedScienceCoverage:
        require("../lib/scientific-cohort-coverage.ts").computePublishedScienceCoverage,
    };
    throw new Error("Unexpected dependency " + name);
  };
  new Function("require","module","exports",compiled)(requireMock, mod, mod.exports);
  return {
    calls,
    keys,
    GET: mod.exports.GET,
    request: cookie => mod.exports.GET({
      cookies: { get: () => cookie ? { value: cookie } : undefined },
    }),
  };
}

async function withEnv(f) {
  const old = {
    PDUFA_API_BASE_URL: process.env.PDUFA_API_BASE_URL,
    PDUFA_INTERNAL_API_KEY: process.env.PDUFA_INTERNAL_API_KEY,
    PDUFA_SCIENTIFIC_API_BASE_URL: process.env.PDUFA_SCIENTIFIC_API_BASE_URL,
  };
  process.env.PDUFA_API_BASE_URL = "https://ordinary-staging.example.com";
  process.env.PDUFA_SCIENTIFIC_API_BASE_URL = "https://isolated-science.example.org";
  process.env.PDUFA_INTERNAL_API_KEY = "FAKE_TEST_KEY_NOT_A_SECRET";
  try { await f(); }
  finally {
    for (const [name, value] of Object.entries(old)) {
      if (value === undefined) delete process.env[name];
      else process.env[name] = value;
    }
  }
}

test("unauthenticated request cannot read published source membership", () => withEnv(async () => {
  const route = audit();
  assert.equal((await route.request()).status, 401);
  assert.equal(route.calls.length, 0);
}));

test("signed-in audit reads only existing workspace and WT GET endpoints", () => withEnv(async () => {
  const route = audit();
  const res = await route.request("valid-cookie");
  assert.equal(res.status, 200);
  assert.equal(res.body.stages[0].exactNctPrograms, 1);
  assert.equal(res.body.stages[2].unlinkedPrograms, 1);
  assert.equal(res.body.archivedScientificRecordsVerified, null);
  assert.equal(res.body.scientificFindingsVerified, null);
  assert.equal(res.body.approvalProbability, null);
  assert.equal(res.body.importsPerformed, false);
  assert.equal(res.body.qualificationPresetsChanged, false);
  assert.equal(route.calls.length, 2);
  assert.deepEqual(route.calls.map(x => x.url).sort(), [
    "https://ordinary-staging.example.com/api/program-watch-trade",
    "https://ordinary-staging.example.com/api/workspace",
  ]);
  for (const call of route.calls) {
    assert.equal(call.init.method, "GET");
    assert.equal(call.init.cache, "no-store");
    assert.equal(call.init.headers["x-pdufa-internal-key"], process.env.PDUFA_INTERNAL_API_KEY);
    assert.ok(!call.url.includes("isolated-science"));
  }
  assert.equal(res.headers["Cache-Control"], "private, no-store");
  assert.doesNotMatch(JSON.stringify(res.body), /FAKE_TEST_KEY|APPROVED|scientific_score.*[0-9]/i);
}));

test("missing or malformed WT membership and backend failures refuse unverified output", () => withEnv(async () => {
  const route = audit();
  route.keys.badWt = true;
  let result = await route.request("valid-cookie");
  assert.equal(result.status, 503);
  assert.equal(result.body.error, "Published exact-trial coverage could not be verified");
  route.keys.badWt = false;
  route.keys.failUpstream = true;
  result = await route.request("valid-cookie");
  assert.equal(result.status, 503);
  assert.equal(result.body.error, "Verified published GEM and WT sources unavailable");
}));

test("ordinary backend key is mandatory and never replaced with science-only variable", () => withEnv(async () => {
  delete process.env.PDUFA_INTERNAL_API_KEY;
  const route = audit();
  const result = await route.request("valid-cookie");
  assert.equal(result.status, 503);
  assert.equal(route.calls.length, 0);
}));

test("source parity mismatch fails closed rather than claiming verified membership", () => withEnv(async () => {
  const workspace = data();
  workspace.sourceHealth.pipelineSourceParity.exactPrograms = 1;
  const route = audit(workspace);
  const result = await route.request("valid-cookie");
  assert.equal(result.status, 503);
  assert.equal(result.body.error, "Published exact-trial coverage could not be verified");
}));
