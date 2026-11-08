const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const source=fs.readFileSync(path.join(__dirname,"../lib/medical-intelligence-specialist-casebook.ts"),"utf8");
const js=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod={exports:{}};
vm.runInNewContext(js,{module:mod,exports:mod.exports});
const {SPECIALIST_CASES,specialistCaseForCycle}=mod.exports;
test("Three source-examined specialty interpretations contain seven grounded clinical dimensions each",()=>{
 assert.equal(SPECIALIST_CASES.length,3);
 assert.equal(new Set(SPECIALIST_CASES.map(x=>x.cycleId)).size,3);
 for(const item of SPECIALIST_CASES){
  assert.equal(item.completedSpecialistSignoff,false);
  assert.equal(item.conclusion,"PARTIAL_SOURCED_RESEARCH");
  assert.match(item.source,/^https:\/\//);
  assert.equal(item.dimensions.length,7);
  assert.ok(item.medicalQuestion.length>60);
  for(const x of item.dimensions){
   assert.ok(x.observedClinicalEvidence.length>60);
   assert.ok(x.specialistInterpretation.length>60);
   assert.ok(x.neededToResolve.length>60);
  }
  assert.equal(specialistCaseForCycle(item.cycleId).specialty,item.specialty);
 }
 assert.equal(specialistCaseForCycle("unknown"),null);
});
test("Case studies preserve distinct neuromuscular, endocrine and oncology reasoning",()=>{
 assert.match(specialistCaseForCycle("capr-deramiocel").specialty,/Neuromuscular/);
 assert.match(specialistCaseForCycle("cort-relacorilant").specialty,/Endocrinology/);
 assert.match(specialistCaseForCycle("cogt-gist").specialty,/oncology/);
 const cort=JSON.stringify(specialistCaseForCycle("cort-relacorilant"));
 assert.match(cort,/between-arm.*not statistically significant/);
 const cogt=JSON.stringify(specialistCaseForCycle("cogt-gist"));
 assert.match(cogt,/10.8%.*1.4%/);
 const capr=JSON.stringify(specialistCaseForCycle("capr-deramiocel"));
 assert.match(capr,/0.66 PUL points/);
});
