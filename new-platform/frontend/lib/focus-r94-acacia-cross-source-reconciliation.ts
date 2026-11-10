/** MAIN R94 — published-source claim comparison, never original sponsor-
 * controlled SAP approval, participant-level case reconciliation or FDA grade.
 */
import raw from "../data/focus-r94-acacia-published-population-safety-source-claims-20261110.json";
import {R93_PRIORITY_SCIENTIFIC_GATES} from "./focus-r93-priority-scientific-gates";

const expected:Record<string,{type:string;url:string;date:string}>={
 S1:{
  type:"PRIMARY_PUBLISHED_ARTICLE",date:"2026-08-28",
  url:"https://www.nejm.org/doi/10.1056/NEJMoa2603021"
 },
 S2:{
  type:"EARLIER_SPONSOR_TOPLINE",date:"2026-05",
  url:"https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Positive-Topline-Results-from-ACACIA-HCM-the-Pivotal-Phase-3-Clinical-Trial-of-Aficamten-in-Patients-with-Non-Obstructive-Hypertrophic-Cardiomyopathy/default.aspx"
 },
 S3:{
  type:"AUTHORED_SECONDARY_CLINICAL_APPRAISAL",date:"2026-10-27",
  url:"https://opensourcecardiology.org/doi/osc.2026.0037"
 },
 S4:{
  type:"LATER_SPONSOR_SAFETY_DISCLOSURE",date:"2026-10-12",
  url:"https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Data-from-ACACIA-HCM-Presented-at-the-HFSA-Annual-Scientific-Meeting-2026/default.aspx"
 },
 S5:{
  type:"PUBLISHED_SECONDARY_RESPONDER_ANALYSIS",date:"2026-08-28",
  url:"https://pmc.ncbi.nlm.nih.gov/articles/PMC13674601/"
 }
};
export function buildR94AcaciaPublishedClaimReconciliation(input:typeof raw=raw){
 const prev=R93_PRIORITY_SCIENTIFIC_GATES;
 if(!prev||prev.priorityOriginalTrialCases!==2||
   prev.unresolvedAuthenticatedScienceRequirements!==11||
   prev.acaciaOriginalHistoricalVersions!==4||
   prev.independentlyVerifiedSignedProspectiveSAPs!==0||
   prev.qualifiedIndependentScienceSignoffs!==0||
   prev.validatedFDAPredictions!==0||
   prev.cases.length!==2||
   prev.cases[0].nct!=="NCT06081894"||
   prev.cases[0].gates.length!==4||
   prev.cases[1].nct!=="NCT06153693"||
   prev.cases[1].gates.length!==7||
   prev.cases.some(x=>x.signedOriginalSAPAuthenticated!==false||
    x.independentScienceApproved!==false||x.methodGrade!==null||
    x.FDAForecast!=="ABSTAIN")||
   input.schema!=="MAIN_R94_ACACIA_REPORTED_POPULATION_AND_HEART_FAILURE_CASES_CROSS_SOURCE_RESEARCH_ONLY"||
   input.asOf!=="2026-11-10"||input.nct!=="NCT06081894"||
   input.ticker!=="CYTK"||input.trial!=="ACACIA-HCM"||
   input.sources.length!==5||
   input.originalAcaciaGatesUnresolved!==4||
   input.launchOriginalGatesUnresolved!==7||
   input.newAuthenticProspectiveSignedSAPs!==0||
   input.newIndependentQualifiedScienceSignoffs!==0||
   input.newValidatedFDAPredictions!==0||
   input.FDAForecast!=="ABSTAIN"||input.noProductionWrites!==true)return null;

 const ids=new Set<string>();
 for(const s of input.sources){
  const e=expected[s.id];
  if(!e||ids.has(s.id)||s.type!==e.type||s.url!==e.url||
     s.published!==e.date||s.contentBytesCaptured!==false||
     s.independentSignedSapProof!==false||
     typeof s.preciseClaim!=="string"||
     s.preciseClaim.length<100||s.preciseClaim.length>700)return null;
  ids.add(s.id);
 }
 if(ids.size!==5||Object.keys(expected).some(id=>!ids.has(id)))return null;
 const p=input.reportedCohorts,sa=input.reportedSafety,a=input.publishedSAPClaim,
  files=input.nejmAttachments;
 if(p.primaryNEJM.aficamtenRandomized!==258||
   p.primaryNEJM.placeboRandomized!==259||
   p.primaryNEJM.randomizedTotal!==517||
   p.primaryNEJM.sourceId!=="S1"||
   p.earlierTopline.numberDescribedAsRandomizedAndTreated!==516||
   p.earlierTopline.sourceId!=="S2"||
   p.earlierTopline.originalPopulationDefinitionIndependentlyCertified!==false||
   p.secondaryAppraisal.randomized!==517||
   p.secondaryAppraisal.treated!==516||
   p.secondaryAppraisal.sourceId!=="S3"||
   p.secondaryAppraisal.individualUntreatedPatientIndependentlyIdentified!==false||
   p.cohortDiscrepancyDefinitivelyResolved!==false||
   sa.primaryNEJM.LVEFbelow50Aficamten!==27||
   sa.primaryNEJM.LVEFbelow50Placebo!==2||
   sa.primaryNEJM.anySAEAficamten!==52||
   sa.primaryNEJM.anySAEPlacebo!==38||
   sa.primaryNEJM.sourceId!=="S1"||
   sa.OctoberSponsor.totalHfSAEAficamten!==12||
   sa.OctoberSponsor.totalHfSAEPlacebo!==3||
   sa.OctoberSponsor.hFSAEAficamtenWithLVEFbelow50!==2||
   sa.OctoberSponsor.hFSAEAficamtenWithoutLVEFbelow50!==10||
   sa.OctoberSponsor.sourceId!=="S4"||
   sa.earlierSourceCaseCount.hFSAEAficamten!==11||
   sa.earlierSourceCaseCount.hFSAEPlacebo!==1||
   sa.actualHFExposurePopulationIndependentlyReviewed!==false||
   sa.safetyFindingsIndependentlyAdjudicated!==false||
   a.sourceId!=="S5"||
   a.authorsStateIncludedBeforeLockAndUnblinding!==true||
   a.sourceQualification!=="AUTHOR_REPORTED_NOT_INDEPENDENTLY_AUTHENTICATED"||
   a.originalApprovedSAPVersionCaptured!==false||
   a.originalSAPSignerApprovalVerified!==false||
   a.originalDatabaseLockDateVerified!==false||
   a.firstUnblindedAccessDateVerified!==false||
   files.protocolFilename!=="nejmoa2603021_protocol.pdf"||
   files.appendixFilename!=="nejmoa2603021_appendix.pdf"||
   files.originalNEJMPublisherAttachmentBytesReadThisRevision!==false)return null;
 if(p.primaryNEJM.aficamtenRandomized+p.primaryNEJM.placeboRandomized!==517||
   sa.OctoberSponsor.hFSAEAficamtenWithLVEFbelow50+
    sa.OctoberSponsor.hFSAEAficamtenWithoutLVEFbelow50!==
    sa.OctoberSponsor.totalHfSAEAficamten)return null;
 return {
  schema:"MAIN_R94_ACACIA_COHORT_AND_HF_SAE_SOURCE_PROVENANCE_NOT_INDEPENDENT_SAP" as const,
  originalSourceDateUtc:input.asOf,
  exactNct:input.nct,
  numberOfOriginalResearchSourceLinks:5 as const,
  randomizedFromNEJM:517 as const,
  aficamtenRandomized:258 as const,
  placeboRandomized:259 as const,
  secondaryPaperReportedTreated:516 as const,
  secondaryPaperTreatVsRandomizedDifferByOne:1 as const,
  sourceComparisonStatus:"PLAUSIBLE_RANDOMIZED_VERSUS_TREATED_COHORT_EXPLANATION_NOT_SOURCE_CERTIFIED" as const,
  earlySourceReportedHfSAECasesAficamten:11 as const,
  earlySourceReportedHfSAECasesPlacebo:1 as const,
  octoberSponsorHfSAECasesAficamten:12 as const,
  octoberSponsorHfSAECasesPlacebo:3 as const,
  octoberSponsorHFWithLVEFBelow50:2 as const,
  octoberSponsorHFWithoutLVEFBelow50:10 as const,
  separateSafetyTermDefinitionsKnownOnlyWithinOctoberSource:true as const,
  earlierHFCountDiscrepancyStillUnresolved:true as const,
  responderAuthorsClaimPreLockPrespecification:true as const,
  independentSAPProspectivityAuthentication:false as const,
  publisherProtocolPdfBytesCaptured:false as const,
  originalAcaciaEvidenceGatesUnresolved:4 as const,
  originalLaunchEvidenceGatesUnresolved:7 as const,
  signedOriginalSAPsIndependentlyAuthenticated:0 as const,
  qualifiedMedicalScienceReviews:0 as const,
  validatedFDAForecasts:0 as const,
  FDAForecast:"ABSTAIN" as const,
  sourceLinks:input.sources.map(s=>({
   id:s.id,type:s.type,published:s.published,
   url:s.url,claim:s.preciseClaim,originalBytesNotCaptured:true as const
  })),
  reviewNeeded:[
   "Reconcile the one-person randomized versus treated difference using source-controlled CONSORT, first-dose listing, FAS/mITT and safety set files; never invent an individual exclusion reason.",
   "Reconcile original 11/1 and October 12/3 HF SAE source populations, MedDRA definitions, windows, adjudication and case numbers using source-controlled patient safety listings.",
   "Acquire publisher protocol/appendix PDF bytes or sponsor-controlled final signed SAP with hash and amendment approvals; separately authenticate SAP signing before first blind-break access.",
   "Apply an independent qualified statistical and medical review to the original source, including efficacy estimands, multiplicity, missingness, dosing and safety."
  ]
 };
}
export const R94_ACACIA_COHORT_SAFETY_SOURCE=buildR94AcaciaPublishedClaimReconciliation();
