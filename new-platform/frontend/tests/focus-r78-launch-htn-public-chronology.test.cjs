"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const x=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
 }});mod._compile(x.outputText,file);
};
const original=require("../data/focus-r78-launch-htn-public-chronology.json");
const {FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY,buildR78LaunchHtnChronology}=
  require("../lib/focus-r78-launch-htn-public-chronology.ts");

test("Original SEC, issuer and JAMA evidence establishes public dates but not lock/unblinding",()=>{
 const d=FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY;
 assert.ok(d);
 assert.equal(d.cycleId,"mlys-lorundrostat");
 assert.equal(d.focusTrialCountUnchanged,29);
 assert.equal(d.provisionalApplicationCycleCountUnchanged,23);
 assert.equal(d.sourceEvents.length,9);
 assert.deepEqual(d.sourceEvents.map(e=>e.date),[
  "2025-01-24","2025-02-13","2025-02-13","2025-02-23","2025-03-07",
  "2025-03-10","2025-06-30","2026-03-09","2026-11-04"]);
 assert.equal(d.observation.journalDescribesMaskingUntilFinalDatabaseLock,true);
 assert.equal(d.observation.originalActualDatabaseLockDate,null);
 assert.equal(d.observation.originalActualUnblindingDate,null);
 assert.equal(d.observation.originalSAPAuthenticPreUnblindingSignatureVerified,false);
 assert.equal(d.observation.twoPrintedSAPCoverDateDiscrepanciesUnresolved,true);
 assert.equal(d.observation.originalPdfSourceByteHashesAvailable,0);
 assert.equal(d.observation.noAuthenticatedOriginalArchive,true);
 assert.equal(d.regulatory.officialOutcomeForecast,"ABSTAIN");
 assert.equal(d.regulatory.signedQualifiedReviewerCount,0);
 assert.equal(d.regulatory.noModelTrainingOrProductionWrites,true);
 assert.ok(d.sourceEvents.every(x=>x.evidenceOnly&&!x.provesUnblinding));
});

test("Evidence confirms target Dec 22 2026 without upgrading sponsor report to final FDA ruling",()=>{
 const d=FOCUS_R78_LAUNCH_HTN_PUBLIC_CHRONOLOGY;
 assert.equal(d.regulatory.reportedNdaAcceptanceDate,"2026-03-09");
 assert.equal(d.regulatory.latestSourceDate,"2026-11-04");
 assert.equal(d.regulatory.pdufaTargetDate,"2026-12-22");
 assert.equal(d.regulatory.acceptanceEvidenceKind,"SPONSOR_ANNOUNCEMENT_NOT_PUBLIC_FDA_ACCEPTANCE_LETTER");
 assert.equal(d.regulatory.asReportedRegulatoryStatus,"SPONSOR_REPORTS_FDA_REVIEW_ONGOING");
 assert.equal(d.regulatory.fdaIssuedDecisionDocumentIndependentlyVerified,false);
 assert.equal(d.regulatory.officialTimingForecast,"UNKNOWN");
 assert.equal(d.regulatory.validatedApplicationForecasts,0);
 assert.equal(d.validatedFDAOutcome,"ABSTAIN");
});

test("Chronology and regulatory source tampering cannot unlock independent clinical grade or decision",()=>{
 const attacks=[
  x=>x.sourceEvents.pop(),
  x=>x.sourceEvents.reverse(),
  x=>x.sourceEvents[0].date="2025-02-13",
  x=>x.sourceEvents[5].eventKind="FDA_APPROVED",
  x=>x.sourceEvents[5].sourceUrl="https://example.invalid/forged",
  x=>x.sourceEvents[5].sourceDate="2025-02-20",
  x=>x.sourceEvents[5].provesUnblinding=true,
  x=>x.sourceEvents[5].evidenceOnly=false,
  x=>x.observation.originalActualDatabaseLockDate="2025-02-12",
  x=>x.observation.originalActualUnblindingDate="2025-02-20",
  x=>x.observation.originalSAPAuthenticPreUnblindingSignatureVerified=true,
  x=>x.observation.noAuthenticatedOriginalArchive=false,
  x=>x.observation.originalPdfSourceByteHashesAvailable=7,
  x=>x.observation.journalDisclosesFinalDatabaseLockCalendarDate=true,
  x=>x.observation.twoPrintedSAPCoverDateDiscrepanciesUnresolved=false,
  x=>x.regulatory.reportedNdaAcceptanceDate="2026-03-10",
  x=>x.regulatory.pdufaTargetDate="2026-11-22",
  x=>x.regulatory.fdaIssuedDecisionDocumentIndependentlyVerified=true,
  x=>x.regulatory.officialOutcomeForecast="APPROVE",
  x=>x.regulatory.officialTimingForecast="ON_TIME",
  x=>x.regulatory.signedQualifiedReviewerCount=1,
  x=>x.regulatory.validatedApplicationForecasts=1,
  x=>x.regulatory.noModelTrainingOrProductionWrites=false,
  x=>x.focusTrialCountUnchanged=30,
  x=>x.provisionalApplicationCycleCountUnchanged=24
 ];
 for(let i=0;i<attacks.length;i++){
  const x=structuredClone(original);attacks[i](x);
  assert.equal(buildR78LaunchHtnChronology(x),null,"tamper "+i);
 }
});

test("R78 is only a source view on Launch-HTN, not an FDA scoring endpoint",()=>{
 const host=fs.readFileSync(path.join(root,
   "app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,
   "app/predictions/evidence-gaps/LaunchHtnPublicChronologyR78.tsx"),"utf8");
 assert.match(host,/nct==="NCT06153693"&&<LaunchHtnPublicChronologyR78\/>/);
 assert.match(panel,/database lock/);
 assert.match(panel,/0\/23/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/March 10|2025-03-10|publicIssuerToplineSECDisclosureDate/);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|setGrade\(|submitClinicalScore/);
});
