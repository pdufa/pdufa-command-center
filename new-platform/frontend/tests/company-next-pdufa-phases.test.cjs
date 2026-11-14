const test=require("node:test");
const assert=require("node:assert/strict");
const {readFileSync}=require("node:fs");
const {join}=require("node:path");

const root=join(__dirname,"..");
const app=(...pieces)=>readFileSync(join(root,"app",...pieces),"utf8");
const evidence=JSON.parse(readFileSync(join(root,"..","..","data",
  "focus_nightly_evidence_current.json"),"utf8"));
const roster=JSON.parse(readFileSync(join(root,"data","p3PostDataActive.json"),"utf8"));
const applications=readFileSync(join(root,"lib","medical-intelligence-applications.ts"),"utf8");

test("COMPANY and popup list future candidates with separate clinical and FDA stages",()=>{
  const ui=app("IntelligenceHub.tsx");
  assert.match(ui,/Next PDUFA candidates/);
  assert.match(ui,/clinicalPhases/);
  assert.match(ui,/phaseByNct/);
  assert.match(ui,/phaseLabel\(entry\.phase\)/);
  assert.match(ui,/registryStatusLabel\(entry\.registryStatus\)/);
  assert.match(ui,/FDA application stage/);
  assert.match(ui,/c\.stage!=="APPROVED_ALREADY"/);
  assert.match(ui,/c\.reportedGoal===null|!c\.reportedGoal/);
  assert.match(ui,/PDUFA goal/);
  assert.match(ui,/Company pipeline programs outside FOCUS/);
  assert.match(ui,/data.*report|No current verified registry phase/);
  assert.match(ui,/phaseProps/);
  assert.equal((ui.match(/<CompanyDetails ticker=/g)||[]).length,2,
    "Both COMPANY sub-tab and company popup should share the same candidate list");
});
test("clinical phase source is source-verified, nightly, read-only, and fail-closed",()=>{
  const api=app("api","company-phase-status","route.ts");
  assert.match(api,/focus_nightly_evidence_current\.json/);
  assert.match(api,/https:\/\/clinicaltrials\.gov\/study\//);
  assert.match(api,/sourceStatus/);
  assert.match(api,/OFFICIAL_REGISTRY_RETRIEVED/);
  assert.match(api,/72\*60\*60\*1000/);
  assert.match(api,/phase:phases/);
  assert.match(api,/source exact-NCT roster|Source exact-NCT roster/i);
  assert.match(api,/status:503/);
  assert.match(api,/no phase inferred/i);
  const ui=app("IntelligenceHub.tsx");
  assert.match(ui,/fetch\("\/api\/company-phase-status"/);
  assert.match(ui,/phaseLoadState==="AVAILABLE"/);
  assert.match(ui,/phaseAgeStatus==="STALE"/);
});
test("clinical registry phase snapshot remains linked by exact NCT, not ticker alone",()=>{
  assert.equal(roster.records.length,32);
  assert.equal(evidence.summary.focusTrials,roster.records.length);
  assert.equal(evidence.trials.length,roster.records.length);
  const byNct=new Map(roster.records.map(x=>[x.nct,x.ticker]));
  assert.equal(byNct.size,32);
  const seen=new Set();
  for(const t of evidence.trials){
    assert.equal(t.ticker,byNct.get(t.nct));
    assert.ok(!seen.has(t.nct));
    assert.match(t.nct,/^NCT\d{8}$/);
    assert.ok(Array.isArray(t.phase));
    assert.ok(t.phase.every(p=>["PHASE1","PHASE2","PHASE3","PHASE4","NA","EARLY_PHASE1"].includes(p)));
    assert.equal(t.sourceStatus,"OFFICIAL_REGISTRY_RETRIEVED");
    seen.add(t.nct);
  }
  const missing=roster.records.filter(r=>!seen.has(r.nct)).map(r=>r.nct).sort();
  assert.deepEqual(missing,[],"The current registry snapshot covers all exact-NCT roster records");
  assert.match(applications,/id:|\"id\":/);
});
