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
const dated=require("../data/focus-r88-source-chronology-triage-20261110.json");
const oldPdf=require("../data/focus-r87-public-pdf-byte-receipts-20261110.json");
const {R88_SOURCE_CHRONOLOGY,buildR88SourceChronology}=
 require("../lib/focus-r88-source-chronology-triage.ts");
test("R88 source-date triage preserves exactly 29 NCTs, 23 files and all 23 provisional cycles",()=>{
 const x=R88_SOURCE_CHRONOLOGY;
 assert.ok(x);
 assert.equal(x.trialCount,29);
 assert.equal(x.applicationCycles,23);
 assert.equal(x.listedPdfFiles,23);
 assert.equal(x.trialsWithPublicListedPdf,12);
 assert.equal(x.trialsWithoutListedPdf,17);
 assert.equal(x.rows.length,29);
 assert.equal(new Set(x.rows.map(r=>r.nct)).size,29);
 assert.equal(new Set(x.rows.flatMap(r=>r.cycleIds)).size,23);
 assert.equal(x.rows.reduce((n,r)=>n+r.sourcePdfFiles.length,0),23);
 assert.equal(x.authenticatedProspectiveSAPs,0);
 assert.equal(x.independentSignedMedicalReviews,0);
 assert.equal(x.independentlyValidatedFDAForecasts,0);
 assert.ok(x.rows.every(r=>r.FDAForecast==="ABSTAIN"&&r.clinicalGrade===null&&
  r.originallySignedPlanVerified===false&&
  r.actualBlindBreakDateIndependentlyVerified===false&&
  r.qualifiedClinicalReviewerSignoff===false));
});
test("R88 compares source document and upload dates with actual registry PRIMARY completion, never blind break",()=>{
 const x=R88_SOURCE_CHRONOLOGY;
 assert.equal(x.sapListedDocumentDatesAfterPrimaryCompletion,11);
 assert.equal(x.sapListedDocumentDatesOnOrBeforePrimaryCompletion,1);
 assert.equal(x.filesUploadedAfterPrimaryCompletion,23);
 assert.equal(x.rows.filter(r=>r.sapDateChronologyState===
  "LISTED_SAP_DATE_AFTER_PRIMARY_COMPLETION_RECONCILE_VERSION").length,11);
 assert.equal(x.rows.filter(r=>r.sapDateChronologyState===
  "SAP_DATE_NOT_AFTER_PRIMARY_COMPLETION_STILL_REQUIRE_SIGNED_LOCK_PROOF").length,1);
 assert.equal(x.rows.filter(r=>r.sapDateChronologyState===
  "NO_CURRENT_REGISTRY_PROTOCOL_SAP_FILES").length,17);
 assert.match(x.notice,/NOT actual blind-break or database lock/);
 const abvx=x.rows.find(r=>r.nct==="NCT05507203");
 const vera=x.rows.find(r=>r.nct==="NCT04716231");
 assert.ok(abvx&&vera);
 assert.equal(abvx.archivedPrimaryCompletionDate,"2025-06-24");
 assert.equal(abvx.sourcePdfFiles.find(f=>f.listsSAP).documentDate,"2025-07-15");
 assert.equal(abvx.sapDateChronologyState,
  "LISTED_SAP_DATE_AFTER_PRIMARY_COMPLETION_RECONCILE_VERSION");
 assert.equal(vera.sapDateChronologyState,
  "SAP_DATE_NOT_AFTER_PRIMARY_COMPLETION_STILL_REQUIRE_SIGNED_LOCK_PROOF");
 assert.equal(vera.sourcePdfFiles.length,1);
 assert.ok(vera.sourcePdfFiles[0].listsProtocol&&vera.sourcePdfFiles[0].listsSAP);
});
test("R88 SHA256 and PDF source locations match all R87 observed real bytes",()=>{
 const x=R88_SOURCE_CHRONOLOGY;
 const pdf=new Map(oldPdf.records.map(r=>[r.nct+"|"+r.filename,r]));
 const docs=x.rows.flatMap(r=>r.sourcePdfFiles.map(d=>({nct:r.nct,...d})));
 assert.equal(docs.length,23);
 for(const r of docs){
  const b=pdf.get(r.nct+"|"+r.filename);
  assert.ok(b,r.nct+" "+r.filename);
  assert.equal(r.sha256,b.sha256);
  assert.equal(r.sourcePdfUrl,b.publicSourceUrl);
  assert.equal(r.sizeBytes,b.byteCount);
 }
});
test("R88 protects the ACACIA-HCM and Launch-HTN missing current registry originals",()=>{
 const x=R88_SOURCE_CHRONOLOGY;
 assert.equal(x.rows[0].originalPilot!==null,true);
 assert.equal(x.rows[1].originalPilot!==null,true);
 for(const nct of ["NCT06081894","NCT06153693"]){
  const r=x.rows.find(v=>v.nct===nct);
  assert.ok(r);
  assert.equal(r.sourcePdfFiles.length,0);
  assert.equal(r.sapDateChronologyState,"NO_CURRENT_REGISTRY_PROTOCOL_SAP_FILES");
  assert.match(r.nextRequiredProof,/absence here is not clinical failure/);
 }
});
test("R88 fails closed on forged source hashes, missing files, dates, NCTs, research claims or FDA outcomes",()=>{
 const scenarios=[
  x=>{x.files[0].observedPdfSha256="a".repeat(64);},
  x=>{x.files[0].sourcePdfUrl="https://attacker.example/a.pdf";},
  x=>{x.files[0].registryPrimaryCompletionDate="2020-01-01";},
  x=>{x.files[0].documentDateAfterPrimaryCompletion=!x.files[0].documentDateAfterPrimaryCompletion;},
  x=>{x.files[0].reportedDocumentDate="invalid";},
  x=>{x.files[0].registryUploadDate="2026-99-99T20:22";},
  x=>{x.files[0].prospectiveSignedSAPVerified=true;},
  x=>{x.files[0].independentStatisticianApproved=true;},
  x=>{x.files[1].filename=x.files[0].filename;x.files[1].nct=x.files[0].nct;},
  x=>{x.files.pop();},
  x=>{x.nctsWithoutCurrentRegistryProtocolSapFiles.pop();},
  x=>{x.counts.sapFilesWithDocumentDateAfterPrimaryCompletion=0;},
  x=>{x.counts.qualifiedSignedScientificReviews=1;},
  x=>{x.officialFDAOutcome="APPROVAL";},
  x=>{x.sources.archivedTrialPhaseBlobSha="bad";},
 ];
 for(const mutate of scenarios){
  const forged=structuredClone(dated);
  mutate(forged);
  assert.equal(buildR88SourceChronology(forged),null);
 }
});
test("R88 frontend presentation has dated provenance and navigation, no scoring action",()=>{
 const page=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/chronology/page.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,
  "app/predictions/original-documents/page.tsx"),"utf8");
 assert.match(page,/SOURCE_CHRONOLOGY/);
 assert.match(page,/primary-completion/);
 assert.match(page,/NOT VERIFIED/);
 assert.match(page,/FDA outcome forecast: ABSTAIN/);
 assert.match(page,/Open public original PDF/);
 assert.match(panel,/\/predictions\/original-documents\/chronology/);
 assert.doesNotMatch(page,/submitClinicalScore|fetch\(|setGrade\(|probabilityPercent/);
});
