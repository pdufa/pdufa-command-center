"use strict";
const test=require("node:test"),assert=require("node:assert/strict");
const fs=require("node:fs"),path=require("node:path"),ts=require("typescript");
const root=path.resolve(__dirname,"..");
require.extensions[".ts"]=(mod,file)=>{
 const out=ts.transpileModule(fs.readFileSync(file,"utf8"),{
  compilerOptions:{target:ts.ScriptTarget.ES2022,module:ts.ModuleKind.CommonJS,
   jsx:ts.JsxEmit.ReactJS,esModuleInterop:true}});
 mod._compile(out.outputText,file);
};
const original=require("../data/focus-r94-acacia-published-population-safety-source-claims-20261110.json");
const {R94_ACACIA_COHORT_SAFETY_SOURCE,buildR94AcaciaPublishedClaimReconciliation}=
 require("../lib/focus-r94-acacia-cross-source-reconciliation.ts");
const {R93_PRIORITY_SCIENTIFIC_GATES}=
 require("../lib/focus-r93-priority-scientific-gates.ts");
test("R94 published original sources classify 517 randomized, 516 treated as plausible, not adjudicated",()=>{
 const r=R94_ACACIA_COHORT_SAFETY_SOURCE;
 assert.ok(r);
 assert.equal(r.exactNct,"NCT06081894");
 assert.equal(r.numberOfOriginalResearchSourceLinks,5);
 assert.equal(new Set(r.sourceLinks.map(x=>x.id)).size,5);
 assert.equal(r.randomizedFromNEJM,517);
 assert.equal(r.aficamtenRandomized,258);
 assert.equal(r.placeboRandomized,259);
 assert.equal(r.secondaryPaperReportedTreated,516);
 assert.equal(r.secondaryPaperTreatVsRandomizedDifferByOne,1);
 assert.equal(r.sourceComparisonStatus,
  "PLAUSIBLE_RANDOMIZED_VERSUS_TREATED_COHORT_EXPLANATION_NOT_SOURCE_CERTIFIED");
 assert.equal(r.independentSAPProspectivityAuthentication,false);
 assert.equal(r.publisherProtocolPdfBytesCaptured,false);
 assert.equal(r.originalAcaciaEvidenceGatesUnresolved,4);
 assert.equal(r.originalLaunchEvidenceGatesUnresolved,7);
 assert.equal(r.signedOriginalSAPsIndependentlyAuthenticated,0);
 assert.equal(r.qualifiedMedicalScienceReviews,0);
 assert.equal(r.validatedFDAForecasts,0);
 assert.equal(r.FDAForecast,"ABSTAIN");
 assert.ok(r.sourceLinks.every(x=>x.originalBytesNotCaptured===true));
});
test("R94 reports October 12/3 HF SAEs with 2+10 subtypes without rewriting earlier 11/1",()=>{
 const d=R94_ACACIA_COHORT_SAFETY_SOURCE;
 assert.equal(d.earlySourceReportedHfSAECasesAficamten,11);
 assert.equal(d.earlySourceReportedHfSAECasesPlacebo,1);
 assert.equal(d.octoberSponsorHfSAECasesAficamten,12);
 assert.equal(d.octoberSponsorHfSAECasesPlacebo,3);
 assert.equal(d.octoberSponsorHFWithLVEFBelow50,2);
 assert.equal(d.octoberSponsorHFWithoutLVEFBelow50,10);
 assert.equal(d.earlierHFCountDiscrepancyStillUnresolved,true);
 assert.equal(d.separateSafetyTermDefinitionsKnownOnlyWithinOctoberSource,true);
 assert.equal(d.responderAuthorsClaimPreLockPrespecification,true);
 assert.equal(d.independentSAPProspectivityAuthentication,false);
 assert.equal(R93_PRIORITY_SCIENTIFIC_GATES.unresolvedAuthenticatedScienceRequirements,11);
 assert.equal(R93_PRIORITY_SCIENTIFIC_GATES.cases[0].gates.length,4);
 assert.equal(R93_PRIORITY_SCIENTIFIC_GATES.cases[1].gates.length,7);
});
test("R94 rejects fake article provenance, cohort counts, HF definitions, original locked SAP assertions and review grades",()=>{
 const attacks=[
  x=>{x.nct="NCT00000000";},
  x=>{x.sources[0].id="S99";},
  x=>{x.sources[0].url="https://attacker.example/fake.pdf";},
  x=>{x.sources[1].contentBytesCaptured=true;},
  x=>{x.sources[4].independentSignedSapProof=true;},
  x=>{x.reportedCohorts.primaryNEJM.randomizedTotal=516;},
  x=>{x.reportedCohorts.secondaryAppraisal.individualUntreatedPatientIndependentlyIdentified=true;},
  x=>{x.reportedCohorts.cohortDiscrepancyDefinitivelyResolved=true;},
  x=>{x.reportedSafety.OctoberSponsor.totalHfSAEAficamten=11;},
  x=>{x.reportedSafety.earlierSourceCaseCount.hFSAEPlacebo=3;},
  x=>{x.reportedSafety.safetyFindingsIndependentlyAdjudicated=true;},
  x=>{x.publishedSAPClaim.originalDatabaseLockDateVerified=true;},
  x=>{x.publishedSAPClaim.originalSAPSignerApprovalVerified=true;},
  x=>{x.nejmAttachments.originalNEJMPublisherAttachmentBytesReadThisRevision=true;},
  x=>{x.newIndependentQualifiedScienceSignoffs=1;},
  x=>{x.FDAForecast="APPROVED";},
  x=>{x.originalAcaciaGatesUnresolved=0;},
  x=>{x.sources.pop();}
 ];
 for(const mutate of attacks){
  const x=structuredClone(original);
  mutate(x);
  assert.equal(buildR94AcaciaPublishedClaimReconciliation(x),null);
 }
});
test("R94 source evidence presentation remains research-only and preserves prior 11 source gates",()=>{
 const page=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
 assert.match(page,/Revision 94: cross-source cohort and heart-failure case-definition audit/);
 assert.match(page,/R94_ACACIA_COHORT_SAFETY_SOURCE/);
 assert.match(page,/not yet confirmed by original CONSORT/);
 assert.match(page,/HF clinical adjudication/);
 assert.match(page,/FDA outcome forecast: ABSTAIN/);
 assert.doesNotMatch(page,/submitClinicalScore|setGrade\(|probabilityPercent|approvedByMedicalReviewer/);
});

test("R94 source handoff CSV keeps 11 original gates and adds qualified 517/516, HF and author-asserted SAP leads",async()=>{
 const {GET}=require("../app/predictions/scientific-reconciliation/priority-gates/export/route.ts");
 const resp=GET();
 assert.equal(resp.status,200);
 const csv=await resp.text();
 assert.equal(csv.trim().split("\r\n").length,12);
 assert.match(csv,/R94_public_source_clarification_not_adjudicated/);
 assert.match(csv,/517 randomized/);
 assert.match(csv,/516 treated/);
 assert.match(csv,/HF SAE 12\/3/);
 assert.match(csv,/11\/1/);
 assert.match(csv,/signed SAP and first-access audit not independently authenticated/);
 assert.match(csv,/main-r94-priority-original-evidence-gates/);
 assert.match(csv,/NOT_VERIFIED/);
 assert.match(csv,/NOT_SIGNED/);
 assert.match(csv,/ABSTAIN/);
});
