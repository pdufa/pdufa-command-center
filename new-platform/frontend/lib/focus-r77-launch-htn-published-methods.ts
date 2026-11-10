/** MAIN R77 — published JAMA statistical-method source map. NOT signed SAP proof. */
import raw from "../data/focus-r77-launch-htn-published-multiplicity-crosswalk.json";
import {FOCUS_R75_LAUNCH_HTN_CHRONOLOGY} from "./focus-r75-launch-htn-chronology";

const NODE_IDS=["H1","H2","H3","H4","H5","H6","H7"] as const;
const ENDPOINTS=[
 "Week-6 change from baseline in automated office systolic BP; randomized pooled lorundrostat 50 mg versus placebo",
 "Week-6 proportion with automated office systolic BP below 130 mm Hg; randomized 50 mg versus placebo",
 "Week-12 change from baseline in automated office systolic BP; randomized 50 mg with possible escalation to 100 mg versus placebo",
 "Week-6 change from baseline in automated office systolic BP among participants taking two antihypertensive medications; 50 mg versus placebo",
 "Week-6 change from baseline in automated office systolic BP among participants taking three or more antihypertensive medications; 50 mg versus placebo",
 "Week-6 change from baseline in automated office systolic BP by obesity status; 50 mg versus placebo",
 "Week-12 change from baseline in automated office systolic BP among participants escalated to 100 mg at week 6; within-participant analysis"
] as const;
const COMPARISONS=[
 "RANDOMIZED_50MG_VERSUS_PLACEBO","RANDOMIZED_50MG_VERSUS_PLACEBO",
 "RANDOMIZED_ESCALATION_STRATEGY_VERSUS_PLACEBO","RANDOMIZED_TWO_AHT_STRATUM",
 "RANDOMIZED_THREE_PLUS_AHT_STRATUM","RANDOMIZED_OBESITY_INTERACTION",
 "WITHIN_PARTICIPANT_NONRANDOMIZED_ESCALATED_SUBSET"
] as const;
const POSITIONS=[
 "ROOT","AFTER_H3","AFTER_H4_H5","FIRST_SPLIT_LEFT",
 "FIRST_SPLIT_RIGHT","FINAL_NODE","AFTER_H2_LEFT"
] as const;
const EDGES=[
 ["H1","H4","HALF"],["H1","H5","HALF"],["H4","H3","UNSPECIFIED"],
 ["H5","H3","UNSPECIFIED"],["H3","H2","UNSPECIFIED"],
 ["H2","H7","HALF"],["H2","H6","HALF"],["H7","H6","UNSPECIFIED"]
] as const;

