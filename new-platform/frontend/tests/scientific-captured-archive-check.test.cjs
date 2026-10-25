"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

function loadTs(file, mocks = {}) {
  const source = fs.readFileSync(file, "utf8");
  const compiled = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true,
  } }).outputText;
  const mod = { exports: {} };
  new Function("require", "module", "exports", compiled)(
    name => {
      if (!(name in mocks)) throw new Error("Unexpected dependency: " + name);
      return mocks[name];
    }, mod, mod.exports,
  );
  return mod.exports;
}

const NCT = "NCT02142738";
const SHA = "a".repeat(64);
const DOCUMENT = {
  documentId: "b".repeat(32),
  gateId: "official_regulatory",
  sourceType: "official_agency_document",
  sha256: SHA,
  byteLength: 107,
  captureStatus: "byte_integrity_checked_unverified",
  scientificVerificationComplete: false,
};
function manifest(documents = [DOCUMENT]) {
  return {
    nctId: NCT, sourceDocumentCount: documents.length,
    allCapturedBytesRehashed: true,
    independentSourceVerificationCompleted: false,
    scientificScore: null, fdaApprovalProbability: null,
    documents,
  };
}
const { compareLocalPdfWithCapturedArchive } = loadTs(
  path.join(__dirname, "../lib/scientific-captured-archive-check.ts"),
);

test("captured PDF snapshot can match local bytes without authenticating scientific source", () => {
  const report = compareLocalPdfWithCapturedArchive(NCT, SHA, 107, manifest());
  assert.equal(report.status, "MATCHES_CAPTURED_BYTES_ONLY");
  assert.deepEqual(report.matches, [{
    documentId: "b".repeat(32), gateId: "official_regulatory",
    sourceType: "official_agency_document",
  }]);
  assert.equal(report.sourceAuthorshipIndependentlyAuthenticated, false);
  assert.equal(report.reviewerIdentitiesAuthenticated, false);
  assert.equal(report.clinicalReviewCompleted, false);
  assert.equal(report.scientificScore, null);
  assert.equal(report.fdaApprovalProbability, null);
  assert.equal(report.promotionAllowed, false);
});

test("distinguishes truly empty archive, unmatched digest and mismatched byte count", () => {
  assert.equal(compareLocalPdfWithCapturedArchive(NCT, SHA, 107, manifest([])).status,
    "NO_ARCHIVED_PDFS");
  assert.equal(compareLocalPdfWithCapturedArchive(NCT, "c".repeat(64), 107, manifest()).status,
    "NO_CAPTURED_BYTE_MATCH");
  assert.equal(compareLocalPdfWithCapturedArchive(NCT, SHA, 108, manifest()).status,
    "NO_CAPTURED_BYTE_MATCH");
});

test("malformed source manifests and forged independent review block comparisons", () => {
  for (const mutation of [
    m => { m.nctId = "NCT00000001"; },
    m => { m.sourceDocumentCount = 8; },
    m => { m.allCapturedBytesRehashed = false; },
    m => { m.independentSourceVerificationCompleted = true; },
    m => { m.scientificScore = 80; },
    m => { m.fdaApprovalProbability = .88; },
    m => { m.documents[0].captureStatus = "independently_verified"; },
    m => { m.documents[0].scientificVerificationComplete = true; },
    m => { m.documents[0].byteLength = 0; },
    m => { m.documents[0].documentId = "bad"; },
    m => { m.documents[0].sha256 = "wrong"; },
    m => { m.documents.push({ ...m.documents[0] }); m.sourceDocumentCount = 2; },
  ]) {
    const m = manifest([{ ...DOCUMENT }]);
    mutation(m);
    assert.throws(() => compareLocalPdfWithCapturedArchive(NCT, SHA, 107, m),
      /Captured source verification blocked/, String(mutation));
  }
  assert.throws(() => compareLocalPdfWithCapturedArchive("NCT00000001", SHA, 107, manifest()));
});

const routeFile = path.join(__dirname, "../app/api/scientific-assessment/captured-source-manifest/route.ts");
function route({ authenticated = true, response = manifest(), upstreamOk = true, contract = true } = {}) {
  const calls = [];
  const routeExports = loadTs(routeFile, {
    "next/server": { NextResponse: { json: (body, options = {}) => ({
      body, status: options.status ?? 200, headers: options.headers ?? {},
    }) } },
    "../../../../lib/auth": {
      COOKIE_NAME: "session_test", authConfigured: () => true,
      hasSession: value => authenticated && value === "valid_cookie",
    },
    "../../../../lib/read-only-warm-retry": {
      fetchReadOnlyWithWarmRetry: async (url, init) => {
        calls.push({ url, init });
        return {
          ok: upstreamOk,
          headers: { get: () => contract ? "science-captured-hashes-v1" : "old-service" },
          json: async () => response,
        };
      },
    },
  });
  async function request(nctId = NCT, extraParams = false) {
    const url = new URL("https://science.example/api/scientific-assessment/captured-source-manifest");
    url.searchParams.set("nct_id", nctId);
    if (extraParams) url.searchParams.set("document_id", "arbitrary");
    return routeExports.GET({
      nextUrl: url,
      cookies: { get: () => ({ value: "valid_cookie" }) },
    });
  }
  return { request, calls };
}

