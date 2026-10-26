"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {
      module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, esModuleInterop: true,
    },
  }).outputText, file
);
const { buildScientificSourceReviewHandoff } =
  require("../lib/scientific-captured-archive-check.ts");
const { compareFourGateSourceHandoffs } =
  require("../lib/scientific-handoff-drift-check.ts");

const NCT = "NCT02142738";
function doc(id, gate, digest = id) {
  return {
    documentId: id.repeat(32),
    gateId: gate,
    sourceType: "official_agency_document",
    sha256: digest.repeat(64),
    byteLength: 107,
    captureStatus: "byte_integrity_checked_unverified",
    scientificVerificationComplete: false,
  };
}
function packet(documents) {
  return buildScientificSourceReviewHandoff(NCT, {
    nctId: NCT, sourceDocumentCount: documents.length,
    allCapturedBytesRehashed: true,
    independentSourceVerificationCompleted: false,
    scientificScore: null, fdaApprovalProbability: null,
    documents,
  });
}

test("identical unsigned handoffs report no inventory drift and never certify archived sources", () => {
  const first = packet([doc("a", "official_regulatory"), doc("b", "protocol_sap")]);
  const second = packet([doc("b", "protocol_sap"), doc("a", "official_regulatory")]);
  const report = compareFourGateSourceHandoffs(first, second);
  assert.equal(report.nctId, NCT);
  assert.equal(report.comparisonResult, "NO_REPORTED_CHANGE");
  assert.equal(report.priorDocumentCount, 2);
  assert.equal(report.laterDocumentCount, 2);
  assert.equal(report.unchangedDocumentCount, 2);
  assert.deepEqual(report.addedDocumentIds, []);
  assert.deepEqual(report.removedDocumentIds, []);
  assert.deepEqual(report.changedDocumentIds, []);
  assert.equal(report.sourcesAuthenticated, false);
  assert.equal(report.snapshotsCryptographicallySigned, false);
  assert.equal(report.reviewerCredentialsVerified, false);
  assert.equal(report.clinicalAdjudicationComplete, false);
  assert.equal(report.scientificScore, null);
  assert.equal(report.fdaApprovalProbability, null);
  assert.equal(report.promotionAllowed, false);
});

test("captured PDF additions, removals, metadata replacement and gate reassignment are distinguished", () => {
  const old = packet([doc("a", "official_regulatory"), doc("b", "protocol_sap"),
    doc("c", "published_results")]);
  const next = packet([doc("a", "official_regulatory", "d"),
    doc("c", "independent_replication"), doc("e", "published_results")]);
  const report = compareFourGateSourceHandoffs(old, next);
  assert.equal(report.comparisonResult, "CAPTURED_INVENTORY_CHANGED");
  assert.deepEqual(report.addedDocumentIds, ["e".repeat(32)]);
  assert.deepEqual(report.removedDocumentIds, ["b".repeat(32)]);
  assert.deepEqual(report.changedDocumentIds, ["a".repeat(32), "c".repeat(32)]);
  assert.equal(report.unchangedDocumentCount, 0);
  assert.deepEqual(report.gates.map(x => [x.gateId,
    x.priorCapturedPdfCount, x.laterCapturedPdfCount]), [
    ["protocol_sap", 1, 0],
    ["published_results", 1, 1],
    ["independent_replication", 0, 1],
    ["official_regulatory", 1, 1],
  ]);
  assert.equal(report.promotionAllowed, false);
});

test("empty inventories compare as empty, without inventing document capture", () => {
  const report = compareFourGateSourceHandoffs(packet([]), packet([]));
  assert.equal(report.comparisonResult, "NO_REPORTED_CHANGE");
  assert.equal(report.priorDocumentCount, 0);
  assert.equal(report.laterDocumentCount, 0);
  assert.equal(report.gates.length, 4);
  assert.ok(report.gates.every(x => x.priorCapturedPdfCount === 0
    && x.laterCapturedPdfCount === 0));
  assert.equal(report.scientificScore, null);
});

test("tampered, falsely verified, duplicate, missing or wrong-NCT handoffs fail closed", () => {
  const original = packet([doc("a", "official_regulatory")]);
  const changed = [
    p => { p.nctId = "NCT00000001"; },
    p => { p.schemaVersion = "future-or-fake"; },
    p => { p.classification = "VERIFIED"; },
    p => { p.scientificScore = 100; },
    p => { p.fdaApprovalProbability = 0.98; },
    p => { p.promotionAllowed = true; },
    p => { p.originalSourceAuthenticated = true; },
    p => { p.independentReviewerCredentialsVerified = true; },
    p => { p.independentSignedAdjudicationComplete = true; },
    p => { p.gateCoverage[3].independentlyVerified = true; },
    p => { p.gateCoverage[3].capturedPdfCount = 0; },
    p => { p.sourceDocumentCount = 8; },
    p => { p.capturedPdfFingerprints[0].sha256 = "bad"; },
    p => { p.capturedPdfFingerprints[0].byteLength = -1; },
    p => { p.capturedPdfFingerprints[0].originalPublisherAuthenticated = true; },
    p => { p.capturedPdfFingerprints[0].gateId = "new_gate"; },
    p => { p.capturedPdfFingerprints[0].documentId = "bad"; },
    p => { p.capturedPdfFingerprints.push({ ...p.capturedPdfFingerprints[0] }); p.sourceDocumentCount = 2; },
    p => { p.documentBytesIncluded = true; },
    p => { p.extraFieldWithReviewerName = "PII"; },
    p => { p.warning = ""; },
  ];
  for (const mutate of changed) {
    const packetData = JSON.parse(original);
    mutate(packetData);
    const bad = JSON.stringify(packetData);
    assert.throws(() => compareFourGateSourceHandoffs(original, bad),
      /Source handoff comparison blocked/, String(mutate));
    assert.throws(() => compareFourGateSourceHandoffs(bad, original),
      /Source handoff comparison blocked/, String(mutate));
  }
  for (const bad of ["", "{notJSON", "null", "[]", "0".repeat(300000), "\0" + original]) {
    assert.throws(() => compareFourGateSourceHandoffs(original, bad),
      /Source handoff comparison blocked/);
  }
});

test("browser-only UI supports two file selections and clears stale results on trial change", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /Compare two saved source handoff inventories \(browser only\)/);
  assert.match(ui, /earlierHandoffFile\.text\(\), laterHandoffFile\.text\(\)/);
  assert.match(ui, /compareFourGateSourceHandoffs\(earlier, later\)/);
  assert.match(ui, /handoffDriftRevision\.current\+\+/);
  assert.match(ui, /setHandoffDrift\(null\)/);
  assert.match(ui, /Neither snapshot authenticated/);
  assert.match(ui, /not that the live archive is immutable or independently verified/);
  assert.match(ui, /Files remain local/);
  assert.doesNotMatch(ui, /uploadHandoff|approveHandoff|admitSourceProof/);
});
