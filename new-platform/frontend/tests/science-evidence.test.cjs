const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../lib/science-evidence.ts"), "utf8");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const exportsObject = {};
vm.runInNewContext(compiled, { exports: exportsObject });
const { assessScienceReadiness } = exportsObject;

function dossier() {
  return {
    schemaVersion: "science-evidence-v1", programId: "NCT123", list: "GEM_JR",
    cutoffDate: "2026-10-01",
    assessments: Array.from({ length: 40 }, (_, i) => ({
      id: "S" + (i + 1), layer: Math.floor(i / 5) + 1,
      depthLevel: (i % 20) + 1, score: 75, confidence: 80,
      evidence: [{ sourceUrl: "https://clinicaltrials.gov/study/NCT123", publishedAt: "2026-09-01", verifiedAt: "2026-09-30", verified: true, note: "test fixture" }],
      missingEvidence: [],
    })),
  };
}
test("complete source-dated dossier is ready without inventing approval probability", () => {
  const r = assessScienceReadiness(dossier());
  assert.equal(r.status, "READY_FOR_ANALYSIS");
  assert.equal(r.verifiedAssessments, 40);
  assert.equal(r.approvalProbability, null);
});
test("missing source is reluctant", () => {
  const d = dossier(); d.assessments[0].evidence = [];
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
});
test("future publication or verification is rejected", () => {
  const d = dossier(); d.assessments[0].evidence[0].publishedAt = "2026-10-02";
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
  d.assessments[0].evidence[0].publishedAt = "2026-09-01";
  d.assessments[0].evidence[0].verifiedAt = "2026-10-02";
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
});
test("missing assessment and duplicate IDs fail closed", () => {
  const d = dossier(); d.assessments.pop();
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
  d.assessments.push({ ...d.assessments[0] });
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
});
test("null score and invalid depth fail closed", () => {
  const d = dossier(); d.assessments[0].score = null;
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
  d.assessments[0].score = 75; d.assessments[0].depthLevel = 21;
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
});

test("forty assessments concentrated in seven layers are not ready", () => {
  const d = dossier();
  d.assessments[39].layer = 1;
  const result = assessScienceReadiness(d);
  assert.equal(result.status, "RELUCTANT");
  assert.ok(result.missing.some(x => x.includes("Incorrect assessment count in layer")));
});
test("malformed assessment record fails closed", () => {
  const d = dossier();
  d.assessments[3] = null;
  const result = assessScienceReadiness(d);
  assert.equal(result.status, "RELUCTANT");
  assert.ok(result.missing.includes("Malformed assessment record"));
});
test("assessment missing evidence arrays fails closed", () => {
  const d = dossier();
  delete d.assessments[0].evidence;
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
});

test("null evidence item fails closed without throwing", () => {
  const d = dossier();
  d.assessments[0].evidence = [null];
  assert.equal(assessScienceReadiness(d).status, "RELUCTANT");
});
