const {test} = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const ts = require('typescript');
require.extensions['.ts'] = (module, file) => module._compile(ts.transpileModule(fs.readFileSync(file, 'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText, file);
const {validReviewSource, validReviewDate} = require('../lib/review-evidence.ts');
const fixture = require('../../validation/review-evidence-cases.json');

for (const item of fixture.cases) test('browser/API evidence agreement: ' + item.name, () => {
  assert.equal(validReviewSource(item.source), item.sourceValid);
  assert.equal(validReviewDate(item.reviewedOn, fixture.today), item.dateValid);
});
test('non-string imported review values are rejected', () => {
  for (const value of [null, undefined, 42, {}, []]) {
    assert.equal(validReviewSource(value), false);
    assert.equal(validReviewDate(value, fixture.today), false);
  }
});
