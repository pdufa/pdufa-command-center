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
 /** Every saved measurement per OG group in original source order. The
  * compact index omits time-point/category identity for repeated values. */
 groupMeasurementSeries:string[][];
 armValueMultiplicity:"SINGLE_VALUE_PER_ARM"|"MULTIPLE_UNRESOLVED_VALUES"|"MISSING";
 roundingUncertainty:number|null;
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
  "ARM_DELTA_NEAR_REPORTED_VALUE_STILL_UNREVIEWED"|
  "AMBIGUOUS_MULTIPLE_GROUP_MEASUREMENTS"|
  "COUNT_ENDPOINT_REQUIRES_PROPORTION_DENOMINATORS"|
  "ROUNDING_COMPATIBLE_MEAN_DIFFERENCE_STILL_UNREVIEWED";
 /** Source observations are not clinical merit or independently audited data. */
 independentHumanReview:"NOT_COMPLETED";
 approvedMetricGrade:null;approvedRaasScore:null;calibratedFdaProbability:null;
};
export type PrimaryContrastReconciliationLedger={
 scope:"RAAS_EXACT_NCT_PRIMARY_ARM_RECONCILIATION_UNGRADED";
 sourceAsOf:string;registryNcts:number;comparisons:number;
 trialsWithComparisons:number;twoArmContexts:number;numericReportedStatistics:number;
 eligibleRawArmChecks:number;nearRawArmDifference:number;rawArmDiscrepancies:number;
 repeatedGroupOutcomes:number;countProportionIncompatibilities:number;
 roundingCompatible:number;
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

/** Last displayed decimal place bounds rounding at half a unit. */
const halfRoundingUnit=(raw:string):number=>{
 const m=raw.trim().match(/^[+-]?\d+(?:\.(\d+))?$/);
 return m?0.5*Math.pow(10,-(m[1]?.length??0)):0;
};
/** Participant counts cannot be subtracted to check a proportion estimate. */
const countProportion=(unit:string,title:string)=>
 /^participants?$/i.test(unit.trim())&&
 /\b(proportions?|percentages?|percent|rates?|responders?)\b/i.test(title);

export function buildPrimaryContrastReconciliationLedger(raw:unknown):
 PrimaryContrastReconciliationLedger{
 const index:RegistryEvidenceIndex=parseRegistryEvidenceIndex(raw);
 const records:PrimaryContrastReconciliation[]=[];
 const seen=new Set<string>(),trialIds=new Set<string>();
 for(const r of index.records){
  if(!r.postedResults)continue;
  for(const [oi,outcome] of r.primaryResults.entries()){
   const names=new Map((outcome.groups||[]).map(g=>[g.id,g.title]));
   // A repeated OG group ID may represent MULTIPLE time points or
   // categories. The former Map dropped earlier values and manufactured
   // discrepancies. Preserve the source sequence, without guessing class.
   const measured=new Map<string,string[]>();
   for(const m of outcome.measurements||[]){
    if(!m.groupId)continue;
    const series=measured.get(m.groupId)??[];
    series.push(m.value??"");measured.set(m.groupId,series);
   }
   for(const [ci,c] of (outcome.comparisons||[]).entries()){
    // Single-group analyses are not treatment-arm comparisons.
    if((c.groupIds||[]).length<2)continue;
    const id=r.nctId+"|primary-"+oi+"|comparison-"+ci;
    if(seen.has(id))throw Error("RAAS_ARM_RECONCILIATION_DUPLICATE_COMPARISON");
    seen.add(id);trialIds.add(r.nctId);
    const groupIds=c.groupIds||[];
    const groupNames=groupIds.map(g=>names.get(g)||"UNRESOLVED_GROUP_ID");
    const groupMeasurementSeries=groupIds.map(g=>measured.get(g)??[]);
    const multi=groupMeasurementSeries.some(a=>a.length>1);
    const armValueMultiplicity=multi?"MULTIPLE_UNRESOLVED_VALUES" as const:
     groupMeasurementSeries.some(a=>a.length!==1)?"MISSING" as const:
     "SINGLE_VALUE_PER_ARM" as const;
    const values=groupMeasurementSeries.map(a=>a.length===1?number(a[0]):null);
    const groupNamesVerified=groupIds.length===2&&
     new Set(groupIds).size===2&&groupIds.every(g=>!!names.get(g));
    const bothArmValuesNumeric=groupNamesVerified&&values.every(v=>v!==null);
    const reportedStatistic=number(c.paramValue);
    const isCountProportion=countProportion(outcome.unit,outcome.title);
    const rawDifferenceEligible=bothArmValuesNumeric&&!isCountProportion&&
     reportedStatistic!==null&&observedMeanDiff(c.paramType||"");
    const observedFirstMinusSecond=bothArmValuesNumeric&&!isCountProportion?
     normal(values[0]!-values[1]!):null;
    const gap=rawDifferenceEligible&&observedFirstMinusSecond!==null?
     normal(Math.min(Math.abs(reportedStatistic!-observedFirstMinusSecond),
      Math.abs(reportedStatistic!+observedFirstMinusSecond))):null;
    const tolerance=gap!==null?normal(Math.max(0.02,
     0.05*Math.abs(reportedStatistic!),0.01*Math.abs(observedFirstMinusSecond!))):null;
    const roundingUncertainty=gap!==null?normal(
     groupMeasurementSeries.reduce((sum,a)=>sum+halfRoundingUnit(a[0]||""),0)+
     halfRoundingUnit(c.paramValue||"")):null;
    const signal:PrimaryContrastReconciliation["signal"]=
     multi?"AMBIGUOUS_MULTIPLE_GROUP_MEASUREMENTS":
     isCountProportion?"COUNT_ENDPOINT_REQUIRES_PROPORTION_DENOMINATORS":
     !bothArmValuesNumeric?"NO_EXACT_TWO_ARM_RECONSTRUCTION":
     reportedStatistic===null?"NO_NUMERIC_REPORTED_STATISTIC":
     !rawDifferenceEligible?"STATISTIC_NOT_RAW_MEAN_DIFFERENCE":
     gap!==null&&tolerance!==null&&gap>tolerance&&
       roundingUncertainty!==null&&gap<=roundingUncertainty?
     "ROUNDING_COMPATIBLE_MEAN_DIFFERENCE_STILL_UNREVIEWED":
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
     groupMeasurementSeries,armValueMultiplicity,roundingUncertainty,
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
  repeatedGroupOutcomes:records.filter(x=>x.signal==="AMBIGUOUS_MULTIPLE_GROUP_MEASUREMENTS").length,
  countProportionIncompatibilities:records.filter(x=>x.signal==="COUNT_ENDPOINT_REQUIRES_PROPORTION_DENOMINATORS").length,
  roundingCompatible:records.filter(x=>x.signal==="ROUNDING_COMPATIBLE_MEAN_DIFFERENCE_STILL_UNREVIEWED").length,
  unverifiedOrNonadditive:records.filter(x=>!x.rawDifferenceEligible).length,
  independentHumanReviews:0,approvedRaasScores:0,calibratedFdaPredictions:0,
  records
 };
}
