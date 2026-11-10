/** MAIN R70: explicitly provisional title/abstract-level PubMed paper-role triage.
 * This is a literature research annotation, NOT a full-paper review, a verified
 * prespecified Phase 3 endpoint, a qualified reviewer signature, a clinical
 * grade, a prospective prediction, or historical FDA accuracy calibration.
 */
import catalog from "../data/focus-r70-abstract-publication-triage.json";
import {FOCUS_R69_REGISTRY_PUBLICATION_LEADS} from "./focus-r69-original-publication-leads";
import {FOCUS_R68_EVIDENCE_RECOVERY} from "./focus-r68-evidence-recovery";

const R69_SHA="8b11d9f7e6f8896286944a454569b59cac9d63c5350fcb9665e6ff47e5519e77";
const roles={
 PRIMARY_PHASE3_ABSTRACT:"Primary Phase 3 results described in abstract",
 SAME_TRIAL_SECONDARY_ANALYSIS:"Additional analysis of the same trial",
 PROTOCOL_ONLY:"Protocol/design paper, no final primary result",
 PHASE2_COMPONENT_NOT_PHASE3:"Phase 2 component, not Phase 3 results",
 EARLIER_PHASE_OTHER_COHORT:"Earlier-phase cohort, not pivotal trial outcome",
 BACKGROUND_NOT_PIVOTAL:"Background/reference study, not pivotal trial outcome",
} as const;
export type R70PaperRole=keyof typeof roles;
type Raw={schema:string;basedOnR69Run:number;basedOnR69Sha256:string;
 verificationBasis:string;independentlyVerifiedOriginalSignedProtocolSAP:boolean;
 qualifiedReviewerSigned:boolean;externalFullTextStatisticalReviewComplete:boolean;
 fdaOutcomeForecast:string;rows:unknown[]};

const expectedRole:Readonly<Record<string,R70PaperRole>>={
 "40098309":"BACKGROUND_NOT_PIVOTAL",
 "34105177":"EARLIER_PHASE_OTHER_COHORT",
 "42848980":"PHASE2_COMPONENT_NOT_PHASE3",
 "42526472":"PRIMARY_PHASE3_ABSTRACT",
 "42233621":"PRIMARY_PHASE3_ABSTRACT",
 "41840328":"PROTOCOL_ONLY",
 "42667274":"SAME_TRIAL_SECONDARY_ANALYSIS",
 "42663312":"PRIMARY_PHASE3_ABSTRACT",
 "42663111":"SAME_TRIAL_SECONDARY_ANALYSIS",
 "40587141":"PRIMARY_PHASE3_ABSTRACT",
 "42849489":"PRIMARY_PHASE3_ABSTRACT",
};

