/** Provisional 60-metric scoring policy, distinct from approved historical calibration.
 * All 60 have a five-anchor review rubric and explicit evidence requirements;
 * three narrow objective experimental pilots have automatic calculations.
 * A specified rubric is NOT the same thing as a completed, validated metric.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {RAAS_THRESHOLD_PROFILES} from "./raas-threshold-profiles";

export const RAAS_PROVISIONAL_POLICY_VERSION="raas-provisional-review-rubrics-2026-11-04-v1";
export const RAAS_PROVISIONAL_BANDS=[0,25,50,75,100] as const;
export type ProvisionalBand=typeof RAAS_PROVISIONAL_BANDS[number];
export type ProvisionalMethod="AUTOMATED_NARROW_PILOT"|"EVIDENCE_REVIEW_REQUIRED";
export type ProvisionalRule={
 metricId:string;stage:RaasStage;name:string;group:string;groupWeight:number;
 requiredEvidence:string;benchmarkRequired:string;direction:string;criticalRisk:string;
 method:ProvisionalMethod;
 anchors:Readonly<Record<ProvisionalBand,string>>;
 approvedForComposite:false;accuracyValidated:false;version:string;
};
const domainAnchors={
 "pre-1": "scientific evidence", "pre-2": "risk-adjusted valuation",
 "pre-3": "downside protection", "pre-4": "catalyst timing",
 "pre-5": "medical and peer advantage", "pre-6": "execution feasibility",
 "post-1": "clinical evidence", "post-2": "remaining valuation",
 "post-3": "FDA and manufacturing review", "post-4": "downside protection",
 "post-5": "commercial evidence", "post-6": "PDUFA timing"
} as const;
function labels(metric:{id:string;name:string;scoreRule:string;criticalRisk:string}):Readonly<Record<ProvisionalBand,string>>{
 const context=domainAnchors[metric.id.slice(0,metric.id.lastIndexOf("-")) as keyof typeof domainAnchors];
 if(!context)throw Error("RAAS_PROVISIONAL_UNKNOWN_METRIC");
 return {
  0:"Verified material adverse "+context+" finding for '"+metric.name+"'; failure threshold documented, not an absent input. Risk: "+metric.criticalRisk,
  25:"Documented unfavorable "+context+" evidence against a dated benchmark; risk unresolved: "+metric.criticalRisk,
  50:"Documented mixed/neutral "+context+" evidence relative to a matched, dated comparator; not a default for missing evidence.",
  75:"Documented favorable "+context+" evidence against a prespecified matched benchmark. Evaluation: "+metric.scoreRule,
  100:"Exceptionally robust "+context+" evidence with independent replication or stress testing and demonstrated control of: "+metric.criticalRisk
 };
}
const automated=new Set(["pre-4-1","post-1-1","post-1-2"]);
export const RAAS_PROVISIONAL_RULES:readonly ProvisionalRule[]=
 (["pre","post"] as const).flatMap(stage=>RAAS_METRIC_CATALOG[stage].flatMap(group=>
  group.metrics.map(metric=>{
   const profile=RAAS_THRESHOLD_PROFILES.find(x=>x.stage===stage&&x.metricId===metric.id);
   if(!profile)throw Error("RAAS_PROVISIONAL_PROFILE_MISSING:"+metric.id);
   return {metricId:metric.id,stage,name:metric.name,group:group.name,
    groupWeight:group.weight,requiredEvidence:metric.requiredEvidence,
    benchmarkRequired:profile.benchmarkRequired,direction:profile.direction,
    criticalRisk:metric.criticalRisk,
    method:automated.has(metric.id)?"AUTOMATED_NARROW_PILOT" as const:"EVIDENCE_REVIEW_REQUIRED" as const,
    anchors:labels(metric),approvedForComposite:false as const,
    accuracyValidated:false as const,version:RAAS_PROVISIONAL_POLICY_VERSION};
  })
 ));
if(RAAS_PROVISIONAL_RULES.length!==60||
   new Set(RAAS_PROVISIONAL_RULES.map(x=>x.metricId)).size!==60)
 throw Error("RAAS_PROVISIONAL_REGISTRY_INCOMPLETE");
export function provisionalRule(stage:RaasStage,metricId:string):ProvisionalRule|null{
 return RAAS_PROVISIONAL_RULES.find(x=>x.stage===stage&&x.metricId===metricId)||null;
}
export type SourceReviewedAnchor={
 nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage;
 metricId:string;band:ProvisionalBand;assessmentAsOf:string;
 sourceDate:string;sourceUrl:string;benchmarkSourceDate:string;benchmarkSourceUrl:string;
 reviewer:string;rationale:string;counterEvidence:string;
};
/** Human-source-reviewed metric anchors are accepted only with *all* dated
 * identity, benchmark, counter-evidence and reviewer fields. This is a
 * provisional review intake, never approval for a validated composite.
 */
export function screenProvisionalAnchor(
 entry:SourceReviewedAnchor,trial:{nctId:string;ticker:string;drug:string;indication:string},
 asOf:string
):{accepted:true;rule:ProvisionalRule;score:ProvisionalBand}|{accepted:false;reason:string}{
 const rule=provisionalRule(entry.stage,entry.metricId);
 if(!rule)return {accepted:false,reason:"RULE_NOT_FOUND"};
 const same=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
 const date=(s:string)=>/^\d{4}-\d{2}-\d{2}$/.test(s)&&
  new Date(s+"T00:00:00Z").toISOString().slice(0,10)===s;
 const url=(s:string)=>/^https:\/\/[^\s/@:?#]+\/[^\s]+$/.test(s)&&!s.includes("@");
 if(!/^NCT\d{8}$/.test(entry.nctId)||entry.nctId!==trial.nctId||
    !same(entry.ticker,trial.ticker)||!same(entry.drug,trial.drug)||
    !same(entry.indication,trial.indication))
  return {accepted:false,reason:"EXACT_TRIAL_IDENTITY_REQUIRED"};
 if(!RAAS_PROVISIONAL_BANDS.includes(entry.band))
  return {accepted:false,reason:"INVALID_NUMERIC_BAND"};
 if(!date(asOf)||!date(entry.assessmentAsOf)||!date(entry.sourceDate)||
    !date(entry.benchmarkSourceDate)||entry.assessmentAsOf>asOf||
    entry.sourceDate>entry.assessmentAsOf||
    entry.benchmarkSourceDate>entry.assessmentAsOf||
    !url(entry.sourceUrl)||!url(entry.benchmarkSourceUrl))
  return {accepted:false,reason:"SOURCE_OR_BENCHMARK_ASOF_INVALID"};
 if(!entry.reviewer?.trim()||entry.rationale?.trim().length<80||
    entry.counterEvidence?.trim().length<30)
  return {accepted:false,reason:"REVIEW_JUSTIFICATION_INCOMPLETE"};
 return {accepted:true,rule,score:entry.band};
}
