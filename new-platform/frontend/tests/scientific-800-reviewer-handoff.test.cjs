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

test("two separate 800-task reviewer templates are blank, source-linked and exact-NCT", () => {
  const { matrix, audit } = fixture();
  const before = JSON.stringify({ matrix, audit });
  const a = buildScientific800ReviewerHandoffCsv(matrix, audit, "A");
  const b = buildScientific800ReviewerHandoffCsv(matrix, audit, "B");
  assert.notEqual(a, b);
  for (const [text, slot] of [[a, "A"], [b, "B"]]) {
    const rows = text.trimEnd().split("\r\n");
    assert.equal(rows.length, 801);
    assert.match(rows[0], /"reviewer_slot","linked_requirement_ids","linked_archive_inputs_present"/);
    assert.match(rows[0], /"reviewer_name","qualification_verified","original_document_url"/);
    assert.match(rows[0], /"source_bytes_verified","review_finding_notes","reviewer_decision","reviewer_signature"/);
    assert.ok(rows[1].startsWith('"NCT02142738","trial_design.assessment_1","1","document_reading"'));
    assert.match(rows[1], new RegExp(',"' + slot + '","archive_integrity;design;eligibility;interventions;enrollment;registered_primary;protocol_sap"'));
    assert.match(rows[800], new RegExp(',"' + slot + '","timeline;published_results;official_regulatory"'));
    assert.equal((text.match(/"PENDING_INDEPENDENT_REVIEW"/g) || []).length, 800);
    assert.equal((text.match(/"NOT_SUBMITTED"/g) || []).length, 1600);
    assert.equal((text.match(/"NOT_VERIFIED"/g) || []).length, 2400);
    assert.equal((text.match(/"NOT_ASSIGNED"/g) || []).length, 3200);
    assert.doesNotMatch(text, /"VERIFIED"|"APPROVED"|"SIGNED"/);
  }
  assert.equal(JSON.stringify({ matrix, audit }), before);
});

test("fake reviewer slot, cross-trial mismatch and forged clinical/source completion block handoff", () => {
  const { matrix, audit } = fixture();
  assert.throws(() => buildScientific800ReviewerHandoffCsv(matrix, audit, "C"),
    /Scientific 800 reviewer export blocked/);
  for (const mutate of [
    ({ audit }) => { audit.nctId = "NCT04280705"; },
    ({ matrix }) => { matrix.depthReview.completedTasks = 1; },
    ({ matrix }) => { matrix.depthReview.tasks[0].scientificScore = 88; },
    ({ matrix }) => { matrix.verification.verified_assessments = 1; },
    ({ matrix }) => { matrix.depthReview.tasks.splice(0, 1); },
    ({ audit }) => { audit.requirements[12].independentlyVerified = true; },
    ({ audit }) => { audit.requirements[15].available = true; },
    ({ audit }) => { audit.scientificReluctance.grade = "A"; },
    ({ audit }) => { audit.fdaApprovalProbability = 0.7; },
  ]) {
    const input = fixture();
    mutate(input);
    assert.throws(() => buildScientific800ReviewerHandoffCsv(input.matrix, input.audit, "B"),
      /Scientific task export blocked|Scientific input checklist export blocked|Scientific 800 evidence map blocked/);
  }
});

test("trial page offers 800-task handoffs for two blank reviewer slots and retains 320-task process", () => {
  const ui = fs.readFileSync(path.join(__dirname, "../app/ScientificAssessment.tsx"), "utf8");
  assert.match(ui, /Independent 800-point reviewer handoff/);
  assert.match(ui, /Download 800-point reviewer A worksheet \(CSV\)/);
  assert.match(ui, /Download 800-point reviewer B worksheet \(CSV\)/);
  assert.match(ui, /buildScientific800ReviewerHandoffCsv\(result.investigation40, result.readinessGrades, reviewerSlot\)/);
  assert.match(ui, /scientific_800_reviewer_/);
  assert.match(ui, /Download reviewer A worksheet \(CSV\)/);
  assert.match(ui, /Download reviewer B worksheet \(CSV\)/);
  assert.match(ui, /Compare returned A\/B worksheets locally/);
  assert.doesNotMatch(ui, /runScan\(|placeTrade\(|saveGrade\(/);
});
