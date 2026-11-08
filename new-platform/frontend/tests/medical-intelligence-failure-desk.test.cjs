const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");
function load(f){
 const src=fs.readFileSync(path.join(__dirname,"../lib/"+f+".ts"),"utf8");
 const compiled=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const m={exports:{}};
 vm.runInNewContext(compiled,{module:m,exports:m.exports});
 return m.exports;
}
const {FAILURE_DESK,FAILURE_DESK_AS_OF,FAILURE_DESK_CYCLE_IDS,deskIssuesForCycle}=load("medical-intelligence-failure-desk");
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
test("Each failure investigation belongs to the exact application and sourced historical record",()=>{
 const ids=new Set(APPLICATION_CYCLES.map(c=>c.id));
 assert.ok(FAILURE_DESK.length>=10);
 assert.equal(new Set(FAILURE_DESK.map(i=>i.id)).size,FAILURE_DESK.length);
 assert.equal(FAILURE_DESK_AS_OF,"2026-11-07");
 assert.equal(FAILURE_DESK_CYCLE_IDS.length,new Set(FAILURE_DESK.map(i=>i.cycleId)).size);
 for(const issue of FAILURE_DESK){
  assert.ok(ids.has(issue.cycleId),"Unknown application "+issue.cycleId);
  assert.match(issue.sourceDate,/^20\d\d-\d\d-\d\d$/);
  assert.ok(issue.sourceDate<=FAILURE_DESK_AS_OF,"Future dated source "+issue.id);
  assert.match(issue.sourceUrl,/^https:\/\//);
  for(const key of ["title","observation","whyItMatters","responseOrCounterevidence","decisiveFollowUp","sourceTitle"]){
    assert.ok(typeof issue[key]==="string"&&issue[key].length>15,issue.id+" missing "+key);
  }
  assert.ok(deskIssuesForCycle(issue.cycleId).some(i=>i.id===issue.id));
 }
 assert.equal(deskIssuesForCycle("not-a-cycle").length,0);
});
test("Historical extension not confused with a new forecast and CMC gaps not described as confirmed failure",()=>{
 const svra=deskIssuesForCycle("svra-molgramostim");
 const historical=svra.find(x=>x.evidenceClass==="PRIOR_EXTENSION");
 assert.ok(historical);
 assert.equal(historical.resolutionState,"HISTORICAL_EVENT");
 assert.equal(historical.consequence,"REVIEW_TIMING");
 const lor=deskIssuesForCycle("mlys-lorundrostat");
 assert.equal(lor[0].evidenceClass,"REVIEW_GAP");
 assert.equal(lor[0].resolutionState,"NOT_ESTABLISHED");
 assert.ok(deskIssuesForCycle("capr-deramiocel").some(x=>x.evidenceClass==="FDA_REVIEWER_OBJECTION"));
 assert.ok(deskIssuesForCycle("cogt-gist").some(x=>x.evidenceClass==="TRIAL_SIGNAL"));
});
