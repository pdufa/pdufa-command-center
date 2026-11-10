"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
for(const ext of [".ts",".tsx"])require.extensions[ext]=(mod,file)=>{
 const c=ts.transpileModule(fs.readFileSync(file,"utf8"),{compilerOptions:{
  target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
  jsx:ts.JsxEmit.ReactJS,esModuleInterop:true
 }});mod._compile(c.outputText,file);
};
const raw=require("../data/focus-r72-capr-regulatory-source-challenge.json");
const {FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE,buildR72CaprSourceChallenge}=
 require("../lib/focus-r72-capr-regulatory-source-challenge.ts");

test("CAPR exact 29/23 application identity and FDA adverse evidence preserve no FDA forecast",()=>{
 const r=FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE;
 assert.ok(r);
 assert.equal(r.asOf,"2026-11-09");
 assert.equal(r.nct,"NCT05126758");
 assert.equal(r.cycleId,"capr-deramiocel");
 assert.equal(r.bla,"125842/0");
 assert.equal(r.originalFDAReportDate,"2026-07-29");
 assert.equal(r.originalFDAFirstPublicAvailabilityAuthenticated,false);
 assert.equal(r.pdufaTarget.date,"2026-11-22");
 assert.equal(r.pdufaTarget.previousDate,"2026-08-22");
 assert.equal(r.pdufaTarget.status,"FORMAL_MAJOR_AMENDMENT_EXTENSION_ALREADY_REPORTED");
 assert.equal(r.futureTimingForecast,"UNKNOWN");
 assert.equal(r.futureApprovalOrCrlForecast,"ABSTAIN");
 assert.equal(r.clinicalGrade,null);
 assert.equal(r.independentClinicalReviewSigned,false);
 assert.equal(r.historicalPredictionSafe,false);
 assert.equal(r.canAwardScienceGrade,false);
 assert.equal(r.canProduceNumericalFDAProbability,false);
 assert.equal(r.researchLimitations.noTrainingOrProductionWrites,true);
});

test("Original FDA Table 7 is never equated to the applicant's percent-change outcome",()=>{
 const p=FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE.primaryAnalysisComparisons;
 assert.deepEqual(p.map(x=>x.id),[
  "FDA_SAP11_PRESPECIFIED","FDA_SAP30_NO_IMPUTATION","APPLICANT_MODIFIED_CSR"]);
 assert.deepEqual(p.map(x=>x.p),["0.24","0.21","0.029"]);
 assert.deepEqual(p.map(x=>x.difference),["0.66","2.53","4.55"]);
 assert.notEqual(p[0].endpointScale,p[2].endpointScale);
 assert.equal(p[0].sourcePdfPrintedPage,40);
 assert.equal(p[2].sourcePdfPrintedPage,40);
 const s=FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE.secondaryAnalysisComparisons;
 assert.deepEqual(s.map(x=>x.p),["0.97","0.09","0.041"]);
 assert.deepEqual(s.map(x=>x.sourcePdfPrintedPage),[42,42,42]);
 assert.equal(FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE.evidenceChronology.length,8);
 assert.equal(FOCUS_R72_CAPR_REGULATORY_SOURCE_CHALLENGE.priorityResearchGates.length,6);
});

test("Research file rejects fabricated provenance, FDA result, grade or timestamp",()=>{
 const attacks=[
  x=>x.nct="NCT99999999",
  x=>x.pdufaTarget.date="2026-11-20",
  x=>x.primaryAnalysisComparisons[0].p="0.029",
  x=>x.primaryAnalysisComparisons[2].difference="0.66",
  x=>x.primaryAnalysisComparisons[0].endpointScale=x.primaryAnalysisComparisons[2].endpointScale,
  x=>x.secondaryAnalysisComparisons[0].p="0.041",
  x=>x.evidenceChronology[7].source="https://attacker.example",
  x=>x.evidenceChronology[5].date="2026-08-29",
  x=>x.originalFDAFirstPublicAvailabilityAuthenticated=true,
  x=>x.clinicalGrade=5,
  x=>x.independentClinicalReviewSigned=true,
  x=>x.futureApprovalOrCrlForecast="APPROVE",
  x=>x.futureTimingForecast="ON_TIME",
  x=>x.researchLimitations.noTrainingOrProductionWrites=false,
  x=>x.newScore=99
 ];
 for(let i=0;i<attacks.length;i++){
  const v=structuredClone(raw);attacks[i](v);
  assert.equal(buildR72CaprSourceChallenge(v),null,"tamper case "+i);
 }
});

test("R72 appears solely in the CAPR evidence-gaps research panel, never a scoring API",()=>{
 const host=fs.readFileSync(path.join(root,
 "app/predictions/evidence-gaps/ScientificOriginalsIntakeR71.tsx"),"utf8");
 const panel=fs.readFileSync(path.join(root,
 "app/predictions/evidence-gaps/CaprFdaChallengeR72.tsx"),"utf8");
 assert.match(host,/nct==="NCT05126758"&&<CaprFdaChallengeR72\/>/);
 assert.match(panel,/FDA vs applicant analysis/);
 assert.match(panel,/incompatible endpoint scales/);
 assert.match(panel,/UNASSESSED/);
 assert.match(panel,/ABSTAIN/);
 assert.match(panel,/not a final ruling/);
 assert.doesNotMatch(panel,/fetch\(|POST\s*\/api|setGrade\(|submitClinicalScore/);
});
