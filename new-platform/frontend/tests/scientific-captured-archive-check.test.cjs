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
function upstreamManifest() {
  const base = manifest();
  return {
    ...base,
    reviewerIdentityVerified: false,
    scientificGradePromotionAllowed: false,
    documents: base.documents.map(item => ({
      ...item,
      nctId: NCT,
      byteIntegrityChecked: true,
      sourceAuthorshipVerified: false,
      documentContentScientificallyVerified: false,
      canCountTowardReadiness: false,
    })),
  };
}
const { compareLocalPdfWithCapturedArchive, summarizeCapturedScientificGates, buildScientificSourceReviewHandoff } = loadTs(
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
function route({ authenticated = true, response = upstreamManifest(), upstreamOk = true, upstreamStatus = 503, contract = true } = {}) {
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
          status: upstreamOk ? 200 : upstreamStatus,
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
    const invalid = upstreamManifest();
    invalid.documents[0].documentContentScientificallyVerified = true;
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


test("read-only proxy distinguishes undelivered Render code, invalid credentials and service downtime", async () =>
  withKeys(async () => {
    for (const [upstreamStatus, reason] of [
      [404, "CAPTURED_ROUTE_NOT_DEPLOYED"],
      [401, "ISOLATED_READ_KEY_REJECTED"],
      [403, "ISOLATED_READ_KEY_REJECTED"],
      [502, "ISOLATED_SCIENTIFIC_SERVICE_UNAVAILABLE"],
      [503, "ISOLATED_SCIENTIFIC_SERVICE_UNAVAILABLE"],
    ]) {
      const r = await route({ upstreamOk: false, upstreamStatus }).request();
      assert.equal(r.status, 503);
      assert.equal(r.body.reason, reason);
      assert.equal(r.headers["Cache-Control"], "private, no-store");
      assert.doesNotMatch(JSON.stringify(r.body), /x-pdufa-internal-key|SAFE_TEST_PREVIEW_KEY|documentId|sha256/i);
    }
    const stale = await route({ contract: false }).request();
    assert.equal(stale.body.reason, "CAPTURED_ROUTE_NOT_DEPLOYED");
  }));

test("live empty captured archive is 200 with a zero count, not undeployed backend", async () =>
  withKeys(async () => {
    const empty = upstreamManifest();
    empty.documents = [];
    empty.sourceDocumentCount = 0;
    const r = await route({ response: empty }).request();
    assert.equal(r.status, 200);
    assert.equal(r.body.sourceDocumentCount, 0);
    assert.deepEqual(r.body.documents, []);
  }));

test("backend deployment-check UI distinguishes missing route from empty archive without upload", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /Check captured-source backend deployment/);
  assert.match(ui, /checkCapturedBackendAvailability\(\)/);
  assert.match(ui, /CAPTURED_ROUTE_NOT_DEPLOYED/);
  assert.match(ui, /pilot has 0 archived PDF snapshots/);
  assert.match(ui, /byte integrity ONLY|Byte integrity ONLY/);
  assert.match(ui, /No file uploads or scientific approval/);
  assert.match(ui, /capturedBackendRevision\.current\+\+/);
  assert.doesNotMatch(ui, /saveBackendReady|uploadHealthCheck|promoteScientificGrade/);
});


test("exact-NCT archive coverage distinguishes captured PDFs across four independent evidence gates", () => {
  const docs = [
    { ...DOCUMENT, gateId: "official_regulatory" },
    { ...DOCUMENT, gateId: "official_regulatory", documentId: "c".repeat(32), sha256: "c".repeat(64) },
    { ...DOCUMENT, gateId: "protocol_sap", documentId: "d".repeat(32), sha256: "d".repeat(64) },
  ];
  const source = manifest(docs);
  const unchanged = JSON.stringify(source);
  const result = summarizeCapturedScientificGates(NCT, source);
  assert.equal(result.nctId, NCT);
  assert.equal(result.sourceDocumentCount, 3);
  assert.equal(result.gatesWithCapturedPdf, 2);
  assert.equal(result.gates.length, 4);
  assert.deepEqual(result.gates.map(g => g.gateId), [
    "protocol_sap", "published_results", "independent_replication", "official_regulatory",
  ]);
  assert.deepEqual(result.gates.map(g => g.capturedPdfCount), [1, 0, 0, 2]);
  assert.deepEqual(result.gates.map(g => g.status), [
    "CAPTURED_UNVERIFIED", "NO_CAPTURED_PDF", "NO_CAPTURED_PDF", "CAPTURED_UNVERIFIED",
  ]);
  assert.ok(result.gates.every(g => g.independentlyVerified === false && g.nextAction.length > 30));
  assert.equal(result.externallyVerifiedGateCount, 0);
  assert.equal(result.readyForScientificConclusion, false);
  assert.equal(result.scientificScore, null);
  assert.equal(result.fdaApprovalProbability, null);
  assert.equal(JSON.stringify(source), unchanged);
});

