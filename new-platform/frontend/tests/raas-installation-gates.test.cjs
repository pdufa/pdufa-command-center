"use strict";
const test=require("node:test");
const assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true
 }}).outputText,file);
const {executeRaasReadinessScan}=require("../lib/raas-readiness-scan.ts");
const {evaluateRaasInstallation}=require("../lib/raas-installation-gates.ts");
const intake=require("../data/raas-ten-year-pdufa-intake.json");
const report=executeRaasReadinessScan();
test("all RAAS release gates report actual missing historical and calibration evidence",()=>{
 const r=evaluateRaasInstallation(report,intake);
 assert.equal(r.state,"INCOMPLETE");
 assert.equal(r.technicalBlueprintReady,true);
 assert.equal(r.completedGates,1);
 assert.equal(r.totalGates,6);
 assert.equal(r.remainingGates,5);
 assert.equal(r.eligibleSourceYears,0);
 assert.equal(r.sourceYears.length,10);
 assert.equal(r.gates.find(x=>x.id==="catalog").achieved,60);
 assert.equal(r.gates.find(x=>x.id==="top-calibration").achieved,0);
 assert.equal(r.gates.find(x=>x.id==="bottom-calibration").achieved,0);
 assert.equal(r.gates.find(x=>x.id==="historical-trades").achieved,0);
 assert.equal(r.gates.find(x=>x.id==="historical-census").achieved,0);
 assert.ok(r.gates.every(x=>x.blocker));
});
test("source-years cannot be promoted without independently sourced audit records",()=>{
 const allYears=intake.yearAudits.map(x=>({...x,status:"FULL_EVENT_CENSUS_AUDITED"}));
 const unlinked=evaluateRaasInstallation(report,{...intake,yearAudits:allYears});
 assert.equal(unlinked.eligibleSourceYears,0);
 const one=allYears.map(x=>x.year===2016?{...x,sourceUrl:"https://www.fda.gov/source/audit"}:x);
 const partial=evaluateRaasInstallation(report,{...intake,yearAudits:one});
 assert.equal(partial.eligibleSourceYears,1);
 assert.equal(partial.state,"INCOMPLETE");
 const dup=[...intake.yearAudits,{year:2016,status:"NOT_AUDITED"}];
 assert.throws(()=>evaluateRaasInstallation(report,{...intake,yearAudits:dup}),
  /RAAS_INSTALLATION_YEAR_CENSUS_INVALID/);
});
test("incomplete 60-metric catalog and wrong intake scope fail closed",()=>{
 assert.throws(()=>evaluateRaasInstallation({...report,metrics:report.metrics.slice(1)},intake),
  /RAAS_INSTALLATION_INPUT_INVALID/);
 assert.throws(()=>evaluateRaasInstallation(report,{...intake,scope:"SCORE_DONE"}),
  /RAAS_INSTALLATION_INPUT_INVALID/);
});
test("even spoofed report metrics cannot declare operational completion while final validation is absent",()=>{
 const forged={
  ...report,
  summary:{...report.summary,historicalAcceptedCases:60,reviewedTrialSnapshots:1},
  metrics:report.metrics.map(m=>({...m,approvedCalibration:true}))
 };
 const filled={...intake,yearAudits:intake.yearAudits.map(x=>({
   ...x,status:"FULL_EVENT_CENSUS_AUDITED",sourceUrl:"https://example.org/census"
 }))};
 const r=evaluateRaasInstallation(forged,filled);
 assert.equal(r.completedGates,6);
 assert.equal(r.state,"INCOMPLETE");
});
test("UI shows RAAS proof-level checklist on the main scan page",()=>{
 const p=fs.readFileSync(path.resolve(__dirname,"../app/raas-scan/page.tsx"),"utf8");
 assert.match(p,/data-raas-installation-gates/);
 assert.match(p,/data-raas-gate/);
 assert.match(p,/Installation acceptance checks/);
 assert.match(p,/2016–2025 study/);
 assert.match(p,/raas-alpaca-ten-year-study\.yml/);
});
