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
const { buildScientific800ReviewCsv } = require("../lib/scientific-800-review-csv.ts");

const LAYERS = ["trial_design", "efficacy", "safety", "biological_rationale",
  "statistical_integrity", "evidence_reproducibility", "regulatory", "timeline_and_uncertainty"];
function inventory() {
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

test("40 x 20 creates exactly 800 pending records, with separate methodological names", () => {
  const matrix = inventory();
  const before = JSON.stringify(matrix);
  const csv = buildScientific800ReviewCsv(matrix);
  const rows = csv.trimEnd().split("\r\n");
  assert.equal(rows.length, 801);
  assert.match(rows[0], /"depth_name","review_status","primary_source_url"/);
  assert.match(rows[1], /^"NCT02142738","trial_design\.assessment_1","1","document_reading","Document Reading"/);
  assert.match(rows[800], /^"NCT02142738","timeline_and_uncertainty\.assessment_5","20","red_team_adjudication"/);
  assert.equal((csv.match(/"PENDING_INDEPENDENT_REVIEW"/g) || []).length, 800);
  assert.equal((csv.match(/"NOT_VERIFIED"/g) || []).length, 800);
  assert.equal((csv.match(/"NOT_ASSIGNED"/g) || []).length, 3200);
  assert.doesNotMatch(csv, /"VERIFIED"|"APPROVED"|"SIGNED"/);
  assert.equal(JSON.stringify(matrix), before);
});

test("forged verified, scored, duplicated and partial input is refused", () => {
  const mutations = [
    m => { m.nctId = "OCUL"; },
    m => { m.verification.verified_assessments = 1; },
    m => { m.verification.approval_probability = 0.9; },
    m => { m.depthReview.completedTasks = 1; },
    m => { m.depthReview.tasks[0].scientificScore = 88; },
    m => { m.depthReview.tasks[0].independentlyVerified = true; },
    m => { m.depthReview.tasks.pop(); },
    m => { m.layers[0].assessments[0] = m.layers[0].assessments[1]; },
  ];
  for (const mutate of mutations) {
    const m = inventory();
    mutate(m);
    assert.throws(() => buildScientific800ReviewCsv(m),
      /Scientific task export blocked|Scientific 800 review export blocked/);
  }
});

test("isolated UI links the new 800-task export but retains the 320-task reviewer handoff", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /Download 800-point investigation plan \(CSV\)/);
  assert.match(ui, /buildScientific800ReviewCsv\(result\.investigation40\)/);
  assert.match(ui, /scientific_800_investigation_plan\.csv/);
  assert.match(ui, /Download 320-task review matrix \(CSV\)/);
  assert.match(ui, /Download reviewer A worksheet \(CSV\)/);
  assert.match(ui, /Download reviewer B worksheet \(CSV\)/);
  assert.doesNotMatch(ui, /runScan\(|placeTrade\(|saveGrade\(/);
});
