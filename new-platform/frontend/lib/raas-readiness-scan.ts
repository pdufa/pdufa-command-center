/** Executable RAAS readiness audit, NOT a scoring or source-ingestion job.
 * Reads actual committed dated evidence; missing grades and historical
 * performances remain absent rather than reconstructed or set to zero.
 */
import {RAAS_METRIC_CATALOG,RAAS_SPEC_VERSION,type RaasStage} from "./raas-metric-specs";
import {parseHistoricalFeed,evaluateHistoricalFeed} from "./raas-historical-backtest";
import {parseMetricHistory,evaluateMetricHistory} from "./raas-metric-backtest";
import {parseRaasCalibrations,parseRaasReviewedLedger} from "./raas-reviewed-score-ledger";
import {parseProspectiveSourceBaselines,prospectiveSourceSummary} from "./raas-prospective-source-baselines";
import {parseTopRetrospective} from "./raas-top-retrospective-intake";
import {parseRetrospectiveFeed} from "./raas-retrospective-intake";
import {parsePriceCrosschecks,priceAuditSummary} from "./raas-price-crosschecks";
import {parseShareBridge,bridgeSummary} from "./raas-share-bridge";
import {parseFdaPrimaryOutcomes,fdaPrimaryOutcomeSummary} from "./raas-fda-primary-outcomes";
import historicalCases from "../data/raas-historical-cases.json";
import historicalScores from "../data/raas-historical-metric-snapshots.json";
import approvedCalibrations from "../data/raas-approved-calibrations.json";
import reviewedSnapshots from "../data/raas-reviewed-snapshots.json";
import prospectiveSources from "../data/raas-prospective-source-baselines.json";
import topResearch from "../data/raas-retrospective-top-cases.json";
import bottomResearch from "../data/raas-retrospective-source-cases.json";
import priceResearch from "../data/raas-price-crosschecks.json";
import shareResearch from "../data/raas-share-bridge-research.json";
import fdaResearch from "../data/raas-fda-primary-outcomes.json";

export type RaasScanMetric={
 stage:RaasStage;id:string;name:string;category:string;requiredEvidence:string;
 prospectiveSourceFacts:number;prospectiveIssuerCount:number;
 validatedHistoricalPrograms:number;holdoutTrainIssuers:number;holdoutTestIssuers:number;
 heldOutHighIssuers:number;heldOutLowIssuers:number;
 benchmarkVersionMatched:boolean;holdoutEvidencePositive:boolean;
 historicalReviewEligible:boolean;approvedCalibration:boolean;
 status:"MISSING_HISTORICAL_VALIDATION"|"REVIEW_ELIGIBLE_NOT_APPROVED"|"CALIBRATION_APPROVED_REVIEW_REQUIRED";
 reason:string;
};
export type RaasReadinessReport={
 schemaVersion:1;scope:"RAAS_EXECUTED_READINESS_AUDIT";
 sourceAsOf:string;specVersion:string;
 scanExecution:"COMPLETED_READ_ONLY_SOURCE_AUDIT";
 finalScoring:"NOT_VALIDATED";
 summary:{
  metricsInspected:number;preMetricsInspected:number;postMetricsInspected:number;
  approvedMetricCalibrations:number;reviewEligibleMetrics:number;
  historicalTradeCases:number;historicalAcceptedCases:number;historicalRatedMetrics:number;
  reviewedTrialSnapshots:number;prospectiveIssuers:number;prospectivePrograms:number;
  prospectiveSourceFacts:number;retrospectiveResearchWindows:number;
  independentlyConfirmedNominalCloses:number;nominalClosePoints:number;
  secShareBridgeCases:number;fdaPrimaryCrosschecks:number;
 };
 categories:{stage:RaasStage;id:string;name:string;total:number;approved:number;
  sourceFacts:number;historicallyValidated:number}[];
 metrics:RaasScanMetric[];
 limitations:string[];
};

