"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (mod, file) => mod._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, file
);

const { buildScientific800EvidenceMap, SCIENTIFIC_800_SOURCE_DEPENDENCIES } =
  require("../lib/scientific-800-evidence-map.ts");

const LAYERS = [
  "trial_design", "efficacy", "safety", "biological_rationale",
  "statistical_integrity", "evidence_reproducibility", "regulatory",
  "timeline_and_uncertainty",
];
const REQUIREMENT_IDS = [
  "archive_integrity", "indication", "design", "eligibility", "interventions",
  "enrollment", "timeline", "registered_primary", "primary_analysis",
  "safety_denominators", "participant_flow", "baseline", "protocol_sap",
  "published_results", "independent_replication", "official_regulatory",
];

function fixture() {
  const nctId = "NCT02142738";
  const layers = LAYERS.map(id => ({
    id, assessments: Array.from({ length: 5 }, (_, i) => "assessment_" + (i + 1)),
  }));
  const depthLevels = Array.from({ length: 8 }, (_, i) => ({
    level: i + 1, id: "depth_" + (i + 1), objective: "Review " + (i + 1),
  }));
  const tasks = layers.flatMap(layer => layer.assessments.flatMap(field =>
    depthLevels.map(depth => ({
      assessmentId: layer.id + "." + field, depthLevel: depth.level,
      depthId: depth.id, status: "pending_independent_review",
      independentlyVerified: false, scientificScore: null,
    }))
  ));
  const matrix = {
    nctId, layers,
    verification: {
      required_assessments: 40, verified_assessments: 0, ready_for_analysis: false,
      scientific_score: null, approval_probability: null,
    },
    depthReview: {
      requiredTasks: 320, completedTasks: 0, depthLevels, tasks,
      readyForScientificConclusion: false, approvalProbability: null,
    },
  };
  const requirements = REQUIREMENT_IDS.map((id, index) => ({
    id, label: "Requirement " + id,
    available: index < 10,
    evidenceLevel: index === 0 ? "archive_verified"
      : index >= 12 ? "independent_review_not_loaded"
      : index < 10 ? "registry_field_present" : "missing_in_archive",
    sourcePath: index >= 12 ? null : "protocolSection." + id,
    nextAction: "Find and independently review " + id,
    independentlyVerified: false,
  }));
  const audit = {
    nctId, requirements,
    missingRequirementIds: REQUIREMENT_IDS.slice(10),
    analysisReadiness: {
      coveragePercent: 63, requirementsCovered: 10, requirementsTotal: 16,
      readyForFullScientificConclusion: false, verdict: "NOT_READY",
      passFail: "FAIL_INCOMPLETE_INPUTS",
    },
    scientificReluctance: {
      grade: "F", level: "CRITICAL", reluctanceToConclude: "MAXIMUM",
      verdict: "WITHHOLD_SCIENTIFIC_CONCLUSION",
    },
    externalEvidenceVerified: false, scientificScore: null, fdaApprovalProbability: null,
  };
  return { matrix, audit };
}


const { buildScientific800ReviewerHandoffCsv } =
  require("../lib/scientific-800-reviewer-handoff.ts");



const { compareScientific800ReviewerCsvs } =
  require("../lib/scientific-800-local-pair-audit.ts");

function pair() {
  const { matrix, audit } = fixture();
  return {
    matrix, audit,
    a: buildScientific800ReviewerHandoffCsv(matrix, audit, "A"),
    b: buildScientific800ReviewerHandoffCsv(matrix, audit, "B"),
  };
}

function edit(csv, rowIndex, field, updatedValue) {
  const rows = csv.trimEnd().split("\r\n");
  const cells = rows[rowIndex].slice(1, -1).split('","');
  assert.equal(cells.length, 29);
  assert.equal(updatedValue.includes('"'), false);
  cells[field] = updatedValue;
  rows[rowIndex] = '"' + cells.join('","') + '"';
  return rows.join("\r\n") + "\r\n";
}