export function buildR77LaunchHtnPublishedMethods(input:unknown=raw){
 const upstream=FOCUS_R75_LAUNCH_HTN_CHRONOLOGY;
 if(!upstream||upstream.nct!=="NCT06153693"||
    upstream.signedOriginalProspectiveStatisticalPlansIndependentlyAuthenticated!==0||
    upstream.futureFDAOutcome!=="ABSTAIN"||
    !input||Array.isArray(input)||typeof input!=="object")return null;
 const d=input as typeof raw;
 if(d.schema!=="MAIN_R77_LAUNCH_HTN_PUBLISHED_H1_H7_AND_MISSINGNESS_SOURCE_CROSSWALK_NOT_SAP_LOCKED"||
   d.asOf!=="2026-11-09"||d.nct!=="NCT06153693"||d.ticker!=="MLYS"||
   d.doi!=="10.1001/jama.2025.9413"||
   d.journalOriginalArticle!=="https://jamanetwork.com/journals/jama/fullarticle/2835763"||
   d.originalSupplementStableIndex!=="https://pmc.ncbi.nlm.nih.gov/articles/PMC12210145/"||
   d.originalSupplementFilename!=="jama-e259413-s001.pdf"||
   d.sourceType!=="PUBLISHED_JAMA_SUPPLEMENT_1_VIA_ORIGINAL_PUBLISHER_PDF_PAGES"||
   d.sourcePagesPhysicalOneBased.eFigure2!==6||
   d.sourcePagesPhysicalOneBased.eTable1!==11||
   d.sourcePagesPhysicalOneBased.imputationMethods!==12||
   d.sourcePagesPhysicalOneBased.eTable2!==13||
   d.sourcePagesPhysicalOneBased.eTable3!==15||
   d.sourcePagesPhysicalOneBased.eTable4!==17||
   d.sourceEfigure2DiagramReviewed!==true||
   d.publishedSourceHypotheses.length!==7||d.graphEdges.length!==8||
   d.alphaTransferDiagram.root!=="H1"||
   d.alphaTransferDiagram.numericAlphaNotEstablishedFromGraph!==true||
   d.alphaTransferDiagram.fullMultiplicityRecalculationPerformed!==false||
   JSON.stringify(d.alphaTransferDiagram.explicitHalfTransfers)!==
     JSON.stringify([["H1","H4"],["H1","H5"],["H2","H7"],["H2","H6"]])||
   d.reviewGates.length!==6)return null;
 for(let i=0;i<NODE_IDS.length;i++){
  const n=d.publishedSourceHypotheses[i];
  if(n.id!==NODE_IDS[i]||n.category!==(i===0?"PRIMARY":"KEY_SECONDARY")||
     n.endpoint!==ENDPOINTS[i]||n.studyComparison!==COMPARISONS[i]||
     n.supplementPhysicalPage!==11||n.prespecifiedGraphPosition!==POSITIONS[i]||
     n.clinicalResultStatus!==(i===0?"AUTHOR_REPORTED_NOT_INDEPENDENTLY_REPLICATED":"NOT_INDEPENDENTLY_REPLICATED"))return null;
 }
 for(let i=0;i<EDGES.length;i++){
  const e=d.graphEdges[i],x=EDGES[i];
  if(e.from!==x[0]||e.to!==x[1]||e.sourceDiagramTransferLabel!==x[2])return null;
 }
 const p=d.primaryPublishedEffect,s=d.sensitivityPublished,m=d.missingness,a=d.safetyReview,g=d.reviewSafety;
 if(p.comparison!=="pooled 50 mg versus placebo at 6 weeks"||
    p.differenceMmHg!==-9.1||JSON.stringify(p.confidenceIntervalMmHg)!=="[-13.3,-4.9]"||
    p.reportedP!=="<0.001"||p.independentlyReplicated!==false||
    s.table!=="eTable 3"||s.sensitivity1DifferenceMmHg!==-9.1||
    s.sensitivity2DifferenceMmHg!==-8.6||
    s.sensitivity4ObservedCaseDifferenceMmHg!==-9.1||
    s.sensitivity1ReportedP!=="<0.001"||s.sensitivity2ReportedP!=="<0.001"||
    s.sensitivity4ReportedP!=="<0.001"||
    s.tippingPointWithinPrespecifiedFortyMmHgShift!==false||
    s.scope!=="AUTHOR_REPORTED_COMPARISONS_NOT_INDEPENDENTLY_REPRODUCED")return null;
 if(m.denominatorSafetyTreated!==1078||m.totalTreatmentDiscontinuationOrDeathIntercurrentEvents!==24||
    m.adverseEventIntercurrentEvents!==23||m.deathIntercurrentEvents!==1||
    m.adverseEventRelatedMissingWeek6!==10||m.adverseEventRelatedMissingWeek12!==12||
    m.deathRelatedMissingWeek12!==1||m.otherMissingMARWeek6!==56||
    m.otherMissingMARWeek12!==67||m.imputedDatasets!==1000||
    m.imputationCodeAndSeedIndependentlyExecuted!==false||
    m.materialityAndOriginalProvenanceIndependentlyAdjudicated!==false||
    !m.sourceReportedMNARApproach.includes("retrieved-dropout")||
    !m.sourceReportedBackup.includes("jump-to-reference"))return null;
 if(a.source!=="Supplement 1 eTable 4"||a.sourcePagePhysicalOneBased!==17||
    JSON.stringify(a.safetyArmDenominators)!=="[270,538,270]"||
    JSON.stringify(a.serumSodiumBelow130)!=="[11,14,4]"||
    JSON.stringify(a.serumPotassiumObserved5Point6To6Point0)!=="[29,38,3]"||
    JSON.stringify(a.serumPotassiumConfirmed5Point6To6Point0)!=="[24,31,2]"||
    a.independentlyReviewed!==false)return null;
 if(g.originalPreUnblindingSAPVersionVerified!==false||
    g.databaseLockAndUnblindingAuthenticated!==false||
    g.fullOriginalPDFBytesSHA256Verified!==false||
    g.independentStatisticalRecalculationPerformed!==false||
    g.familywiseAlphaRecalculationPerformed!==false||
    g.signedClinicalReviewerCount!==0||
    g.independentlyValidatedFDAApplicationForecasts!==0||
    g.finalScientificGrade!==null||
    g.regulatoryForecast!=="ABSTAIN"||g.timingForecast!=="UNKNOWN"||
    g.trainingOrProductionWrites!==false||
    d.reviewGates.some(x=>typeof x!=="string"||x.length<55))return null;
 return {...d,methodsMapped:7,graphEdgesMapped:8,missingnessGroupsMapped:3,
   sourceVerifiedOnly:true as const,scientificReviewCompleted:false as const,
   independentPredictionAllowed:false as const};
}
export const FOCUS_R77_LAUNCH_HTN_PUBLISHED_METHODS=buildR77LaunchHtnPublishedMethods();
