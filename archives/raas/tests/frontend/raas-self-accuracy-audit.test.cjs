"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
 module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022,esModuleInterop:true
 }}).outputText,file);
const {executeRaasReadinessScan}=require("../lib/raas-readiness-scan.ts");
const {evaluateRaasInstallation}=require("../lib/raas-installation-gates.ts");
const {auditRaasSurveyAccuracy}=require("../lib/raas-self-accuracy-audit.ts");
const intake=require("../data/raas-active-2024-2025-pdufa-intake.json");
const fda=require("../data/raas-fda-three-way-accuracy-site-snapshot.json");
const report=executeRaasReadinessScan();
const installation=evaluateRaasInstallation(report,intake);
const run=(r=report,i=installation,f=fda)=>auditRaasSurveyAccuracy(r,i,f);

test("current self-audit rates RAAS reliability NOT MEASURABLE, never zero accuracy",()=>{
 const a=run();
 assert.equal(a.scope,"RAAS_SURVEY_ACCURACY_SELF_AUDIT");
 assert.equal(a.status,"NOT_MEASURABLE");
 assert.equal(a.numericAccuracyRating,null);
 assert.equal(a.independentReturnAccuracyPct,null);
 assert.equal(a.independentFDAThreeWayAccuracyPct,null);
 assert.equal(a.raasGatesPassed,1);
 assert.equal(a.raasGatesRequired,5);
 assert.deepEqual(a.raasGates.map(g=>[g.id,g.achieved,g.passed]),[
  ["metric-catalog",60,true],
  ["historical-census",0,false],
  ["return-cases",0,false],
  ["issuer-disjoint-holdout",0,false],
  ["approved-calibrations",0,false]
 ]);
 assert.equal(a.fdaProspectiveGate.achieved,0);
 assert.equal(a.fdaProspectiveGate.passed,false);
 assert.equal(a.retrospectiveDifferenceInCorrectCalls,-4);
 assert.equal(a.retrospectiveBaselineDifferencePctPoints,-2.74);
});
test("misleading FDA percentages, stale calibrations and corrupted class list fail closed",()=>{
 assert.throws(()=>run(report,installation,{...fda,legacyRetrospectiveAccuracyPct:99}),
  /RAAS_SELF_AUDIT_FDA_SNAPSHOT_INCONSISTENT/);
 assert.throws(()=>run(report,installation,{...fda,approvedRaasMetricCalibrations:60}),
  /RAAS_SELF_AUDIT_FDA_SNAPSHOT_INCONSISTENT/);
 assert.throws(()=>run(report,installation,{...fda,classes:["PASS","CRL"]}),
  /RAAS_SELF_AUDIT_FDA_SNAPSHOT_INCONSISTENT/);
 assert.throws(()=>run(report,installation,{...fda,alwaysApproveCorrect:147}),
  /RAAS_SELF_AUDIT_FDA_SNAPSHOT_INCONSISTENT/);
});
test("a retrospective baseline or unsigned prospective counts cannot become certified accuracy",()=>{
 const spoofed={...fda,
  predecisionThreeWayIndependentlyVerifiedForecasts:50,
  approvedThreeWayFDAOutcomeModel:true,
  completeEligibleCohortIndependentlyVerified:true,
  independentOutcomeAdjudicationComplete:true,
  certifiedFDAThreeWayPredictionAccuracyPct:94};
 const a=run(report,installation,spoofed);
 assert.equal(a.status,"EVIDENCE_UNDER_REVIEW");
 assert.equal(a.fdaProspectiveGate.passed,false);
 assert.equal(a.independentFDAThreeWayAccuracyPct,null);
 assert.equal(a.numericAccuracyRating,null);
});
test("60 metric identities, holdout totals and acceptance gates must reconcile",()=>{
 assert.throws(()=>run({...report,metrics:report.metrics.slice(1)}),
  /RAAS_SELF_AUDIT_SOURCE_INCONSISTENT/);
 assert.throws(()=>run({...report,summary:{...report.summary,approvedMetricCalibrations:1}}),
  /RAAS_SELF_AUDIT_SOURCE_INCONSISTENT/);
 assert.throws(()=>run(report,{...installation,eligibleSourceYears:2}),
  /RAAS_SELF_AUDIT_SOURCE_INCONSISTENT/);
});
test("retired audit UI and CLI cannot execute the historical self-audit",()=>{
 const root=path.resolve(__dirname,"..");
 const page=fs.readFileSync(path.join(root,"app/raas-scan/page.tsx"),"utf8");
 const cli=fs.readFileSync(path.join(root,"scripts/raas-readiness-scan.cjs"),"utf8");
 assert.match(page,/permanently retired/);assert.doesNotMatch(page,/auditRaasSurveyAccuracy|data-raas-self-audit/);
 assert.doesNotMatch(cli,/require\(['"]\.\.\/lib\/raas-self-accuracy-audit/);
});
