const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");

require.extensions[".ts"] = (module, file) => module._compile(
  ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText, file
);

const {FDA_REVIEW_WORKLIST_SNAPSHOT, auditFDAReviewWorklist} =
  require("../lib/fda-review-worklist-snapshot.ts");
const ui = fs.readFileSync(path.join(__dirname, "..", "app", "installation-audit", "page.tsx"), "utf8");

test("pinned official FDA published-letter source identities reconcile exactly", () => {
  const s = FDA_REVIEW_WORKLIST_SNAPSHOT;
  const derived = auditFDAReviewWorklist(s);
  assert.equal(s.asOf, "2026-10-25");
  assert.equal(s.sourceState, "QUARANTINED_RESEARCH_ONLY");
  assert.equal(s.publishedLetterReferences, 458);
  assert.equal(s.matchedOriginalApplicationReferences, 334);
  assert.equal(s.missingFromApprovalCentricRosterReferences, 107);
  assert.equal(s.ambiguousApplicationReferences, 17);
  assert.equal(s.distinctMissingApplicationCandidates, 84);
  assert.equal(derived.pendingLetterReferences, 124);
  assert.equal(derived.searchPackets, 101);
  assert.equal(derived.searchPackets, 84 + 17);
});

test("source search preparation cannot certify FDA review-cycle decisions or probabilities", () => {
  const s = FDA_REVIEW_WORKLIST_SNAPSHOT;
  assert.equal(s.independentlyVerifiedReviewCycles, 0);
  assert.equal(s.modelEligibleReviewCycles, 0);
  assert.equal(s.completeOriginalDecisionDenominatorVerified, false);
  assert.equal(s.predictionProbability, null);
  for (const changed of [
    {independentlyVerifiedReviewCycles: 1},
    {modelEligibleReviewCycles: 1},
    {completeOriginalDecisionDenominatorVerified: true},
    {predictionProbability: 0.8},
    {sourceState: "VERIFIED"},
    {publishedLetterReferences: 457},
    {distinctMissingApplicationCandidates: 108},
    {asOf: "2026-10-26"},
    {researchWorkflowUrl: "https://example.com"},
  ]) {
    assert.throws(() => auditFDAReviewWorklist({...s, ...changed}), /cannot be accepted/);
  }
});

test("SYSTEM STATUS shows dated research queue separately from live OUTCOME and is read-only", () => {
  assert.match(ui, /OUTCOME historical FDA source readiness — research only/);
  assert.match(ui, /quarantined FDA research workflow, not the live OUTCOME API/);
  assert.match(ui, /proven rejected or never approved/);
  assert.ok(ui.includes("<strong>not</strong>"));
  assert.match(ui, /fdaWorklist\.pendingLetterReferences/);
  assert.match(ui, /fdaWorklist\.searchPackets/);
  assert.match(ui, /fdaWorklist\.independentlyVerifiedReviewCycles/);
  assert.match(ui, /FDA approval probabilities remain unavailable/);
  assert.match(ui, /FDA_REVIEW_WORKLIST_SNAPSHOT\.researchWorkflowUrl/);
  assert.match(ui, /FDA_REVIEW_WORKLIST_SNAPSHOT\.reviewIssueUrl/);
  assert.doesNotMatch(ui, /\bonClick=|\bonSubmit=|\buseEffect\(/);
});
