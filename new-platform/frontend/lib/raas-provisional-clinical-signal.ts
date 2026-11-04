/** Research-only descriptive BOTTOM efficacy contrast pilot.
 * Thresholds are exploratory within a specified indication and endpoint,
 * NOT independent calibration, chance of FDA approval, or clinical merit.
 * Only the source-confirmed placebo-controlled 150 mg Q4W barzolvolimab
 * UAS7 Week-12 observations may pass these narrow 2026-11-04-v1 rules.
 */
import type {RaasObservation} from "./raas-score-engine";
import type {ProvisionalMetricGrade} from "./raas-threshold-profiles";
import readoutEvidence from "../public/phase3-public-readout-evidence-2026-11-01.json";
export const RAAS_POST_SIGNAL_RULE_VERSION="uas7-placebo-contrast-descriptive-2026-11-04-v1";
const eligible=new Map((readoutEvidence.entries||[]).filter(e=>
 e.kind==="POST_PUBLIC_READOUT"&&e.primaryEndpointP&&e.ticker==="CLDX"&&
 e.drug==="barzolvolimab"&&e.indication==="chronic spontaneous urticaria")
 .map(e=>[e.nctId,e]));
const band=(delta:number,cutoffs:readonly [number,number,number]):0|25|50|75|100=>
 delta<=0?0:delta<cutoffs[0]?25:delta<cutoffs[1]?50:delta<cutoffs[2]?75:100;
export function provisionalUas7Contrast(
 trial:{nctId:string;ticker:string;drug:string;indication:string},
 observations:readonly RaasObservation[],asOf:string
):ProvisionalMetricGrade[]{
 const matched=eligible.get(trial.nctId);
 if(!matched||trial.ticker!=="CLDX"||trial.drug!=="barzolvolimab"||
  trial.indication!=="chronic spontaneous urticaria"||
  matched.evidenceDate>asOf||!matched.primaryEndpointP||
  !/^p\s*<\s*0\.00001$/.test(matched.primaryEndpointP.display))return [];
 const grades:ProvisionalMetricGrade[]=[];
 for(const o of observations){
  if(o.assessmentDate>asOf||o.assessmentDate<matched.evidenceDate||
    o.sourceUrl!== "https://ir.celldex.com/node/16781/ixbrl-viewer"||
    !o.title.includes("150 mg Q4W")||!o.title.includes("Week 12")||
    o.measurementDate>o.assessmentDate)continue;
  let delta:number,score:0|25|50|75|100,metricId:string,inputs:string,limits:string;
  if(o.kind==="active_control_mean_change"&&
   o.metricIds.includes("post-1-1")&&o.unit==="UAS7 points"&&
   Number.isFinite(o.activeChange)&&Number.isFinite(o.controlChange)&&
   o.activeChange!<=0&&o.controlChange!<=0&&
   o.activeChange!>=-42&&o.controlChange!>=-42){
   delta=Math.round((o.controlChange!-o.activeChange!)*100)/100;
   score=band(delta,[2,5,10]);metricId="post-1-1";
   inputs="Placebo-adjusted LS mean UAS7 change "+delta+" points, 150 mg Q4W, Week 12";
   limits="Research-only UAS7 contrast bins: nonpositive 0; positive <2 =25; 2–<5 =50; 5–<10 =75; >=10 =100. Not a clinically validated between-arm minimal important difference.";
  }else if(o.kind==="active_control_response"&&
   o.metricIds.includes("post-1-2")&&o.title.includes("complete response")&&
   Number.isFinite(o.activePercent)&&Number.isFinite(o.controlPercent)&&
   o.activePercent!>=0&&o.activePercent!<=100&&
   o.controlPercent!>=0&&o.controlPercent!<=100){
   delta=Math.round((o.activePercent!-o.controlPercent!)*100)/100;
   score=band(delta,[10,20,30]);metricId="post-1-2";
   inputs="Placebo-adjusted UAS7=0 complete-response difference "+delta+" percentage points, 150 mg Q4W, Week 12";
   limits="Research-only complete-response contrast bins: nonpositive 0; positive <10pp =25; 10–<20pp =50; 20–<30pp =75; >=30pp =100. Does not compare to an active treatment.";
  }else continue;
  grades.push({metricId,stage:"post",snapshot:"CURRENT",score,
   ruleId:RAAS_POST_SIGNAL_RULE_VERSION,kind:"RESEARCH_ONLY_NOT_VALIDATED",
   observationId:o.id,sourceUrl:o.sourceUrl,sourceDate:o.assessmentDate,
   label:metricId==="post-1-1"?"Placebo-adjusted UAS7 effect (research only)":
    "Placebo-adjusted complete response (research only)",
   inputs,explanation:limits+" Primary release is company-reported, not independent clinical adjudication.",
   limitations:"Pilot heuristic, not an independently calibrated RAAS clinical grade or PDUFA/return forecast. Full clinical, safety, valuation and regulatory assessments remain incomplete."
  });
 }
 if(new Set(grades.map(x=>x.metricId)).size!==grades.length)return [];
 return grades;
}
