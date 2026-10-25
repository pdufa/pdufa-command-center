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
  }).outputText, file
);
const { buildScientificDepthReviewCsv, buildScientificReviewerHandoffCsv } =
  require("../lib/scientific-depth-review-csv.ts");
const { auditScientificReviewerCsvs, buildScientificReviewerAuditReceipt, compareLocalSourceSha256Claims, compareTwoLocalSourcePdfSha256Claims } =
  require("../lib/scientific-reviewer-local-audit.ts");

const LAYERS = [
  "trial_design", "efficacy", "safety", "biological_rationale",
  "statistical_integrity", "evidence_reproducibility", "regulatory",
  "timeline_and_uncertainty",
];

function matrix() {
  const layers = LAYERS.map(id => ({
    id, assessments: Array.from({ length: 5 }, (_, i) => "assessment_" + (i + 1)),
  }));
  const depthLevels = Array.from({ length: 8 }, (_, i) => ({
    level: i + 1, id: "depth_" + (i + 1), objective: "Review evidence source " + (i + 1),
  }));
  return {
    nctId: "NCT02142738",
    layers,
    verification: {
      required_assessments: 40, verified_assessments: 0, ready_for_analysis: false,
      scientific_score: null, approval_probability: null,
    },
    depthReview: {
      requiredTasks: 320, completedTasks: 0, readyForScientificConclusion: false,
      approvalProbability: null, depthLevels,
      tasks: layers.flatMap(layer => layer.assessments.flatMap(item => depthLevels.map(depth => ({
        assessmentId: layer.id + "." + item,
        depthLevel: depth.level,
        depthId: depth.id,
        status: "pending_independent_review",
        independentlyVerified: false,
        scientificScore: null,
      })))),
    },
  };
}

function worksheets(m = matrix()) {
  return {
    m,
    inventory: buildScientificDepthReviewCsv(m),
    a: buildScientificReviewerHandoffCsv(m, "A"),
    b: buildScientificReviewerHandoffCsv(m, "B"),
  };
}

function changeRow(csv, row = 1, change = items => items) {
  const lines = csv.trimEnd().split("\r\n");
  const cells = lines[row].match(/"(?:""|[^"])*"/g);
  assert.equal(cells.length, 21);
  const raw = cells.map(cell => cell.slice(1, -1).replaceAll('""', '"'));
  change(raw);
  lines[row] = raw.map(cell => '"' + cell.replaceAll('"', '""') + '"').join(",");
  return lines.join("\r\n") + "\r\n";
}

function observe(csv, decision) {
  return changeRow(csv, 1, cells => {
    cells[11] = "Reviewer candidate";
    cells[13] = "https://clinicaltrials.gov/study/NCT02142738";
    cells[14] = "a".repeat(64);
    cells[15] = "2016-10-08";
    cells[16] = "Table 2";
    cells[17] = "Observation candidate, not authenticated";
    cells[18] = decision;
    cells[19] = "Typed name, NOT a signed claim";
  });
}

test("blank A/B exports can be inspected without implying source or reviewer authentication", () => {
  const { m, inventory, a, b } = worksheets();
  const before = JSON.stringify(m);
  const report = auditScientificReviewerCsvs(m, inventory, a, b);
  assert.equal(report.validatedTaskRows, 320);
  assert.deepEqual(report.candidateObservations, { A: 0, B: 0 });
  assert.deepEqual(report.missingProvenance, { A: 0, B: 0 });
  assert.equal(report.conflictingCandidateDecisions, 0);
  assert.equal(report.independentlyAdjudicatedTasks, 0);
  assert.equal(report.reviewerIdentitiesVerified, false);
  assert.equal(report.sourceBytesVerified, false);
  assert.equal(report.signaturesVerified, false);
  assert.equal(report.promotionAllowed, false);
  assert.equal(report.scientificScore, null);
  assert.equal(report.fdaApprovalProbability, null);
  assert.equal(JSON.stringify(m), before);
});

