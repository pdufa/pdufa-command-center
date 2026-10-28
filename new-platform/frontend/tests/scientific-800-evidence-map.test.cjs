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

test("eight layers link 16 source requirements to 800 unreviewed tasks", () => {
  const { matrix, audit } = fixture();
  const original = JSON.stringify({matrix, audit});
  const result = buildScientific800EvidenceMap(matrix, audit);
  assert.equal(result.nctId, "NCT02142738");
  assert.equal(result.layers.length, 8);
  assert.equal(result.totalPendingTasks, 800);
  assert.equal(result.independentlyReviewedTasks, 0);
  assert.equal(result.independentlyVerifiedEvidenceSources, 0);
  assert.equal(result.readyForScientificConclusion, false);
  assert.equal(result.fdaApprovalProbability, null);
  assert.deepEqual(result.layers.map(x => x.layerId), LAYERS);
  assert.ok(result.layers.every(x => x.pendingTasks === 100 && x.assessmentIds.length === 5));
  assert.ok(result.layers.every(x => x.independentlyReviewedTasks === 0));
  const all = new Set(result.layers.flatMap(x => x.dependencies.map(d => d.id)));
  assert.deepEqual([...all].sort(), [...REQUIREMENT_IDS].sort());
  assert.ok(result.layers.every(x =>
    x.sourceInputsPresent === x.dependencies.filter(d => d.available).length));
  assert.ok(result.layers.some(x => x.dependencies.some(d =>
    d.evidenceLevel === "independent_review_not_loaded")));
  assert.equal(SCIENTIFIC_800_SOURCE_DEPENDENCIES.length, 8);
  assert.equal(JSON.stringify({matrix, audit}), original);
});

test("identity mismatch, forged score or forged source approval fails closed", () => {
  for (const mutate of [
    ({ audit }) => { audit.nctId = "NCT04280705"; },
    ({ matrix }) => { matrix.nctId = "OCUL"; },
    ({ matrix }) => { matrix.verification.verified_assessments = 1; },
    ({ matrix }) => { matrix.depthReview.tasks[0].scientificScore = 90; },
    ({ matrix }) => { matrix.depthReview.tasks.pop(); },
    ({ audit }) => { audit.requirements[15].available = true; },
    ({ audit }) => { audit.requirements[13].independentlyVerified = true; },
    ({ audit }) => { audit.scientificReluctance.grade = "A"; },
    ({ audit }) => { audit.fdaApprovalProbability = 0.8; },
  ]) {
    const input = fixture();
    mutate(input);
    assert.throws(() => buildScientific800EvidenceMap(input.matrix, input.audit),
      /Scientific input checklist export blocked|Scientific task export blocked|Scientific 800 evidence map blocked/);
  }
});

test("trial UI visibly distinguishes the eight-layer source map from completed science", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /800-point evidence dependency map/);
  assert.match(ui, /0\/800 independently reviewed/);
  assert.match(ui, /buildScientific800EvidenceMap\(result\.investigation40!, result\.readinessGrades!\)/);
  assert.match(ui, /Source coverage and review completion are separate measurements/);
  assert.match(ui, /Download 800-point investigation plan \(CSV\)/);
  assert.match(ui, /Download reviewer A worksheet \(CSV\)/);
  assert.doesNotMatch(ui, /runScan\(|placeTrade\(|saveGrade\(/);
});
