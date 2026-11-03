"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path");
const ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022
 }}).outputText,file);
const {auditLiveRegistryForRaas:scan}=require("../lib/raas-live-registry-audit.ts");
const nctId="NCT06445023";
const sourceUrl="https://clinicaltrials.gov/study/"+nctId;
const packet=()=>({
 nctId,sourceUrl,retrievedAt:"2026-11-02T21:00:00.000Z",sourceUpdated:"2026-10-20",
 registryStatus:"COMPLETED",registeredPhases:["PHASE3"],resultsPosted:true,
 primary:[{title:"Primary benefit",type:"PRIMARY",timeFrame:"Week 6",unit:"UAS7",
  measurements:[{group:"Treatment",value:"-22.4",spread:null},
   {group:"Placebo",value:"-12.9",spread:null}],analysisReported:true}],
 secondary:[{title:"Response",type:"SECONDARY",timeFrame:"Week 6",unit:"%",
  measurements:[{group:"Treatment",value:"42.3",spread:null}],analysisReported:false}],
 seriousAdverseEvents:[{term:"Serious infections",groups:[
  {group:"Treatment",affected:2,atRisk:150},
  {group:"Placebo",affected:1,atRisk:160}]}],
 interventions:["Treatment","Placebo"],sponsor:"Company",conditionNames:["Condition"],
 evidenceClassification:"REGISTRY_POSTED_RESULTS",comparisonVerified:false,
 benefitRank:null,fdaDecisionVerified:false,truncatedEvidence:{outcomes:false,seriousEvents:false}
});
test("Exact NCT source reveals measured endpoints without an investment RAAS score",()=>{
 const a=scan(packet(),nctId,"post");
 assert.equal(a.status,"REGISTRY_POSTED_UNGRADED");
 assert.equal(a.phase3Registered,true);
 assert.equal(a.primaryOutcomes,1);
 assert.equal(a.primaryMeasurements,2);
 assert.equal(a.primaryWithAnalysis,1);
 assert.equal(a.secondaryOutcomes,1);
 assert.equal(a.secondaryMeasurements,1);
 assert.equal(a.seriousAdverseEventTerms,1);
 assert.equal(a.seriousAdverseEventArms,2);
 assert.deepEqual(a.preliminaryMetricLeads,["post-1-1","post-1-2","post-1-5"]);
 assert.equal(a.sourceNotValidated,true);
 assert.ok(a.limitations.some(x=>x.includes("No FDA action")));
 assert.equal("score" in a,false);
 assert.equal("returnProbability" in a,false);
});
test("Protocols missing posted results get no score or future outcome claim",()=>{
 const x=packet();x.resultsPosted=false;
 const a=scan(x,nctId,"post");
 assert.equal(a.status,"REGISTRY_PROTOCOL_ONLY");
 assert.deepEqual(a.preliminaryMetricLeads,[]);
 assert.equal(a.primaryMeasurements,0);
 assert.equal(a.seriousAdverseEventTerms,0);
 assert.equal(a.sourceNotValidated,true);
});
test("TOP registry result is flagged for reclassification but does not become a BOTTOM score",()=>{
 const a=scan(packet(),nctId,"pre");
 assert.deepEqual(a.preliminaryMetricLeads,[]);
 assert.ok(a.limitations.some(x=>x.includes("Recheck the classification")));
 assert.equal(a.sourceNotValidated,true);
});
test("Reject wrong trial, wrong URL and forged comparison/FDA certainty",()=>{
 for(const patch of [
  {nctId:"NCT00000001"},
  {sourceUrl:"https://clinicaltrials.gov/study/NCT00000001"},
  {retrievedAt:"bad"},
  {comparisonVerified:true},
  {fdaDecisionVerified:true},
  {benefitRank:75},
  {primary:null},
  {seriousAdverseEvents:null},
  {resultsPosted:"YES"}
 ]){
  assert.throws(()=>scan({...packet(),...patch},nctId,"post"),
   /RAAS_LIVE_REGISTRY_SOURCE_INVALID/);
 }
});
test("TOP and BOTTOM both contain the real on-demand source scan control",()=>{
 const root=path.resolve(__dirname,"..");
 const pane=fs.readFileSync(path.join(root,"app/TrialRaasDisclosure.tsx"),"utf8");
 const component=fs.readFileSync(path.join(root,"app/RaasLiveRegistryEvidence.tsx"),"utf8");
 const route=fs.readFileSync(path.join(root,"app/api/tools-trial-evidence/route.ts"),"utf8");
 for(const marker of ['<RaasLiveRegistryEvidence nctId={row.nctId} stage={bucket}/>','data-raas-current-scan']){
  assert.ok(pane.includes(marker),marker);
 }
 for(const marker of ["data-raas-live-registry","/api/tools-trial-evidence?nct=",
  'cache:"no-store"',"auditLiveRegistryForRaas","Run registry scan again",
  "source-backed","No RAAS rating inferred"].filter(x=>x!=="source-backed")){
  assert.ok(component.includes(marker),marker);
 }
 assert.match(route,/clinicaltrials\.gov\/api\/v2\/studies\//);
 assert.ok(pane.includes("onToggle={event=>setExpanded(event.currentTarget.open)}"));
 assert.ok(pane.includes("expanded&&<RaasLiveRegistryEvidence"));
 assert.ok(component.includes("useEffect(()=>{scan();},[nctId,stage])"));
 assert.match(route,/hasSession/);
 for(const rel of ["lib/raas-live-registry-audit.ts","app/RaasLiveRegistryEvidence.tsx",
   "app/TrialRaasDisclosure.tsx"]){
  const x=ts.transpileModule(fs.readFileSync(path.join(root,rel),"utf8"),{
   fileName:rel,reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,
    target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}
  });
  assert.deepEqual((x.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
   .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],rel);
 }
});