test("a live empty PDF archive keeps every independent scientific gate absent and unverified", () => {
  const result = summarizeCapturedScientificGates(NCT, manifest([]));
  assert.equal(result.sourceDocumentCount, 0);
  assert.equal(result.gatesWithCapturedPdf, 0);
  assert.deepEqual(result.gates.map(g => g.capturedPdfCount), [0, 0, 0, 0]);
  assert.ok(result.gates.every(g => g.status === "NO_CAPTURED_PDF" && !g.independentlyVerified));
  assert.equal(result.externallyVerifiedGateCount, 0);
  assert.equal(result.fdaApprovalProbability, null);
});

test("four captured evidence gate categories remain scientifically unverified without reviewers", () => {
  const ids = ["protocol_sap", "published_results", "independent_replication", "official_regulatory"];
  const docs = ids.map((gateId, i) => ({
    ...DOCUMENT, documentId: String(i+1).repeat(32), sha256: String(i+1).repeat(64), gateId,
  }));
  const result = summarizeCapturedScientificGates(NCT, manifest(docs));
  assert.equal(result.gatesWithCapturedPdf, 4);
  assert.equal(result.externallyVerifiedGateCount, 0);
  assert.equal(result.readyForScientificConclusion, false);
  assert.equal(result.scientificScore, null);
});

test("unrecognized captured gate, forged score, incomplete NCT or mutated digest must fail closed", () => {
  const altered = [
    m => { m.documents[0].gateId = "unsupported_evidence_gate"; },
    m => { m.documents[0].gateId = "approved"; },
    m => { m.documents[0].captureStatus = "independently_verified"; },
    m => { m.documents[0].scientificVerificationComplete = true; },
    m => { m.documents[0].sha256 = "wrong"; },
    m => { m.documents[0].documentId = "wrong"; },
    m => { m.independentSourceVerificationCompleted = true; },
    m => { m.scientificScore = 87; },
    m => { m.fdaApprovalProbability = 0.9; },
    m => { m.sourceDocumentCount = 2; },
  ];
  for (const mutate of altered) {
    const m = manifest([{ ...DOCUMENT }]);
    mutate(m);
    assert.throws(() => summarizeCapturedScientificGates(NCT, m),
      /Captured source verification blocked/, String(mutate));
  }
  assert.throws(() => summarizeCapturedScientificGates("NCT00000001", manifest()),
    /Captured source verification blocked/);
});

test("trial UI only shows four-gate coverage after successful authorized manifest validation", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /summarizeCapturedScientificGates\("NCT02142738", body\)/);
  assert.match(ui, /revision === capturedBackendRevision\.current/);
  assert.match(ui, /Four independent scientific evidence gates captured source coverage/);
  assert.match(ui, /capturedScientificGates\.gates\.map/);
  assert.match(ui, /Independently verified categories:/);
  assert.match(ui, /Scientific score: NOT ASSIGNED/);
  assert.match(ui, /Source authorship authenticated: NO/);
  assert.doesNotMatch(ui, /promoteCapturedGate|approveScientificGrade|uploadSourcePdf/);
});


