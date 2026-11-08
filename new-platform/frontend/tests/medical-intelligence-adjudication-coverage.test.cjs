const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const path=require("node:path");
const ts=require("typescript");
const cache={};
function load(name){
 if(cache[name])return cache[name];
 const src=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const js=ts.transpileModule(src,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 vm.runInNewContext(js,{module,exports:module.exports,require:(dep)=>{
   if(!dep.startsWith("./"))throw Error("Unexpected dependency "+dep);
   return load(dep.slice(2));
 }});
 cache[name]=module.exports;
 return module.exports;
}
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
const {ADJUDICATION_CASES,INVESTIGATION_PRIORITIES,getAdjudicationCase,adjudicationForCycle}=load("medical-intelligence-clinical-adjudication");
const {ADJUDICATION_WAVE_A}=load("medical-intelligence-clinical-adjudication-wave-a");
const {ADJUDICATION_WAVE_B}=load("medical-intelligence-clinical-adjudication-wave-b");
test("Full 23-cycle coverage, source-typed 87 claims, and no invented future FDA action",()=>{
 assert.equal(APPLICATION_CYCLES.length,23);
 assert.equal(ADJUDICATION_WAVE_A.length,6);
 assert.equal(ADJUDICATION_WAVE_B.length,6);
 assert.equal(ADJUDICATION_CASES.length,23);
 assert.equal(ADJUDICATION_CASES.reduce((n,x)=>n+x.sources.length,0),87);
 assert.equal(new Set(ADJUDICATION_CASES.map(x=>x.id)).size,23);
 assert.equal(new Set(ADJUDICATION_CASES.map(x=>x.cycleId)).size,23);
 for(const app of APPLICATION_CYCLES){
   assert.equal(adjudicationForCycle(app.id).length,1,app.id);
   assert.equal(getAdjudicationCase(adjudicationForCycle(app.id)[0].id).cycleId,app.id);
 }
 for(const item of ADJUDICATION_CASES){
   const app=APPLICATION_CYCLES.find(x=>x.id===item.cycleId);
   assert.ok(app.ncts.includes(item.nct));
   assert.equal(item.researchDate,"2026-11-07");
   assert.ok(item.clinicalSynthesis.length>100);
   assert.ok(item.bestCase.length>60);
   assert.equal(item.timing,"NO_NEW_TIMING_EVENT_PROVEN");
   assert.ok(item.sources.some(x=>x.role==="CHALLENGING"));
   assert.ok(item.sources.some(x=>x.role==="FAVORABLE"));
   assert.ok(item.whatWouldResolve.length>=4);
   for(const evidence of item.sources){
     assert.match(evidence.trial,/^NCT\d{8}$/);
     assert.match(evidence.url,/^https:\/\//);
     assert.ok(evidence.date<="2026-11-07");
     for(const prop of ["title","section","measure","limits","result"]){
       assert.ok(evidence[prop].length>20,item.cycleId+" claim "+evidence.id+": "+prop);
     }
     if(!app.ncts.includes(evidence.trial))
       assert.equal(evidence.scope,"RELATED_EXTERNAL_TRIAL","Unmarked external trial "+item.cycleId+" "+evidence.id);
     if(evidence.scope==="RELATED_EXTERNAL_TRIAL")
       assert.ok(!app.ncts.includes(evidence.trial),"Incorrect external-trial flag for "+evidence.id);
   }
 }
 assert.equal(INVESTIGATION_PRIORITIES.length,22);
});
test("ABTECT maintenance belongs to NCT05535946, not ABTECT-2 induction",()=>{
 const c=getAdjudicationCase("abvx-uc-dose-transportability");
 assert.equal(c.nct,"NCT05507216");
 const induction=c.sources.find(s=>s.id==="abvx-induction25");
 assert.equal(induction.trial,"NCT05507216");
 assert.match(induction.result,/0.1034/);
 const maintenance=c.sources.find(s=>s.id==="abvx-maintenance");
 assert.equal(maintenance.trial,"NCT05535946");
 assert.equal(maintenance.scope,"RELATED_EXTERNAL_TRIAL");
 assert.match(maintenance.limits,/not.*ABTECT-2/i);
});
test("Already FDA-approved obstructive aficamten is not a pending PDUFA alert",()=>{
 const c=getAdjudicationCase("cytk-obstructive-approved-status");
 assert.equal(c.cycleId,"cytk-aficamten-ohcm");
 assert.equal(c.verdict,"ALREADY_APPROVED_NO_PENDING_FIRST_APPROVAL");
 assert.equal(c.mode,"REGULATORY_STATUS_CORRECTION");
 const fda=c.sources.find(s=>s.id==="cytk-fda-approved");
 assert.equal(fda.type,"FDA_PUBLIC_APPROVAL");
 assert.equal(fda.trial,"NCT05186818");
 assert.equal(fda.scope,"RELATED_EXTERNAL_TRIAL");
 assert.match(fda.result,/December 19, 2025/);
 assert.ok(!INVESTIGATION_PRIORITIES.some(a=>a.cycleId===c.cycleId));
 const n=getAdjudicationCase("cytk-nonobstructive-safety");
 assert.equal(n.cycleId,"cytk-aficamten-nhcm");
 assert.equal(n.verdict,"UNRESOLVED_REQUIRES_INDEPENDENT_ADJUDICATION");
 assert.match(n.sources.find(x=>x.id==="cytk-nhcm-lvef").result,/10.5%/);
});
test("IR on-demand vs XR prevention are separately monitored, not combined or assigned the other's deadline",()=>{
 const ir=getAdjudicationCase("phvs-ir-acute-response");
 const xr=getAdjudicationCase("phvs-xr-prevention-subgroups");
 assert.equal(ir.cycleId,"phvs-ondemand");
 assert.equal(xr.cycleId,"phvs-prophylaxis");
 assert.notEqual(ir.nct,xr.nct);
 assert.match(ir.sources.find(x=>x.id==="phvs-ir-relief").result,/1.28 hours/);
 assert.match(xr.sources.find(x=>x.id==="phvs-xr-primary").result,/83%/);
 const a=APPLICATION_CYCLES.find(x=>x.id===xr.cycleId);
 assert.equal(a.reportedGoal,null);
 assert.equal(a.stage,"PLANNED");
 assert.match(xr.sourceInterpretation,/not an FDA review event/i);
});
test("Single-arm UGN-103 denominator, and peer-reviewed blinded IgG4 flare evidence, stay distinct",()=>{
 const u=getAdjudicationCase("urgn-singlearm-response");
 assert.match(u.sources.find(x=>x.id==="urgn-cr").limits,/No randomized comparator/);
 assert.match(u.sources.find(x=>x.id==="urgn-dor").limits,/Not 94.5% of all/);
 const z=getAdjudicationCase("zbio-organ-flare-steroid");
 assert.equal(z.sources.find(x=>x.id==="zbio-flare").type,"PEER_REVIEWED_TRIAL");
 assert.match(z.sources.find(x=>x.id==="zbio-flare").result,/26\/97/);
 assert.match(z.sources.find(x=>x.id==="zbio-steroid").result,/929.8 mg/);
 assert.match(z.sources.find(x=>x.id==="zbio-safety").limits,/cannot exclude uncommon/);
});