test("800 blank A/B rows compare without pretending to authenticate reviewers", () => {
  const x = pair();
  const previous = JSON.stringify({matrix:x.matrix, audit:x.audit});
  const report = compareScientific800ReviewerCsvs(x.matrix, x.audit, x.a, x.b);
  assert.deepEqual(report.candidateDecisions, { A: 0, B: 0 });
  assert.deepEqual(report.missingOriginalSourceProvenance, { A: 0, B: 0 });
  assert.equal(report.comparedTaskRows, 800);
  assert.equal(report.oneSidedDecisions, 0);
  assert.equal(report.conflictingCandidateDecisions, 0);
  assert.equal(report.conflictingDocumentReferences, 0);
  assert.equal(report.adjudicatedTasks, 0);
  assert.equal(report.reviewerIdentityAuthenticated, false);
  assert.equal(report.independentQualificationVerified, false);
  assert.equal(report.sourceBytesVerified, false);
  assert.equal(report.signaturesVerified, false);
  assert.equal(report.scientificScore, null);
  assert.equal(report.fdaApprovalProbability, null);
  assert.equal(JSON.stringify({matrix:x.matrix,audit:x.audit}), previous);
});

test("untrusted edits show one-sided, conflict, provenance and same claimed name warnings", () => {
  const x = pair();
  const sourceA = "a".repeat(64), sourceB = "b".repeat(64);
  let a = edit(x.a, 1, 26, "supports");
  a = edit(a, 1, 18, "Reviewer X");
  a = edit(a, 1, 20, "https://clinicaltrials.gov/study/NCT02142738");
  a = edit(a, 1, 21, sourceA);
  a = edit(a, 1, 22, "2025-01-01");
  a = edit(a, 1, 23, "Table 1");
  a = edit(a, 1, 25, "Claimed benefit");
  let b = edit(x.b, 1, 26, "contradicts");
  b = edit(b, 1, 18, "reviewer x");
  b = edit(b, 1, 20, "https://clinicaltrials.gov/study/NCT02142738");
  b = edit(b, 1, 21, sourceB);
  b = edit(b, 1, 22, "2025-01-01");
  b = edit(b, 1, 23, "Table 1");
  b = edit(b, 1, 25, "Claimed not supported");
  a = edit(a, 2, 26, "uncertain");

  const out = compareScientific800ReviewerCsvs(x.matrix, x.audit, a, b);
  assert.deepEqual(out.candidateDecisions, { A: 2, B: 1 });
  assert.deepEqual(out.missingOriginalSourceProvenance, { A: 1, B: 0 });
  assert.equal(out.oneSidedDecisions, 1);
  assert.equal(out.conflictingCandidateDecisions, 1);
  assert.equal(out.conflictingDocumentReferences, 1);
  assert.equal(out.matchingClaimedReviewerNames, 1);
  assert.deepEqual(out.conflictTaskKeys, ["trial_design.assessment_1:depth_1"]);
  assert.equal(out.adjudicatedTasks, 0);
});

test("forged verification and modified task identity always fail closed", () => {
  const x = pair();
  for (const [source, field, value] of [
    ["a", 0, "NCT04280705"], ["a", 5, "COMPLETE"],
    ["a", 11, "VERIFIED"], ["a", 12, "90"],
    ["a", 15, "official_regulatory"], ["a", 19, "VERIFIED"],
    ["b", 24, "VERIFIED"], ["a", 28, "SUBMITTED"],
    ["b", 26, "APPROVED"], ["b", 14, "A"],
  ]) {
    const changed = edit(x[source], 1, field, value);
    assert.throws(() => compareScientific800ReviewerCsvs(
      x.matrix, x.audit, source === "a" ? changed : x.a, source === "b" ? changed : x.b),
      /800-task reviewer comparison blocked/);
  }
  assert.throws(() => compareScientific800ReviewerCsvs(x.matrix, x.audit, x.b, x.a));
  assert.throws(() => compareScientific800ReviewerCsvs(x.matrix, x.audit,
    x.a.split("\r\n").slice(0, -2).join("\r\n"), x.b));
  assert.throws(() => compareScientific800ReviewerCsvs(x.matrix, x.audit,
    x.a.replace('"reviewer_slot"', '"fake_header"'), x.b));
  assert.throws(() => compareScientific800ReviewerCsvs(x.matrix, x.audit,
    x.a.replace('"reviewer_slot"', '"bad"unclosed'), x.b));
  assert.throws(() => compareScientific800ReviewerCsvs(x.matrix, x.audit,
    x.a + "x".repeat(3 * 1024 * 1024), x.b));
  const m = fixture();
  m.audit.nctId = "NCT04280705";
  assert.throws(() => compareScientific800ReviewerCsvs(m.matrix, m.audit, x.a, x.b));
});

