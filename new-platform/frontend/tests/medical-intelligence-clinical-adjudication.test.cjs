const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const ts=require("typescript");
const cache={};
function load(name){
 if(cache[name])return cache[name];
 const source=fs.readFileSync(path.join(__dirname,"../lib/"+name+".ts"),"utf8");
 const compiled=ts.transpileModule(source,{compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
 const module={exports:{}};
 vm.runInNewContext(compiled,{module,exports:module.exports,require:spec=>{
   if(!spec.startsWith("./"))throw Error("Unknown dependency "+spec);
   return load(spec.slice(2));
 }});
 cache[name]=module.exports;
 return module.exports;
}
const {APPLICATION_CYCLES}=load("medical-intelligence-applications");
const {ADJUDICATION_CASES,ADJUDICATION_AS_OF,INVESTIGATION_PRIORITIES,adjudicationForCycle,getAdjudicationCase,adverseEventAbsoluteDifference}=load("medical-intelligence-clinical-adjudication");
test("Exact application and NCT identity, source authorship, and dates checked for all deep issue comparisons",()=>{
 assert.equal(ADJUDICATION_CASES.length,23);
 assert.equal(ADJUDICATION_AS_OF,"2026-11-07");
 assert.equal(new Set(ADJUDICATION_CASES.map(x=>x.id)).size,23);
 const caseCycles=new Set(ADJUDICATION_CASES.map(x=>x.cycleId));
 assert.equal(caseCycles.size,23);
 for(const c of ADJUDICATION_CASES){
   const app=APPLICATION_CYCLES.find(a=>a.id===c.cycleId);
   assert.ok(app,"Unknown application "+c.cycleId);
   assert.ok(app.ncts.includes(c.nct),"Foreign NCT "+c.nct);
   assert.equal(c.researchDate,ADJUDICATION_AS_OF);
   assert.equal(c.verdict,c.cycleId==="cytk-aficamten-ohcm"?"ALREADY_APPROVED_NO_PENDING_FIRST_APPROVAL":"UNRESOLVED_REQUIRES_INDEPENDENT_ADJUDICATION");
   assert.equal(c.timing,"NO_NEW_TIMING_EVENT_PROVEN");
   assert.ok(c.sources.length>=3);
   assert.ok(c.sources.some(x=>x.role==="FAVORABLE"));
   assert.ok(c.sources.some(x=>x.role==="CHALLENGING"));
   assert.ok(c.clinicalSynthesis.length>100);
   assert.ok(c.bestCase.length>60);
   assert.ok(c.whatWouldResolve.length>=4);
   for(const claim of c.sources){
     assert.ok(app.ncts.includes(claim.trial)||claim.scope==="RELATED_EXTERNAL_TRIAL","Unattributed external NCT "+claim.trial+" for "+c.cycleId);
     assert.match(claim.url,/^https:\/\//);
     assert.ok(claim.date<=ADJUDICATION_AS_OF,"Future evidence not allowed: "+claim.id);
     assert.match(claim.date,/^20\d\d-\d\d-\d\d$/);
     for(const property of ["measure","result","limits","section","title"]){
       assert.ok(claim[property].length>20,claim.id+" missing "+property);
     }
     if(claim.type==="SPONSOR_REPORT_OF_FDA_COMMUNICATION")
       assert.notEqual(claim.type,"FDA_REVIEWER");
   }
   assert.equal(getAdjudicationCase(c.id).cycleId,c.cycleId);
   assert.equal(adjudicationForCycle(c.cycleId).length,1);
 }
 assert.equal(getAdjudicationCase("not-a-case"),null);
 assert.equal(adjudicationForCycle("unknown").length,0);
});
test("FDA prespecified PUL failure is not replaced by modified SAP result",()=>{
 const c=getAdjudicationCase("capr-hope3-analysis");
 assert.equal(c.mode,"ANALYSIS_CONFLICT");
 const original=c.sources.find(x=>x.id==="capr-fda-original");
 const revised=c.sources.find(x=>x.id==="capr-modified");
 assert.equal(original.type,"FDA_REVIEWER");
 assert.equal(revised.type,"FDA_DOCUMENTED_APPLICANT_ANALYSIS");
 assert.match(original.result,/p=0\.24/);
 assert.match(revised.result,/p=0\.029/);
 assert.match(original.result,/0\.66 PUL points/);
 assert.match(revised.result,/4\.55%/);
 assert.notEqual(original.measure,revised.measure);
});
test("VELA-2 NCT and sponsor Type B description cannot be presented as final FDA determination",()=>{
 const c=getAdjudicationCase("mltx-vela2-estimand");
 assert.equal(c.nct,"NCT06411379");
 assert.equal(c.sources.find(x=>x.id==="mltx-composite").result.includes("p=0.053"),true);
 assert.equal(c.sources.find(x=>x.id==="mltx-treatment-policy").result.includes("p=0.033"),true);
 assert.equal(c.sources.find(x=>x.id==="mltx-fda-typeb").type,"SPONSOR_REPORT_OF_FDA_COMMUNICATION");
 assert.match(c.sourceInterpretation,/not a public FDA determination/);
 const a=APPLICATION_CYCLES.find(x=>x.id===c.cycleId);
 assert.equal(a.reportedGoal,null,"No invented accepted PDUFA date after submission");
});
test("AD109 dropouts are distinct from treatment-related serious events",()=>{
 const c=getAdjudicationCase("apmd-synairgy-clinical");
 assert.equal(c.nct,"NCT05813275");
 const r=adverseEventAbsoluteDifference(69,325,10,319);
 assert.equal(r.treatedPercent,21.23);
 assert.equal(r.controlPercent,3.13);
 assert.equal(r.excessPercentagePoints,18.10);
 const ae=c.sources.find(x=>x.id==="apmd-discontinuation");
 const serious=c.sources.find(x=>x.id==="apmd-serious-safety");
 assert.ok(ae.result.includes("69/325"));
 assert.ok(serious.result.includes("5/325"));
 assert.ok(serious.limits.includes("distinct categories"));
 assert.throws(()=>adverseEventAbsoluteDifference(4,3,1,2));
 assert.throws(()=>adverseEventAbsoluteDifference(1,0,1,2));
});
test("No automated approval odds and already-approved indication excluded from forward review queue",()=>{
 assert.equal(INVESTIGATION_PRIORITIES.length,22);
 assert.ok(!INVESTIGATION_PRIORITIES.some(x=>x.cycleId==="cytk-aficamten-ohcm"));
 assert.ok(INVESTIGATION_PRIORITIES.every(x=>x.currentOutcome==="INDETERMINATE"));
 assert.ok(INVESTIGATION_PRIORITIES.every(x=>x.missingCoreEvidence.length===4));
 assert.ok(INVESTIGATION_PRIORITIES.some(x=>x.cycleId==="apmd-ad109"&&x.detailedCaseCount===1));
 assert.ok(INVESTIGATION_PRIORITIES.some(x=>x.cycleId==="achv-cytisinicline"&&x.goal===null));
});
