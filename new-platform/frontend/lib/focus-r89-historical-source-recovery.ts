/** MAIN R89 — source recovery for 17 exact FOCUS NCTs lacking public documents
 * in the dated R86 current-registry snapshot. This classifies existing original
 * journal leads and historical-registry lookup tasks; NO clinical conclusions.
 */
import {R88_SOURCE_CHRONOLOGY} from "./focus-r88-source-chronology-triage";
import {FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE} from "./focus-r71-pivotal-evidence-intake";
import {FOCUS_R81_SOURCE_READINESS} from "./focus-r81-all-focus-source-readiness";

type Chronology=NonNullable<typeof R88_SOURCE_CHRONOLOGY>;
type Journal=NonNullable<typeof FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE>;
type Source=NonNullable<typeof FOCUS_R81_SOURCE_READINESS>;
const FIVE=[
 "NCT05126758","NCT05662241","NCT06081894","NCT06153693","NCT06343779"
] as const;

export const R89_RECOVERY_NOTICE=
 "Missing current registry protocol/SAP PDF listings do not imply missing original documents, absent clinical results, trial failure, or an FDA decision. Published journal leads and official historical registry versions require dated original-source verification, locked SAP chronology and independent review.";

export function buildR89HistoricalSourceRecovery(
 timeline:Chronology|null=R88_SOURCE_CHRONOLOGY,
 journal:Journal|null=FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE,
 source:Source|null=FOCUS_R81_SOURCE_READINESS
){
 if(!timeline||!journal||!source||
    timeline.trialCount!==29||timeline.applicationCycles!==23||
    timeline.rows.length!==29||timeline.trialsWithoutListedPdf!==17||
    timeline.listedPdfFiles!==23||timeline.authenticatedProspectiveSAPs!==0||
    timeline.independentSignedMedicalReviews!==0||
    timeline.independentlyValidatedFDAForecasts!==0||
    journal.focusNcts!==29||journal.applicationCycles!==23||
    journal.candidateMainResultPublications!==5||
    journal.fiveRecords.length!==5||
    journal.independentlyValidatedSignedSAPVersions!==0||
    journal.qualifiedClinicalScienceReviewSignoffs!==0||
    journal.scientificallyValidatedFutureFDAForecasts!==0||
    journal.officialFutureFDAOutcome!=="ABSTAIN"||
    source.exactTrials!==29||source.provisionalCycles!==23||
    source.rows.length!==29||
    source.independentScientificSignoffs!==0||source.validFutureFDAApplicationForecasts!==0||
    source.originalSignedProspectiveSAPsVerified!==0||
    source.FDAOutcome!=="ABSTAIN")return null;
 const bySource=new Map(source.rows.map(r=>[r.nct,r]));
 const papers=new Map(journal.fiveRecords.map(r=>[r.nct,r]));
 if(bySource.size!==29||papers.size!==5||
    FIVE.some(nct=>!papers.has(nct)))return null;
 const rows:Array<{
  nct:string;ticker:string;cycleIds:string[];reportedPhase:string;
  archivedPrimaryCompletionDate:string;exactStudyUrl:string;
  currentRegistryProtocolSapFiles:0;
  archiveResearchLane:string;researchPilot:string|null;
  originalIndexedPivotalPublication:{
    title:string;pmid:string;doi:string;articleUrl:string;
    journalUrl:string;sourceAccess:string;supplementUrl:string|null;
    authorReportedEffect:string;
    originalSignedSapChronologyIndependentlyVerified:false;
    qualifiedReviewerSigned:false
  }|null;
  existingCurrentRegistryPrimaryTable:boolean;
  existingCurrentRegistrySafetyArms:boolean;
  historicalVersionsInspectedInThisNewR89Run:0;
  historicalSourceRecordsIndependentlyAuthenticated:0;
  nextDocumentTasks:string[];
  independentQualifiedScienceReview:false;
  prospectivelyAuthenticatedSignedSAP:false;
  validatedFDAOutcome:"ABSTAIN"
 }> = [];
 const seen=new Set<string>();
 for(const trial of timeline.rows){
  const src=bySource.get(trial.nct);
  if(!src||seen.has(trial.nct)||src.ticker!==trial.ticker||
     trial.qualifiedClinicalReviewerSignoff!==false||
     trial.originallySignedPlanVerified!==false||
     trial.actualBlindBreakDateIndependentlyVerified!==false||
     trial.clinicalGrade!==null||trial.FDAForecast!=="ABSTAIN"||
     src.officialFDAOutcome!=="ABSTAIN"||
     JSON.stringify(src.cycleIds)!==JSON.stringify(trial.cycleIds))return null;
  seen.add(trial.nct);
  if(trial.sourcePdfFiles.length!==0)continue;
  const published=papers.get(trial.nct);
  if(Boolean(published)!==src.indexedOriginalPivotalPublication)return null;
  if(published && (published.ticker!==trial.ticker||
       published.qualifiedReviewerSignoffs!==0||
       published.originalSignedSapChronologyVerified!==false||
       published.futureFDAOutcome!=="ABSTAIN"||
       published.scienceGrade!==null))return null;
  const sourceLane=published?
   "ORIGINAL_PIVOTAL_JOURNAL_LEAD_PLUS_MISSING_AUTHENTICATED_SAP":
   "HISTORICAL_REGISTRY_SPONSOR_JOURNAL_SOURCE_DISCOVERY_NEEDED";
  rows.push({
    nct:trial.nct,ticker:trial.ticker,cycleIds:[...trial.cycleIds],
    reportedPhase:trial.reportedPhase,
    archivedPrimaryCompletionDate:trial.archivedPrimaryCompletionDate,
    exactStudyUrl:trial.registryStudyUrl,
    currentRegistryProtocolSapFiles:0 as const,
    archiveResearchLane:sourceLane,
    researchPilot:trial.originalPilot,
    originalIndexedPivotalPublication:published?{
      title:published.trial,
      pmid:published.pmid,
      doi:published.doi,
      articleUrl:published.articleUrl,
      journalUrl:published.journalUrl,
      sourceAccess:published.sourcePublicationEvidenceLevel,
      supplementUrl:published.supplementUrl,
      authorReportedEffect:published.reportedEffect,
      originalSignedSapChronologyIndependentlyVerified:false as const,
      qualifiedReviewerSigned:false as const
    }:null,
    existingCurrentRegistryPrimaryTable:src.currentRegistryPrimaryTable,
    existingCurrentRegistrySafetyArms:src.currentRegistrySafetyArms,
    historicalVersionsInspectedInThisNewR89Run:0 as const,
    historicalSourceRecordsIndependentlyAuthenticated:0 as const,
    nextDocumentTasks:published?[
      "Capture actual original publisher protocol/SAP supplement versions where publicly accessible",
      "Identify exact dated approvals and change-control for each version",
      "Obtain original database-lock/unblinding audit before certifying prospectiveness",
      "Independently reconcile journal endpoints, efficacy populations and safety windows"
    ]:[
      "Inspect official ClinicalTrials.gov historical version index and dated changes",
      "Seek historical protocol/SAP, sponsor or journal originals, CSR and regulatory records",
      "Obtain approval/lock/unblinding provenance and verify original file bytes",
      "Independent phase-specific statistical and safety review"
    ],
    independentQualifiedScienceReview:false as const,
    prospectivelyAuthenticatedSignedSAP:false as const,
    validatedFDAOutcome:"ABSTAIN" as const
  });
 }
 if(seen.size!==29||rows.length!==17||
    rows.filter(r=>r.originalIndexedPivotalPublication!==null).length!==5||
    rows.filter(r=>r.originalIndexedPivotalPublication===null).length!==12||
    FIVE.some(nct=>!rows.some(r=>r.nct===nct&&r.originalIndexedPivotalPublication!==null)))
    return null;
 const priority=(r:typeof rows[number])=>
   r.researchPilot?0:r.originalIndexedPivotalPublication?1:2;
 rows.sort((a,b)=>priority(a)-priority(b)||
   a.ticker.localeCompare(b.ticker)||a.nct.localeCompare(b.nct));
 return {
  schema:"MAIN_R89_17_NCT_HISTORICAL_SOURCE_DISCOVERY_NOT_VERIFIED_SAP" as const,
  sourceSnapshotDate:"2026-11-10" as const,
  notice:R89_RECOVERY_NOTICE,
  exactFocusTrialCount:29 as const,
  provisionalApplicationCycles:23 as const,
  missingPublicProtocolSapListingNcts:17 as const,
  originalPivotalPublisherLeadsInFiveStudyIndex:5 as const,
  unindexedPivotalPublicationInFiveStudyIndex:12 as const,
  independentlyAuthenticatedSignedProspectiveSAPs:0 as const,
  independentQualifiedScienceReviews:0 as const,
  validatedFutureFDAForecasts:0 as const,
  readOnly:true as const,
  rows
 };
}
export const R89_HISTORICAL_SOURCE_RECOVERY=buildR89HistoricalSourceRecovery();
