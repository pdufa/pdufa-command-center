"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
const read=p=>fs.readFileSync(path.join(root,p),"utf8");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const registry=require("../lib/raas-registry-evidence.ts");
const sample=(nctId="NCT12345678",postedResults=false)=>({
 nctId,ticker:"TEST",sourceUrl:"https://clinicaltrials.gov/study/"+nctId,
 sourceHash:"a".repeat(64),retrievedAt:"2026-11-04T16:00:00Z",
 registryLastUpdated:"2026-10-12",resultsFirstPosted:postedResults?"2026-10-11":null,
 registryStatus:"COMPLETED",registeredPhases:["PHASE3"],
 registeredConditions:["Test disease"],registeredInterventions:["Test treatment"],
 primaryDefinitions:[{measure:"Primary clinical endpoint",timeFrame:"Week 12"}],
 postedResults,postedPrimaryOutcomeCount:postedResults?1:0,
 postedOtherOutcomeCount:0,
 primaryResults:postedResults?[{title:"Change in patient severity",timeFrame:"Week 12",
  unit:"points",analysisCount:1,pValues:["0.002"]}]:[],
 seriousAdverseEventTermCount:postedResults?2:0,
 evidenceState:postedResults?"POSTED_RESULTS_UNGRADED":"PROTOCOL_ONLY"
});
const index=(records)=>({schemaVersion:1,scope:"RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
 source:"ClinicalTrials.gov API v2 exact-NCT evidence",
 sourceAsOf:"2026-11-04T16:00:00Z",
 summary:{researchNcts:records.length,registryRecords:records.length,
  postedRegistryResults:records.filter(x=>x.postedResults).length,
  protocolOnly:records.filter(x=>!x.postedResults).length,approvedOverallRaasScores:0},
 records});
test("all indexed NCTs remain independent without any invented grades",()=>{
 const r=registry.parseRegistryEvidenceIndex(index([
  sample(),sample("NCT12345679",true)]));
 assert.equal(r.summary.researchNcts,2);
 assert.equal(r.summary.postedRegistryResults,1);
 assert.equal(r.summary.approvedOverallRaasScores,0);
 assert.equal(registry.registryTrialFor(r,{nctId:"NCT12345679",ticker:"TEST"}).postedResults,true);
 assert.equal(registry.registryTrialFor(r,{nctId:"NCT12345679",ticker:"FAKE"}),null);
 assert.equal(registry.registryTrialFor(r,{nctId:"NCT12345679",ticker:"TEST",drug:"Unrelated"}),null);
});
test("protocol is a TOP study-design lead only, not a BOTTOM result",()=>{
 const e=sample();
 const trial={nctId:e.nctId,ticker:e.ticker,drug:"Test treatment"};
 const pre=registry.registryMetricLeads(e,"pre",trial);
 assert.deepEqual(pre.map(x=>x.metricIds),[["pre-1-2"]]);
 assert.equal(pre[0].measurement,null);
 assert.equal(registry.registryMetricLeads(e,"post",trial).length,0);
 assert.equal(registry.registryMetricLeads(e,"pre",{...trial,drug:"Other therapy"}).length,0);
});
test("posted primary results, analyses and adverse terms stay source leads",()=>{
 const e=sample("NCT12345678",true);
 const trial={nctId:e.nctId,ticker:e.ticker,drug:"Test treatment"};
 const leads=registry.registryMetricLeads(e,"post",trial);
 assert.deepEqual(leads.flatMap(x=>x.metricIds),["post-1-1","post-1-3","post-1-5"]);
 assert.ok(leads.every(x=>x.measurement===null&&x.sourceUrl===e.sourceUrl));
 assert.ok(leads.every(x=>!Object.hasOwn(x,"grade")&&!Object.hasOwn(x,"score")));
 assert.ok(leads.every(x=>x.sourceDate===e.resultsFirstPosted));
});
test("identity, duplicate, missing and unpublished result claims rejected",()=>{
 const e=sample(); const base=index([e]);
 for(const bad of [
  index([e,e]),index([{...e,sourceUrl:"https://clinicaltrials.gov/study/NCT99999999"}]),
  index([{...e,sourceHash:"bad"}]),
  index([{...e,postedPrimaryOutcomeCount:1}]),
  {...base,summary:{...base.summary,postedRegistryResults:1}},
  {...base,summary:{...base.summary,approvedOverallRaasScores:99}}
 ])assert.throws(()=>registry.parseRegistryEvidenceIndex(bad),/RAAS_REGISTRY_INDEX/);
});
test("all-trial UI exposes primary evidence even without verified readout stage",()=>{
 const ui=read("app/RaasFullUniverseScores.tsx");
 const button=read("app/RaasRegistryEvidenceButton.tsx");
 const details=read("app/RaasMetricGradebook.tsx");
 const gradebook=read("lib/raas-metric-gradebook.ts");
 assert.match(ui,/RaasRegistryEvidenceButton row=\{x\.row\}/);
 assert.match(button,/data-raas-registry-evidence=\{row\.nctId\}/);
 assert.match(button,/loadRegistryEvidenceIndex/);
 assert.match(button,/not a numeric RAAS grade/);
 assert.match(details,/registrySourceLeadCount/);
 assert.match(details,/loadRegistryEvidenceIndex/);
 assert.match(gradebook,/registryMetricLeads/);
 for(const name of ["app/RaasFullUniverseScores.tsx","app/RaasRegistryEvidenceButton.tsx",
    "app/RaasMetricGradebook.tsx","lib/raas-registry-evidence.ts"]){
  const file=read(name);
  const out=ts.transpileModule(file,{fileName:name,reportDiagnostics:true,
   compilerOptions:{jsx:ts.JsxEmit.ReactJSX,target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext}});
  assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
 }
});
