/** MAIN R95 — disambiguate ACACIA-HCM EU trial protocol CY 6033 from
 * separate aficamten CY 6032 MAPLE-HCM. This is identity and source-date
 * research ONLY, not a recovered signed final SAP.
 */
import raw from "../data/focus-r95-acacia-eu-protocol-identity-and-cohort-conflict-20261110.json";
import {R94_ACACIA_COHORT_SAFETY_SOURCE} from "./focus-r94-acacia-cross-source-reconciliation";
import {R93_PRIORITY_SCIENTIFIC_GATES} from "./focus-r93-priority-scientific-gates";
const VALID_SOURCES={
 CTIS_EU_ORIGINAL:{
  url:"https://euclinicaltrials.eu/ctis-public/view/2023-505797-15-00?lang=en",
  kind:"OFFICIAL_EU_REGISTRY_STUDY_IDENTITY_AND_AMENDMENT_HISTORY",
  protocol:"CY 6033",nct:"NCT06081894"},
 CTIS_EU_INDEXED_LIST:{
  url:"https://ctis.eu/trial/2023-505797-15-00",
  kind:"SECONDARY_INDEX_OF_PUBLIC_EU_TRIAL_RECORD_AND_133_DOCUMENT_ENTRIES",
  protocol:"CY 6033",nct:"NCT06081894"},
 JACC_CY6032_DIFFERENT_TRIAL:{
  url:"https://www.jacc.org/doi/suppl/10.1016/j.jacc.2025.08.022/suppl_file/mmc3.pdf",
  kind:"DIFFERENT_TRIAL_OBSTRUCTIVE_HCM_AFICAMTEN_VERSUS_METOPROLOL_NOT_ACACIA",
  protocol:"CY 6032",nct:null},
 AUG_CYTK_SPONSOR:{
  url:"https://ir.cytokinetics.com/press-releases/press-release-details/2026/Cytokinetics-Announces-Additional-Results-from-ACACIA-HCM-and-MAPLE-HCM-Presented-in-Late-Breaking-Clinical-Trial-Session-at-the-European-Society-of-Cardiology-ESC-Congress-2026/default.aspx",
  kind:"LATER_SPONSOR_REPORTED_RANDOMIZED_AND_TREATED_517",
  protocol:null,nct:null}
} as const;
const expectedDocs=[
 ["D1_2023-505797-15-00_Protocol_FP","AM4","PROTOCOL_FOR_PUBLICATION"],
 ["D1_2023-505797-15-00_Protocol_el_FP","AM4","PROTOCOL_FOR_PUBLICATION_GREEK"],
 ["D1_2023-505797-15-00_Synopsis_EN_FP","AM3","PROTOCOL_SYNOPSIS_FOR_PUBLICATION"]
] as const;
const expectedDates=[
 ["IN","2023-10-26","2024-03-04","ACCEPTABLE_WITH_CONDITIONS"],
 ["SM-3","2024-12-19","2025-04-08","ACCEPTABLE"],
 ["SM-4","2025-07-08","2025-09-08","ACCEPTABLE"],
 ["SM-5","2025-11-13","2026-03-09","ACCEPTABLE"]
] as const;
export function buildR95EuProtocolIdentityGates(input:typeof raw=raw){
 const r=R94_ACACIA_COHORT_SAFETY_SOURCE,p=R93_PRIORITY_SCIENTIFIC_GATES;
 if(!r||!p||r.exactNct!=="NCT06081894"||
    r.numberOfOriginalResearchSourceLinks!==5||
    r.originalAcaciaEvidenceGatesUnresolved!==4||
    r.originalLaunchEvidenceGatesUnresolved!==7||
    r.independentSAPProspectivityAuthentication!==false||
    r.validatedFDAForecasts!==0||
    p.unresolvedAuthenticatedScienceRequirements!==11||
    p.independentlyVerifiedSignedProspectiveSAPs!==0||
    p.qualifiedIndependentScienceSignoffs!==0||
    input.schema!=="MAIN_R95_ACACIA_EU_CY6033_EXACT_ID_AMENDMENT_AND_COHORT_DISCREPANCY_NOT_SIGNED_SAP"||
    input.reviewDateUtc!=="2026-11-10"||
    input.exactResearchNct!=="NCT06081894"||
    input.ticker!=="CYTK"||
    input.exactSponsorProtocolCode!=="CY 6033"||
    input.exactEuTrialNumber!=="2023-505797-15-00"||
    input.comparator!=="PLACEBO"||
    input.populationDisease!=="SYMPTOMATIC NON-OBSTRUCTIVE HYPERTROPHIC CARDIOMYOPATHY"||
    input.documentarySourceReceipts.length!==4||
    input.originalAcaciaGatesStillUnresolved!==4||
    input.originalLaunchGatesStillUnresolved!==7||
    input.newProspectivelyAuthenticatedSignedSAPs!==0||
    input.newIndependentScientificSignoffs!==0||
    input.validatedFDAForecasts!==0||
    input.prediction!=="ABSTAIN"||
    input.changesToProduction!==false)return null;
 const seen=new Set<string>();
 for(const s of input.documentarySourceReceipts){
  const x=VALID_SOURCES[s.id as keyof typeof VALID_SOURCES];
  if(!x||seen.has(s.id)||s.url!==x.url||s.sourceKind!==x.kind||
     s.reportedProtocol!==x.protocol||s.reportedNct!==x.nct||
     s.sourceTextRead!==true||s.pdfBytesObtained!==false)return null;
  seen.add(s.id);
 }
 if(seen.size!==4||Object.keys(VALID_SOURCES).some(id=>!seen.has(id)))return null;
 const ctis=input.ctisCrosswalk;
 if(ctis.officialEUCTisIdentity!==input.exactEuTrialNumber||
    ctis.nct!==input.exactResearchNct||
    ctis.sponsorProtocolCode!==input.exactSponsorProtocolCode||
    ctis.listedDocumentEntries!==133||
    ctis.CTISPlannedTotalParticipants!==435||
    ctis.CTISPlannedEUCountrySum!==175||
    ctis.CTISPlannedRestOfWorld!==260||
    ctis.CTISPlannedTargetNotActualRandomized!==true||
    ctis.CTISPlannedEUCountrySum+ctis.CTISPlannedRestOfWorld!==ctis.CTISPlannedTotalParticipants||
    ctis.amendedProtocolListing.length!==3||
    ctis.regulatorySubmissions.length!==4||
    ctis.exactApprovedSAPContainedInPublicCTISIndex!==false||
    ctis.originalApprovalPdfBytesCaptured!==false||
    ctis.authoritativePreUnblindingPlanApproved!==false)return null;
 for(let i=0;i<expectedDocs.length;i++){
  const d=ctis.amendedProtocolListing[i],e=expectedDocs[i];
  if(!d||d.docTitle!==e[0]||d.documentVersion!==e[1]||
     d.docType!==e[2]||d.contentBytesObtained!==false)return null;
 }
 for(let i=0;i<expectedDates.length;i++){
  const d=ctis.regulatorySubmissions[i],e=expectedDates[i];
  if(!d||d.id!==e[0]||d.dateSubmitted!==e[1]||
     d.decisionDate!==e[2]||d.decision!==e[3])return null;
 }
 const other=input.wrongTrialSource,cohorts=input.reportedCohortConflict,
  supplement=input.publicNejmSupplement;
 if(other.protocolCode!=="CY 6032"||other.comparator!=="METOPROLOL"||
    other.condition!=="OBSTRUCTIVE_HYPERTROPHIC_CARDIOMYOPATHY"||
    other.distinctFromAcaciaProtocolCY6033!==true||
    other.excludeFromAcaciaOriginalSourceCorpus!==true||
    cohorts.earlierMaySponsor!=="516 randomized and treated outside Japan"||
    cohorts.primaryAugustNEJM!=="517 randomized, arms 258 aficamten and 259 placebo"||
    cohorts.laterAugustSponsor!=="517 randomized and treated outside Japan"||
    cohorts.OctoberSecondaryAppraisal!=="517 randomized but 516 treated"||
    cohorts.conflictIsOnlyAProvenanceAndPopulationDefinitionQuestion!==true||
    cohorts.whetherExactlyOneParticipantWasNotTreated!==null||
    cohorts.firstDoseListingAuthenticallyRead!==false||
    cohorts.definitivePopulationReconciliation!==false||
    cohorts.scientificConclusion!=="NOT_VERIFIED_OR_RESOLVED"||
    supplement.protocolAdvertisedFilename!=="nejmoa2603021_protocol.pdf"||
    supplement.appendixAdvertisedFilename!=="nejmoa2603021_appendix.pdf"||
    supplement.exactOriginalSupplementaryPDFBytesRead!==false||
    supplement.originalControlledSignedSAPVerified!==false||
    supplement.attemptedDirectJournalAccessBlocked!==true)return null;
 return {
  schema:"MAIN_R95_ACACIA_CY6033_CTIS_VALIDATED_PUBLIC_INDEX_NO_SIGNED_SAP" as const,
  exactNct:input.exactResearchNct,
  euTrialNumber:input.exactEuTrialNumber,
  sponsorProtocolCode:"CY 6033" as const,
  correctComparator:"PLACEBO" as const,
  wrongProtocolCodeExcluded:"CY 6032" as const,
  wrongProtocolComparison:"AFICAMTEN_VS_METOPROLOL_OBSTRUCTIVE_HCM_NOT_ACACIA" as const,
  CTISPublicDocumentEntries:133 as const,
  ctisAmendment4ProtocolEntries:2 as const,
  ctisAmendment3SynopsisEntries:1 as const,
  plannedInCTIS:435 as const,
  plannedEUMemberStates:175 as const,
  plannedRestOfWorld:260 as const,
  ctisSubstantialModification3Submitted:"2024-12-19" as const,
  ctisSubstantialModification3Decision:"2025-04-08" as const,
  ctisSubstantialModification4Submitted:"2025-07-08" as const,
  ctisSubstantialModification4Decision:"2025-09-08" as const,
  populationExplanationStatus:"CONFLICTED_516_517_SPONSOR_PUBLIC_COHORT_CLAIMS_NOT_RECONCILED" as const,
  sourcePublishedCohortClaims:[
   {source:"Earlier May sponsor",claim:cohorts.earlierMaySponsor},
   {source:"NEJM original",claim:cohorts.primaryAugustNEJM},
   {source:"Later August sponsor",claim:cohorts.laterAugustSponsor},
   {source:"October secondary article",claim:cohorts.OctoberSecondaryAppraisal}
  ],
  observedSponsorCohortClaimContradiction:true as const,
  originalParticipantFlowCertification:false as const,
  officialEUHistorySource:input.documentarySourceReceipts[0].url,
  publicDocumentIndexSource:input.documentarySourceReceipts[1].url,
  confusingOtherTrialProtocolSource:input.documentarySourceReceipts[2].url,
  laterSponsorCohortSource:input.documentarySourceReceipts[3].url,
  publicDocumentRecords:ctis.amendedProtocolListing.map(x=>({
   document:x.docTitle,version:x.documentVersion,
   originalByteSourceObtained:false as const
  })),
  signedFinalSapVersionsVerified:0 as const,
  exactOriginalPdfBytesCaptured:0 as const,
  trialSafetyIndependentlySigned:false as const,
  qualifiedIndependentStatisticalReview:false as const,
  originalAcaciaGatesUnresolved:4 as const,
  originalLaunchGatesUnresolved:7 as const,
  calibratedFDAPredictionAccuracyVerified:false as const,
  FDAForecast:"ABSTAIN" as const,
  note:"The 133 CTIS index entries and EU regulatory submission history are public-record leads. They are not 133 authenticated original files, an approved final SAP, or evidence of pre-unblinding lock. The contrasting CY 6032 public PDF belongs to a different trial and is rejected."
 };
}
export const R95_EU_ACACIA_PROTOCOL_IDENTITY=buildR95EuProtocolIdentityGates();
