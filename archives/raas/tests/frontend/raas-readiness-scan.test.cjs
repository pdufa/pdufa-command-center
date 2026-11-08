"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),os=require("node:os");
const child=require("node:child_process"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,
 compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true}
}).outputText,file);
const {executeRaasReadinessScan}=require("../lib/raas-readiness-scan.ts");
const raw=executeRaasReadinessScan();
test("RAAS source scan actually inspects exactly 60 stage-specific metrics and all 12 categories",()=>{
 assert.equal(raw.schemaVersion,1);
 assert.equal(raw.scanExecution,"COMPLETED_READ_ONLY_SOURCE_AUDIT");
 assert.equal(raw.finalScoring,"NOT_VALIDATED");
 assert.equal(raw.summary.metricsInspected,60);
 assert.equal(raw.metrics.length,60);
 assert.equal(raw.categories.length,12);
 assert.equal(raw.summary.preMetricsInspected,30);
 assert.equal(raw.summary.postMetricsInspected,30);
 assert.equal(new Set(raw.metrics.map(m=>m.stage+"|"+m.id)).size,60);
 assert.ok(raw.categories.every(g=>g.total===5));
 assert.ok(raw.metrics.every(m=>m.requiredEvidence&&m.reason&&m.name));
});
test("The output exposes missing real historical evidence, never synthetic scores",()=>{
 const s=raw.summary;
 assert.equal(s.approvedMetricCalibrations,0);
 assert.equal(s.reviewEligibleMetrics,0);
 assert.equal(s.historicalTradeCases,0);
 assert.equal(s.historicalAcceptedCases,0);
 assert.equal(s.historicalRatedMetrics,0);
 assert.equal(s.reviewedTrialSnapshots,0);
 assert.ok(raw.metrics.every(m=>m.status==="MISSING_HISTORICAL_VALIDATION"));
 assert.ok(raw.metrics.every(m=>m.approvedCalibration===false&&m.historicalReviewEligible===false));
 assert.ok(raw.metrics.every(m=>m.holdoutTrainIssuers===0&&m.holdoutTestIssuers===0));
});
test("Recorded clinical leads and independent nominal-price audits count accurately but never as RAAS grades",()=>{
 const s=raw.summary;
 assert.equal(s.prospectiveIssuers,2);
 assert.equal(s.prospectivePrograms,2);
 assert.equal(s.prospectiveSourceFacts,9);
 assert.equal(s.retrospectiveResearchWindows,8);
 assert.equal(s.independentlyConfirmedNominalCloses,14);
 assert.equal(s.nominalClosePoints,16);
 assert.equal(s.secShareBridgeCases,8);
 assert.equal(s.secShareCapMismatches,2);
 assert.equal(s.fdaPrimaryCrosschecks,5);
 const lbrx=raw.metrics.find(m=>m.id==="pre-4-1");
 const trvi=raw.metrics.find(m=>m.id==="pre-1-1");
 assert.equal(lbrx.prospectiveIssuerCount,2);
 assert.ok(lbrx.prospectiveSourceFacts>=3);
 assert.equal(trvi.prospectiveIssuerCount,1);
 assert.equal(trvi.approvedCalibration,false);
 assert.ok(raw.limitations.some(x=>/source audit completed/i.test(x)));
});
test("retired readiness CLI cannot run or overwrite a saved scan",()=>{
 const temp=fs.mkdtempSync(path.join(os.tmpdir(),"pdufa-raas-retired-"));
 try{
  const output=path.join(temp,"scan.json");fs.writeFileSync(output,'{"historical":true}');
  const r=child.spawnSync(process.execPath,["scripts/raas-readiness-scan.cjs"],{cwd:path.resolve(__dirname,".."),env:{...process.env,RAAS_SCAN_OUTPUT:output},encoding:"utf8",timeout:30000});
  assert.notEqual(r.status,0);assert.match(r.stderr,/RAAS_PERMANENTLY_RETIRED/);
  assert.equal(fs.readFileSync(output,"utf8"),'{"historical":true}');
 }finally{fs.rmSync(temp,{force:true,recursive:true});}
});
test("retired readiness UI cannot load calculators or expose scoring controls",()=>{
 const root=path.resolve(__dirname,"..");
 const page=fs.readFileSync(path.join(root,"app/raas-scan/page.tsx"),"utf8");
 const historical=fs.readFileSync(path.join(root,"app/raas-history/page.tsx"),"utf8");
 const trial=fs.readFileSync(path.join(root,"app/TrialRaasDisclosure.tsx"),"utf8");
 assert.match(page,/permanently retired/);assert.doesNotMatch(page,/from ["'][^"']*raas-/);
 assert.match(historical,/archive\/raas/);assert.doesNotMatch(historical,/analyzeRaasHistoricalReturns/);
 assert.doesNotMatch(trial,/computeRaasScore|scanRaasCurrentEvidence|href=["']\/raas-scan/);
});