test("UI uses browser-local untrusted CSVs; no backend verification or grading", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/Scientific800Handoff.tsx"), "utf8");
  assert.match(ui, /Compare 800-point A\/B worksheets locally/);
  assert.match(ui, /compareScientific800ReviewerCsvs\(/);
  assert.match(ui, /Reviewers are NOT authenticated/);
  assert.match(ui, /file\.text\(\)/);
  assert.match(ui, /Sources and signatures are NOT verified/); // no authenticity claim asserted
  assert.doesNotMatch(ui, /runScan\(|placeTrade\(|saveGrade\(/);
});


const { buildScientific800DiscrepancyLedgerCsv } =
  require("../lib/scientific-800-local-pair-audit.ts");

test("complete discrepancy ledger exports exact-NCT 800 rows without pretending science was adjudicated", () => {
  const x = pair();
  const orig = JSON.stringify({ matrix: x.matrix, audit: x.audit });
  const csv = buildScientific800DiscrepancyLedgerCsv(x.matrix, x.audit, x.a, x.b);
  const rows = csv.trimEnd().split("\r\n");
  assert.equal(rows.length, 801);
  assert.equal(rows[0].slice(1, -1).split('","').length, 20);
  assert.match(rows[0], /"independent_review_next_actions","scientific_adjudication_status"$/);
  assert.match(rows[1], /"NCT02142738","trial_design.assessment_1:depth_1"/);
  assert.match(rows[800], /"timeline_and_uncertainty.assessment_5:depth_20"/);
  assert.equal((csv.match(/"NOT_ADJUDICATED"/g) || []).length, 800);
  assert.equal((csv.match(/"COLLECT_MISSING_INDEPENDENT_REVIEW;AUTHENTICATE_REVIEWERS_AND_VERIFY_ORIGINAL_SOURCES"/g) || []).length, 800);
  assert.doesNotMatch(csv, /"SCIENTIFICALLY_VERIFIED"|"APPROVED"|"SIGNED"/);
  assert.equal(JSON.stringify({ matrix: x.matrix, audit: x.audit }), orig);
});

test("complete per-task flags preserve reviewer-source conflicts without claiming verification", () => {
  const x = pair();
  const shaA = "c".repeat(64), shaB = "d".repeat(64);
  let a = edit(x.a, 1, 26, "supports");
  a = edit(a, 1, 18, "Example Reviewer");
  a = edit(a, 1, 20, "https://clinicaltrials.gov/study/NCT02142738");
  a = edit(a, 1, 21, shaA);
  a = edit(a, 1, 22, "2025-01-02");
  a = edit(a, 1, 23, "Table 2");
  a = edit(a, 1, 25, "Candidate observation");
  let b = edit(x.b, 1, 26, "contradicts");
  b = edit(b, 1, 18, "example reviewer");
  b = edit(b, 1, 20, "https://clinicaltrials.gov/study/NCT02142738");
  b = edit(b, 1, 21, shaB);
  b = edit(b, 1, 22, "2025-01-02");
  b = edit(b, 1, 23, "Table 2");
  b = edit(b, 1, 25, "Candidate disagreement");
  a = edit(a, 2, 26, "uncertain");
  const csv = buildScientific800DiscrepancyLedgerCsv(x.matrix, x.audit, a, b);
  const lines = csv.trimEnd().split("\r\n");
  const row = lines[1].slice(1, -1).split('","');
  assert.equal(row[0], "NCT02142738");
  assert.equal(row[1], "trial_design.assessment_1:depth_1");
  assert.equal(row[6], "supports");
  assert.equal(row[7], "contradicts");
  assert.equal(row[10], shaA);
  assert.equal(row[11], shaB);
  assert.equal(row[12], "NO");
  assert.equal(row[13], "NO");
  assert.equal(row[14], "NO");
  assert.equal(row[15], "YES");
  assert.equal(row[16], "YES");
  assert.equal(row[17], "YES");
  assert.match(row[18], /RECONCILE_CONFLICTING_FINDINGS/);
  assert.match(row[18], /RECONCILE_CLAIMED_SOURCE_DOCUMENTS/);
  assert.match(row[18], /CHECK_REVIEWER_INDEPENDENCE/);
  assert.equal(row[19], "NOT_ADJUDICATED");
  const oneSidedRow = lines[2].slice(1, -1).split('","');
  assert.equal(oneSidedRow[14], "YES");
  assert.equal(oneSidedRow[12], "YES");
  assert.match(oneSidedRow[18], /OBTAIN_COMPLETE_SOURCE_PROVENANCE/);
  assert.equal(lines.length, 801);
});

test("output escapes spreadsheet formula injection in untrusted source references", () => {
  const x = pair();
  let a = edit(x.a, 1, 26, "supports");
  a = edit(a, 1, 20, "=HYPERLINK(https://evil.invalid)");
  const csv = buildScientific800DiscrepancyLedgerCsv(x.matrix, x.audit, a, x.b);
  assert.match(csv, /"'=HYPERLINK/);
  const rows = csv.trimEnd().split("\r\n");
  assert.equal(rows.length, 801);
  assert.match(rows[1], /OBTAIN_COMPLETE_SOURCE_PROVENANCE/);
});

test("invalid or forged sheet input blocks ledger export before writing any rows", () => {
  const x = pair();
  for (const [which, col, value] of [
    ["a", 0, "NCT04280705"], ["b", 4, "invented_depth"],
    ["a", 12, "0.99"], ["b", 28, "SUBMITTED"],
    ["a", 11, "VERIFIED"], ["b", 19, "VERIFIED"],
    ["a", 26, "APPROVED"], ["b", 15, "invalid_source_gate"],
  ]) {
    const altered = edit(x[which], 1, col, value);
    assert.throws(() => buildScientific800DiscrepancyLedgerCsv(
      x.matrix, x.audit, which === "a" ? altered : x.a,
      which === "b" ? altered : x.b),
      /800-task reviewer comparison blocked/);
  }
  assert.throws(() => buildScientific800DiscrepancyLedgerCsv(
    x.matrix, x.audit, x.b, x.a));
  const x2 = pair();
  x2.audit.nctId = "NCT04280705";
  assert.throws(() => buildScientific800DiscrepancyLedgerCsv(
    x2.matrix, x2.audit, x2.a, x2.b));
});

test("UI offers full 800-task CSV only after local comparison and clears stale results", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/Scientific800Handoff.tsx"), "utf8");
  assert.match(ui, /Download full 800-task discrepancy ledger \(CSV\)/);
  assert.match(ui, /buildScientific800DiscrepancyLedgerCsv\(/);
  assert.match(ui, /_scientific_800_AB_discrepancy_ledger_UNVERIFIED\.csv/);
  assert.match(ui, /setLocalDiscrepancyCsv\(""\)/);
  assert.match(ui, /localAudit\.nctId !== validated\.matrix\.nctId/);
  assert.match(ui, /URLs and SHA-256 strings are untrusted claims/);
  assert.doesNotMatch(ui, /saveGrade\(|placeTrade\(|runScan\(/);
});
