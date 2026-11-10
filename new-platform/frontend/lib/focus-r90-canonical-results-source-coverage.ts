/** MAIN R90 — restore existing canonical FOCUS results-source leads into
 * the 17-case original research queue. Nine URLs pre-existed in the locked
 * 29-trial baseline. A sponsor result or SEC exhibit is NEVER a signed SAP,
 * independent efficacy/safety adjudication, or calibrated FDA forecast.
 */
import raw from "../data/focus-r90-nine-existing-result-page-readbacks-20261110.json";
import {R89_HISTORICAL_SOURCE_RECOVERY} from "./focus-r89-historical-source-recovery";
import {R89_NEW_PUBLIC_SOURCE_LEADS} from "./focus-r89-new-public-source-leads";

const EXPECTED:Readonly<Record<string,{ticker:string;url:string;date:string;identity:string}>>={
 NCT05059223:{ticker:"AXSM",url:"https://www.sec.gov/Archives/edgar/data/1579428/000095017024035655/axsm-ex99_1.htm",date:"2024-03-25",identity:"TRIAL_NAME_REGISTRY_CROSSWALK_NOT_EXPLICIT_NCT_ON_REPORT"},
 NCT05113745:{ticker:"AXSM",url:"https://www.sec.gov/Archives/edgar/data/1579428/000095017024130755/axsm-ex99_1.htm",date:"2024-11-26",identity:"TRIAL_NAME_REGISTRY_CROSSWALK_NOT_EXPLICIT_NCT_ON_REPORT"},
 NCT05244304:{ticker:"BLTE",url:"https://investors.belitebio.com/news-releases/news-release-details/new-hope-people-living-disease-once-deemed-untreatable-belite",date:"2025-12-01",identity:"TRIAL_NAME_REGISTRY_CROSSWALK_NOT_EXPLICIT_NCT_ON_REPORT"},
 NCT06445023:{ticker:"CLDX",url:"https://celldex.gcs-web.com/news-releases/news-release-details/celldex-announces-positive-results-phase-3-embarq-csu1-and",date:"2026-09-22",identity:"REPORT_DIRECTLY_NAMES_EXACT_NCT"},
 NCT06455202:{ticker:"CLDX",url:"https://celldex.gcs-web.com/news-releases/news-release-details/celldex-announces-positive-results-phase-3-embarq-csu1-and",date:"2026-09-22",identity:"REPORT_DIRECTLY_NAMES_EXACT_NCT"},
 NCT05208047:{ticker:"COGT",url:"https://investors.cogentbio.com/news-releases/news-release-details/cogent-biosciences-reports-positive-results-bezuclastinib-peak",date:"2025-11-10",identity:"TRIAL_NAME_REGISTRY_CROSSWALK_NOT_EXPLICIT_NCT_ON_REPORT"},
 NCT04871282:{ticker:"IMNM",url:"https://investors.immunome.com/immunome-announces-detailed-phase-3-ringside-data-for-varegacestat-in-adults-with-progressing-desmoid-tumors-at-the-2026-asco-annual-meeting/",date:"2026-05-30",identity:"REPORT_DIRECTLY_NAMES_EXACT_NCT"},
 NCT06669754:{ticker:"PHVS",url:"https://www.sec.gov/Archives/edgar/data/1830487/000119312526384339/phvs-ex99_1.htm",date:"2026-09-08",identity:"REPORT_DIRECTLY_NAMES_EXACT_NCT"},
 NCT06087276:{ticker:"PRAX",url:"https://ir.praxismedicines.com/news-releases/news-release-details/praxis-precision-medicines-announces-positive-topline-results-1",date:"2025-10-16",identity:"REPORT_DIRECTLY_NAMES_EXACT_NCT"}
};
type SourceRow={
 nct:string;ticker:string;trial:string;reportType:string;publicDate:string;
 url:string;title:string;note:string;verification:string;
 exactRegistryUrl:string;noSAP:true;noScienceReview:true;FDAForecast:"ABSTAIN"
};
const DIRECT="REPORT_DIRECTLY_NAMES_EXACT_NCT";
const CROSS="TRIAL_NAME_REGISTRY_CROSSWALK_NOT_EXPLICIT_NCT_ON_REPORT";
export function buildR90CanonicalResultsSourceCoverage(input:typeof raw=raw){
 const first=R89_HISTORICAL_SOURCE_RECOVERY,three=R89_NEW_PUBLIC_SOURCE_LEADS;
 if(!first||!three||first.rows.length!==17||three.rows.length!==3||
    first.originalPivotalPublisherLeadsInFiveStudyIndex!==5||
    first.unindexedPivotalPublicationInFiveStudyIndex!==12||
    first.independentlyAuthenticatedSignedProspectiveSAPs!==0||
    first.independentQualifiedScienceReviews!==0||
    first.validatedFutureFDAForecasts!==0||
    three.independentQualifiedScientificReviews!==0||
    three.independentlyAuthenticatedProspectivelySignedSAPs!==0||
    three.validatedFutureFDAPredictions!==0||
    input.schema!=="MAIN_R90_NINE_PREEXISTING_CANONICAL_FOCUS_RESULT_URLS_PUBLIC_SOURCE_READBACK_ONLY"||
    input.reviewDateUtc!=="2026-11-10"||
    input.canonicalFocusDataPath!=="new-platform/backend/app/data/focus_snapshot.json"||
    input.records.length!==9||input.exactPreviouslyUnindexedNcts!==9||
    input.uniqueUnderlyingPublicResultPages!==8||
    input.reportsThatExplicitlyPrintNct!==5||
    input.reportsRequiringRegistryTrialNameCrosswalk!==4||
    input.peerReviewedFullManuscriptsNewlyAuthenticated!==0||
    input.originalProspectiveSapSignaturesAuthenticated!==0||
    input.qualifiedIndependentScientificReviews!==0||
    input.validatedFDAForecasts!==0||input.FDAForecast!=="ABSTAIN")return null;
 const byMissing=new Map(first.rows.map(r=>[r.nct,r]));
 const extra=new Set(three.rows.map(r=>r.nct));
 if(byMissing.size!==17||extra.size!==3)return null;
 const nine=new Set(first.rows.filter(r=>!r.originalIndexedPivotalPublication&&
    !extra.has(r.nct)).map(r=>r.nct));
 if(nine.size!==9||Object.keys(EXPECTED).some(n=>!nine.has(n)))return null;
 const seen=new Set<string>();
 const rows:SourceRow[]=[];
 for(const r of input.records){
  const x=EXPECTED[r.nct],base=byMissing.get(r.nct);
  if(!x||!base||!nine.has(r.nct)||seen.has(r.nct)||
     r.ticker!==x.ticker||base.ticker!==x.ticker||
     r.url!==x.url||r.publicDate!==x.date||
     r.idEvidence!==x.identity||
     r.originalClinicalTrialRegistryUrl!=="https://clinicaltrials.gov/study/"+r.nct||
     !r.trial||r.trial.length>80||
     !r.title||r.title.length>250||
     !r.note||r.note.length<35||r.note.length>650||
     !["SEC_FILED_ISSUER_RESULT_DISCLOSURE","ORIGINAL_SPONSOR_RESULTS_NEWS_RELEASE",
       "ORIGINAL_SPONSOR_ASCO_DATA_NEWS_RELEASE"].includes(r.reportType)||
     r.originalResultPageVisitedAndAvailable!==true||
     r.authenticatedOriginalSignedSAP!==false||
     r.qualifiedIndependentClinicalAssessment!==false||
     r.FDAOutcome!=="ABSTAIN"||
     base.originalIndexedPivotalPublication!==null)return null;
  seen.add(r.nct);
  rows.push({
   nct:r.nct,ticker:r.ticker,trial:r.trial,reportType:r.reportType,
   publicDate:r.publicDate,url:r.url,title:r.title,note:r.note,
   verification:r.idEvidence,exactRegistryUrl:r.originalClinicalTrialRegistryUrl,
   noSAP:true,noScienceReview:true,FDAForecast:"ABSTAIN"
  });
 }
 if(seen.size!==9||[...nine].some(nct=>!seen.has(nct))||
   new Set(rows.map(r=>r.url)).size!==8||
   rows.filter(r=>r.verification===DIRECT).length!==5||
   rows.filter(r=>r.verification===CROSS).length!==4)return null;
 rows.sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R90_ALL_17_RESEARCH_RESULT_LINKS_NOT_SIGNED_SAP" as const,
  datedReadback:"2026-11-10" as const,
  exactFocusNcts:29 as const,
  provisionalCycles:23 as const,
  trialsWithoutCurrentRegistryProtocolSAP:17 as const,
  existingPriorFivePivotalPublicationResearchLeads:5 as const,
  additionalThreeConferenceIssuerResearchLeads:3 as const,
  alreadyHeldNineIssuerSecResultsLinksVerified:9 as const,
  sourceResultLeadCoverageForSeventeen:17 as const,
  distinctPreviouslyUnindexedSourcePages:8 as const,
  directExactNctInNineReports:5 as const,
  nameAndRegistryCrosswalkInNineReports:4 as const,
  signedOriginalSAPsAuthenticated:0 as const,
  independentClinicalReviewSignoffs:0 as const,
  calibratedFDAPredictions:0 as const,
  notice:"All 17 have at least a publisher, sponsor, or SEC reported-results link in retained source research. None of this verifies final signed prospective SAPs, source custody, original analysis populations, adverse events, FDA review or FDA outcome.",
  rows
 };
}
export const R90_CANONICAL_RESULTS_RECOVERY=buildR90CanonicalResultsSourceCoverage();
