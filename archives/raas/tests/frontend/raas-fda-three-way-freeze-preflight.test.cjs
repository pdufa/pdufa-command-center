"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const ts=require("typescript"),fs=require("node:fs"),path=require("node:path");
const {createHash}=require("node:crypto");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const accepted=require("../data/raas-current-accepted-fda-applications.json");
const leads=require("../data/raas-v2-top8-2026-source-intake.json");
const {buildThreeWayFDAFreezePreflightPlan:build}=
 require("../lib/raas-fda-three-way-freeze-preflight.ts");
const {GET}=require("../app/api/raas-fda-threeway-preflight/route.ts");
const plan=build();
const byKey=new Map(plan.records.map(x=>[x.caseKey,x]));

test("each of 11 saved FDA research cases has a unique, unsigned 7-proof three-class freeze plan",()=>{
 assert.equal(plan.total,accepted.applications.length+leads.records.length);
 assert.equal(plan.total,11);
 assert.equal(byKey.size,plan.total);
 assert.equal(plan.frozenVerifiedThreeWayForecasts,0);
 assert.equal(plan.certifiedThreeWayAccuracy,null);
 assert.equal(plan.phase2Excluded,2);
 assert.equal(plan.originalGoalElapsed,1);
 assert.equal(plan.unverifiedApplicationOrCycle,7);
 assert.equal(plan.needsExactCycleAndCalibration,1);
 for(const r of plan.records){
  assert.equal(r.schemaVersion,1);
  assert.equal(r.requiredProof.length,7);
  assert.equal(new Set(r.requiredProof.map(p=>p.id)).size,7);
  assert.ok(r.requiredProof.every(p=>p.status!=="APPROVED"));
  assert.match(r.sourceFingerprint,/^[a-f0-9]{64}$/);
  assert.equal(r.forecastReceiptDraft.sourceFingerprint,r.sourceFingerprint);
  assert.equal(r.forecastReceiptDraft.forecastFrozenAt,null);
  assert.equal(r.forecastReceiptDraft.firstAnnouncedGoalDate,r.originalFirstGoalDate);
  assert.equal(r.forecastReceiptDraft.probabilities.PASS,null);
  assert.equal(r.forecastReceiptDraft.probabilities.CRL,null);
  assert.equal(r.forecastReceiptDraft.probabilities.EXTENSION,null);
  assert.equal(r.forecastReceiptDraft.signedFreezeReceiptDigest,null);
  assert.equal(r.verifiedThreeWayForecast,null);
  assert.equal(r.approvedRaasGrade,null);
  assert.equal(r.releaseStatus,"ABSTAIN_NO_FORECAST_FROZEN");
 }
});
test("COGT GIST Phase 3 is distinct from two excluded Phase 2 FDA applications",()=>{
 const gist=byKey.get("COGT-BEZUCLASTINIB-GIST-2026");
 assert.ok(gist);
 assert.equal(gist.eligibility,"PHASE3_SOURCE_ELIGIBLE");
 assert.equal(gist.originalFirstGoalDate,"2026-11-30");
 assert.equal(gist.trialNctId,"NCT05208047");
 assert.equal(gist.preflightStatus,"EXACT_CYCLE_AND_CALIBRATION_NOT_VERIFIED");
 const rest=plan.records.filter(r=>r.ticker==="COGT"&&r.caseKey!==gist.caseKey);
 assert.equal(rest.length,2);
 assert.ok(rest.every(x=>x.preflightStatus==="PHASE2_OUT_OF_SCOPE"));
 assert.ok(rest.every(x=>x.requiredProof.find(p=>p.id==="minimum-phase3-evidence").status==="OUT_OF_SCOPE"));
});
test("CAPR first original goal cannot be overwritten by a later formal extension",()=>{
 const r=byKey.get("CAPR|DERAMIOCEL_DMD_20261122");
 assert.ok(r);
 assert.equal(r.originalFirstGoalDate,"2026-08-22");
 assert.equal(r.listedTargetDate,"2026-11-22");
 assert.equal(r.goalHasFormalRevision,true);
 assert.equal(r.formalRevisedGoalDate,"2026-11-22");
 assert.equal(r.preflightStatus,"ORIGINAL_GOAL_ALREADY_ELAPSED");
 assert.equal(r.requiredProof.find(p=>p.id==="immutable-predecision-receipt").status,"OUT_OF_SCOPE");
});
test("no applicant can backdate their first forecast after the original goal",()=>{
 const after=build("2027-07-01");
 assert.equal(after.total,plan.total);
 assert.equal(after.originalGoalElapsed,9);
 assert.equal(after.phase2Excluded,2);
 assert.ok(after.records.every(x=>x.preflightStatus!=="EXACT_CYCLE_AND_CALIBRATION_NOT_VERIFIED"));
 assert.throws(()=>build("2026-11-02"),/RAAS_FDA_PREFLIGHT_BASELINE_NOT_VERIFIED/);
});
test("one case can download a source-linked unsigned template, unknown cases fail closed",async()=>{
 const key="COGT-BEZUCLASTINIB-GIST-2026";
 const url="https://example.test/api/raas-fda-threeway-preflight?case="+encodeURIComponent(key);
 const response=GET(new Request(url));
 assert.equal(response.status,200);
 assert.match(response.headers.get("content-type"),/application\/json/);
 assert.match(response.headers.get("content-disposition"),/raas-fda-threeway-preflight-COGT/);
 assert.equal(response.headers.get("Cache-Control"),"no-store");
 const data=await response.json();
 assert.equal(data.caseKey,key);
 assert.deepEqual(data.forecastReceiptDraft.probabilities,{PASS:null,CRL:null,EXTENSION:null});
 assert.equal(data.releaseStatus,"ABSTAIN_NO_FORECAST_FROZEN");
 for(const k of ["", "BAD_CASE", "\n", "x".repeat(200)]){
  const r=GET(new Request("https://example.test/api/raas-fda-threeway-preflight?case="+encodeURIComponent(k)));
  assert.ok([400,404].includes(r.status));
  assert.equal(r.headers.get("Cache-Control"),"no-store");
 }
});
test("Predictions page exposes each exact-case original-goal checklist without claiming a forecast",()=>{
 const s=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 assert.match(s,/data-raas-fda-threeway-freeze-preflight/);
 assert.match(s,/data-raas-fda-exact-freeze-preflight/);
 assert.match(s,/raas-fda-threeway-preflight\?/);
 assert.match(s,/first announced goal/i);
 assert.match(s,/All PASS\/CRL\/EXTENSION fields are null/);
 assert.match(s,/new URLSearchParams\(\{case:r.key\}\)/);
 const typescript=ts.transpileModule(s,{fileName:"predictions-page.tsx",
  reportDiagnostics:true,compilerOptions:{
   target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.ESNext,
   jsx:ts.JsxEmit.ReactJSX
  }});
 assert.equal((typescript.diagnostics||[]).filter(d=>d.category===ts.DiagnosticCategory.Error).length,0);
});