test("four-gate source handoff is repeatable, SHA-linked, unsigned and private-field-free", () => {
  const items = [
    { ...DOCUMENT, gateId: "official_regulatory", documentId: "a".repeat(32), sha256: "a".repeat(64) },
    { ...DOCUMENT, gateId: "protocol_sap", documentId: "c".repeat(32), sha256: "c".repeat(64) },
  ];
  const input = manifest(items);
  input.verifiedEmail = "SHOULD-NOT-BE-COPIED";
  input.privateSourceURL = "https://sensitive.example/some-source";
  input.documents[0].reviewer_name = "PRIVATE";
  input.documents[0].sourceUrl = "https://secret.example/original.pdf";
  const before = JSON.stringify(input);
  const raw = buildScientificSourceReviewHandoff(NCT, input);
  const packet = JSON.parse(raw);
  assert.equal(raw, buildScientificSourceReviewHandoff(NCT, input));
  assert.equal(JSON.stringify(input), before);
  assert.equal(packet.schemaVersion, "isolated-science-source-review-handoff-v1");
  assert.equal(packet.classification, "UNSIGNED_UNVERIFIED_SOURCE_INVENTORY");
  assert.equal(packet.nctId, NCT);
  assert.equal(packet.sourceDocumentCount, 2);
  assert.equal(packet.capturedEvidenceCategories, 2);
  assert.equal(packet.independentlyVerifiedCategories, 0);
  assert.deepEqual(packet.gateCoverage.map(g => g.capturedPdfCount), [1, 0, 0, 1]);
  assert.deepEqual(packet.capturedPdfFingerprints.map(d => d.gateId), [
    "official_regulatory", "protocol_sap",
  ]);
  assert.ok(packet.capturedPdfFingerprints.every(d => !d.originalPublisherAuthenticated
      && !d.sourceContentClinicallyAdjudicated));
  assert.ok(packet.gateCoverage.every(g => !g.independentlyVerified
      && g.requiredNextAction.length > 30));
  assert.equal(packet.originalSourceAuthenticated, false);
  assert.equal(packet.independentSignedAdjudicationComplete, false);
  assert.equal(packet.scientificallyReady, false);
  assert.equal(packet.promotionAllowed, false);
  assert.equal(packet.scientificScore, null);
  assert.equal(packet.fdaApprovalProbability, null);
  assert.equal(packet.documentBytesIncluded, false);
  for (const banned of ["PRIVATE", "SHOULD-NOT-BE-COPIED", "sensitive.example",
    "secret.example", "reviewer_name", "sourceUrl", "privateSourceURL", "reviewerEmail",
    "contentBase64", "payload"]) {
    assert.ok(!raw.includes(banned), banned + " leaked into the source handoff");
  }
});

test("empty captured archive produces usable four-gate worklist without invented source evidence", () => {
  const packet = JSON.parse(buildScientificSourceReviewHandoff(NCT, manifest([])));
  assert.equal(packet.sourceDocumentCount, 0);
  assert.equal(packet.capturedEvidenceCategories, 0);
  assert.deepEqual(packet.gateCoverage.map(g => g.status), [
    "NO_CAPTURED_PDF", "NO_CAPTURED_PDF", "NO_CAPTURED_PDF", "NO_CAPTURED_PDF",
  ]);
  assert.deepEqual(packet.capturedPdfFingerprints, []);
  assert.equal(packet.scientificScore, null);
});

test("tampered cross-trial, source fields or forged scientific completion cannot produce handoff", () => {
  const mutations = [
    m => { m.nctId = "NCT00000001"; },
    m => { m.sourceDocumentCount = 8; },
    m => { m.allCapturedBytesRehashed = false; },
    m => { m.independentSourceVerificationCompleted = true; },
    m => { m.fdaApprovalProbability = 0.99; },
    m => { m.scientificScore = 97; },
    m => { m.documents[0].captureStatus = "independently_verified"; },
    m => { m.documents[0].scientificVerificationComplete = true; },
    m => { m.documents[0].documentId = "bad"; },
    m => { m.documents[0].sha256 = "corrupted"; },
    m => { m.documents[0].gateId = "arbitrary"; },
    m => { m.documents[0].byteLength = -1; },
    m => { m.documents.push({ ...m.documents[0] }); m.sourceDocumentCount = 2; },
  ];
  for (const mutation of mutations) {
    const m = manifest([{ ...DOCUMENT }]);
    mutation(m);
    assert.throws(() => buildScientificSourceReviewHandoff(NCT, m),
      /Captured source verification blocked/, String(mutation));
  }
  assert.throws(() => buildScientificSourceReviewHandoff("NCT00000001", manifest()));
});

test("four-gate handoff download appears only with authenticated manifest results, not on error", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /buildScientificSourceReviewHandoff\("NCT02142738", body\)/);
  assert.match(ui, /setCapturedHandoffJson\(handoffJson\)/);
  assert.match(ui, /capturedScientificGates && capturedHandoffJson && <p>/);
  assert.match(ui, /Download unverified four-gate source review handoff \(JSON\)/);
  assert.match(ui, /_unverified_four_gate_source_handoff\.json/);
  assert.match(ui, /setCapturedHandoffJson\(null\)/);
  assert.match(ui, /No raw PDF bytes, source URLs, reviewer names, signatures or scientific outcome claims/);
  assert.doesNotMatch(ui, /uploadSourceHandoff|approveCapturedGate|promoteReviewerGrade/);
});
