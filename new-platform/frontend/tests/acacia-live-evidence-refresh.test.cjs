"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const root=path.resolve(__dirname,"..");
function load(sourcePath,dependencies={}){
  const source=fs.readFileSync(path.join(root,sourcePath),"utf8");
  const compiled=ts.transpileModule(source,{compilerOptions:{
    target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS}}).outputText;
  const mod={exports:{}};
  vm.runInNewContext(compiled,{
    module:mod,exports:mod.exports,URL,Date,
    require:(name)=>{if(Object.hasOwn(dependencies,name))return dependencies[name];
      throw Error("Unapproved import in read-only test: "+name);
    }
  },{timeout:1000});
  return mod.exports;
}
const base=load("lib/pilot-research-readiness.ts");
const live=load("lib/acacia-live-evidence-refresh.ts",{
  "./pilot-research-readiness":base
});
const pilot=JSON.parse(fs.readFileSync(path.join(root,"data","acacia-pilot-prediction-workup-20261108.json"),"utf8"));
const clone=()=>structuredClone(pilot);
const now="2026-11-09T00:00:00.000Z";
const probe=(sourceId,status)=>({
  sourceId,status,observedAt:now,sourceUrl:live.pinnedSourceUrls[sourceId],
  message:"Synthetic official-source identity check"
});
const probes=(a="MATCH",b="MATCH")=>[probe("REGISTRY",a),probe("NEJM_PIVOTAL",b)];

test("exact Phase 3 pilot registry identity matches; wrong trial and phase are rejected",()=>{
  const sample={protocolSection:{
    identificationModule:{nctId:"NCT06081894",briefTitle:"ACACIA-HCM randomized aficamten in nonobstructive HCM"},
    designModule:{phases:["PHASE3"]}
  }};
  assert.equal(live.registryIdentityValid(sample),true);
  const wrong=structuredClone(sample);
  wrong.protocolSection.identificationModule.nctId="NCT11111111";
  assert.equal(live.registryIdentityValid(wrong),false);
  wrong.protocolSection.identificationModule.nctId="NCT06081894";
  wrong.protocolSection.designModule.phases=["PHASE2"];
  assert.equal(live.registryIdentityValid(wrong),false);
  assert.equal(live.registryIdentityValid(null),false);
});
test("publication identity rechecked against exact original PMID and research topic",()=>{
  const paper={resultList:{result:[{
    id:"42663312",pmid:"42663312",
    title:"Aficamten for Nonobstructive Hypertrophic Cardiomyopathy"
  }]}};
  assert.equal(live.publicationIdentityValid(paper),true);
  paper.resultList.result[0].pmid="1";
  assert.equal(live.publicationIdentityValid(paper),false);
  paper.resultList.result[0].pmid="42663312";
  paper.resultList.result[0].title="Unrelated journal publication";
  assert.equal(live.publicationIdentityValid(paper),false);
  assert.equal(live.publicationIdentityValid({resultList:{result:[]}}),false);
});
test("automatic source check recalculates all 3 prior documentary scores, not clinical grades",()=>{
  const r=live.evaluateSourceRefresh(clone(),probes(),now);
  assert.ok(r);
  assert.equal(r.schema,"MAIN_PILOT_DOCUMENTARY_REFRESH_V1");
  assert.equal(r.nct,"NCT06081894");
  assert.equal(r.currentness,"SOURCE_IDENTITIES_MATCH");
  assert.deepEqual(Array.from(r.cards.map(x=>[x.assessmentId,x.points,x.outOf])),[
    ["5.1",3,5],["4.2",3,5],["5.3",2,5]
  ]);
  assert.equal(r.evidenceSnapshotAsOf,"2026-11-08");
  assert.equal(r.mode,"ON_VIEW_REFRESH_NOT_BACKGROUND_SCAN");
  assert.equal(r.officialClinicalMethodGrades,0);
  assert.equal(r.independentPhaseVerified,false);
  assert.equal(r.fdaPrediction,"ABSTAIN");
  assert.equal(r.accuracy,"NOT_CALIBRATED");
  assert.equal(r.automaticClinicalRescore,false);
});
test("unavailable public API is neither an adverse clinical finding nor a green source check",()=>{
  const r=live.evaluateSourceRefresh(clone(),probes("UNAVAILABLE","MATCH"),now);
  assert.ok(r);
  assert.equal(r.currentness,"PARTIALLY_UNAVAILABLE");
  assert.equal(r.officialClinicalMethodGrades,0);
  const changed=live.evaluateSourceRefresh(clone(),probes("MATCH","CHANGED"),now);
  assert.equal(changed.currentness,"REVIEW_REQUIRED");
});
test("tampered snapshots, unknown source identifiers or newly assigned scores fail closed",()=>{
  const bad=[
    p=>{p.nct="NCT12345678";},
    p=>{p.phaseIndependentReviewerVerified=true;},
    p=>{p.scientificFramework.independentlyGradedMethodPositions=1;},
    p=>{p.provisionalResearchScore.gates[0].sourceId="FAKE";},
    p=>{p.additionalProvisionalResearchScores[1].gates[2].state="RESEARCH_OBSERVED";},
    p=>{p.finalDecision.approval="APPROVAL";}
  ];
  for(const fn of bad){
    const copy=clone();fn(copy);
    assert.equal(live.evaluateSourceRefresh(copy,probes(),now),null);
  }
  assert.equal(live.evaluateSourceRefresh(clone(),probes().reverse(),now),null);
  const wrong=probes();wrong[0].sourceUrl="https://invalid.example/pretend";
  assert.equal(live.evaluateSourceRefresh(clone(),wrong,now),null);
  assert.equal(live.evaluateSourceRefresh(clone(),probes(),"not-a-date"),null);
});
test("route requires established dashboard session and hardcoded public API GET only",()=>{
  const route=fs.readFileSync(path.join(root,"app/api/predictions/medical-provisional-refresh/route.ts"),"utf8");
  assert.match(route,/authConfigured\(\)/);
  assert.match(route,/hasSession\(/);
  assert.match(route,/getAll\("nct"\)/);
  assert.match(route,/probeSource\("REGISTRY"/);
  assert.match(route,/probeSource\("NEJM_PIVOTAL"/);
  assert.match(route,/redirect:"error"/);
  assert.match(route,/AbortSignal\.timeout\(10000\)/);
  assert.match(route,/force-dynamic/);
  assert.match(route,/private, no-store/);
  assert.doesNotMatch(route,/export async function POST\(/);
  assert.doesNotMatch(route,/PDUFA_MEDICAL_REVIEW_WRITES_ENABLED/);
});
test("preview UI refreshes on visibility and every 15 minutes without pretending to be scheduled background work",()=>{
  const ui=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotLiveEvidenceRefresh.tsx"),"utf8");
  const parent=fs.readFileSync(path.join(root,"app/predictions/assessment/PilotPredictionWorkup.tsx"),"utf8");
  assert.match(ui,/15\*60\*1000/);
  assert.match(ui,/visibilitychange/);
  assert.match(ui,/Check sources now/);
  assert.match(ui,/REVIEW_REQUIRED/);
  assert.match(ui,/automaticClinicalRescore===false/);
  assert.match(ui,/while nobody has the page open/);
  assert.match(ui,/Official scientific grades remain/i);
  assert.match(parent,/<PilotLiveEvidenceRefresh nct=\{nct\}/);
});
