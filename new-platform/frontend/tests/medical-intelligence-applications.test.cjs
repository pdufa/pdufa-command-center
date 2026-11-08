const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const source=fs.readFileSync(path.join(__dirname,"../lib/medical-intelligence-applications.ts"),"utf8");
const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
const mod={exports:{}};
vm.runInNewContext(compiled,{module:mod,exports:mod.exports});
const {APPLICATION_CYCLES,CYCLE_COUNTS,applicationsForNct}=mod.exports;
const focus=JSON.parse(fs.readFileSync(path.join(__dirname,"../data/p3PostDataActive.json"),"utf8"));
const ncts=new Set(focus.records.map(r=>r.nct));
test("All exact NCTs link to a distinct product/indication/review cycle",()=>{
 assert.equal(APPLICATION_CYCLES.length,23);
 assert.equal(new Set(APPLICATION_CYCLES.map(a=>a.id)).size,23);
 for(const a of APPLICATION_CYCLES){
  assert.match(a.sourceUrl,/^https:\/\//);
  assert.match(a.sourceDate,/^\d{4}-\d{2}-\d{2}$/);
  assert.ok(a.sourceDate<="2026-11-07");
  assert.ok(a.ncts.length>0);
  assert.ok(a.criticalQuestion.length>20);
  for(const nct of a.ncts)assert.ok(ncts.has(nct),"Unlisted NCT: "+nct);
  if(["PLANNED","PRIOR_CRL_RESUBMISSION_PLANNED","SUBMITTED_PENDING_ACCEPTANCE","APPROVED_ALREADY"].includes(a.stage))
    assert.equal(a.reportedGoal,null,"No forecasted goal allowed for "+a.id);
 }
 for(const nct of ncts)assert.ok(applicationsForNct(nct).length>0,"Unlinked FOCUS NCT: "+nct);
 assert.equal(CYCLE_COUNTS.total,APPLICATION_CYCLES.length);
});
test("No trial-count/app-count conflation for Sarepta, Cytokinetics and Pharvaris",()=>{
 assert.equal(applicationsForNct("NCT02500381").length,2,"ESSENCE supports distinct supplement applications");
 assert.notEqual(applicationsForNct("NCT05767346")[0].id,applicationsForNct("NCT06081894")[0].id,"Approved obstructive and planned non-obstructive indications differ");
 assert.notEqual(applicationsForNct("NCT06343779")[0].id,applicationsForNct("NCT06669754")[0].id,"On-demand and prophylactic NDAs differ");
 assert.equal(applicationsForNct("NCT05767346")[0].stage,"APPROVED_ALREADY");
 assert.equal(applicationsForNct("NCT06411379")[0].stage,"SUBMITTED_PENDING_ACCEPTANCE");
 assert.equal(applicationsForNct("NCT00000000").length,0);
});
