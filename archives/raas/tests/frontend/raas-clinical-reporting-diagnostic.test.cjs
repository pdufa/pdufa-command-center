"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const ts=require("typescript"),fs=require("node:fs");
require.extensions[".ts"]=(module,file)=>module._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,esModuleInterop:true}}
).outputText,file);
const {raasClinicalReportingDiagnostic}=require("../lib/raas-clinical-reporting-diagnostic.ts");
const trial={nctId:"NCT00000001",ticker:"TST"};
const e=(posted=true)=>({
 ...trial,sourceUrl:"https://clinicaltrials.gov/study/NCT00000001",
 postedResults:posted,primaryResults:posted?[{
  measurements:[{groupId:"GX",value:"4"},{groupId:"GY",value:"3"}],
  comparisons:[{groupIds:["GX","GY"],pValue:"0.02",paramValue:"1",
   ciLowerLimit:"0.3",ciUpperLimit:"1.7"}]
 }]:[],
 seriousEventDetails:posted?[{term:"SAEs",groups:[
  {groupId:"GX",numAffected:2,numAtRisk:30}]}]:[]
});
test("5/5 posted-source reporting criteria calculate 100 documentation, never overall RAAS",()=>{
 const x=raasClinicalReportingDiagnostic(e(),trial);
 assert.equal(x.score,100);assert.equal(x.documentedOf5,5);
 assert.equal(x.fullRaasScore,null);
 assert.equal(x.kind,"CLINICAL_RESULTS_DOCUMENTATION_NOT_RAAS");
});
test("protocol-only incomplete reporting is N/A, not a zero efficacy grade",()=>{
 const x=raasClinicalReportingDiagnostic(e(false),trial);
 assert.equal(x.score,null);assert.equal(x.documentedOf5,null);
});
test("posted source with no relevant documentation can get 0 DOCUMENTATION only",()=>{
 const src=e();src.primaryResults=[];src.seriousEventDetails=[];
 const x=raasClinicalReportingDiagnostic(src,trial);
 assert.equal(x.score,0);
 assert.equal(x.fullRaasScore,null);
});
test("statistical p-value cannot backfill a missing CI or unknown group identity",()=>{
 const src=e();
 src.primaryResults[0].comparisons[0].ciUpperLimit="";
 let x=raasClinicalReportingDiagnostic(src,trial);
 assert.equal(x.score,80);assert.equal(x.facets.primaryConfidenceLimits,false);
 src.primaryResults[0].comparisons[0].groupIds=["GX"];
 x=raasClinicalReportingDiagnostic(src,trial);
 assert.equal(x.score,40);
 assert.equal(x.facets.identifiedGroupContrast,false);
 assert.equal(x.facets.statisticalResult,false);
});
test("exact NCT and ticker gate source carryover",()=>{
 assert.equal(raasClinicalReportingDiagnostic(e(),{...trial,nctId:"NCT00000002"}),null);
 assert.equal(raasClinicalReportingDiagnostic(e(),{...trial,ticker:"OTHER"}),null);
});
test("serious event affected count over denominator is excluded",()=>{
 const src=e();src.seriousEventDetails[0].groups[0].numAffected=31;
 const x=raasClinicalReportingDiagnostic(src,trial);
 assert.equal(x.score,80);assert.equal(x.facets.observedSeriousEventDenominators,false);
});
