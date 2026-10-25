const { test } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const ts = require("typescript");
for (const ext of [".ts", ".tsx"]) require.extensions[ext] = (module, file) =>
  module._compile(ts.transpileModule(fs.readFileSync(file, "utf8"), {
    compilerOptions: {module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX,esModuleInterop:true},
  }).outputText,file);
const { auditScienceIndex, auditOutcomeStatus } = require("../lib/science-outcome-gates.ts");
const weights = {PIPELINE:[25,20,15,15,10,10,5],GEM_JR:[20,15,20,15,15,10,5],GEM:[25,20,15,15,10,10,5]};
const empty = () => [null,0,0,...Array(7).fill(0),...Array(7).fill(0)];
const complete = w => [100,100,100,...w,...w];
function index(hasComplete = false) {
  return {
    status:"COMPLETE",modelVersion:"candidate-assessments-v1",version:"source-v1",
    workspaceVersion:"workspace-v1",asOf:"2026-10-25",computedAt:"2026-10-25T22:00:00Z",
    total:1,registryLinked:0,registryMissing:1,reviewSource:"AVAILABLE",
    totals:{PIPELINE:{complete:hasComplete?1:0,partial:0,missing:hasComplete?0:1},
      GEM_JR:{complete:0,partial:0,missing:1},GEM:{complete:0,partial:0,missing:1}},
    records:[["TRIAL|NCT00000001",hasComplete?complete(weights.PIPELINE):empty(),empty(),empty(),[]]],
  };
}
function hop() {
  return {status:"RESEARCH_ONLY",checkedAt:"2026-10-25T22:00:00Z",
    publishedLetters:458,approvedApplications:29416,sourcePageReviewRows:458,
    independentlyVerifiedReviewCycles:0,modelEligibleReviewCycles:0,
    modelValidated:false,predictionAvailable:false,denominatorComplete:false,probability:null};
}
test("reads exact score model completeness without claiming any SCIENCE-40 certification",()=>{
  const status = auditScienceIndex(index());
  assert.equal(status.total,1);
  assert.equal(status.registryMissing,1);
  assert.equal(status.scores.PIPELINE.missing,1);
  assert.equal(status.scientific40Verified,false);
  assert.equal(status.clinicalOutcomeCertified,false);
  const s2=auditScienceIndex(index(true));
  assert.equal(s2.scores.PIPELINE.complete,1);
  assert.equal(s2.scientific40Verified,false);
});
test("science source totals must match every model's exact records and no duplicate identities",()=>{
  const bad=index();
  bad.totals.GEM_JR.complete=1;
  assert.throws(()=>auditScienceIndex(bad),/reconcile/);
  const mismatch=index();
  mismatch.registryLinked=1;
  assert.throws(()=>auditScienceIndex(mismatch),/reconcile/);
  const duplicate=index();duplicate.total=2;duplicate.registryMissing=2;
  duplicate.records.push(duplicate.records[0]);duplicate.totals.PIPELINE.missing=2;
  duplicate.totals.GEM_JR.missing=2;duplicate.totals.GEM.missing=2;
  assert.throws(()=>auditScienceIndex(duplicate),/coverage/);
  assert.throws(()=>auditScienceIndex({status:"BUILDING"}),/not complete/);
});
test("OUTCOME remains blocked with zero independently model-eligible FDA cycles",()=>{
  const r=auditOutcomeStatus(hop());
  assert.equal(r.modelEligibleReviewCycles,0);
  assert.equal(r.modelValidated,false);
  assert.equal(r.predictionAvailable,false);
  assert.equal(r.publishedLetters,458);
});
test("outcome fails closed if the status unexpectedly declares a prediction or unvalidated cohort",()=>{
  for (const changed of [
    {modelEligibleReviewCycles:1},{predictionAvailable:true},{modelValidated:true},
    {probability:0.78},{denominatorComplete:true},{status:"READY"},
    {independentlyVerifiedReviewCycles:-3},{checkedAt:"unknown"},
  ]) assert.throws(()=>auditOutcomeStatus({...hop(),...changed}));
});
