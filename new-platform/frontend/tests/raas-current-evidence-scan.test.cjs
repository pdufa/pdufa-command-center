"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}
).outputText,file);
const pilot=require("../lib/raas-score-engine.ts").parseRaasPilotFeed(require("../data/raas-pilot-observations.json"));
const prospective=require("../lib/raas-prospective-source-baselines.ts").parseProspectiveSourceBaselines(
 require("../data/raas-prospective-source-baselines.json"));
const scan=require("../lib/raas-current-evidence-scan.ts").scanRaasCurrentEvidence;
const sourceAsOf="2026-11-02";
const run=(trial,stage)=>scan(pilot,prospective,trial,stage,sourceAsOf);
test("TOP source leads show both pre-readout programs without inventing overall RAAS",()=>{
 const l=run({nctId:"NCT07363577",ticker:"LBRX"},"pre");
 assert.equal(l.mappedMetrics,5);
 assert.equal(l.pilotObservations.length,3);
 assert.equal(l.prospectiveFacts.length,4);
 assert.equal(l.exploratoryTimingGrade.score,50);
 assert.equal(l.exploratoryTimingGrade.kind,"RESEARCH_ONLY_NOT_VALIDATED");
 assert.equal(l.approvedOverallScore,null);
 assert.equal(l.missingMetricCount,25);
 const trvi=run({nctId:"NCT07671911",ticker:"TRVI"},"pre");
 assert.equal(trvi.prospectiveFacts.length,5);
 assert.equal(trvi.pilotObservations.length,1);
 assert.equal(trvi.mappedMetrics,7);
 assert.equal(trvi.exploratoryTimingGrade,null);
 assert.equal(trvi.approvedOverallScore,null);
});
test("BOTTOM counts two CLDX trials separately but never implies two independent calibrations",()=>{
 const c1=run({nctId:"NCT06445023",ticker:"CLDX"},"post");
 const c2=run({nctId:"NCT06455202",ticker:"CLDX"},"post");
 const m=run({nctId:"NCT06641076",ticker:"MLTX"},"post");
 for(const c of [c1,c2]){
  assert.equal(c.pilotObservations.length,2);
  assert.equal(c.mappedMetrics,3);
  assert.equal(c.missingMetricCount,27);
  assert.equal(c.exploratoryTimingGrade,null);
  assert.equal(c.approvedOverallScore,null);
 }
 assert.equal(m.mappedMetrics,3);
 assert.equal(m.pilotObservations.length,2);
 assert.equal(m.approvedOverallScore,null);
});
test("Exact NCT plus listed issuer and stage gate every mapped fact",()=>{
 const wrong=run({nctId:"NCT07363577",ticker:"CLDX"},"pre");
 assert.equal(wrong.mappedMetrics,0);
 assert.equal(wrong.pilotObservations.length,0);
 assert.equal(wrong.prospectiveFacts.length,0);
 assert.equal(wrong.status,"NO_METRIC_SOURCE_LEADS");
 assert.equal(run({nctId:"NCT07363577",ticker:"LBRX"},"post").mappedMetrics,0);
 assert.equal(run({nctId:"NCT99999999",ticker:"TRVI"},"pre").mappedMetrics,0);
 assert.throws(()=>scan(pilot,prospective,{nctId:"NCT07363577",ticker:"LBRX"},"pre","2026-11-03"),/RAAS_EVIDENCE_SCAN_ASOF_INVALID/);
});
test("No pre-readout knowledge is transferred into an earlier time or as-of market snapshot",()=>{
 const a=scan(pilot,prospective,{nctId:"NCT07363577",ticker:"LBRX"},"pre","2026-04-01");
 assert.equal(a.pilotObservations.length,1);
 assert.equal(a.prospectiveFacts.length,1);
 assert.equal(a.mappedMetrics,1);
 assert.equal(a.exploratoryTimingGrade,null);
 const trvi=scan(pilot,prospective,{nctId:"NCT07671911",ticker:"TRVI"},"pre","2026-01-01");
 assert.equal(trvi.mappedMetrics,1);
 assert.equal(trvi.prospectiveFacts.length,1);
});
test("Spreadsheet RAAS cells are visibly populated with mapped sources and honest grade separation",()=>{
 const page=fs.readFileSync(path.join(__dirname,"../app/TrialRaasDisclosure.tsx"),"utf8");
 const sheets=fs.readFileSync(path.join(__dirname,"../app/Phase3ReadoutSheets.tsx"),"utf8");
 for(const marker of ["data-raas-current-scan","data-raas-source-scan","currentEvidence.mappedMetrics","currentEvidence.categories.map","currentEvidence.prospectiveFacts.map","Overall RAAS —/100 · pending"])
  assert.ok(page.includes(marker),marker);
 assert.ok(sheets.includes("<TrialRaasDisclosure row={row} bucket={bucket}"));
 for(const rel of ["lib/raas-current-evidence-scan.ts","app/TrialRaasDisclosure.tsx"]){
  const x=ts.transpileModule(fs.readFileSync(path.join(__dirname,"..",rel),"utf8"),{
   fileName:rel,reportDiagnostics:true,compilerOptions:{module:ts.ModuleKind.ESNext,
    target:ts.ScriptTarget.ES2022,jsx:ts.JsxEmit.ReactJSX}
  });
  assert.deepEqual((x.diagnostics||[]).filter(x=>x.category===ts.DiagnosticCategory.Error)
   .map(x=>ts.flattenDiagnosticMessageText(x.messageText," ")),[],rel);
 }
});
