"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const path=require("node:path"),fs=require("node:fs"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>mod._compile(ts.transpileModule(
 fs.readFileSync(file,"utf8"),{fileName:file,compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  esModuleInterop:true,jsx:ts.JsxEmit.ReactJSX
 }}).outputText,file);
const saved=require("../data/raas-fda-forecast-freeze-receipts.json");
const {auditRaasFdaForecastFreezeReceipts:audit,currentRaasFdaForecastFreezeReceiptAudit:current}
 =require("../lib/raas-fda-forecast-freeze-receipt-audit.ts");
const {buildThreeWayFDAFreezePreflightPlan}
 =require("../lib/raas-fda-three-way-freeze-preflight.ts");
const {GET}=require("../app/api/raas-fda-freeze-receipt-audit/route.ts");
const plan=buildThreeWayFDAFreezePreflightPlan();
const cogt=plan.records.find(x=>x.caseKey==="COGT-BEZUCLASTINIB-GIST-2026");
const capr=plan.records.find(x=>x.ticker==="CAPR");
const phase2=plan.records.find(x=>x.caseKey==="COGT-BEZUCLASTINIB-NONADVSM-2026");
assert.ok(cogt&&capr&&phase2);
const doc=(records)=>({...saved,records});
const example=(p=cogt)=>({
 receiptId:"test-receipt-0001",caseKey:p.caseKey,
 sourceFingerprint:p.sourceFingerprint,
 ticker:p.ticker,drug:p.drug,indication:p.indication,
 trialNctId:p.trialNctId,firstAnnouncedGoalDate:p.originalFirstGoalDate,
 sourceSnapshotAsOf:p.snapshotAsOf,
 exactFdaApplicationNumber:"NDA TEST-123456",
 exactReviewCycleId:"REVIEW-CYCLE-TEST-1",
 forecastFrozenAt:"2026-11-05T08:00:00Z",
 independentWitnessRecordedAt:"2026-11-05T08:01:00Z",
 witnessArchiveReference:"restricted-archive://research-forecast-receipt",
 signedArtifactSha256:"a".repeat(64),
 modelVersion:"research-model-v-test",
 calibrationReportReference:"restricted-archive://calibration-review-test",
 independentSourceAuditReference:"restricted-archive://source-review-test",
 probabilities:{PASS:0.6,CRL:0.3,EXTENSION:0.1}
});
test("saved public ledger contains zero unverified receipts and certifies no outcomes",async()=>{
 assert.equal(saved.records.length,0);
 assert.equal(saved.schemaVersion,1);
 const a=current();
 assert.equal(a.eligibleResearchCaseLeads,9);
 assert.equal(a.submitted,0);
 assert.equal(a.pendingIndependentAuthentication,0);
 assert.equal(a.blocked,0);
 assert.equal(a.independentlyAuthenticatedForecasts,0);
 assert.equal(a.validatedFdaThreeWayAccuracy,null);
 assert.equal(a.approvedTradingSignals,0);
 const response=GET();
 assert.equal(response.status,200);
 assert.equal(response.headers.get("cache-control"),"no-store");
 const api=await response.json();
 assert.equal(api.submitted,0);
 assert.equal(api.validatedFdaThreeWayAccuracy,null);
});
test("syntactically complete synthetic three-way freeze is only pending human authentication",()=>{
 const result=audit(doc([example()]));
 assert.equal(result.submitted,1);
 assert.equal(result.pendingIndependentAuthentication,1);
 assert.equal(result.blocked,0);
 assert.equal(result.independentlyAuthenticatedForecasts,0);
 assert.equal(result.validatedFdaThreeWayAccuracy,null);
 assert.equal(result.approvedTradingSignals,0);
 assert.equal(result.checks[0].status,"INTAKE_COMPLETE_PENDING_INDEPENDENT_AUTHENTICATION");
});
test("late or backdated-to-revised original-cycle freezes fail closed",()=>{
 for(const patch of [
  {forecastFrozenAt:"2026-11-30T00:00:00Z"},
  {independentWitnessRecordedAt:"2026-11-30T00:00:00Z"},
  {independentWitnessRecordedAt:"2026-11-05T07:59:59Z"},
  {forecastFrozenAt:"2026-11-03T20:00:00Z"},
  {forecastFrozenAt:"2026-11-05T08:00:00"},
  {firstAnnouncedGoalDate:"2026-11-22"}
 ]){
  const r=audit(doc([{...example(),...patch}]));
  assert.equal(r.blocked,1,JSON.stringify(patch));
  assert.equal(r.independentlyAuthenticatedForecasts,0);
 }
 const revised=audit(doc([{
  ...example(capr),forecastFrozenAt:"2026-11-05T08:00:00Z",
  firstAnnouncedGoalDate:capr.listedTargetDate
 }]));
 assert.ok(revised.checks[0].reasons.includes("REVISED_GOAL_SUBSTITUTED_FOR_ORIGINAL"));
 assert.ok(revised.checks[0].reasons.includes("FORECAST_OR_WITNESS_NOT_PRE_ORIGINAL_GOAL"));
});
test("improper probabilities, fake source fingerprints and cross-application substitutions are rejected",()=>{
 for(const patch of [
  {probabilities:{PASS:0.7,CRL:0.7,EXTENSION:-0.4}},
  {probabilities:{PASS:0.6,CRL:0.3,EXTENSION:0.11}},
  {probabilities:{PASS:NaN,CRL:0.2,EXTENSION:0.8}},
  {probabilities:{PASS:0.5,CRL:0.5,EXTENSION:0,OTHER:0}},
  {sourceFingerprint:"b".repeat(64)},
  {ticker:"OTHER"},
  {drug:"other sponsor asset"},
  {trialNctId:"NCT00000000"},
  {caseKey:"FAKE-CASE"},
  {exactReviewCycleId:""},
  {signedArtifactSha256:"incorrect"},
  {witnessArchiveReference:""},
  {modelVersion:""},
  {sourceSnapshotAsOf:"2027-01-01"}
 ]){
  const r=audit(doc([{...example(),...patch}]));
  assert.equal(r.blocked,1,JSON.stringify(patch));
  assert.equal(r.pendingIndependentAuthentication,0);
 }
});
test("duplicated receipts for one exact application both block rather than selecting a favorable one",()=>{
 const a=example(),b={...example(),receiptId:"test-receipt-0002",
  probabilities:{PASS:0.1,CRL:0.8,EXTENSION:0.1}};
 const r=audit(doc([a,b]));
 assert.equal(r.submitted,2);
 assert.equal(r.blocked,2);
 assert.equal(r.duplicateCaseReceipts,2);
 assert.equal(r.pendingIndependentAuthentication,0);
 assert.ok(r.checks.every(x=>x.reasons.includes("DUPLICATE_FORECAST_FOR_EXACT_CASE")));
 const id=audit(doc([a,{...b,receiptId:a.receiptId}]));
 assert.ok(id.checks.every(x=>x.reasons.includes("DUPLICATE_OR_INVALID_RECEIPT_ID")));
});
test("Phase 2 cases remain blocked even if all receipt fields appear populated",()=>{
 const r=audit(doc([{
  ...example(phase2),forecastFrozenAt:"2026-11-05T08:00:00Z"
 }]));
 assert.equal(r.blocked,1);
 assert.ok(r.checks[0].reasons.includes("PHASE2_NOT_ELIGIBLE_FOR_PHASE3_PIPELINE"));
});
test("malformed ledger schema fails closed and the UI shows audit status without releasing predictions",()=>{
 for(const feed of [{...saved,schemaVersion:4},{...saved,scope:"OTHER"},
  {...saved,records:{}},{...saved,note:"short"}]){
  assert.throws(()=>audit(feed),/RAAS_FDA_FREEZE_RECEIPT_LEDGER_INVALID/);
 }
 const page=fs.readFileSync(path.join(root,"app/predictions/page.tsx"),"utf8");
 assert.match(page,/data-raas-fda-freeze-receipt-audit/);
 assert.match(page,/currentRaasFdaForecastFreezeReceiptAudit/);
 assert.match(page,/independentlyAuthenticatedForecasts/);
 assert.match(page,/raas-fda-freeze-receipt-audit/);
 assert.match(page,/No recorded receipt is automatically authenticated/);
 const route=fs.readFileSync(path.join(root,
  "app/api/raas-fda-freeze-receipt-audit/route.ts"),"utf8");
 assert.match(route,/Cache-Control/);
});
