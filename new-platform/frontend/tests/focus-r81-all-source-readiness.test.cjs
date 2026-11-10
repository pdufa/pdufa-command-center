"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const extension of [".ts",".tsx"]){
 require.extensions[extension]=(mod,file)=>{
  const compiled=ts.transpileModule(fs.readFileSync(file,"utf8"),{
   compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
    jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
  mod._compile(compiled.outputText,file);
 };
}
const {FOCUS_R68_EVIDENCE_RECOVERY}=require("../lib/focus-r68-evidence-recovery.ts");
const {FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE}=require("../lib/focus-r71-pivotal-evidence-intake.ts");
const {FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES}=require("../lib/focus-r79-launch-htn-sap-lock-evidence-gates.ts");
const {FOCUS_R81_SOURCE_READINESS,buildR81SourceReadiness}=
 require("../lib/focus-r81-all-focus-source-readiness.ts");
const focus=require("../../backend/app/data/focus_snapshot.json");
const cycles=require("../../backend/app/data/focus_application_snapshot.json");
test("Exact 29 NCT source statuses, 23 provisional cycle identities, five published report leads",()=>{
 const x=FOCUS_R81_SOURCE_READINESS;
 assert.ok(x,"whole 29/23 source coverage must validate");
 assert.equal(x.exactTrials,29);
 assert.equal(x.provisionalCycles,23);
 assert.equal(x.R71PublicationLeads,5);
 assert.equal(x.remainingNotIndexedInR71,24);
 assert.equal(x.applicationGroups.length,23);
 assert.equal(x.rows.length,29);
 assert.deepEqual(new Set(x.rows.map(y=>y.nct)),new Set(focus.records.map(y=>y.nct)));
 assert.deepEqual(new Set(x.applicationGroups.map(y=>y.cycleId)),
    new Set(cycles.records.flatMap(y=>y.candidateApplications.map(c=>c.cycleId))));
 const byNct=new Map(cycles.records.map(y=>[y.nct,y]));
 for(const row of x.rows){
  const official=byNct.get(row.nct);
  assert.ok(official);
  assert.deepEqual(new Set(row.cycleIds),new Set(official.candidateApplications.map(c=>c.cycleId)));
  assert.equal(row.scientificGrade,null);
  assert.equal(row.originalProspectiveSAPAuthenticated,false);
  assert.equal(row.independentScienceReviewed,false);
  assert.equal(row.validatedFDAApplicationPrediction,false);
  assert.equal(row.officialFDAOutcome,"ABSTAIN");
 }
});
test("Read-only source categories are not forecasts and R71 source leads are not negative findings",()=>{
 const x=FOCUS_R81_SOURCE_READINESS;
 assert.equal(x.registryCurrentPrimaryTrials,12);
 assert.equal(x.registryCurrentSafetyArmTrials,12);
 assert.equal(x.registryCurrentMethodPageLeadTrials,12);
 assert.equal(x.fullScientificSourceReviewPositions,232);
 assert.equal(x.completedScientificSourceReviews,0);
 assert.equal(x.originalSignedProspectiveSAPsVerified,0);
 assert.equal(x.independentScientificSignoffs,0);
 assert.equal(x.validFutureFDAApplicationForecasts,0);
 assert.equal(x.accuracyCalibrated,false);
 assert.equal(x.FDAOutcome,"ABSTAIN");
 assert.equal(x.noProductionOrModelTrainingWrites,true);
 assert.equal(x.rows.filter(y=>y.indexedOriginalPivotalPublication).length,5);
 assert.equal(x.rows.filter(y=>!y.indexedOriginalPivotalPublication).length,24);
 const mlys=x.rows.find(y=>y.nct==="NCT06153693");
 assert.equal(mlys.originalJournalIntakeStage,"ORIGINAL_JOURNAL_METHOD_PAGES_REVIEWED_NOT_ADJUDICATED");
 assert.equal(mlys.indexedOriginalPivotalPublication,true);
 const group=x.applicationGroups.find(y=>y.cycleId==="mlys-lorundrostat");
 assert.ok(group);
 assert.ok(group.ncts.includes("NCT06153693"));
 assert.equal(group.prospectivelyAuthenticatedSAPs,0);
 assert.equal(group.independentlySignedScientificReviews,0);
 assert.equal(group.validatedFDAApplicationForecasts,0);
 assert.equal(group.FDAOutcome,"ABSTAIN");
});
test("Duplicate NCT, falsified trial outcome, missing journal source and altered cycle ownership fail closed",()=>{
 const tests=[
  {name:"duplicate NCT",fn:(a)=>a.rows[1].nct=a.rows[0].nct},
  {name:"wrong trial ticker",fn:(a)=>a.rows[0].ticker="FAKE"},
  {name:"fake clinical grade",fn:(a)=>a.rows[0].clinicalScienceScore=20},
  {name:"fake positive future FDA outcome",fn:(a)=>a.rows[0].officialFutureFdaOutcome="APPROVAL"},
  {name:"fake completed signoff",fn:(a)=>a.qualifiedReviewerSignoffs=3},
  {name:"too few trials",fn:(a)=>a.rows.pop()},
  {name:"cycle overwrite",fn:(a)=>a.rows[0].applicationCycles=["unknown-fake-cycle"]},
  {name:"fake registry primary count",fn:(a)=>a.postedPrimaryTrials=29}
 ];
 tests.forEach(({name,fn})=>{
   const data=structuredClone(FOCUS_R68_EVIDENCE_RECOVERY);
   fn(data);
   assert.equal(buildR81SourceReadiness(data,FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE,FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES),null,name);
 });
 const sources=structuredClone(FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE);
 sources.fiveRecords[0].scienceGrade=20;
 assert.equal(buildR81SourceReadiness(FOCUS_R68_EVIDENCE_RECOVERY,sources,FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES),null);
 const auth=structuredClone(FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES);
 auth.requirementsIndependentlyVerified=7;
 assert.equal(buildR81SourceReadiness(FOCUS_R68_EVIDENCE_RECOVERY,FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE,auth),null);
});
test("R81 board presents 23 cycle drilldowns without grade-submission or network writes",()=>{
 const board=fs.readFileSync(path.join(root,"app/predictions/evidence-gaps/EvidenceRecoveryBoardR68.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,"app/predictions/evidence-gaps/FocusSourceReadinessR81.tsx"),"utf8");
 assert.match(board,/<FocusSourceReadinessR81\s*\/>/);
 assert.match(panel,/Expand all 23 provisional application cycles/);
 assert.match(panel,/not a ranking of drugs/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/unassessed/);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|setGrade\(|submitClinicalScore/);
});
