const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
function load(name,modules={}){
 const code=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const js=ts.transpileModule(code,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 vm.runInNewContext(js,{module,exports:module.exports,require:n=>{
  if(!(n in modules))throw Error("Unexpected dependency "+n);
  return modules[n];
 }});
 return module.exports;
}
const apps=load("medical-intelligence-applications");
const findings=load("medical-intelligence-reviewed-findings");
const decision=load("medical-intelligence-decision-brief",{
 "./medical-intelligence-applications":apps,
 "./medical-intelligence-reviewed-findings":findings
});
test("All 23 application briefs preserve indecision without evidence-overstating forecasts",()=>{
 for(const cycle of apps.APPLICATION_CYCLES){
  const brief=decision.buildDecisionBrief(cycle.id);
  assert.ok(brief,"missing decision brief for "+cycle.id);
  assert.equal(brief.researchState,"INITIAL_SOURCE_MAPPING_ONLY");
  assert.equal(brief.confidence,"NOT_CALIBRATED");
  assert.ok(brief.evidenceLimitations.length>=4);
  const arr=["approvalEvidence","documentedFdaObjections","pastCrls","scientificUncertainties","priorExtensions","otherEvidence"];
  assert.ok(arr.some(key=>brief[key].length>0),"missing source-backed findings "+cycle.id);
  assert.equal(brief.outcome,cycle.stage==="APPROVED_ALREADY"?"ALREADY_APPROVED":"INDETERMINATE");
  assert.equal(brief.timing,cycle.stage==="APPROVED_ALREADY"?"NOT_APPLICABLE":"INDETERMINATE");
 }
 assert.equal(decision.buildDecisionBrief("not-a-cycle"),null);
});
test("Do not turn historical CRL, failed endpoint or past extension into future forecasts",()=>{
 const achv=decision.buildDecisionBrief("achv-cytisinicline");
 assert.ok(achv.pastCrls.length>0);
 assert.equal(achv.outcome,"INDETERMINATE");
 const srpt=decision.buildDecisionBrief("srpt-casimersen");
 assert.ok(srpt.scientificUncertainties.length>0);
 assert.equal(srpt.outcome,"INDETERMINATE");
 const capr=decision.buildDecisionBrief("capr-deramiocel");
 assert.ok(capr.priorExtensions.length>0);
 assert.ok(capr.documentedFdaObjections.length>0);
 assert.equal(capr.timing,"INDETERMINATE");
 const cytk=decision.buildDecisionBrief("cytk-aficamten-ohcm");
 assert.equal(cytk.outcome,"ALREADY_APPROVED");
});