test("contradictory candidates are identified by task key but never accepted as scientific conclusions", () => {
  const { m, inventory, a, b } = worksheets();
  const report = auditScientificReviewerCsvs(
    m, inventory, observe(a, "supports"), observe(b, "contradicts"),
  );
  assert.deepEqual(report.candidateObservations, { A: 1, B: 1 });
  assert.equal(report.conflictingCandidateDecisions, 1);
  assert.deepEqual(report.conflictTaskKeys, ["trial_design.assessment_1:1"]);
  assert.equal(report.promotionAllowed, false);
  assert.equal(report.independentlyAdjudicatedTasks, 0);
});

test("one-sided candidate and incomplete document claims are flagged, not approved", () => {
  const { m, inventory, a, b } = worksheets();
  const report = auditScientificReviewerCsvs(m, inventory,
    changeRow(observe(a, "supports"), 1, row => { row[13] = "http://untrusted.example"; }),
    observe(b, "supports"));
  assert.deepEqual(report.candidateObservations, { A: 0, B: 1 });
  assert.deepEqual(report.missingProvenance, { A: 1, B: 0 });
  assert.equal(report.oneSidedObservations, 1);
  assert.equal(report.promotionAllowed, false);
});

test("rejects malformed, wrong-trial, fabricated approval, unsupported reviewer status and forged inventories", () => {
  const changes = [
    x => { x.inventory = x.inventory.replace("NCT02142738", "NCT04280705"); },
    x => { x.a = x.a.replace("NCT02142738", "NCT04280705"); },
    x => { x.b = x.b.replace('"B","","NOT_VERIFIED"', '"A","","NOT_VERIFIED"'); },
    x => { x.a = x.a.replace('"NOT_VERIFIED"', '"VERIFIED"'); },
    x => { x.b = x.b.replace('"NOT_SUBMITTED"', '"SIGNED"'); },
    x => { x.a = changeRow(x.a, 1, row => { row[8] = "99"; }); },
    x => { x.a = changeRow(x.a, 1, row => { row[7] = "TRUE"; }); },
    x => { x.a = changeRow(x.a, 1, row => { row[18] = "APPROVED"; }); },
    x => { x.inventory = x.inventory.split("\r\n").slice(0, -2).join("\r\n") + "\r\n"; },
    x => { x.a = x.a.replace('"reviewer_slot"', '"reviewer_slot","duplicate"'); },
    x => { x.b = x.b.replace('"reviewer_slot"', '"reviewer_slot"x'); },
    x => { x.a = x.a + x.a.slice(x.a.indexOf("\r\n") + 2); },
    x => { x.a = "\0" + x.a; },
    x => { x.b = x.b + "x".repeat(1_048_576); },
  ];
  for (const change of changes) {
    const x = worksheets();
    change(x);
    assert.throws(() => auditScientificReviewerCsvs(x.m, x.inventory, x.a, x.b),
      /Reviewer worksheet comparison blocked|Scientific task export blocked/,
      String(change));
  }
});

test("only exact loaded trial inventory may be compared and no browser network/upload is added", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(source, /Compare returned A\/B worksheets locally/);
  assert.match(source, /Compare three CSV files \(browser only\)/);
  assert.match(source, /auditScientificReviewerCsvs\(result\.investigation40, inventoryCsv, aCsv, bCsv\)/);
  assert.match(source, /reviewInventoryFile\.text\(\), reviewerAFile\.text\(\), reviewerBFile\.text\(\)/);
  assert.match(source, /No clinical review has been independently verified/);
  assert.doesNotMatch(source, /uploadReviewer|promoteScientificReview|saveReviewerApproval/);
});