async function withKeys(fn, hasBase = true) {
  const names = ["PDUFA_SCIENTIFIC_API_BASE_URL", "PDUFA_SCIENTIFIC_PREVIEW_READ_KEY",
    "PDUFA_INTERNAL_API_KEY", "PDUFA_API_BASE_URL"];
  const before = Object.fromEntries(names.map(name => [name, process.env[name]]));
  if (hasBase) process.env.PDUFA_SCIENTIFIC_API_BASE_URL = "https://isolated-science.example.org";
  else delete process.env.PDUFA_SCIENTIFIC_API_BASE_URL;
  process.env.PDUFA_SCIENTIFIC_PREVIEW_READ_KEY = "SAFE_TEST_PREVIEW_KEY_ONLY";
  process.env.PDUFA_INTERNAL_API_KEY = "ORDINARY_KEY_MUST_NEVER_BE_SENT";
  process.env.PDUFA_API_BASE_URL = "https://ordinary.example.org";
  try { return await fn(); }
  finally {
    for (const name of names) {
      if (before[name] === undefined) delete process.env[name];
      else process.env[name] = before[name];
    }
  }
}

test("preview proxy denies anonymous and wrong-NCT requests without contacting archive", async () =>
  withKeys(async () => {
    const anonymous = route({ authenticated: false });
    assert.equal((await anonymous.request()).status, 401);
    assert.equal(anonymous.calls.length, 0);
    const wrong = route();
    assert.equal((await wrong.request("NCT00000001")).status, 422);
    assert.equal((await wrong.request(NCT, true)).status, 422);
    assert.equal(wrong.calls.length, 0);
  }));

test("preview proxy uses only isolated read-key and returns stripped metadata not PDF bytes", async () =>
  withKeys(async () => {
    const mock = route();
    const reply = await mock.request();
    assert.equal(reply.status, 200);
    assert.equal(reply.headers["Cache-Control"], "private, no-store");
    assert.equal(mock.calls.length, 1);
    assert.equal(mock.calls[0].url,
      "https://isolated-science.example.org/api/scientific-assessment/captured-source-manifest/" + NCT);
    assert.equal(mock.calls[0].init.headers["x-pdufa-internal-key"], "SAFE_TEST_PREVIEW_KEY_ONLY");
    assert.equal(mock.calls[0].init.cache, "no-store");
    assert.equal(reply.body.sourceDocumentCount, 1);
    assert.equal(reply.body.documents[0].sha256, SHA);
    assert.equal(reply.body.documents[0].scientificVerificationComplete, false);
    assert.equal(reply.body.fdaApprovalProbability, null);
    assert.doesNotMatch(JSON.stringify(reply.body), /sourceUrl|capturedBy|contentBase64|reviewerEmail/);
  }));

test("preview proxy refuses fallback, malformed archive, or outdated isolated contract", async () =>
  withKeys(async () => {
    assert.equal((await route({ contract: false }).request()).status, 503);
    assert.equal((await route({ upstreamOk: false }).request()).status, 503);
    const invalid = manifest();
    invalid.documents[0] = { ...DOCUMENT, scientificVerificationComplete: true };
    assert.equal((await route({ response: invalid }).request()).status, 503);
  }));

test("preview never falls back to ordinary dashboard when isolated base is missing", async () =>
  withKeys(async () => {
    const mock = route();
    assert.equal((await mock.request()).status, 503);
    assert.equal(mock.calls.length, 0);
  }, false));

test("trial UI only checks remote archive after local digest and retains scientific non-verification", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /Compare local PDF against captured scientific archive \(read-only\)/);
  assert.match(ui, /compareLocalPdfWithCapturedArchive\(/);
  assert.match(ui, /captured-source-manifest\?nct_id=NCT02142738/);
  assert.match(ui, /Source authorship authenticated: NO/);
  assert.match(ui, /No local PDF bytes leave the browser/);
  assert.doesNotMatch(ui, /uploadCapturedPdf|approveArchivedSource|promoteSourceEvidence/);
});
