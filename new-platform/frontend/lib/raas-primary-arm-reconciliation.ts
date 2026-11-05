/** Exact ClinicalTrials.gov primary contrast-to-arm reconciliation.
 * This is an independent reproducibility worklist, NOT an independently
 * reviewed efficacy assessment, a treatment ranking, or RAAS/FDA score.
 * Group IDs are scoped to each outcome; EG adverse-event groups are never
 * joined to OG outcome groups.
 */
import {parseRegistryEvidenceIndex,type RegistryEvidenceIndex} from "./raas-registry-evidence";

export type PrimaryContrastReconciliation={
 id:string;nctId:string;ticker:string;sourceUrl:string;sourceHash:string;
 sourceAsOf:string;resultsFirstPosted:string|null;
 outcomeIndex:number;comparisonIndex:number;
 outcomeTitle:string;outcomeTimeFrame:string;outcomeUnit:string;
 groupIds:string[];groupNames:string[];
 groupValues:(number|null)[];
 reportedStatisticType:string;reportedStatistic:number|null;
 reportedStatisticRaw:string;reportedCILevel:string;
 reportedCILower:number|null;reportedCIUpper:number|null;
 pValueRaw:string;method:string;
 observedFirstMinusSecond:number|null;
 absoluteGapToEitherDirection:number|null;
 gapThreshold:number|null;
 groupNamesVerified:boolean;bothArmValuesNumeric:boolean;
 rawDifferenceEligible:boolean;
 signal:"NO_EXACT_TWO_ARM_RECONSTRUCTION"|"NO_NUMERIC_REPORTED_STATISTIC"|
  "STATISTIC_NOT_RAW_MEAN_DIFFERENCE"|"ARM_DELTA_DISCREPANCY_NEEDS_ESTIMAND_REVIEW"|
  "ARM_DELTA_NEAR_REPORTED_VALUE_STILL_UNREVIEWED";
 /** Source observations are not clinical merit or independently audited data. */
 independentHumanReview:"NOT_COMPLETED";
 approvedMetricGrade:null;approvedRaasScore:null;calibratedFdaProbability:null;
};
export type PrimaryContrastReconciliationLedger={
 scope:"RAAS_EXACT_NCT_PRIMARY_ARM_RECONCILIATION_UNGRADED";
 sourceAsOf:string;registryNcts:number;comparisons:number;
 trialsWithComparisons:number;twoArmContexts:number;numericReportedStatistics:number;
 eligibleRawArmChecks:number;nearRawArmDifference:number;rawArmDiscrepancies:number;
 unverifiedOrNonadditive:number;independentHumanReviews:0;
 approvedRaasScores:0;calibratedFdaPredictions:0;
 records:PrimaryContrastReconciliation[];
};
const number=(value:unknown):number|null=>{
 if(typeof value!=="string"||!/^[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?$/i.test(value.trim()))
  return null;
 const v=Number(value);
 return Number.isFinite(v)&&Math.abs(v)<=1e12?v:null;
};
const normal=(value:number)=>Math.round(value*1e9)/1e9;
const observedMeanDiff=(name:string)=>/^mean difference\b/i.test(name.trim())&&
 !/log|ratio|hazard|odds|percent|rate ratio/i.test(name);

export function buildPrimaryContrastReconciliationLedger(raw:unknown):
 PrimaryContrastReconciliationLedger{
 const index:RegistryEvidenceIndex=parseRegistryEvidenceIndex(raw);
 const records:PrimaryContrastReconciliation[]=[];
 const seen=new Set<string>(),trialIds=new Set<string>();
 for(const r of index.records){
  if(!r.postedResults)continue;
  for(const [oi,outcome] of r.primaryResults.entries()){
   const names=new Map((outcome.groups||[]).map(g=>[g.id,g.title]));
   const measured=new Map((outcome.measurements||[]).map(m=>
    [m.groupId,number(m.value)]));
   for(const [ci,c] of (outcome.comparisons||[]).entries()){
    const id=r.nctId+"|primary-"+oi+"|comparison-"+ci;
    if(seen.has(id))throw Error("RAAS_ARM_RECONCILIATION_DUPLICATE_COMPARISON");
    seen.add(id);trialIds.add(r.nctId);
    const groupIds=c.groupIds||[];
    const groupNames=groupIds.map(g=>names.get(g)||"UNRESOLVED_GROUP_ID");
    const values=groupIds.map(g=>measured.get(g)??null);
    const groupNamesVerified=groupIds.length===2&&
     new Set(groupIds).size===2&&groupIds.every(g=>!!names.get(g));
    const bothArmValuesNumeric=groupNamesVerified&&values.every(v=>v!==null);
    const reportedStatistic=number(c.paramValue);
    const rawDifferenceEligible=bothArmValuesNumeric&&
     reportedStatistic!==null&&observedMeanDiff(c.paramType||"");
    const observedFirstMinusSecond=bothArmValuesNumeric?
     normal(values[0]!-values[1]!):null;
    const gap=rawDifferenceEligible&&observedFirstMinusSecond!==null?
     normal(Math.min(Math.abs(reportedStatistic!-observedFirstMinusSecond),
      Math.abs(reportedStatistic!+observedFirstMinusSecond))):null;
    const tolerance=gap!==null?normal(Math.max(0.02,
     0.05*Math.abs(reportedStatistic!),0.01*Math.abs(observedFirstMinusSecond!))):null;
    const signal:PrimaryContrastReconciliation["signal"]=
     !bothArmValuesNumeric?"NO_EXACT_TWO_ARM_RECONSTRUCTION":
     reportedStatistic===null?"NO_NUMERIC_REPORTED_STATISTIC":
     !rawDifferenceEligible?"STATISTIC_NOT_RAW_MEAN_DIFFERENCE":
     gap!==null&&tolerance!==null&&gap>tolerance?
     "ARM_DELTA_DISCREPANCY_NEEDS_ESTIMAND_REVIEW":
     "ARM_DELTA_NEAR_REPORTED_VALUE_STILL_UNREVIEWED";
    records.push({
     id,nctId:r.nctId,ticker:r.ticker,sourceUrl:r.sourceUrl,
     sourceHash:r.sourceHash,sourceAsOf:index.sourceAsOf,
     resultsFirstPosted:r.resultsFirstPosted,
     outcomeIndex:oi,comparisonIndex:ci,
     outcomeTitle:outcome.title,outcomeTimeFrame:outcome.timeFrame,
     outcomeUnit:outcome.unit,
     groupIds,groupNames,groupValues:values,
     reportedStatisticType:c.paramType||"",
     reportedStatistic,reportedStatisticRaw:c.paramValue||"",
     reportedCILevel:c.ciPctValue||"",
     reportedCILower:number(c.ciLowerLimit),reportedCIUpper:number(c.ciUpperLimit),
     pValueRaw:c.pValue||"",method:c.method||"",
     observedFirstMinusSecond,
     absoluteGapToEitherDirection:gap,gapThreshold:tolerance,
     groupNamesVerified,bothArmValuesNumeric,rawDifferenceEligible,signal,
     independentHumanReview:"NOT_COMPLETED",
     approvedMetricGrade:null,approvedRaasScore:null,calibratedFdaProbability:null
    });
   }
  }
 }
 return {
  scope:"RAAS_EXACT_NCT_PRIMARY_ARM_RECONCILIATION_UNGRADED",
  sourceAsOf:index.sourceAsOf,registryNcts:index.records.length,
  comparisons:records.length,trialsWithComparisons:trialIds.size,
  twoArmContexts:records.filter(x=>x.bothArmValuesNumeric).length,
  numericReportedStatistics:records.filter(x=>x.reportedStatistic!==null).length,
  eligibleRawArmChecks:records.filter(x=>x.rawDifferenceEligible).length,
  nearRawArmDifference:records.filter(x=>x.signal==="ARM_DELTA_NEAR_REPORTED_VALUE_STILL_UNREVIEWED").length,
  rawArmDiscrepancies:records.filter(x=>x.signal==="ARM_DELTA_DISCREPANCY_NEEDS_ESTIMAND_REVIEW").length,
  unverifiedOrNonadditive:records.filter(x=>!x.rawDifferenceEligible).length,
  independentHumanReviews:0,approvedRaasScores:0,calibratedFdaPredictions:0,
  records
 };
}
