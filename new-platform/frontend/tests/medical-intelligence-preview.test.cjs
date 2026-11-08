const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const ts = require("typescript");

const source = fs.readFileSync(path.join(__dirname, "../lib/medical-intelligence-preview.ts"), "utf8");
const compiled = ts.transpileModule(source, {
  compilerOptions: {module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}
}).outputText;
const moduleObj = {exports:{}};
vm.runInNewContext(compiled, {module:moduleObj,exports:moduleObj.exports});
const {FAILURE_INVESTIGATIONS,INITIAL_DECISION,summarizeRegistryStudy} = moduleObj.exports;

test("Failure investigations are independent and cover clinical, condition and application risks", () => {
  assert.equal(FAILURE_INVESTIGATIONS.length,14);
  assert.equal(new Set(FAILURE_INVESTIGATIONS.map(d=>d.id)).size,14);
  const scopes=new Set(FAILURE_INVESTIGATIONS.map(d=>d.scope));
  assert.ok(scopes.has("Condition")&&scopes.has("Clinical trial")&&scopes.has("FDA application"));
  assert.ok(FAILURE_INVESTIGATIONS.some(d=>d.id==="cmc"));
  assert.ok(FAILURE_INVESTIGATIONS.some(d=>d.id==="timing"));
  assert.ok(!source.toLowerCase().includes("raas"));
});

test("Exact registry NCT validation prevents cross-candidate leakage", () => {
  const registry={protocolSection:{identificationModule:{nctId:"NCT01234567",briefTitle:"Illustrative trial"},conditionsModule:{conditions:["Example condition"]},armsInterventionsModule:{interventions:[{name:"Example medicine"}]},designModule:{phases:["PHASE3"],enrollmentInfo:{count:200},designInfo:{allocation:"RANDOMIZED",maskingInfo:{masking:"DOUBLE"}}},statusModule:{overallStatus:"COMPLETED"},outcomesModule:{primaryOutcomes:[{measure:"Primary benefit"}]}}};
  const result=summarizeRegistryStudy(registry,"NCT01234567");
  assert.equal(result.nct,"NCT01234567");
  assert.equal(result.enrollment,200);
  assert.equal(result.primaryEndpoints[0],"Primary benefit");
  assert.equal(result.resultsPosted,false);
  assert.throws(()=>summarizeRegistryStudy(registry,"NCT99999999"),/mismatch/);
});

test("Missing or present registry results never yield a fabricated approval decision", () => {
  assert.match(INITIAL_DECISION.applicationOutcome,/Indeterminate/);
  assert.match(INITIAL_DECISION.timingOutcome,/Indeterminate/);
  assert.equal(INITIAL_DECISION.adjudicatedBlockers,0);
  assert.match(INITIAL_DECISION.note,/missing public record/);
});