export function executeRaasReadinessScan():RaasReadinessReport{
 // The parse functions fail closed on corrupt IDs, sources, calendars or dates.
 const historical=parseHistoricalFeed(historicalCases);
 const rated=parseMetricHistory(historicalScores);
 const calibrations=parseRaasCalibrations(approvedCalibrations);
 const reviewed=parseRaasReviewedLedger(reviewedSnapshots);
 const prospective=parseProspectiveSourceBaselines(prospectiveSources);
 const prospectiveStats=prospectiveSourceSummary(prospective);
 const earlier=parseTopRetrospective(topResearch);
 const later=parseRetrospectiveFeed(bottomResearch);
 const price=parsePriceCrosschecks(priceResearch,earlier,later);
 const shares=parseShareBridge(shareResearch,earlier,later);
 const fda=parseFdaPrimaryOutcomes(fdaResearch,later);
 const verified=evaluateHistoricalFeed(historical);
 const diagnostics=evaluateMetricHistory(historical,verified,rated);
 const byMetric=new Map(diagnostics.map(d=>[d.stage+"|"+d.metricId,d]));
 const approved=new Map(calibrations.entries.map(e=>[e.stage+"|"+e.metricId,e]));
 const sourceFacts=prospective.records.flatMap(r=>r.observations.flatMap(o=>
   o.metricIds.map(metricId=>({metricId,stage:r.stage,
    issuer:r.ticker.trim().toUpperCase(),source:o.sourceUrl}))));
 const metrics:RaasScanMetric[]=[];
 const categories:RaasReadinessReport["categories"]=[];
 for(const stage of ["pre","post"] as const){
  for(const category of RAAS_METRIC_CATALOG[stage]){
   for(const m of category.metrics){
    const key=stage+"|"+m.id,d=byMetric.get(key);
    if(!d)throw Error("RAAS_SCAN_METRIC_HISTORY_MISSING:"+key);
    const linked=sourceFacts.filter(x=>x.stage===stage&&x.metricId===m.id);
    const linkedIssuers=new Set(linked.map(x=>x.issuer));
    const rule=approved.get(key);
    // A calibration record is NOT enough: only matching chronological
    // issuer-disjoint holdout evidence makes a metric review-eligible.
    const holdoutOK=d.status==="REVIEW_ELIGIBLE_NOT_APPROVED"&&
      d.protocolConsistent&&d.holdoutTrainPrograms>=30&&
      d.holdoutTestPrograms>=Math.max(30,rule?.outOfSampleTrials??30)&&
      d.holdoutHighPrograms>=5&&d.holdoutLowPrograms>=5&&
      d.holdoutSpearmanScoreToReturn!==null&&d.holdoutSpearmanScoreToReturn>0&&
      d.holdoutHighMinusLowPercent!==null&&d.holdoutHighMinusLowPercent>0;
    const matched=!!rule&&d.benchmarkId===rule.benchmarkId&&d.ruleVersion===rule.ruleVersion;
    const approvedCalibration=!!rule&&holdoutOK&&matched;
    metrics.push({
     stage,id:m.id,name:m.name,category:category.name,requiredEvidence:m.requiredEvidence,
     prospectiveSourceFacts:linked.length,prospectiveIssuerCount:linkedIssuers.size,
     validatedHistoricalPrograms:d.independentPrograms,
     holdoutTrainIssuers:d.holdoutTrainPrograms,holdoutTestIssuers:d.holdoutTestPrograms,
     heldOutHighIssuers:d.holdoutHighPrograms,heldOutLowIssuers:d.holdoutLowPrograms,
     benchmarkVersionMatched:matched,holdoutEvidencePositive:holdoutOK,
     historicalReviewEligible:holdoutOK,approvedCalibration,
     status:approvedCalibration?"CALIBRATION_APPROVED_REVIEW_REQUIRED":
      holdoutOK?"REVIEW_ELIGIBLE_NOT_APPROVED":"MISSING_HISTORICAL_VALIDATION",
     reason:approvedCalibration?
      "Approved calibration exists; complete trial-specific snapshots and risk gates still required.":
      d.reason
    });
   }
   const group=metrics.filter(m=>m.stage===stage&&m.category===category.name);
   categories.push({stage,id:category.id,name:category.name,total:category.metrics.length,
    approved:group.filter(m=>m.approvedCalibration).length,
    sourceFacts:group.reduce((n,m)=>n+m.prospectiveSourceFacts,0),
    historicallyValidated:group.filter(m=>m.historicalReviewEligible).length});
  }
 }
 if(metrics.length!==60||new Set(metrics.map(m=>m.stage+"|"+m.id)).size!==60||
    metrics.filter(m=>m.stage==="pre").length!==30||
    metrics.filter(m=>m.stage==="post").length!==30||
    categories.length!==12)throw Error("RAAS_SCAN_CATALOG_INCOMPLETE");
 const priceSummary=priceAuditSummary(price,earlier,later);
 const shareSummary=bridgeSummary(shares,earlier,later);
 const fdaSummary=fdaPrimaryOutcomeSummary(fda,later);
 const approvedCount=metrics.filter(m=>m.approvedCalibration).length;
 // A source-readiness scan can never certify a complete clinical/trading
 // score without separately reviewed per-trial snapshots and risk gates.
 return {
  schemaVersion:1,scope:"RAAS_EXECUTED_READINESS_AUDIT",
  sourceAsOf:historical.sourceAsOf,specVersion:RAAS_SPEC_VERSION,
  scanExecution:"COMPLETED_READ_ONLY_SOURCE_AUDIT",
  finalScoring:"NOT_VALIDATED",
  summary:{
   metricsInspected:60,preMetricsInspected:30,postMetricsInspected:30,
   approvedMetricCalibrations:approvedCount,
   reviewEligibleMetrics:metrics.filter(m=>m.historicalReviewEligible).length,
   historicalTradeCases:historical.cases.length,historicalAcceptedCases:verified.accepted.length,
   historicalRatedMetrics:rated.records.length,reviewedTrialSnapshots:reviewed.records.length,
   prospectiveIssuers:prospectiveStats.distinctIssuers,
   prospectivePrograms:prospectiveStats.distinctPrograms,
   prospectiveSourceFacts:prospectiveStats.recordedSourceFacts,
   retrospectiveResearchWindows:earlier.records.length+later.records.length,
   independentlyConfirmedNominalCloses:priceSummary.matchedPoints,
   nominalClosePoints:priceSummary.quotedPoints,
   secShareBridgeCases:shareSummary.withSecShareCount,
   fdaPrimaryCrosschecks:fdaSummary.crosschecked
  },
  categories,metrics,
  limitations:[
   "The source audit completed; a completed audit is not a completed or qualified predictive RAAS scan.",
   "Historical cases selected retrospectively are never backdated into pre-entry forecasts.",
   "Issuer-source leads and retrospective prices cannot substitute for accepted metric scores.",
   "30 independent training issuers and 30 disjoint later holdout issuers per metric, high/low cohort checks, pre-entry rule versions, verified adjusted returns and independent audit remain required.",
   "This scan evaluates committed research snapshots only. It does not retrieve real-time source updates, brokerage prices, or external data.",
   "Final per-trial RAAS composite also requires all 30 approved metric grades, complete point-in-time snapshots and passed risk gates."
  ]
 };
}
