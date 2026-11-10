"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
 const x=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(x.outputText,file);
};
const {APPLICATION_CYCLES}=require("../lib/medical-intelligence-applications.ts");
const {FOCUS_R81_SOURCE_READINESS}=
 require("../lib/focus-r81-all-focus-source-readiness.ts");
const {buildR84ApplicationVerificationQueue,R84_APPLICATION_VERIFICATION}=
 require("../lib/focus-r84-application-verification-queue.ts");
test("R84 has one dated provenance record for 23 provisional cycles and 29 unique NCTs",()=>{
 const x=R84_APPLICATION_VERIFICATION;
 assert.ok(x);
 assert.equal(x.provisionalCycles,23);
 assert.equal(x.exactTrials,29);
 assert.equal(x.rows.length,23);
 assert.equal(new Set(x.rows.flatMap(r=>r.linkedNcts)).size,29);
 assert.deepEqual(new Set(x.rows.map(r=>r.cycleId)),
   new Set(APPLICATION_CYCLES.map(r=>r.id)));
 assert.equal(x.independentFDAApplicationStatusConfirmations,0);
 assert.equal(x.independentlyValidatedForecasts,0);
 assert.equal(x.reportedTargetCount+x.noReportedTargetCount,23);
 assert.ok(x.rows.every(r=>r.fdaOutcomePrediction==="ABSTAIN"&&
   r.fdaTimingPrediction==="UNKNOWN"&&r.scienceSignoff==="NOT_COMPLETED"));
 const dated=x.rows.filter(r=>r.sponsorReportedGoal!==null);
 assert.deepEqual(dated.map(r=>r.sponsorReportedGoal),
   [...dated.map(r=>r.sponsorReportedGoal)].sort());
});
test("R84 does not conflate oHCM observed status with planned nHCM application",()=>{
 const x=R84_APPLICATION_VERIFICATION;
 const o=x.rows.find(r=>r.cycleId==="cytk-aficamten-ohcm");
 const n=x.rows.find(r=>r.cycleId==="cytk-aficamten-nhcm");
 assert.ok(o&&n);
 assert.equal(o.observedHistoricalStatusClaim,true);
 assert.equal(o.prospectiveDecisionCandidate,false);
 assert.equal(o.sponsorReportedGoal,null);
 assert.equal(n.observedHistoricalStatusClaim,false);
 assert.equal(n.prospectiveDecisionCandidate,true);
 assert.equal(n.sponsorReportedGoal,null);
 assert.equal(x.rows.at(-1).cycleId,"cytk-aficamten-ohcm");
});
test("R84 rejects forged cycles, source identities, claimed FDA forecasts and duplicate rows",()=>{
 const scenarios=[
  arr=>{arr[0].ncts=["NCT00000000"];},
  arr=>{arr[0].stage="APPROVED_ALREADY";arr[0].reportedGoal="2027-01-01";},
  arr=>{arr[0].reportedGoal="not-a-date";},
  arr=>{arr[0].sourceUrl="http://insecure.example/a";},
  arr=>{arr[0].id=arr[1].id;},
  arr=>{arr.pop();}
 ];
 for(const mutate of scenarios){
  const x=structuredClone(APPLICATION_CYCLES);
  mutate(x);
  assert.equal(buildR84ApplicationVerificationQueue(FOCUS_R81_SOURCE_READINESS,x),null);
 }
 const forged=structuredClone(FOCUS_R81_SOURCE_READINESS);
 forged.rows[0].validatedFDAApplicationPrediction=true;
 assert.equal(buildR84ApplicationVerificationQueue(forged),null);
});
test("R84 read-only interface displays dates, grouped exact trials, blockers and warnings",()=>{
 const ui=fs.readFileSync(path.join(root,
  "app/predictions/evidence-gaps/ApplicationVerificationR84.tsx"),"utf8");
 const board=fs.readFileSync(path.join(root,
  "app/predictions/evidence-gaps/FocusSourceReadinessR81.tsx"),"utf8");
 assert.match(board,/<ApplicationVerificationR84\s*\/>/);
 assert.match(ui,/Source-reported target/);
 assert.match(ui,/Already-observed status claims/);
 assert.match(ui,/link.*exact supporting NCTs/);
 assert.match(ui,/ABSTAIN/);
 assert.match(ui,/Original source/);
 assert.doesNotMatch(ui,/setGrade\(|submitClinicalScore|POST\s*\/api/);
});