test("privacy-minimized JSON receipt contains no reviewer names, raw notes, URLs or signature claims", () => {
  const { m, inventory, a, b } = worksheets();
  const report = auditScientificReviewerCsvs(
    m, inventory, observe(a, "supports"), observe(b, "contradicts"),
  );
  const raw = buildScientificReviewerAuditReceipt(m, report);
  const receipt = JSON.parse(raw);
  assert.equal(receipt.nctId, "NCT02142738");
  assert.equal(receipt.status, "UNVERIFIED_OFFLINE_WORKSHEET_COMPARISON");
  assert.equal(receipt.exactTrialTasksValidated, 320);
  assert.deepEqual(receipt.syntacticallyCompleteCandidateObservations, { A: 1, B: 1 });
  assert.deepEqual(receipt.unresolvedCandidateDisagreementTaskKeys, ["trial_design.assessment_1:1"]);
  assert.equal(receipt.reviewGates.independentlyAdjudicatedTasks, 0);
  assert.equal(receipt.reviewGates.promoteEvidenceAllowed, false);
  assert.equal(receipt.reviewGates.scientificScore, null);
  assert.equal(receipt.reviewGates.fdaApprovalProbability, null);
  for (const privateFragment of ["Reviewer candidate", "Observation candidate", "https://",
    "typed-name", "primary_document_url", "reviewer_signature", '"reviewer_name"']) {
    assert.ok(!raw.includes(privateFragment), privateFragment + " leaked into receipt");
  }
});

test("refuse receipts with forged success, extra conflicts, invalid keys or inflated candidate counts", () => {
  const mutations = [
    r => { r.nctId = "NCT00000001"; },
    r => { r.reviewerIdentitiesVerified = true; },
    r => { r.sourceBytesVerified = true; },
    r => { r.signaturesVerified = true; },
    r => { r.independentlyAdjudicatedTasks = 1; },
    r => { r.scientificScore = 90; },
    r => { r.fdaApprovalProbability = 0.83; },
    r => { r.promotionAllowed = true; },
    r => { r.validatedTaskRows = 319; },
    r => { r.candidateObservations.A = -1; },
    r => { r.candidateObservations.B = 321; },
    r => { r.missingProvenance.A = 320; },
    r => { r.oneSidedObservations = 4; },
    r => { r.conflictingCandidateDecisions = 2; },
    r => { r.conflictTaskKeys = ["trial_design.assessment_1:1", "trial_design.assessment_1:1"]; r.conflictingCandidateDecisions=2; },
    r => { r.conflictTaskKeys = ["unknown:1"]; },
  ];
  for (const change of mutations) {
    const { m, inventory, a, b } = worksheets();
    const r = auditScientificReviewerCsvs(
      m, inventory, observe(a, "supports"), observe(b, "contradicts"),
    );
    change(r);
    assert.throws(() => buildScientificReviewerAuditReceipt(m, r),
      /Reviewer worksheet comparison blocked|Scientific task export blocked/, String(change));
  }
});

test("local audit receipt UI is only shown after comparison and does not upload its contents", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(source, /Download unverified A\/B comparison receipt \(JSON\)/);
  assert.match(source, /buildScientificReviewerAuditReceipt\(result\.investigation40, localAudit\)/);
  assert.match(source, /_unverified_reviewer_ab_diagnostic\.json/);
  assert.match(source, /localAudit && <section/);
  assert.match(source, /Local, privacy-minimized diagnostic only/);
  assert.doesNotMatch(source, /uploadAuditReceipt|approveReviewerSignature|registerScientificScore/);
});


