"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {parseRegistryEvidenceIndex,registryTrialFor}=require("../lib/raas-registry-evidence.ts");
const nct="NCT12345678",sourceUrl="https://clinicaltrials.gov/study/"+nct;
const row=(posted=true)=>({
 nctId:nct,ticker:"TEST",sourceUrl,sourceHash:"f".repeat(64),
 retrievedAt:"2026-11-04T18:10:00Z",registryLastUpdated:"2026-11-04",
 resultsFirstPosted:posted?"2026-10-31":null,registryStatus:"COMPLETED",
 registeredPhases:["PHASE3"],registeredDesign:{allocation:"RANDOMIZED",masking:"DOUBLE",
  interventionModel:"PARALLEL",studyType:"INTERVENTIONAL",enrollment:210,enrollmentType:"ACTUAL"},
 registeredInterventions:["Drug A","Placebo"],registeredConditions:["Condition A"],
 primaryDefinitions:[{measure:"Symptoms",timeFrame:"Week 12"}],
 postedResults:posted,postedPrimaryOutcomeCount:posted?1:0,postedOtherOutcomeCount:0,
 primaryResults:posted?[{title:"Change in symptoms",timeFrame:"Week 12",unit:"points",
  analysisCount:1,pValues:["0.004"],
  groups:[{id:"OG000",title:"Drug A"},{id:"OG001",title:"Placebo"}],
  measurements:[{groupId:"OG000",value:"-13.5"},{groupId:"OG001",value:"-5.5"}],
  comparisons:[{groupIds:["OG000","OG001"],pValue:"0.004",method:"MMRM",
   paramType:"MEAN_DIFFERENCE",paramValue:"-8.0",ciPctValue:"95",
   ciLowerLimit:"-12.1",ciUpperLimit:"-3.9"}]}]:[],
 seriousAdverseEventTermCount:posted?1:0,
 seriousEventDetails:posted?[{term:"Infection",groups:[
  {groupId:"EG000",numAffected:4,numAtRisk:100,numEvents:5},
  {groupId:"EG001",numAffected:7,numAtRisk:110,numEvents:7}]}]:[],
 evidenceState:posted?"POSTED_RESULTS_UNGRADED":"PROTOCOL_ONLY"
});
const wrap=records=>({schemaVersion:1,scope:"RAAS_REGISTRY_TRIAL_EVIDENCE_INDEX",
 source:"ClinicalTrials.gov API v2 exact-NCT evidence",
 sourceAsOf:"2026-11-04T18:10:00Z",
 summary:{researchNcts:records.length,registryRecords:records.length,
 postedRegistryResults:records.filter(x=>x.postedResults).length,
 protocolOnly:records.filter(x=>!x.postedResults).length,approvedOverallRaasScores:0},records});
test("posted primary arm measurements and contrasts retain exact NCT and raw uncertainty without an invented RAAS score",()=>{
 const index=parseRegistryEvidenceIndex(wrap([row(true)]));
 const e=registryTrialFor(index,{nctId:nct,ticker:"TEST"});
 assert.equal(e.primaryResults[0].groups[0].title,"Drug A");
 assert.equal(e.primaryResults[0].measurements[0].value,"-13.5");
 assert.deepEqual(e.primaryResults[0].comparisons[0].groupIds,["OG000","OG001"]);
 assert.equal(e.primaryResults[0].comparisons[0].ciLowerLimit,"-12.1");
 assert.equal(e.primaryResults[0].comparisons[0].ciUpperLimit,"-3.9");
 assert.equal(e.seriousEventDetails[0].groups[0].numAtRisk,100);
 assert.equal(e.seriousEventDetails[0].groups[0].numAffected,4);
 assert.equal(index.summary.approvedOverallRaasScores,0);
 assert.equal(Object.hasOwn(e,"overallRaasScore"),false);
 assert.equal(registryTrialFor(index,{nctId:nct,ticker:"BAD"}),null);
});
test("quantitative counts are audited against actual source rows, not trusted metadata",()=>{
 const base=wrap([row(true)]);
 base.summary.trialsWithPrimaryComparisons=1;
 base.summary.trialsWithPrimaryGroupMeasurements=1;
 base.summary.trialsWithPrimaryConfidenceIntervals=1;
 base.summary.trialsWithSafetyRiskDenominators=1;
 assert.equal(parseRegistryEvidenceIndex(base).records.length,1);
 const invalid=structuredClone(base);
 invalid.summary.trialsWithPrimaryComparisons=2;
 assert.throws(()=>parseRegistryEvidenceIndex(invalid),/RAAS_REGISTRY_INDEX_SOURCE_COVERAGE_MISMATCH/);
});
test("protocol-only source cannot inject unpublished analyses, endpoints or SAE counts",()=>{
 const good=row(false);
 assert.deepEqual(parseRegistryEvidenceIndex(wrap([good])).records[0].primaryResults,[]);
 for(const patch of [
  {primaryResults:row(true).primaryResults},
  {seriousEventDetails:row(true).seriousEventDetails},
  {postedPrimaryOutcomeCount:1}
 ])assert.throws(()=>parseRegistryEvidenceIndex(wrap([{...good,...patch}])),/RAAS_REGISTRY_INDEX/);
});
test("safety denominator is a valid nonnegative integer and bound",()=>{
 for(const n of [-1,3.5,1000001]){
  const bad=row(true);bad.seriousEventDetails[0].groups[0].numAtRisk=n;
  assert.throws(()=>parseRegistryEvidenceIndex(wrap([bad])),/RAAS_REGISTRY_INDEX_SAE/);
 }
});
test("all-trial evidence panel exposes group measurements, confidence intervals and SAE numerator/denominator",()=>{
 const ui=fs.readFileSync(path.join(root,"app/RaasRegistryEvidenceButton.tsx"),"utf8");
 assert.match(ui,/data-raas-registry-primary-group-values="true"/);
 assert.match(ui,/data-raas-registry-primary-statistics="true"/);
 assert.match(ui,/data-raas-registry-serious-event-numerators="true"/);
 assert.match(ui,/numAffected/);assert.match(ui,/numAtRisk/);
 const out=ts.transpileModule(ui,{fileName:"RaasRegistryEvidenceButton.tsx",
  reportDiagnostics:true,compilerOptions:{jsx:ts.JsxEmit.ReactJSX,module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}});
 assert.deepEqual((out.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error),[]);
});
