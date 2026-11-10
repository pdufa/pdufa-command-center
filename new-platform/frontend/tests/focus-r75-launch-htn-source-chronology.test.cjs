"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const out=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
 }});mod._compile(out.outputText,file);
};
const raw=require("../data/focus-r75-launch-htn-source-date-reconciliation.json");
const {FOCUS_R75_LAUNCH_HTN_CHRONOLOGY,buildR75LaunchHtnChronology}=
 require("../lib/focus-r75-launch-htn-chronology.ts");

test("Seven original publisher PDFs observed with 10 physical pages and two printed-year discrepancies",()=>{
 const x=FOCUS_R75_LAUNCH_HTN_CHRONOLOGY;
 assert.ok(x);
 assert.equal(x.publisherSupplementsLinked,7);
 assert.equal(x.originalPublicSourcePdfPagesVisuallyRead,10);
 assert.equal(x.observedLastParticipantFollowUpDate,"2025-01-24");
 assert.equal(x.docs[1].printedEffectiveOrHeaderDate,"2024-06-11");
 assert.equal(x.docs[3].printedEffectiveOrHeaderDate,"2024-01-08");
 assert.equal(x.docs[4].printedSignatureDate,"2025-02-23");
 assert.equal(x.docs[5].printedSignatureDate,"2025-02-13");
 assert.equal(x.docs[6].printedSignatureDate,"2025-02-13");
 assert.deepEqual(x.docs.filter(d=>d.printedDateConflict).map(d=>d.supplementNumber),[5,7]);
 assert.equal(x.signedOriginalProspectiveStatisticalPlansIndependentlyAuthenticated,0);
 assert.equal(x.databaseLockDateAuthenticated,false);
 assert.equal(x.firstUnblindingDateAuthenticated,false);
 assert.equal(x.originalPlansInEffectAtUnblindingAuthenticated,false);
 assert.equal(x.clinicalScienceGrade,null);
 assert.equal(x.validatedFutureFDAForecasts,0);
 assert.equal(x.FDAForecast,"ABSTAIN");
 assert.equal(x.reviewTimingForecast,"UNKNOWN");
});

test("Tamper printed SAP signatures, protocol versions, release flags or FDA grades fails closed",()=>{
 const attacks=[
  x=>x.docs.pop(),
  x=>x.docs.reverse(),
  x=>x.docs[2].filename="modified.pdf",
  x=>x.docs[1].documentVersion="4.0",
  x=>x.docs[1].printedEffectiveOrHeaderDate="2024-01-08",
  x=>x.docs[4].printedDateConflict=false,
  x=>x.docs[4].printedSignatureDate="2024-02-23",
  x=>x.docs[5].printedSignatureDate="2025-01-23",
  x=>x.docs[6].sourceRenderedPages=11,
  x=>x.docs[4].observedPageNumbers=[1],
  x=>x.originalSourcePdfByteHashesCaptured=7,
  x=>x.originalPdfFirstPublicPublicationDatesAuthenticated=true,
  x=>x.signedOriginalProspectiveStatisticalPlansIndependentlyAuthenticated=3,
  x=>x.databaseLockDateAuthenticated=true,
  x=>x.firstUnblindingDateAuthenticated=true,
  x=>x.originalPlansInEffectAtUnblindingAuthenticated=true,
  x=>x.originalSignedScienceReviewerAssessed=true,
  x=>x.clinicalScienceGrade=5,
  x=>x.validatedFutureFDAForecasts=23,
  x=>x.futureFDAOutcome="APPROVAL",
  x=>x.noTrainingOrProductionWrites=false
 ];
 for(let i=0;i<attacks.length;i++){
  const x=structuredClone(raw);attacks[i](x);
  assert.equal(buildR75LaunchHtnChronology(x),null,"tamper "+i);
 }
});

test("Original PDF observations are visible only in the Launch-HTN scientific source panel",()=>{
 const host=fs.readFileSync(path.join(root,
   "app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,
   "app/predictions/evidence-gaps/LaunchHtnSourceChronologyR75.tsx"),"utf8");
 assert.match(host,/nct==="NCT06153693"&&<LaunchHtnSourceChronologyR75\/>/);
 assert.match(panel,/Chronology is NOT verified as prospective/);
 assert.match(panel,/source PDF SHA receipts/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/Printed internal year conflict/);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|setGrade\(|submitClinicalScore/);
});
