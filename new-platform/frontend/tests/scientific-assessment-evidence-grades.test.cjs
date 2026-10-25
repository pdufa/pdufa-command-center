"use strict";
const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
const React = require("react");
const { create, act } = require("react-test-renderer");
global.IS_REACT_ACT_ENVIRONMENT = true;

for (const ext of [".ts", ".tsx"]) {
  require.extensions[ext] = (mod, file) => mod._compile(
    ts.transpileModule(fs.readFileSync(file, "utf8"), {
      compilerOptions: {
        module: ts.ModuleKind.CommonJS,
        target: ts.ScriptTarget.ES2022,
        jsx: ts.JsxEmit.ReactJSX,
        esModuleInterop: true,
      },
    }).outputText, file,
  );
}
const Component = require("../app/ScientificAssessment.tsx").default;
const ID = "TRIAL|NCT02142738";
const NCT = "NCT02142738";
const LAYERS = [
  "trial_design", "efficacy", "safety", "biological_rationale",
  "statistical_integrity", "evidence_reproducibility", "regulatory", "timeline_and_uncertainty",
];

function payload(id = ID) {
  return {
    exactId: id,
    assessment: {
      overall_score: null, status: "insufficient_verified_evidence",
      domains: { trial_design: { score: null, verified_fields: 0, required_fields: 5, missing_fields: ["randomization"] } },
    },
    readinessGrades: {
      nctId: NCT, externalEvidenceVerified: false,
      scientificScore: null, fdaApprovalProbability: null,
      analysisReadiness: {
        grade: "C", coveragePercent: 63, requirementsCovered: 10, requirementsTotal: 16,
        readyForFullScientificConclusion: false, verdict: "NOT_READY", passFail: "FAIL_INCOMPLETE_INPUTS",
      },
      scientificReluctance: {
        grade: "F", level: "CRITICAL", reluctanceToConclude: "MAXIMUM",
        verdict: "WITHHOLD_SCIENTIFIC_CONCLUSION",
      },
    },
    investigation20: {
      nctId: NCT, levelCount: 20, scientificallyVerifiedLevels: 0,
      overallScore: null, fdaApprovalProbability: null,
      levels: Array.from({ length: 20 }, (_, i) => ({
        level: i + 1, title: "Review level " + (i + 1), status: "external_review_required",
        sourceEvidenceCount: 0, sourceFieldCount: 1, requiresExternalReview: true,
        scientificallyVerified: false, score: null, caution: "Independent source check required.",
      })),
    },
    investigation40: {
      nctId: NCT,
      layers: LAYERS.map(id => ({
        id, assessments: Array.from({ length: 5 }, (_, i) => "assessment_" + (i + 1)),
      })),
      verification: {
        required_assessments: 40, verified_assessments: 0, ready_for_analysis: false,
        scientific_score: null, approval_probability: null,
      },
      depthReview: { requiredTasks: 320, completedTasks: 0 },
    },
  };
}

function allText(root) {
  return root.findAll(() => true).map(node =>
    node.children.filter(child => typeof child === "string").join(" ")).join(" ");
}

async function mountAndLoad(data) {
  let tree;
  await act(async () => { tree = create(React.createElement(Component, { exactId: ID })); });
  const originalFetch = global.fetch;
  global.fetch = async () => ({ ok: true, json: async () => data, status: 200 });
  try {
    await act(async () => {
      await tree.root.findByType("button").props.onClick();
    });
    return tree;
  } finally {
    global.fetch = originalFetch;
  }
}

test("two evidence grades, 20 levels, eight layers and 40 tasks appear without outcome scores", async () => {
  const tree = await mountAndLoad(payload());
  const displayed = allText(tree.root);
  assert.match(displayed, /Analysis readiness: C/);
  assert.match(displayed, /Reluctance grade: F/);
  assert.match(displayed, /Maximum reluctance/);
  assert.match(displayed, /Level 1: Review level 1/);
  assert.match(displayed, /Level 20: Review level 20/);
  assert.match(displayed, /40 assessments/);
  assert.match(displayed, /0\/40 independently verified/);
  assert.match(displayed, /0\/320 planned in-depth review tasks/);
  assert.match(displayed, /FDA approval probability/);
  assert.match(displayed, /NOT ASSIGNED/);
  assert.doesNotMatch(displayed, /Scientific score: [0-9]/);
  assert.equal(tree.root.findAllByType("li").length, 60);
  await act(async () => tree.unmount());
});

test("unverified numeric scientific scores are blocked without displaying grades", async () => {
  const corrupted = payload();
  corrupted.assessment.overall_score = 95;
  const tree = await mountAndLoad(corrupted);
  assert.match(allText(tree.root), /unverified scientific score/);
  assert.equal(tree.root.findAllByProps({ "aria-label": "Two evidence readiness grades" }).length, 0);
  await act(async () => tree.unmount());
});

test("mismatched archived trial identity rejects all review claims", async () => {
  const corrupted = payload("TRIAL|NCT04280705");
  const tree = await mountAndLoad(corrupted);
  assert.match(allText(tree.root), /identity or structure failed verification/);
  assert.equal(tree.root.findAllByProps({ "aria-label": "Two evidence readiness grades" }).length, 0);
  await act(async () => tree.unmount());
});

test("missing archived evidence is labeled unavailable, never passed", async () => {
  const empty = payload();
  empty.readinessGrades = null;
  empty.investigation20 = null;
  empty.investigation40 = null;
  const tree = await mountAndLoad(empty);
  const displayed = allText(tree.root);
  assert.match(displayed, /grades are unavailable/);
  assert.match(displayed, /no checksum-verified trial archive/);
  assert.doesNotMatch(displayed, /Analysis readiness: A/);
  await act(async () => tree.unmount());
});

test("switching NCT clears previous trial grades and archived review levels", async () => {
  let tree;
  await act(async () => { tree = create(React.createElement(Component, { exactId: ID })); });
  const original = global.fetch;
  global.fetch = async () => ({ ok: true, status: 200, json: async () => payload() });
  try {
    await act(async () => { await tree.root.findByType("button").props.onClick(); });
    assert.match(allText(tree.root), /Analysis readiness: C/);
    await act(async () => tree.update(React.createElement(Component, { exactId: "TRIAL|NCT04280705" })));
    assert.doesNotMatch(allText(tree.root), /Analysis readiness: C/);
  } finally {
    global.fetch = original;
    await act(async () => tree.unmount());
  }
});
