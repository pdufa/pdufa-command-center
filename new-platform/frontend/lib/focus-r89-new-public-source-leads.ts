/** MAIN R89 additional original publisher and issuer **research** source leads,
 * distinct from five previously indexed R71 pivotal publications.
 * Sponsor-reported effects and a conference abstract are NOT independent
 * efficacy analysis, authenticated signed SAPs, or calibrated FDA outcomes.
 */
import raw from "../data/focus-r89-new-public-original-source-leads-20261110.json";
import {R89_HISTORICAL_SOURCE_RECOVERY} from "./focus-r89-historical-source-recovery";

const EXPECTED={
 NCT02500381:{
  ticker:"SRPT",type:"PUBLISHER_CONFERENCE_SUPPLEMENT_ABSTRACT_NOT_FULL_MANUSCRIPT",
  date:"2026-10",url:"https://www.sciencedirect.com/science/article/abs/pii/S0960896626004931"
 },
 NCT06411899:{
  ticker:"MLTX",type:"ISSUER_REPORT_WITH_NCT_MATCH_NO_SIGNED_SAP",
  date:"2026-08-10",url:"https://moonlaketx.gcs-web.com/news-releases/news-release-details/moonlake-announces-positive-topline-results-phase-3-izar-1-trial"
 },
 NCT06411379:{
  ticker:"MLTX",type:"ISSUER_REPORT_WITH_NCT_MATCH_NO_SIGNED_SAP",
  date:"2026-08-10",url:"https://moonlaketx.gcs-web.com/news-releases/news-release-details/moonlake-announces-positive-topline-results-phase-3-izar-1-trial"
 }
} as const;
export function buildR89NewPublicResearchLeads(input:typeof raw=raw){
 const base=R89_HISTORICAL_SOURCE_RECOVERY;
 if(!base||base.rows.length!==17||base.originalPivotalPublisherLeadsInFiveStudyIndex!==5||
    base.unindexedPivotalPublicationInFiveStudyIndex!==12||
    base.independentQualifiedScienceReviews!==0||
    base.validatedFutureFDAForecasts!==0||
    input.schema!=="MAIN_R89_THREE_NEW_PUBLIC_PUBLISHER_ISSUER_REPORT_LEADS_RESEARCH_ONLY"||
    input.researchObservedOn!=="2026-11-10"||
    input.sourceCases.length!==3||
    input.newExactTrialSourceLeads!==3||
    input.distinctUnderlyingOriginalSourcePages!==2||
    input.authenticatedOriginalSignedSAPs!==0||
    input.qualifiedIndependentScientificReviews!==0||
    input.validatedFDAOutcomeForecasts!==0||
    input.futureFDAOutcome!=="ABSTAIN")return null;

 const byNct=new Map(base.rows.map(r=>[r.nct,r]));
 const seen=new Set<string>();
 const rows:Array<{
  nct:string;ticker:string;trial:string;evidenceClass:string;sourceDate:string;
  sourceUrl:string;sourceTitle:string;sourceReportedObservation:string;
  preliminarySourceLevel:string;
  originalFullManuscriptIndependentlyReviewed:false;
  sourceOriginalBytesCaptured:false;
  prospectivelySignedSAPIndependentlyVerified:false;
  qualifiedClinicalScienceReviewSigned:false;
  clinicalGrade:null;FDAOutcome:"ABSTAIN"
 }> = [];
 for(const x of input.sourceCases){
  const id=x.nct as keyof typeof EXPECTED;
  const want=EXPECTED[id],baseRow=byNct.get(x.nct);
  if(!want||!baseRow||seen.has(x.nct)||
     baseRow.ticker!==want.ticker||x.ticker!==want.ticker||
     x.sourceType!==want.type||x.sourceDate!==want.date||
     x.sourceUrl!==want.url||
     baseRow.originalIndexedPivotalPublication!==null||
     typeof x.sourceReportedObservation!=="string"||
     x.sourceReportedObservation.length<80||x.sourceReportedObservation.length>800||
     !x.trial||x.trial.length>60||
     !x.reportTitle||x.reportTitle.length>230||
     !["PUBLISHER_ABSTRACT_TEXT_LEAD","SPONSOR_PUBLIC_RESEARCH_DISCLOSURE"].includes(
      x.sourceAuthenticityLevel)||
     x.documentBytesCaptured!==false||
     x.originalProspectiveSapAuthenticated!==false||
     x.independentScienceReviewed!==false||
     x.FDAForecast!=="ABSTAIN")return null;
  seen.add(x.nct);
  rows.push({
   nct:x.nct,ticker:x.ticker,trial:x.trial,
   evidenceClass:x.sourceType,sourceDate:x.sourceDate,
   sourceUrl:x.sourceUrl,sourceTitle:x.reportTitle,
   sourceReportedObservation:x.sourceReportedObservation,
   preliminarySourceLevel:x.sourceAuthenticityLevel,
   originalFullManuscriptIndependentlyReviewed:false as const,
   sourceOriginalBytesCaptured:false as const,
   prospectivelySignedSAPIndependentlyVerified:false as const,
   qualifiedClinicalScienceReviewSigned:false as const,
   clinicalGrade:null,
   FDAOutcome:"ABSTAIN" as const
  });
 }
 if(seen.size!==3||Object.keys(EXPECTED).some(n=>!seen.has(n))||
    new Set(rows.map(r=>r.sourceUrl)).size!==2)return null;
 rows.sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R89_NEW_EXTERNAL_PUBLIC_RESEARCH_LEADS_THREE_NOT_GRADED" as const,
  researchDate:"2026-11-10" as const,
  exactNctMatchedNewSourceLeads:3 as const,
  conferenceSupplementAbstractLeads:1 as const,
  sponsorPublicReportLeads:2 as const,
  originalFiveStudyPivotalIndexStill:5 as const,
  previouslyUnindexedResearchRowsStill:12 as const,
  ofThoseWithAdditionalPublicLeadNow:3 as const,
  remainingWithoutNewPublicLeadThisPass:9 as const,
  independentQualifiedScientificReviews:0 as const,
  independentlyAuthenticatedProspectivelySignedSAPs:0 as const,
  validatedFutureFDAPredictions:0 as const,
  rows
 };
}
export const R89_NEW_PUBLIC_SOURCE_LEADS=buildR89NewPublicResearchLeads();
