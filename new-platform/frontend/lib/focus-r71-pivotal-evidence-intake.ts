/** MAIN R71 five exact NCT original published main-result source intake.
 * Source-reported effect/p-values and a published supplement listing are NOT
 * independently verified statistical plans, completed science, a pass/fail
 * clinical trial, calibrated probability or FDA/regulator outcome.
 */
import data from "../data/focus-r71-five-main-publication-source-review.json";
import {FOCUS_R70_PUBLICATION_TRIAGE} from "./focus-r70-publication-abstract-triage";
import {FOCUS_R70_ARTICLE_SOURCE} from "./focus-r70-pubmed-article-source";
import {FOCUS_R68_EVIDENCE_RECOVERY} from "./focus-r68-evidence-recovery";
type Case=typeof data.cases[number];
const EXPECTED:Readonly<Record<string,{pmid:string;doi:string}>>={
 NCT05126758:{pmid:"42526472",doi:"10.1016/S0140-6736(26)01385-1"},
 NCT05662241:{pmid:"42233621",doi:"10.1056/NEJMoa2601337"},
 NCT06081894:{pmid:"42663312",doi:"10.1056/NEJMoa2603021"},
 NCT06153693:{pmid:"40587141",doi:"10.1001/jama.2025.9413"},
 NCT06343779:{pmid:"42849489",doi:"10.1016/S0140-6736(26)01296-1"},
};
const ACCESS=[
 "PUBMED_PRIMARY_ABSTRACT_REVIEWED",
 "PUBLISHER_MAIN_REPORT_ABSTRACT_AND_SUPPLEMENT_LINKS_LISTED",
 "OPEN_PMC_FULL_ARTICLE_AND_JAMA_SUPPLEMENT_1_EXTRACTED_TEXT_REVIEWED",
 "PUBLISHER_INDEXED_OPEN_ACCESS_ABSTRACT_TEXT_FULL_MANUSCRIPT_NOT_INDEPENDENTLY_READ"
] as const;
const DOMAIN=[
 {key:"PRIMARY_ENDPOINT",label:"Exact original primary endpoint",needed:"Reconcile stated primary endpoint definition, estimand, units, population and timepoint against protocol and CSR"},
 {key:"ESTIMAND_ANALYSIS_POPULATION",label:"Estimand and analysis population",needed:"Verify exact ITT, mITT or paired-attack population, intercurrent-event treatment and exclusions"},
 {key:"STATISTICAL_MODEL",label:"Statistical model and effect",needed:"Recreate the specified model, uncertainty intervals, effect-size scale and all source comparisons"},
 {key:"MULTIPLICITY_CONTROL",label:"Prespecified multiplicity and gates",needed:"Read locked statistical testing graph, all primary and key secondary hypotheses, alpha and gatekeeping"},
 {key:"MISSING_DATA_INTERCURRENT_EVENTS",label:"Missingness and intercurrent events",needed:"Verify MAR/MNAR assumptions, treatment-policy/retrieved dropout estimand and reasons for missingness"},
 {key:"SENSITIVITY_ANALYSIS",label:"Sensitivity and robustness",needed:"Check the prospectively specified alternative models and any differences from reported results"},
 {key:"ADVERSE_EVENTS_SAFETY",label:"Exposure-adjusted safety",needed:"Reconcile treatment-arm denominators, SAE, relatedness, withdrawal, and clinically material adverse events"},
 {key:"PROTOCOL_SAP_VERSION_CHANGES",label:"Original protocol/SAP chronology",needed:"Establish every original signed version, amendment, date and database-lock/unblinding order"}
] as const;
export function buildR71PivotalEvidenceIntake(input:unknown=data){
 const source=FOCUS_R70_PUBLICATION_TRIAGE,metadata=FOCUS_R70_ARTICLE_SOURCE;
 const recovery=FOCUS_R68_EVIDENCE_RECOVERY;
 if(!source||!metadata||!recovery||
    source.abstractPrimaryReportCandidates!==5||
    source.uniqueTrialsWithPrimaryReportCandidates!==5||
    source.paperCount!==11||source.signedScientificReviews!==0||
    source.independentlyValidatedFDAForecasts!==0||
    source.officialFutureFDAOutcome!=="ABSTAIN"||
    metadata.originalPubmedRecordsRetrieved!==11||
    metadata.independentlyAdjudicatedPivotalPrimaryPublications!==0||
    metadata.validatedFDAForecasts!==0||metadata.futureFDAOutcome!=="ABSTAIN"||
    recovery.uniqueTrials!==29||recovery.provisionalApplicationCycles!==23||
    recovery.validatedFDAForecasts!==0||recovery.allFutureFdaOutcomes!=="ABSTAIN"||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const raw=input as typeof data;
 if(Object.keys(raw).sort().join("|")!==[
  "cases","independentQualifiedScienceReviews","officialFDAForecast",
  "originalR70PubmedResearchRun","originalR70PubmedSha256",
  "originalSignedPreunblindingStatisticalPlansVerified","reviewDate",
  "schema","validatedFutureFdaApplicationForecasts","verificationType"].join("|")||
    raw.schema!=="MAIN_R71_FIVE_PIVOTAL_ABSTRACT_RESULT_AND_FULLTEXT_ACCESS_REVIEW_ONLY"||
    raw.reviewDate!=="2026-11-09"||
    raw.originalR70PubmedResearchRun!==42729546458||
    raw.originalR70PubmedSha256!=="03434b975e511b2d603227bab3e25768dbcc3a0e7b412d479d9afbd100cd2577"||
    raw.verificationType!=="PUBLISHED_RESULTS_OR_EXCERPTS_WITH_EXPLICIT_UNREVIEWED_ORIGINAL_PROSPECTIVE_SAP"||
    raw.originalSignedPreunblindingStatisticalPlansVerified!==0||
    raw.independentQualifiedScienceReviews!==0||
    raw.validatedFutureFdaApplicationForecasts!==0||
    raw.officialFDAForecast!=="ABSTAIN"||
    !Array.isArray(raw.cases)||raw.cases.length!==5)return null;
 const papers=new Map(source.papers.map(p=>[p.pmid,p]));
 const fromRecovery=new Map(recovery.rows.map(r=>[r.nct,r]));
 const byNct=new Map(metadata.studies.map(s=>[s.nct,s.articles]));
 const seen=new Set<string>();
 const records=[];
 for(const c of raw.cases){
  const match=EXPECTED[c.nct];
  const paper=papers.get(c.pmid);
  const coverage=fromRecovery.get(c.nct);
  const pubmed=byNct.get(c.nct)?.find(x=>x.pmid===c.pmid);
  if(!match||seen.has(c.nct)||c.pmid!==match.pmid||c.doi!==match.doi||
     !paper||paper.nct!==c.nct||paper.trialTicker!==c.ticker||
     paper.role!=="PRIMARY_PHASE3_ABSTRACT"||
     paper.qualifiedReviewerSigned!==false||
     !coverage||coverage.sourcePrimaryTableAvailable!==false||
     coverage.scientificAssessmentLevel!=="UNASSESSED_SOURCE_ONLY"||
     !pubmed||pubmed.doi!==match.doi||
     pubmed.scientificGrade!==null||pubmed.qualifiedReviewerSigned!==false||
     c.fullOriginalPaperIndependentlyRead!==false||
     !/^202[0-6]-\d{2}-\d{2}$/.test(c.published)||
     c.published>raw.reviewDate||
     typeof c.trial!=="string"||c.trial.length>70||
     !ACCESS.includes(c.sourceAccess as typeof ACCESS[number])||
     !/^https:\/\/(pubmed\.ncbi\.nlm\.nih\.gov|pmc\.ncbi\.nlm\.nih\.gov)\//.test(c.articleUrl)||
     !/^https:\/\/(www\.nejm\.org|jamanetwork\.com|doi\.org|www\.sciencedirect\.com)\//.test(c.journalUrl)||
     !(c.supplementUrl===null||/^https:\/\/(www\.nejm\.org|jamanetwork\.com)\//.test(c.supplementUrl))||
     typeof c.supplementStatus!=="string"||
     !Array.isArray(c.specificReviewNeeds)||
     c.specificReviewNeeds.length<3||c.specificReviewNeeds.length>5||
     c.specificReviewNeeds.some(s=>typeof s!=="string"||s.length<30||s.length>200)||
     [c.primaryEndpoint,c.reportedEffect,c.analysisPopulation,c.safetyObservation]
      .some(s=>typeof s!=="string"||s.length<35||s.length>500)
  )return null;
  seen.add(c.nct);
  records.push({
    ...c,
    originalPublicationTitle:pubmed.title,
    sourcePublicationEvidenceLevel:c.sourceAccess,
    originalPublicationInResearchArchive:source.sourceR69ArchiveUrl,
    sourceMayPostdateBlindPredictionOrigin:true,
    completeOriginalArticleAndSupplementsScientificallyAdjudicated:false as const,
    originalSignedSapChronologyVerified:false as const,
    safetyRiskIndependentlyAssessed:false as const,
    scienceGrade:null,
    qualifiedReviewerSignoffs:0,
    futureFDAOutcome:"ABSTAIN" as const,
    historicalValidationAccuracy:null,
    domains:DOMAIN.map(d=>({
      ...d,
      status:"SOURCE_LEADS_PENDING_SCIENTIFIC_ADJUDICATION" as const,
      sourceReportedEvidenceAvailable:d.key==="PRIMARY_ENDPOINT",
      scientificGrade:null,reviewerSigned:false
    }))
  });
 }
 if(seen.size!==5||Object.keys(EXPECTED).some(nct=>!seen.has(nct))||
    records.filter(c=>c.supplementUrl!==null).length!==3||
    records.filter(c=>c.sourceAccess==="OPEN_PMC_FULL_ARTICLE_AND_JAMA_SUPPLEMENT_1_EXTRACTED_TEXT_REVIEWED").length!==1||
    records.filter(c=>c.sourceAccess==="PUBLISHER_MAIN_REPORT_ABSTRACT_AND_SUPPLEMENT_LINKS_LISTED").length!==2||
    records.some(c=>c.domains.length!==8))return null;
 return {
  schema:"MAIN_R71_FIVE_SOURCE_LINKED_MAIN_REPORT_SCIENCE_REVIEW_INTAKE" as const,
  focusNcts:29,applicationCycles:23,
  candidateMainResultPublications:5,sourceReviewDomainsPerTrial:8,
  sourceResearchPositionsAwaitingAdjudication:40,
  fiveRecords:records,
  casesWithOriginalPublishedJournalProtocolOrAppendixListings:3,
  studiesWithOpenPMCFullArticleAndSupplementExcerpts:1,
  independentlyValidatedSignedSAPVersions:0,
  qualifiedClinicalScienceReviewSignoffs:0,
  scientificallyValidatedFutureFDAForecasts:0,
  historicalAccuracy:null,officialFutureFDAOutcome:"ABSTAIN" as const,
  sourceSummaryCannotBeUsedAsAClinicalGrade:true,
  noHistoricalOutcomeLookupsOrProductionWrites:true
 };
}
export const FOCUS_R71_PIVOTAL_EVIDENCE_INTAKE=buildR71PivotalEvidenceIntake();
