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
const { buildScientificReviewerHandoffCsv } = require("../lib/scientific-depth-review-csv.ts");
const { reconcileLocalReviewerWorksheets } = require("../lib/scientific-reviewer-local-audit.ts");

const LAYERS = [
  "trial_design", "efficacy", "safety", "biological_rationale",
  "statistical_integrity", "evidence_reproducibility", "regulatory", "timeline_and_uncertainty",
];
function matrix() {
  const layers = LAYERS.map(id => ({
    id, assessments: Array.from({ length: 5 }, (_, i) => "assessment_" + (i + 1)),
  }));
  const depthLevels = Array.from({ length: 8 }, (_, i) => ({
    level: i + 1, id: "depth_" + (i + 1), objective: "Review task depth " + (i + 1),
  }));
  const tasks = layers.flatMap(layer => layer.assessments.flatMap(assessment =>
    depthLevels.map(depth => ({
      assessmentId: layer.id + "." + assessment, depthLevel: depth.level,
      depthId: depth.id, status: "pending_independent_review",
      independentlyVerified: false, scientificScore: null,
    }))
  ));
  return {
    nctId: "NCT02142738", layers,
    verification: {
      required_assessments: 40, verified_assessments: 0,
      ready_for_analysis: false, scientific_score: null, approval_probability: null,
    },
    depthReview: {
      requiredTasks: 320, completedTasks: 0, depthLevels, tasks,
      readyForScientificConclusion: false, approvalProbability: null,
    },
  };
}

function changeCell(csv, rowIndex, col, value) {
  const lines = csv.split("\r\n");
  const cells = lines[rowIndex].slice(1, -1).split('","');
  cells[col] = String(value).replaceAll('"', '""');
  lines[rowIndex] = '"' + cells.join('","') + '"';
  return lines.join("\r\n");
}

function entered(csv, decision, opts = {}) {
  for (const [col, value] of [
    [11, opts.name ?? "Claimed reviewer"],
    [13, opts.url ?? "https://example.org/original-study"],
    [14, opts.sha ?? "a".repeat(64)],
    [15, opts.date ?? "2016-10-08"],
    [16, opts.section ?? "Table 2"],
    [17, opts.notes ?? "Source claim only; not authenticated"],
    [18, decision],
    [19, opts.signature ?? "typed signature - not verified"],
  ]) csv = changeCell(csv, 1, col, value);
  return csv;
}

test("blank A/B files audit 320 tasks, record zero reviews, and never promote clinical results", () => {
  const data = matrix();
  const a = buildScientificReviewerHandoffCsv(data, "A");
  const b = buildScientificReviewerHandoffCsv(data, "B");
  const before = JSON.stringify(data);
  const report = reconcileLocalReviewerWorksheets(data, a, b);
  assert.equal(report.exactNctId, "NCT02142738");
  assert.equal(report.candidateA, 0);
  assert.equal(report.candidateB, 0);
  assert.equal(report.candidateDisagreementCount, 0);
  assert.equal(report.tasksIndependentlyAdjudicated, 0);
  assert.equal(report.scientificScore, null);
  assert.equal(report.fdaApprovalProbability, null);
  assert.equal(report.promotionAllowed, false);
  assert.equal(report.reviewersAuthenticated, false);
  assert.equal(report.sourceDocumentsAuthenticated, false);
  assert.equal(JSON.stringify(data), before);
});

test("contradictory claimed A/B findings appear only as candidate disagreements", () => {
  const data = matrix();
  const a = entered(buildScientificReviewerHandoffCsv(data, "A"), "supports");
  const b = entered(buildScientificReviewerHandoffCsv(data, "B"), "contradicts");
  const report = reconcileLocalReviewerWorksheets(data, a, b);
  assert.equal(report.candidateA, 1);
  assert.equal(report.candidateB, 1);
  assert.equal(report.candidateDisagreementCount, 1);
  assert.deepEqual(report.disagreementTaskIds, ["trial_design.assessment_1:1"]);
  assert.equal(report.signaturesVerified, false);
  assert.equal(report.tasksIndependentlyAdjudicated, 0);
  assert.equal(report.promotionAllowed, false);
  assert.equal(report.fdaApprovalProbability, null);
  assert.equal(Object.keys(report).some(x => /reviewer_name|finding_notes/i.test(x)), false);
});

test("one-sided observations, incomplete provenance and multiline quoted notes are handled", () => {
  const data = matrix();
  const a = entered(buildScientificReviewerHandoffCsv(data, "A"), "supports", {
    notes: 'Efficacy table, "not independently verified"\nsecond sentence',
    url: "http://unsafe.example.org/",
  });
  const b = entered(buildScientificReviewerHandoffCsv(data, "B"), "supports", {
    notes: "Registry statement", date: "2016-10-08",
  });
  const report = reconcileLocalReviewerWorksheets(data, a, b);
  assert.equal(report.candidateA, 0);
  assert.equal(report.missingProvenanceA, 1);
  assert.equal(report.candidateB, 1);
  assert.equal(report.oneSidedObservations, 1);
  assert.equal(report.candidateDisagreementCount, 0);
});

test("wrong NCT, swapped slot, forged completion, invalid choices, modified tasks and unsafe CSV all block", () => {
  const data = matrix();
  const a = buildScientificReviewerHandoffCsv(data, "A");
  const b = buildScientificReviewerHandoffCsv(data, "B");
  const mutations = [
    [changeCell(a, 1, 0, "NCT04280705"), b],
    [changeCell(a, 1, 10, "B"), b],
    [changeCell(a, 1, 7, "TRUE"), b],
    [changeCell(a, 1, 8, "92"), b],
    [changeCell(a, 1, 12, "VERIFIED"), b],
    [changeCell(a, 1, 20, "SIGNED"), b],
    [changeCell(a, 1, 18, "APPROVED"), b],
    [changeCell(a, 1, 2, "efficacy.invalid"), b],
    [a, changeCell(b, 1, 2, "regulatory.bad")],
    [a.slice(0, a.lastIndexOf("\r\n", a.length - 3)), b],
    [a.replace('"reviewer_name"', '"reviewer_slot"'), b],
    [a + '"extra","invalid"\r\n', b],
    [a.replace('"PENDING_INDEPENDENT_REVIEW"', '"NOT_PENDING"'), b],
    [a.replace('"Review task depth 1"', '"Unclosed'), b],
  ];
  for (const [badA, badB] of mutations) {
    assert.throws(() => reconcileLocalReviewerWorksheets(data, badA, badB), /Local reviewer audit blocked|Scientific task export blocked/);
  }
});

test("preview exposes local two-file diagnostic without a network submission or grading action", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /Local A\/B reviewer worksheet audit/);
  assert.match(ui, /Audit A\/B worksheets locally/);
  assert.match(ui, /const matrix = result\.investigation40;/);
  assert.match(ui, /reconcileLocalReviewerWorksheets\(matrix, a, b\)/);
  assert.match(ui, /reconcileLocalReviewerWorksheets/);
  assert.match(ui, /No files are uploaded/);
  assert.doesNotMatch(ui, /submitReviewerDecision\(|saveGrade\(|uploadReviewerWorksheet\(/);
});
