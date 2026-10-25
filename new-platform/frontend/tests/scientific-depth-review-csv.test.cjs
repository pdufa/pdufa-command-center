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
const { buildScientificDepthReviewCsv } = require("../lib/scientific-depth-review-csv.ts");

const LAYERS = ["trial_design", "efficacy", "safety", "biological_rationale",
  "statistical_integrity", "evidence_reproducibility", "regulatory", "timeline_and_uncertainty"];
function inventory() {
  const layers = LAYERS.map(id => ({
    id, assessments: Array.from({ length: 5 }, (_, i) => "assessment_" + (i + 1)),
  }));
  const depthLevels = Array.from({ length: 8 }, (_, i) =>
    ({ level: i + 1, id: "depth_" + (i + 1), objective: "Review documentation " + (i + 1) }));
  const tasks = layers.flatMap(layer => layer.assessments.flatMap(item =>
    depthLevels.map(depth => ({
      assessmentId: layer.id + "." + item,
      depthLevel: depth.level,
      depthId: depth.id,
      status: "pending_independent_review",
      independentlyVerified: false,
      scientificScore: null,
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

test("export provides exactly 320 separately labeled pending reviews in stable layer/depth order", () => {
  const m = inventory();
  const original = JSON.stringify(m);
  const csv = buildScientificDepthReviewCsv(m);
  const lines = csv.trimEnd().split("\r\n");
  assert.equal(lines.length, 321);
  assert.match(lines[0], /"nct_id","layer","assessment","depth_level","depth","review_objective"/);
  assert.match(lines[1], /^"NCT02142738","trial_design","trial_design.assessment_1","1"/);
  assert.match(lines[320], /^"NCT02142738","timeline_and_uncertainty","timeline_and_uncertainty.assessment_5","8"/);
  assert.equal(csv.match(/"PENDING_INDEPENDENT_REVIEW"/g).length, 320);
  assert.equal(csv.match(/"NOT_ASSIGNED"/g).length, 640);
  assert.equal(csv.match(/"FALSE"/g).length, 320);
  assert.doesNotMatch(csv, /,"APPROVED"|,"VERIFIED"|,"READY"/);
  assert.equal(JSON.stringify(m), original);
});

test("CSV does not permit formulas, newlines, or spreadsheet row injection from an objective", () => {
  const m = inventory();
  m.depthReview.depthLevels[0].objective = '\r\n =HYPERLINK("https://bad.example","click")';
  const csv = buildScientificDepthReviewCsv(m);
  assert.equal(csv.trimEnd().split("\r\n").length, 321);
  assert.match(csv, /"'\s+=HYPERLINK\(""https:\/\/bad\.example"",""click""\)"/);
  assert.doesNotMatch(csv, /\r\n =HYPERLINK/);
});

test("forged verified review, scientific score, probability, or incomplete records fail closed", () => {
  const mutations = [
    m => { m.nctId = "FAKE"; },
    m => { m.verification.verified_assessments = 1; },
    m => { m.verification.ready_for_analysis = true; },
    m => { m.verification.scientific_score = 80; },
    m => { m.verification.approval_probability = 0.9; },
    m => { m.depthReview.completedTasks = 1; },
    m => { m.depthReview.readyForScientificConclusion = true; },
    m => { m.depthReview.approvalProbability = 99; },
    m => { m.depthReview.tasks[0].status = "complete"; },
    m => { m.depthReview.tasks[0].independentlyVerified = true; },
    m => { m.depthReview.tasks[0].scientificScore = 90; },
    m => { m.depthReview.tasks.splice(0, 1); },
    m => { m.depthReview.tasks[0] = { ...m.depthReview.tasks[1] }; },
    m => { m.depthReview.tasks[0].depthId = "wrong"; },
    m => { m.layers[0].assessments[1] = m.layers[0].assessments[0]; },
    m => { m.depthReview.depthLevels[0].level = 9; },
    m => { m.depthReview.depthLevels[1].objective = ""; },
  ];
  for (const mutate of mutations) {
    const m = inventory();
    mutate(m);
    assert.throws(() => buildScientificDepthReviewCsv(m),
      /Scientific task export blocked/, String(mutate));
  }
});

test("trial UI offers CSV export only after validated exact-NCT inventory and does not touch scans", () => {
  const source = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(source, /Download 320-task review matrix \(CSV\)/);
  assert.match(source, /buildScientificDepthReviewCsv\(result\.investigation40\)/);
  assert.match(source, /disabled=\{!result\.investigation40\}/);
  assert.match(source, /scientific_320_depth_review\.csv/);
  assert.match(source, /No reviewer attestation or scientific decision/);
  assert.doesNotMatch(source, /runScan\(|placeTrade\(|saveGrade\(/);
});