test("local PDF digest comparison matches an A/B claim, without authenticating source or reviewers", () => {
  const { m, inventory, a, b } = worksheets();
  const sha = "f".repeat(64);
  const claimA = changeRow(a, 1, row => { row[14] = sha; });
  const claimB = changeRow(b, 1, row => { row[14] = sha.toUpperCase(); });
  const result = compareLocalSourceSha256Claims(
    m, inventory, claimA, claimB, "trial_design.assessment_1:1", sha,
  );
  assert.equal(result.reviewerA, "MATCHES_CLAIMED_BYTES");
  assert.equal(result.reviewerB, "MATCHES_CLAIMED_BYTES");
  assert.equal(result.assessmentTaskKey, "trial_design.assessment_1:1");
  assert.equal(result.comparisonIsOnlyAgainstUntrustedWorksheetClaims, true);
  assert.equal(result.originalSourceAuthenticated, false);
  assert.equal(result.sourcePublicationDateVerified, false);
  assert.equal(result.reviewerIdentitiesVerified, false);
  assert.equal(result.independentlyAdjudicatedTasks, 0);
  assert.equal(result.scientificScore, null);
  assert.equal(result.fdaApprovalProbability, null);
  assert.equal(result.promotionAllowed, false);
});

test("source byte check distinguishes missing, wrong and invalid reviewer SHA-256 text", () => {
  const { m, inventory, a, b } = worksheets();
  const actual = "a".repeat(64);
  const report = compareLocalSourceSha256Claims(
    m, inventory,
    changeRow(a, 1, row => { row[14] = "bad-hash"; }),
    changeRow(b, 1, row => { row[14] = "b".repeat(64); }),
    "trial_design.assessment_1:1", actual,
  );
  assert.equal(report.reviewerA, "INVALID_DIGEST_CLAIM");
  assert.equal(report.reviewerB, "DIFFERS_FROM_CLAIM");
  const empty = compareLocalSourceSha256Claims(
    m, inventory, a, b, "trial_design.assessment_1:1", actual,
  );
  assert.equal(empty.reviewerA, "NO_DIGEST_CLAIM");
  assert.equal(empty.reviewerB, "NO_DIGEST_CLAIM");
});

test("local source digest comparison rejects trial swaps, forged signoff and unknown task identities", () => {
  const mutations = [
    x => { x.inventory = x.inventory.replace("NCT02142738", "NCT04280705"); },
    x => { x.a = x.a.replace('"NOT_SUBMITTED"', '"VERIFIED"'); },
    x => { x.b = x.b.replace('"NOT_ASSIGNED"', '"80"'); },
    x => { x.task = "trial_design.assessment_1:9"; },
    x => { x.task = "efficacy.assessment_1:0"; },
    x => { x.digest = "bad-hash"; },
    x => { x.digest = "0".repeat(65); },
  ];
  for (const mutate of mutations) {
    const x = { ...worksheets(), task: "trial_design.assessment_1:1", digest: "a".repeat(64) };
    mutate(x);
    assert.throws(
      () => compareLocalSourceSha256Claims(x.m, x.inventory, x.a, x.b, x.task, x.digest),
      /Reviewer worksheet comparison blocked|Scientific task export blocked/, String(mutate),
    );
  }
});

test("source byte check is browser-only PDF SHA-256, not evidence import or outcome scoring", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(source, /Compare source PDF bytes with A\/B worksheet SHA-256 claims/);
  assert.match(source, /crypto\.subtle\.digest\("SHA-256", pdfBytes\)/);
  assert.match(source, /String\.fromCharCode\(\.\.\.header\) !== "%PDF-"/);
  assert.match(source, /compareLocalSourceSha256Claims\(/);
  assert.match(source, /Original source authenticated: NO/);
  assert.match(source, /PDF is not uploaded/);
  assert.doesNotMatch(source, /uploadPdfForReview|admitEvidence|approveScientificReview/);
});


