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
const raw=require("../data/focus-r73-launch-htn-original-document-index.json");
const {FOCUS_R73_LAUNCH_HTN_DOCUMENT_INDEX,buildR73LaunchHtnDocumentIndex}=
 require("../lib/focus-r73-launch-htn-document-index.ts");

test("R73 shows exactly 3 protocol versions, 3 SAP files and one methods supplement",()=>{
 const x=FOCUS_R73_LAUNCH_HTN_DOCUMENT_INDEX;
 assert.ok(x);
 assert.equal(x.nct,"NCT06153693");
 assert.equal(x.pmid,"40587141");
 assert.equal(x.indexedDocumentCount,7);
 assert.equal(x.protocolVersions,3);
 assert.equal(x.sapDocuments,3);
 assert.equal(x.independentlyAuthenticatedOriginalPdfBytes,0);
 assert.equal(x.independentlySignedSAPs,0);
 assert.equal(x.releaseOfClinicalGrades,false);
 assert.equal(x.officialFutureFDAOutcome,"ABSTAIN");
 assert.equal(x.forecastTiming,"UNKNOWN");
 assert.equal(x.documents.length,7);
 for(let i=0;i<7;i++){
   assert.equal(x.documents[i].supplementNumber,i+1);
   assert.match(x.documents[i].publicOriginalIndexLink,/https:\/\/pmc[.]ncbi[.]nlm[.]nih[.]gov\/articles\/instance\/12210145\/bin\//);
   assert.equal(x.documents[i].sha256,null);
   assert.equal(x.documents[i].firstPublicAvailabilityDate,null);
 }
});

test("R73 document URLs, release claims and scientific scores fail closed under tampering",()=>{
 const attacks=[
  x=>x.documents.pop(),
  x=>x.documents.reverse(),
  x=>x.documents[0].publicOriginalIndexLink="https://fake.invalid/a.pdf",
  x=>x.documents[1].role="SAP_AMENDMENT",
  x=>x.documents[1].filename="fake.pdf",
  x=>x.documents[4].title="Statistical analysis plan signed before unblinding",
  x=>x.documents[1].originalPdfBytesIndependentVerification=true,
  x=>x.documents[1].sha256="a".repeat(64),
  x=>x.documents[2].documentInternalVersionDate="2025-01-01",
  x=>x.documents[2].firstPublicAvailabilityDate="2025-01-01",
  x=>x.documents[2].prospectivelySignedAndLockedBeforeUnblinding=true,
  x=>x.originalPreunblindingSignaturesVerified=1,
  x=>x.originalFullPdfScientificReviewsSigned=1,
  x=>x.validatedFDAApplicationForecasts=1,
  x=>x.clinicalGrade=5,
  x=>x.officialFutureFDAOutcome="APPROVAL",
  x=>x.trainingOrProductionWrites=true
 ];
 for(let i=0;i<attacks.length;i++){
  const clone=structuredClone(raw);attacks[i](clone);
  assert.equal(buildR73LaunchHtnDocumentIndex(clone),null,"tamper "+i);
 }
});

test("R73 original index renders only in Launch-HTN evidence research, not grading API",()=>{
 const host=fs.readFileSync(path.join(root,
   "app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,
   "app/predictions/evidence-gaps/LaunchHtnOriginalDocumentsR73.tsx"),"utf8");
 assert.match(host,/nct==="NCT06153693"&&<LaunchHtnOriginalDocumentsR73\/>/);
 assert.match(panel,/Seven exact original publication supplement links/);
 assert.match(panel,/0\/7/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/NOT/);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|setGrade\(|submitClinicalScore/);
});
