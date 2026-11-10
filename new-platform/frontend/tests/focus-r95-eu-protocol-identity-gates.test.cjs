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
const source=require("../data/focus-r95-acacia-eu-protocol-identity-and-cohort-conflict-20261110.json");
const {R95_EU_ACACIA_PROTOCOL_IDENTITY,buildR95EuProtocolIdentityGates}=
 require("../lib/focus-r95-eu-protocol-identity-gates.ts");
const {R94_ACACIA_COHORT_SAFETY_SOURCE}=
 require("../lib/focus-r94-acacia-cross-source-reconciliation.ts");
const {R93_PRIORITY_SCIENTIFIC_GATES}=
 require("../lib/focus-r93-priority-scientific-gates.ts");

test("R95 exact EU and NCT study identity makes CY6033 the only permissible ACACIA source protocol",()=>{
 const d=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 assert.ok(d);
 assert.equal(d.exactNct,"NCT06081894");
 assert.equal(d.euTrialNumber,"2023-505797-15-00");
 assert.equal(d.sponsorProtocolCode,"CY 6033");
 assert.equal(d.correctComparator,"PLACEBO");
 assert.equal(d.wrongProtocolCodeExcluded,"CY 6032");
 assert.equal(d.wrongProtocolComparison,
  "AFICAMTEN_VS_METOPROLOL_OBSTRUCTIVE_HCM_NOT_ACACIA");
 assert.equal(d.officialEUHistorySource,
  "https://euclinicaltrials.eu/ctis-public/view/2023-505797-15-00?lang=en");
 assert.equal(d.publicDocumentIndexSource,"https://ctis.eu/trial/2023-505797-15-00");
 assert.match(d.confusingOtherTrialProtocolSource,/jacc\.org/);
 assert.equal(d.originalAcaciaGatesUnresolved,4);
 assert.equal(d.originalLaunchGatesUnresolved,7);
 assert.equal(R93_PRIORITY_SCIENTIFIC_GATES.unresolvedAuthenticatedScienceRequirements,11);
 assert.equal(R94_ACACIA_COHORT_SAFETY_SOURCE.originalAcaciaEvidenceGatesUnresolved,4);
 assert.equal(d.signedFinalSapVersionsVerified,0);
 assert.equal(d.exactOriginalPdfBytesCaptured,0);
 assert.equal(d.trialSafetyIndependentlySigned,false);
 assert.equal(d.qualifiedIndependentStatisticalReview,false);
 assert.equal(d.calibratedFDAPredictionAccuracyVerified,false);
 assert.equal(d.FDAForecast,"ABSTAIN");
});
test("R95 public CTIS amendment index is 133 entries, with AM4 protocol, AM3 synopsis, 435 planned NOT 517 actual",()=>{
 const d=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 assert.equal(d.CTISPublicDocumentEntries,133);
 assert.equal(d.ctisAmendment4ProtocolEntries,2);
 assert.equal(d.ctisAmendment3SynopsisEntries,1);
 assert.deepEqual(d.publicDocumentRecords.map(v=>v.version),["AM4","AM4","AM3"]);
 assert.ok(d.publicDocumentRecords.every(v=>v.originalByteSourceObtained===false));
 assert.deepEqual(d.publicDocumentRecords.map(v=>v.document),[
  "D1_2023-505797-15-00_Protocol_FP",
  "D1_2023-505797-15-00_Protocol_el_FP",
  "D1_2023-505797-15-00_Synopsis_EN_FP"
 ]);
 assert.equal(d.plannedInCTIS,435);
 assert.equal(d.plannedEUMemberStates,175);
 assert.equal(d.plannedRestOfWorld,260);
 assert.equal(d.plannedEUMemberStates+d.plannedRestOfWorld,435);
 assert.equal(d.ctisSubstantialModification3Submitted,"2024-12-19");
 assert.equal(d.ctisSubstantialModification3Decision,"2025-04-08");
 assert.equal(d.ctisSubstantialModification4Submitted,"2025-07-08");
 assert.equal(d.ctisSubstantialModification4Decision,"2025-09-08");
 assert.equal(source.ctisCrosswalk.CTISPlannedTargetNotActualRandomized,true);
 assert.equal(source.ctisCrosswalk.originalApprovalPdfBytesCaptured,false);
 assert.equal(source.ctisCrosswalk.authoritativePreUnblindingPlanApproved,false);
});
test("R95 source-cohort claims are conflicting, so R94 one-person-treated hypothesis is NOT certified",()=>{
 const d=R95_EU_ACACIA_PROTOCOL_IDENTITY;
 assert.equal(d.observedSponsorCohortClaimContradiction,true);
 assert.equal(d.populationExplanationStatus,
  "CONFLICTED_516_517_SPONSOR_PUBLIC_COHORT_CLAIMS_NOT_RECONCILED");
 assert.deepEqual(d.sourcePublishedCohortClaims.map(v=>v.claim),[
  "516 randomized and treated outside Japan",
  "517 randomized, arms 258 aficamten and 259 placebo",
  "517 randomized and treated outside Japan",
  "517 randomized but 516 treated"
 ]);
 assert.equal(source.reportedCohortConflict.whetherExactlyOneParticipantWasNotTreated,null);
 assert.equal(source.reportedCohortConflict.firstDoseListingAuthenticallyRead,false);
 assert.equal(source.reportedCohortConflict.definitivePopulationReconciliation,false);
 assert.equal(R94_ACACIA_COHORT_SAFETY_SOURCE.secondaryPaperTreatVsRandomizedDifferByOne,1);
 assert.equal(R94_ACACIA_COHORT_SAFETY_SOURCE.independentSAPProspectivityAuthentication,false);
});
test("R95 rejects misidentified trials, foreign source PDFs, invented SAP bytes, and forged approval claims",()=>{
 const attacks=[
  x=>{x.exactResearchNct="NCT05767346";},
  x=>{x.exactEuTrialNumber="2023-504809-37-00";},
  x=>{x.exactSponsorProtocolCode="CY 6032";},
  x=>{x.comparator="METOPROLOL";},
  x=>{x.documentarySourceReceipts[0].reportedProtocol="CY 6032";},
  x=>{x.documentarySourceReceipts[1].url="https://fake.example";},
  x=>{x.documentarySourceReceipts[2].reportedProtocol="CY 6033";},
  x=>{x.documentarySourceReceipts[2].pdfBytesObtained=true;},
  x=>{x.documentarySourceReceipts.pop();},
  x=>{x.ctisCrosswalk.amendedProtocolListing[0].documentVersion="AM5";},
  x=>{x.ctisCrosswalk.amendedProtocolListing[1].contentBytesObtained=true;},
  x=>{x.ctisCrosswalk.listedDocumentEntries=134;},
  x=>{x.ctisCrosswalk.CTISPlannedEUCountrySum=435;},
  x=>{x.ctisCrosswalk.CTISPlannedTargetNotActualRandomized=false;},
  x=>{x.ctisCrosswalk.regulatorySubmissions[2].decisionDate="2025-05-15";},
  x=>{x.ctisCrosswalk.authoritativePreUnblindingPlanApproved=true;},
  x=>{x.wrongTrialSource.excludeFromAcaciaOriginalSourceCorpus=false;},
  x=>{x.reportedCohortConflict.laterAugustSponsor="516 randomized and treated outside Japan";},
  x=>{x.reportedCohortConflict.whetherExactlyOneParticipantWasNotTreated=true;},
  x=>{x.reportedCohortConflict.definitivePopulationReconciliation=true;},
  x=>{x.publicNejmSupplement.exactOriginalSupplementaryPDFBytesRead=true;},
  x=>{x.newProspectivelyAuthenticatedSignedSAPs=1;},
  x=>{x.newIndependentScientificSignoffs=1;},
  x=>{x.prediction="APPROVAL";}
 ];
 for(const mutate of attacks){
  const clone=structuredClone(source);
  mutate(clone);
  assert.equal(buildR95EuProtocolIdentityGates(clone),null);
 }
});
test("R95 UI identifies the correct EU protocol and does not promote source listings to final clinical grades",()=>{
 const file=fs.readFileSync(path.join(root,
  "app/predictions/scientific-reconciliation/priority-gates/page.tsx"),"utf8");
 assert.match(file,/R95_EU_ACACIA_PROTOCOL_IDENTITY/);
 assert.match(file,/Revision 95: correct original EU protocol identity/);
 assert.match(file,/wrongProtocolCodeExcluded/);
 assert.match(file,/planning target/);
 assert.match(file,/original CONSORT and first-dose listings/);
 assert.match(file,/FDA forecast: ABSTAIN/);
 assert.doesNotMatch(file,/setGrade\(|submitClinicalScore|modelTraining\(/);
});
