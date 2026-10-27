const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const ts = require("typescript");
const vm = require("node:vm");
const lib = path.join(__dirname, "../lib");
function load(filename, requireFn) {
  const src = fs.readFileSync(path.join(lib, filename), "utf8");
  const compiled = ts.transpileModule(src, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const exports = {};
  vm.runInNewContext(compiled, { exports, require: requireFn });
  return exports;
}
const catalog = load("science-question-catalog.proposed.ts", require);
const register = load("peak-evidence-register.proposed.ts", () => catalog).PEAK_SCIENCE_REGISTER;
test("PEAK register is exact-trial and includes all catalog questions", () => {
  assert.equal(register.trialId, "NCT05208047");
  assert.equal(register.list, "GEM");
  assert.equal(register.assessments.length, 40);
  assert.deepEqual(Array.from(register.assessments, a=>a.id), Array.from(catalog.SCIENCE_QUESTION_CATALOG, q=>q.id));
});
test("no unverified evidence, scores, reviewers or FDA probabilities are fabricated", () => {
  assert.equal(register.approvalProbability, null);
  for (const a of register.assessments) {
    assert.equal(a.status, "NOT_REVIEWED");
    assert.equal(a.score, null);
    assert.equal(a.confidence, null);
    assert.equal(a.reviewer, null);
    assert.equal(a.evidence.length, 0);
    assert.ok(a.missingEvidence.length > 0);
  }
});