test("two physical PDF digests are compared separately to each reviewer own hash claim", () => {
  const { m, inventory, a, b } = worksheets();
  const shaA = "a".repeat(64);
  const shaB = "b".repeat(64);
  const claimA = changeRow(a, 1, row => { row[14] = shaA.toUpperCase(); });
  const claimB = changeRow(b, 1, row => { row[14] = shaB; });
  const report = compareTwoLocalSourcePdfSha256Claims(
    m, inventory, claimA, claimB, "trial_design.assessment_1:1", shaA, shaB,
  );
  assert.equal(report.pdfByteRelation, "DISTINCT_BYTES");
  assert.equal(report.reviewerAClaim, "MATCHES_CLAIMED_BYTES");
  assert.equal(report.reviewerBClaim, "MATCHES_CLAIMED_BYTES");
  assert.equal(report.reviewerAPdfSha256, shaA);
  assert.equal(report.reviewerBPdfSha256, shaB);
  assert.equal(report.nctId, "NCT02142738");
  assert.equal(report.independentOriginalSourceAuthenticated, false);
  assert.equal(report.independentReviewersAuthenticated, false);
  assert.equal(report.sourcePublicationDatesVerified, false);
  assert.equal(report.signedAdjudicationsVerified, false);
  assert.equal(report.independentlyAdjudicatedTasks, 0);
  assert.equal(report.scientificScore, null);
  assert.equal(report.fdaApprovalProbability, null);
  assert.equal(report.promotionAllowed, false);
});

test("same PDF bytes do not imply independent reviewer verification", () => {
  const { m, inventory, a, b } = worksheets();
  const sha = "f".repeat(64);
  const report = compareTwoLocalSourcePdfSha256Claims(
    m, inventory, changeRow(a, 1, row => { row[14] = sha; }),
    changeRow(b, 1, row => { row[14] = "0".repeat(64); }),
    "trial_design.assessment_1:1", sha, sha,
  );
  assert.equal(report.pdfByteRelation, "IDENTICAL_BYTES");
  assert.equal(report.reviewerAClaim, "MATCHES_CLAIMED_BYTES");
  assert.equal(report.reviewerBClaim, "DIFFERS_FROM_CLAIM");
  assert.equal(report.independentReviewersAuthenticated, false);
  assert.equal(report.independentlyAdjudicatedTasks, 0);
});

test("two-PDF check rejects unrecognized task, forged status, bad digest and cross-trial files", () => {
  const mutations = [
    x => { x.task = "trial_design.assessment_1:9"; },
    x => { x.inventory = x.inventory.replace("NCT02142738", "NCT00000001"); },
    x => { x.a = x.a.replace('"NOT_ASSIGNED"', '"95"'); },
    x => { x.b = x.b.replace('"NOT_VERIFIED"', '"VERIFIED"'); },
    x => { x.digestB = "not-a-sha"; },
    x => { x.digestA = "f".repeat(65); },
    x => { x.b = x.b.replace('"B","","NOT_VERIFIED"', '"A","","NOT_VERIFIED"'); },
  ];
  for (const mutate of mutations) {
    const x = { ...worksheets(), task: "trial_design.assessment_1:1",
      digestA: "a".repeat(64), digestB: "b".repeat(64) };
    mutate(x);
    assert.throws(() => compareTwoLocalSourcePdfSha256Claims(
      x.m, x.inventory, x.a, x.b, x.task, x.digestA, x.digestB,
    ), /Reviewer worksheet comparison blocked|Scientific task export blocked/, String(mutate));
  }
});

test("dual-PDF preview hashes local PDF bytes after checking PDF markers, without uploading", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(source, /Compare reviewer A and B PDF bytes independently/);
  assert.match(source, /sha256LocalPdf\(localSourcePdf\), sha256LocalPdf\(localReviewerBPdf\)/);
  assert.match(source, /String\.fromCharCode\(\.\.\.data\.subarray\(0, 5\)\) !== "%PDF-"/);
  assert.match(source, /tail\.includes\("%%EOF"\)/);
  assert.match(source, /crypto\.subtle\.digest\("SHA-256", bytes\)/);
  assert.match(source, /compareTwoLocalSourcePdfSha256Claims\(/);
  assert.match(source, /Files are not uploaded or stored/);
  assert.match(source, /Identical bytes do not prove independent review/);
  assert.doesNotMatch(source, /uploadTwoPdfs|storeReviewerPdf|admitPdfEvidence/);
});
