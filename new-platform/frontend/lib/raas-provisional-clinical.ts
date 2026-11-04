/** Experimental BOTTOM clinical magnitude pilots, NOT validated RAAS efficacy ratings.
 * Fixed, explicitly arbitrary five-bin research-only heuristics, separated by
 * disease endpoint and requiring dated, arm-level placebo comparisons.
 * Never compare UAS7 within-patient MID to a between-arm contrast.
 */
import type {RaasObservation} from "./raas-score-engine";
import type {ProvisionalMetricGrade} from "./raas-threshold-profiles";
export const RAAS_CLINICAL_PILOT_VERSION="csu-placebo-contrast-heuristic-2026-11-04-v1";
const valid=(o:RaasObservation)=>/^https:\/\/[^\s/]+\/\S+/.test(o.sourceUrl)&&
 /^\d{4}-\d{2}-\d{2}$/.test(o.assessmentDate)&&o.measurementDate<=o.assessmentDate;
const finite=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const band=(value:number,thresholds:readonly [number,number,number]):0|25|50|75|100=>{
 if(value<=0)return 0;
 if(value<thresholds[0])return 25;
 if(value<thresholds[1])return 50;
 if(value<thresholds[2])return 75;
 return 100;
};
/** These are *metric proxies*: the other required protocol, SAP, confidence,
 * missing-data, comparative and safety checks have NOT been met.
 * The numerical bands intentionally carry no approved probability/return meaning.
 */
export function provisionalCsuMagnitudeGrade(o:RaasObservation,indication:string):
 ProvisionalMetricGrade|null{
 if(!/chronic (?:spontaneous|idiopathic) urticaria/i.test(indication)||!valid(o))return null;
 if(o.kind==="active_control_mean_change"&&o.unit==="UAS7 points"&&
  o.metricIds.includes("post-1-1")&&
  finite(o.activeChange)&&finite(o.controlChange)&&
  o.activeChange>=-42&&o.activeChange<=0&&o.controlChange>=-42&&o.controlChange<=0){
  const diff=Number((o.controlChange-o.activeChange).toFixed(2));
  if(diff<-42||diff>42)return null;
  const score=band(diff,[3,6,9]);
  return {metricId:"post-1-1",stage:"post",snapshot:"CURRENT",score,
   ruleId:RAAS_CLINICAL_PILOT_VERSION,kind:"RESEARCH_ONLY_NOT_VALIDATED",
   observationId:o.id,sourceUrl:o.sourceUrl,sourceDate:o.assessmentDate,
   label:"Placebo-adjusted UAS7 endpoint magnitude proxy (research only)",
   inputs:"Active "+o.activeChange+", placebo "+o.controlChange+
    "; placebo-adjusted improvement "+diff+" UAS7 points",
   explanation:"Exploratory and uncalibrated bins for same-scale between-arm contrast: "+
    "<=0 -> 0; >0 to <3 -> 25; 3 to <6 -> 50; 6 to <9 -> 75; >=9 -> 100. "+
    "These bins are not established clinical thresholds and do not express success probability.",
   limitations:"Only one reported arm-level endpoint; independent protocol/SAP, uncertainty, "+
    "multiplicity, missing-data, full safety and regulatory review remain required. "+
    "Within-patient UAS7 minimal important difference is NOT this comparator-adjusted effect. "+
    "Do not use in approved RAAS aggregation."};
 }
 if(o.kind==="active_control_response"&&
  /complete response\s*\(UAS7\s*=\s*0\)/i.test(o.title)&&
  o.metricIds.includes("post-1-2")&&
  finite(o.activePercent)&&finite(o.controlPercent)&&
  o.activePercent>=0&&o.activePercent<=100&&o.controlPercent>=0&&o.controlPercent<=100){
  const diff=Number((o.activePercent-o.controlPercent).toFixed(2));
  if(diff<-100||diff>100)return null;
  const score=band(diff,[10,20,30]);
  return {metricId:"post-1-2",stage:"post",snapshot:"CURRENT",score,
   ruleId:RAAS_CLINICAL_PILOT_VERSION,kind:"RESEARCH_ONLY_NOT_VALIDATED",
   observationId:o.id,sourceUrl:o.sourceUrl,sourceDate:o.assessmentDate,
   label:"Placebo-adjusted complete-response percentage-point proxy (research only)",
   inputs:"Active "+o.activePercent+"%, placebo "+o.controlPercent+
    "%; complete-response difference "+diff+" percentage points",
   explanation:"Exploratory and uncalibrated placebo-adjusted complete-response bins: "+
    "<=0 -> 0; >0 to <10 pp -> 25; 10 to <20 pp -> 50; "+
    "20 to <30 pp -> 75; >=30 pp -> 100. Not a validated clinical-importance grade.",
   limitations:"Only a reported complete-response contrast, not full patient-reported "+
    "quality of life, protocol/SAP, confidence interval, safety, treatment durability, "+
    "or comparative value versus approved alternatives. Do not use in overall RAAS."};
 }
 return null;
}
