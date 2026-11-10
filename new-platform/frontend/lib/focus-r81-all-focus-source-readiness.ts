/** MAIN R81: all 29 exact-NCT source-intake coverage, grouped by 23
 * provisional FDA application cycles. NOT clinical or approval ranking.
 * A journal source lead is not a signed SAP, blinded test, or FDA prediction.
 */
import {FOCUS_R68_EVIDENCE_RECOVERY} from "./focus-r68-evidence-recovery";
import {FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE} from "./focus-r71-pivotal-evidence-intake";
import {FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES} from "./focus-r79-launch-htn-sap-lock-evidence-gates";

type Recovery=NonNullable<typeof FOCUS_R68_EVIDENCE_RECOVERY>;
type Journals=NonNullable<typeof FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE>;
type Auth=NonNullable<typeof FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES>;
export function buildR81SourceReadiness(
 recovery:Recovery|null=FOCUS_R68_EVIDENCE_RECOVERY,
 journals:Journals|null=FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE,
 auth:Auth|null=FOCUS_R79_LAUNCH_HTN_SAP_LOCK_GATES
){
 if(!recovery||!journals||!auth||recovery.uniqueTrials!==29||
  recovery.provisionalApplicationCycles!==23||
  recovery.rows.length!==29||
  recovery.postedPrimaryTrials!==12||
  recovery.currentSafetyArmTrials!==12||
  recovery.trialsWithCurrentPdfPageLeads!==12||
  recovery.scientificDomainSourcePositions!==232||
  recovery.qualifiedReviewerSignoffs!==0||
  recovery.validatedFDAForecasts!==0||
  recovery.allFutureFdaOutcomes!=="ABSTAIN"||
  journals.focusNcts!==29||journals.applicationCycles!==23||
  journals.candidateMainResultPublications!==5||
  journals.fiveRecords.length!==5||
  journals.sourceResearchPositionsAwaitingAdjudication!==40||
  journals.independentlyValidatedSignedSAPVersions!==0||
  journals.qualifiedClinicalScienceReviewSignoffs!==0||
  journals.scientificallyValidatedFutureFDAForecasts!==0||
  journals.officialFutureFDAOutcome!=="ABSTAIN"||
  auth.nct!=="NCT06153693"||auth.cycleId!=="mlys-lorundrostat"||
  auth.sourceRequirements.length!==7||
  auth.requirementsIndependentlyVerified!==0||
  auth.originalSourceAttestationsVerified!==false||
  auth.qualifiedIndependentReviewersSigned!==0||
  auth.FDAOutcome!=="ABSTAIN")return null;

 // The R68 source is independently validated against the original R60/R64/R65/R67
 // rosters. Caller-supplied evidence snapshots cannot forge an NCT/ticker,
 // application-cycle, registry availability or scientific signoff identity.
 const canonical=FOCUS_R68_EVIDENCE_RECOVERY;
 if(!canonical||canonical.rows.length!==29)return null;
 const canonicalBy=new Map(canonical.rows.map(x=>[x.nct,x]));
 const pubs=new Map(journals.fiveRecords.map(x=>[x.nct,x]));
 if(pubs.size!==5)return null;
 const seen=new Set<string>();
 const rows=[];
 const cycles=new Map<string,{
  cycleId:string,tickers:Set<string>,ncts:string[],
  journalLeadNcts:string[],recordedPrimaryNcts:string[],
  currentMethodPageLeadNcts:string[]
 }>();
 let leadCount=0,withCurrentPrimary=0,withMethodPages=0;
 for(const row of recovery.rows){
  if(seen.has(row.nct)||!/^NCT\d{8}$/.test(row.nct)||
     !/^[A-Z0-9]{2,7}$/.test(row.ticker)||
     row.scientificAssessmentLevel!=="UNASSESSED_SOURCE_ONLY"||
     row.qualifiedReviewerSigned!==false||
     row.clinicalScienceScore!==null||
     row.officialFutureFdaOutcome!=="ABSTAIN"||
     row.historicalMeasuredAccuracy!==null||
     !Array.isArray(row.applicationCycles)||
     row.applicationCycles.length<1||row.applicationCycles.length>2||
     new Set(row.applicationCycles).size!==row.applicationCycles.length)return null;
  const truth=canonicalBy.get(row.nct);
  if(!truth||truth.ticker!==row.ticker||
     JSON.stringify(truth.applicationCycles)!==JSON.stringify(row.applicationCycles)||
     truth.sourcePrimaryTableAvailable!==row.sourcePrimaryTableAvailable||
     truth.sourceSafetyArmsAvailable!==row.sourceSafetyArmsAvailable||
     truth.sourcePdfPageLeadsAvailable!==row.sourcePdfPageLeadsAvailable)return null;
  seen.add(row.nct);
  const pub=pubs.get(row.nct);
  if(pub && (pub.ticker!==row.ticker||pub.scienceGrade!==null||
       pub.originalSignedSapChronologyVerified!==false||
       pub.qualifiedReviewerSignoffs!==0||
       pub.futureFDAOutcome!=="ABSTAIN"))return null;
  if(pub)leadCount++;
  if(row.sourcePrimaryTableAvailable)withCurrentPrimary++;
  if(row.sourcePdfPageLeadsAvailable)withMethodPages++;
  const stage=pub?
   (row.nct==="NCT06153693"?
      "ORIGINAL_JOURNAL_METHOD_PAGES_REVIEWED_NOT_ADJUDICATED":
      "PUBLISHED_PIVOTAL_REPORT_LEAD_NOT_ADJUDICATED"):
     "NOT_INDEXED_IN_R71_FIVE_PIVOTAL_REPORT_INTAKE";
  rows.push({
    nct:row.nct,ticker:row.ticker,
    cycleIds:[...row.applicationCycles],
    currentRegistryPrimaryTable:row.sourcePrimaryTableAvailable,
    currentRegistrySafetyArms:row.sourceSafetyArmsAvailable,
    retainedMethodPageLeads:row.sourcePdfPageLeadsAvailable,
    originalJournalIntakeStage:stage,
    indexedOriginalPivotalPublication:!!pub,
    publisherOrPubmedUrl:pub?.journalUrl??null,
    exactPublishedMainResultSourceSigned:false as const,
    originalProspectiveSAPAuthenticated:false as const,
    independentScienceReviewed:false as const,
    scientificGrade:null,
    validatedFDAApplicationPrediction:false as const,
    officialFDAOutcome:"ABSTAIN" as const
  });
  for(const cycleId of row.applicationCycles){
    if(!/^[a-z0-9]+(?:-[a-z0-9]+)+$/.test(cycleId))return null;
    let c=cycles.get(cycleId);
    if(!c){c={cycleId,tickers:new Set(),ncts:[],journalLeadNcts:[],
       recordedPrimaryNcts:[],currentMethodPageLeadNcts:[]};cycles.set(cycleId,c);}
    c.tickers.add(row.ticker);c.ncts.push(row.nct);
    if(pub)c.journalLeadNcts.push(row.nct);
    if(row.sourcePrimaryTableAvailable)c.recordedPrimaryNcts.push(row.nct);
    if(row.sourcePdfPageLeadsAvailable)c.currentMethodPageLeadNcts.push(row.nct);
  }
 }
 if(seen.size!==29||leadCount!==5||withCurrentPrimary!==12||
    withMethodPages!==12||cycles.size!==23||
    [...pubs.keys()].some(nct=>!seen.has(nct)))return null;
 const applicationGroups=[...cycles.values()].sort((a,b)=>a.cycleId.localeCompare(b.cycleId))
  .map(c=>({
    cycleId:c.cycleId,
    ticker:[...c.tickers].sort().join("/"),
    trialCount:c.ncts.length,
    ncts:[...c.ncts].sort(),
    originalPublishedMainReportLeads:c.journalLeadNcts.length,
    originalReportNcts:[...c.journalLeadNcts].sort(),
    currentRegistryPrimaryNcts:[...c.recordedPrimaryNcts].sort(),
    currentMethodPageLeadNcts:[...c.currentMethodPageLeadNcts].sort(),
    prospectivelyAuthenticatedSAPs:0 as const,
    independentlySignedScientificReviews:0 as const,
    validatedFDAApplicationForecasts:0 as const,
    FDAOutcome:"ABSTAIN" as const,
    clinicalGrade:null
  }));
 if(applicationGroups.reduce((n,x)=>n+x.trialCount,0)!==
    rows.reduce((n,x)=>n+x.cycleIds.length,0)||
    applicationGroups.some(x=>x.trialCount<1||x.ncts.length!==x.trialCount||
      x.originalPublishedMainReportLeads>x.trialCount))return null;
 return {
  schema:"MAIN_R81_FOCUS_29_TRIAL_23_CYCLE_RESEARCH_SOURCE_READINESS_NOT_GRADED" as const,
  exactTrials:29 as const,provisionalCycles:23 as const,
  registryCurrentPrimaryTrials:12 as const,
  registryCurrentSafetyArmTrials:12 as const,
  registryCurrentMethodPageLeadTrials:12 as const,
  R71PublicationLeads:5 as const,
  originalJAMAExtractedMethodCaseNcts:["NCT06153693"] as const,
  remainingNotIndexedInR71:24 as const,
  originalSignedProspectiveSAPsVerified:0 as const,
  independentScientificSignoffs:0 as const,
  fullScientificSourceReviewPositions:232 as const,
  completedScientificSourceReviews:0 as const,
  validFutureFDAApplicationForecasts:0 as const,
  accuracyCalibrated:false as const,
  FDAOutcome:"ABSTAIN" as const,
  noProductionOrModelTrainingWrites:true as const,
  rows,applicationGroups
 };
}
export const FOCUS_R81_SOURCE_READINESS=buildR81SourceReadiness();
