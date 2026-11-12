const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const source = fs.readFileSync(path.join(__dirname, "../lib/science-question-catalog.proposed.ts"), "utf8");
const ts = require("typescript");
const vm = require("node:vm");
const compiled = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
const output = {};
vm.runInNewContext(compiled, { exports: output });
const questions = output.SCIENCE_QUESTION_CATALOG;
test("catalog contains 40 unique stable IDs across 8 layers", () => {
  assert.equal(questions.length, 40);
  assert.equal(new Set(questions.map(q => q.id)).size, 40);
  for (let i=0; i<40; i++) assert.equal(questions[i].id, "S"+String(i+1).padStart(2,"0"));
  for (let layer=1; layer<=8; layer++) assert.equal(questions.filter(q=>q.layer===layer).length, 5);
});
test("each proposed question has evidence requirements", () => {
  for (const q of questions) {
    assert.ok(q.question.length > 15);
    assert.ok(q.layerName.length > 3);
    assert.ok(q.requiredEvidence.length > 5);
    assert.equal("score" in q, false);
    assert.equal("approvalProbability" in q, false);
  }
  assert.equal(output.SCIENCE_QUESTION_CATALOG_IS_CERTIFIED, false);
});