export function buildR70PublicationAbstractTriage(input:unknown=catalog){
 const original=FOCUS_R69_REGISTRY_PUBLICATION_LEADS, recovery=FOCUS_R68_EVIDENCE_RECOVERY;
 if(!original||!recovery||original.candidateReferenceCount!==11||
    original.casesWithUnverifiedPublicationLeads!==7||
    original.retainedRegistryPrimaryMissingNcts!==17||
    original.exactNctPivotalOutcomeVerified!==0||
    original.paperTextIndependentReviews!==0||
    original.scientificReviewSignoffs!==0||
    original.fdaForecastsValidated!==0||
    original.futureFdaOutcome!=="ABSTAIN"||
    original.measuredForecastAccuracy!==null||
    original.originalResearchSha256!==R69_SHA||
    recovery.uniqueTrials!==29||recovery.provisionalApplicationCycles!==23||
    recovery.validatedFDAForecasts!==0||
    recovery.allFutureFdaOutcomes!=="ABSTAIN"||
    recovery.historicalPredictionAccuracy!==null||
    !input||typeof input!=="object"||Array.isArray(input))return null;
 const d=input as Raw;
 const columns=["basedOnR69Run","basedOnR69Sha256","externalFullTextStatisticalReviewComplete",
  "fdaOutcomeForecast","independentlyVerifiedOriginalSignedProtocolSAP",
  "qualifiedReviewerSigned","rows","schema","verificationBasis"];
 if(Object.keys(d).sort().join("|")!==columns.sort().join("|")||
    d.schema!=="MAIN_R70_PUBMED_ABSTRACT_ROLE_TRIAGE_NOT_CLINICAL_ADJUDICATION"||
    d.basedOnR69Run!==42727350931||d.basedOnR69Sha256!==R69_SHA||
    d.verificationBasis!=="PUBLIC_PUBMED_AND_JOURNAL_TITLE_ABSTRACT_METADATA"||
    d.independentlyVerifiedOriginalSignedProtocolSAP!==false||
    d.qualifiedReviewerSigned!==false||
    d.externalFullTextStatisticalReviewComplete!==false||
    d.fdaOutcomeForecast!=="ABSTAIN"||
    !Array.isArray(d.rows)||d.rows.length!==11)return null;

 const prior=new Map(original.cases.map(x=>[x.nct,x]));
 const linked=new Map(original.cases.flatMap(x=>
   x.sourceReferenceLeads.map(p=>[p.pmid,{nct:x.nct,pmid:p.pmid,pubmedUrl:p.pubmedUrl}] as const)));
 if(prior.size!==17||linked.size!==11)return null;
 const seen=new Set<string>();
 const papers=[];
 for(const row of d.rows){
  if(!Array.isArray(row)||row.length!==5||
     row.some(x=>typeof x!=="string")||
     row.some(x=>(x as string).length>260))return null;
  const [nct,pmid,role,title,reason]=row as string[];
  const fromOriginal=linked.get(pmid);
  if(!fromOriginal||fromOriginal.nct!==nct||seen.has(pmid)||
     !Object.prototype.hasOwnProperty.call(expectedRole,pmid)||
     expectedRole[pmid]!==role||!title||title.length<15||
     !reason||reason.length<28||!prior.has(nct))return null;
  seen.add(pmid);
  const roleKey=role as R70PaperRole;
  const source=prior.get(nct)!;
  if(source.sourcePrimaryTablePostedInRetainedRecord!==false||
     source.futureFDAOutcome!=="ABSTAIN"||
     source.independentlyVerifiedPivotalStudyOutcome!==null)return null;
  papers.push({
   nct,pmid,title,reason,role:roleKey,roleLabel:roles[roleKey],
   pubmedUrl:fromOriginal.pubmedUrl,
   trialTicker:source.ticker,
   applicationCycles:[...source.applicationCycles],
   evidenceBasis:"PUBMED_JOURNAL_TITLE_ABSTRACT_ONLY" as const,
   exactNctPublicationAssociationAtAbstractLevel:roleKey!=="BACKGROUND_NOT_PIVOTAL" &&
    roleKey!=="EARLIER_PHASE_OTHER_COHORT",
   potentialPivotalPrimaryResultFromAbstract:roleKey==="PRIMARY_PHASE3_ABSTRACT",
   studyPrimaryDataFullyValidated:false as const,
   articleFullTextMethodsIndependentlyAdjudicated:false as const,
   originalPreunblindingSAPVerified:false as const,
   qualifiedReviewerSigned:false as const,
   scientificGrade:null,
   officialFdaPrediction:"ABSTAIN" as const,
  });
 }
 if(seen.size!==11||[...linked.keys()].some(p=>!seen.has(p)))return null;
 const byRole={
  PRIMARY_PHASE3_ABSTRACT:papers.filter(x=>x.role==="PRIMARY_PHASE3_ABSTRACT").length,
  SAME_TRIAL_SECONDARY_ANALYSIS:papers.filter(x=>x.role==="SAME_TRIAL_SECONDARY_ANALYSIS").length,
  PROTOCOL_ONLY:papers.filter(x=>x.role==="PROTOCOL_ONLY").length,
  PHASE2_COMPONENT_NOT_PHASE3:papers.filter(x=>x.role==="PHASE2_COMPONENT_NOT_PHASE3").length,
  EARLIER_PHASE_OTHER_COHORT:papers.filter(x=>x.role==="EARLIER_PHASE_OTHER_COHORT").length,
  BACKGROUND_NOT_PIVOTAL:papers.filter(x=>x.role==="BACKGROUND_NOT_PIVOTAL").length,
 };
 if(JSON.stringify(byRole)!==JSON.stringify({
  PRIMARY_PHASE3_ABSTRACT:5,SAME_TRIAL_SECONDARY_ANALYSIS:2,
  PROTOCOL_ONLY:1,PHASE2_COMPONENT_NOT_PHASE3:1,
  EARLIER_PHASE_OTHER_COHORT:1,BACKGROUND_NOT_PIVOTAL:1
 }))return null;
 if(new Set(papers.filter(x=>x.potentialPivotalPrimaryResultFromAbstract).map(x=>x.nct)).size!==5)return null;
 const sorted=[...papers].sort((a,b)=>
  a.trialTicker.localeCompare(b.trialTicker)||a.nct.localeCompare(b.nct)||
  a.pmid.localeCompare(b.pmid));
 return {
  schema:"MAIN_R70_PUBLICATION_ABSTRACT_SOURCE_ROLE_NOT_SIGNED_SCIENCE" as const,
  sourceR69ArchiveUrl:original.sourceArchiveUrl,
  paperCount:11,exactNctReferences:7,
  abstractPrimaryReportCandidates:5,
  uniqueTrialsWithPrimaryReportCandidates:5,
  additionalSameTrialAnalyses:2,
  protocolPapers:1,
  phase2NotPhase3:1,
  earlierPhaseOtherCohort:1,
  backgroundNotPivotal:1,
  originalMissingPrimaryTrialCount:17,
  scienceScoresAssigned:0,
  signedScientificReviews:0,
  independentlyValidatedFDAForecasts:0,
  measuredForecastAccuracy:null,
  officialFutureFDAOutcome:"ABSTAIN" as const,
  papers:sorted,
  fullOriginalScientificStatisticalReviewCompleted:false,
  trialResultNotScoredOrCountedMultipleTimes:true,
  noProductionWritesOrModelTraining:true,
 };
}
export const FOCUS_R70_PUBLICATION_TRIAGE=buildR70PublicationAbstractTriage();
