/** Explicit, review-gated provisional rubric for EVERY RAAS TOP/BOTTOM metric.
 * Metric-specific clinical/valuation benchmarks are NOT assumed. All 60
 * definitions are scoreable once a dated independent review supplies their
 * source, comparator and evidence; absence of proof is null, never zero.
 * No provisional grade is a calibrated PDUFA or stock-return prediction.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {RAAS_THRESHOLD_PROFILES} from "./raas-threshold-profiles";
export type RaasProvisionalFinding="MATERIAL_ADVERSE"|"BELOW_BENCHMARK"|
 "MIXED_EVIDENCE"|"ABOVE_BENCHMARK"|"EXCEPTIONAL_EVIDENCE";
export const RAAS_PROVISIONAL_FINDINGS:Readonly<Record<RaasProvisionalFinding,0|25|50|75|100>>={
 MATERIAL_ADVERSE:0,BELOW_BENCHMARK:25,MIXED_EVIDENCE:50,
 ABOVE_BENCHMARK:75,EXCEPTIONAL_EVIDENCE:100
};
export type RaasProvisionalRubric={
 metricId:string;stage:RaasStage;name:string;categoryName:string;
 categoryWeightPercent:number;metricWeightPercent:number;
 requiredEvidence:string;benchmarkRequirement:string;assessmentRule:string;
 criticalRisk:string;sourceStatus:"PRIMARY_AND_COMPARATOR_REQUIRED";
 approvedForComposite:false;bands:readonly {score:0|25|50|75|100;finding:RaasProvisionalFinding;definition:string}[];
};
const bandDescriptions:Record<RaasProvisionalFinding,string>={
 MATERIAL_ADVERSE:"Independently reviewed primary evidence confirms a material adverse outcome or risk against the predeclared metric-specific benchmark. Never use this for an unknown.",
 BELOW_BENCHMARK:"Dated, reviewed evidence is below the metric-specific benchmark, with the negative difference and uncertainty documented.",
 MIXED_EVIDENCE:"Dated, reviewed primary evidence shows a genuinely mixed/intermediate result against the benchmark; unknown is never mixed.",
 ABOVE_BENCHMARK:"Dated, reviewed result exceeds the metric-specific benchmark under a specified conservative sensitivity check.",
 EXCEPTIONAL_EVIDENCE:"Strong result exceeds a predeclared exceptional threshold and has independently corroborated robustness and uncertainty."
};
const findingNames=Object.keys(RAAS_PROVISIONAL_FINDINGS) as RaasProvisionalFinding[];
export const RAAS_PROVISIONAL_RUBRICS:readonly RaasProvisionalRubric[]=
 (["pre","post"] as const).flatMap(stage=>RAAS_METRIC_CATALOG[stage].flatMap(category=>
  category.metrics.map(metric=>{
   const profile=RAAS_THRESHOLD_PROFILES.find(p=>p.stage===stage&&p.metricId===metric.id);
   if(!profile)throw Error("RAAS_PROVISIONAL_PROFILE_MISSING:"+metric.id);
   return {metricId:metric.id,stage,name:metric.name,categoryName:category.name,
    categoryWeightPercent:category.weight,metricWeightPercent:category.weight/5,
    requiredEvidence:metric.requiredEvidence,benchmarkRequirement:profile.benchmarkRequired,
    assessmentRule:metric.scoreRule,criticalRisk:metric.criticalRisk,
    sourceStatus:"PRIMARY_AND_COMPARATOR_REQUIRED" as const,
    approvedForComposite:false as const,
    bands:findingNames.map(finding=>({finding,score:RAAS_PROVISIONAL_FINDINGS[finding],
     definition:bandDescriptions[finding]}))
   };
  })
 ));
export type RaasProvisionalReview={
 nctId:string;ticker:string;drug:string;indication:string;stage:RaasStage;
 metricId:string;finding:RaasProvisionalFinding;
 // Review made after obtaining the source, not backdated to publication day.
 assessedAt:string;sourceDate:string;sourceUrl:string;
 benchmarkSourceUrl:string;benchmarkId:string;benchmarkContext:string;
 observedResult:string;uncertaintyReview:string;criticalRiskReview:string;
 reviewerMethod:string;independentReview:"PASSED"|"AI_SOURCE_CROSSCHECKED";
};
export type RaasProvisionalReviewedGrade={
 metricId:string;stage:RaasStage;score:0|25|50|75|100;
 finding:RaasProvisionalFinding;ruleVersion:"raas-provisional-review-v1";
 sourceUrl:string;sourceDate:string;assessedAt:string;
 explanation:string;benchmarkSourceUrl:string;reviewMethod:string;
 approvedForComposite:false;
 reviewClass:"INDEPENDENT_REVIEW"|"AI_SOURCE_CROSSCHECKED";
};
const isoDay=(x:string)=>/^\d{4}-\d{2}-\d{2}$/.test(x)&&
 !Number.isNaN(Date.parse(x+"T00:00:00Z"))&&new Date(x+"T00:00:00Z").toISOString().slice(0,10)===x;
const secure=(s:string)=>typeof s==="string"&&/^https:\/\/[^\s/@?#]+\.[^\s/@?#]+\/\S+$/.test(s);
const exact=(a:string,b:string)=>a.trim().toLowerCase()===b.trim().toLowerCase();
const explicit=(x:string)=>typeof x==="string"&&x.trim().length>=12&&x.length<=5000;
export function provisionalReviewedGrade(
 trial:{nctId:string;ticker:string;drug:string;indication:string},stage:RaasStage,
 review:RaasProvisionalReview,asOf:string
):RaasProvisionalReviewedGrade|null{
 if(!/^NCT\d{8}$/.test(trial.nctId)||!isoDay(asOf))return null;
 const rubric=RAAS_PROVISIONAL_RUBRICS.find(x=>x.stage===stage&&x.metricId===review.metricId);
 if(!rubric||review.nctId!==trial.nctId||!exact(review.ticker,trial.ticker)||
  !exact(review.drug,trial.drug)||!exact(review.indication,trial.indication)||
  review.stage!==stage||!(review.finding in RAAS_PROVISIONAL_FINDINGS)||
  !["PASSED","AI_SOURCE_CROSSCHECKED"].includes(review.independentReview)||!isoDay(review.assessedAt)||
  !isoDay(review.sourceDate)||review.sourceDate>review.assessedAt||
  review.assessedAt>asOf||!secure(review.sourceUrl)||!secure(review.benchmarkSourceUrl)||
  !explicit(review.benchmarkId)||!explicit(review.benchmarkContext)||
  !explicit(review.observedResult)||!explicit(review.uncertaintyReview)||
  !explicit(review.criticalRiskReview)||!explicit(review.reviewerMethod))return null;
 // Source and benchmark cannot be the same unchecked self-claim.
 if(review.sourceUrl===review.benchmarkSourceUrl)return null;
 return {metricId:review.metricId,stage,score:RAAS_PROVISIONAL_FINDINGS[review.finding],
  finding:review.finding,ruleVersion:"raas-provisional-review-v1",
  sourceUrl:review.sourceUrl,sourceDate:review.sourceDate,assessedAt:review.assessedAt,
  benchmarkSourceUrl:review.benchmarkSourceUrl,reviewMethod:review.reviewerMethod,
  explanation:review.observedResult+" | Benchmark: "+review.benchmarkContext+
   " | Uncertainty: "+review.uncertaintyReview+" | Critical risks: "+review.criticalRiskReview,
  approvedForComposite:false,
  reviewClass:review.independentReview==="PASSED"?"INDEPENDENT_REVIEW":"AI_SOURCE_CROSSCHECKED"};
}
/** An experimental completeness diagnostic. NOT an overall RAAS, not a
 * point-in-time investment recommendation. Null unless every metric is graded.
 */
export function provisionalStageCoverage(
 stage:RaasStage,grades:readonly {metricId:string;score:number}[]
){
 const rubrics=RAAS_PROVISIONAL_RUBRICS.filter(x=>x.stage===stage);
 const accepted=new Map<string,number>(),rejected:string[]=[];
 for(const grade of grades){
  if(!rubrics.some(x=>x.metricId===grade.metricId)||!Object.values(RAAS_PROVISIONAL_FINDINGS).includes(grade.score as 0|25|50|75|100)||
   accepted.has(grade.metricId)){rejected.push(grade.metricId);continue;}
  accepted.set(grade.metricId,grade.score);
 }
 if(rejected.length)return {scored:0,missing:30,weightCoveredPercent:0,
  observedComponentMean:null,fullyCoveredProvisionalScore:null,rejected};
 let weightCovered=0,weighted=0;
 for(const r of rubrics){const grade=accepted.get(r.metricId);if(grade===undefined)continue;
  weightCovered+=r.metricWeightPercent;weighted+=r.metricWeightPercent*grade;}
 const observedComponentMean=weightCovered?Math.round(weighted/weightCovered*10)/10:null;
 const fullyCoveredProvisionalScore=accepted.size===30&&Math.abs(weightCovered-100)<.001?
  Math.round(weighted/100*10)/10:null;
 return {scored:accepted.size,missing:30-accepted.size,weightCoveredPercent:Math.round(weightCovered*100)/100,
  observedComponentMean,fullyCoveredProvisionalScore,rejected};
}
