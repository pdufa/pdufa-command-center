/** Stage-specific full 30-metric RAAS research-score calculator.
 * This is NOT an FDA approval probability, trading forecast or externally
 * validated RAAS model. A provisional score appears ONLY after all 30 metrics
 * have separately documented primary sources, independent comparator reviews,
 * uncertainty and critical-risk reviews, and the readout stage is verified.
 * Unknown metrics are null; never impute 0, 50 or an average as a full score.
 */
import {RAAS_METRIC_CATALOG,type RaasStage} from "./raas-metric-specs";
import {provisionalReviewedGrade,provisionalStageCoverage,
 type RaasProvisionalReview,type RaasProvisionalReviewedGrade}
 from "./raas-provisional-rubric-engine";
import reviewData from "../data/raas-reviewed-metric-assessments.json";

export type ReviewedMetricFeed={
 schemaVersion:1;scope:"RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY";
 sourceAsOf:string;records:RaasProvisionalReview[];
};
export type ReviewedTrialCandidate={
 nctId:string;ticker:string;stage:RaasStage;
 reviewedCount:number;independentReviewedCount:number;aiCrosscheckedCount:number;
 missingMetricIds:string[];
 weightedCoveragePercent:number;observedMean:number|null;
 /** Only a full, exact-trial, explicitly reviewed 30/30 and stage-verification. */
 fullResearchScore:number|null;
 approvedOverallScore:null;
 type:"UNVALIDATED_REVIEWED_RESEARCH_SCORE_NOT_FDA_PROBABILITY";
 grades:RaasProvisionalReviewedGrade[];
};
const isoDay=(d:unknown):d is string=>typeof d==="string"&&
 /^\d{4}-\d{2}-\d{2}$/.test(d)&&!Number.isNaN(Date.parse(d+"T00:00:00Z"))&&
 new Date(d+"T00:00:00Z").toISOString().slice(0,10)===d;
const norm=(x:string)=>x.trim().replace(/\s+/g," ").toLowerCase();
const same=(a:string,b:string)=>norm(a)===norm(b);
const allowed=new Set(["pre","post"]);
const key=(x:RaasProvisionalReview)=>[
 x.nctId,norm(x.ticker),norm(x.drug),norm(x.indication),x.stage,x.metricId].join("|");
export function parseReviewedMetricFeed(raw:unknown):ReviewedMetricFeed{
 if(!raw||typeof raw!=="object")throw Error("RAAS_REVIEWED_FEED_INVALID");
 const x=raw as ReviewedMetricFeed;
 if(x.schemaVersion!==1||x.scope!=="RAAS_EXPLICIT_METRIC_REVIEWS_RESEARCH_ONLY"||
  !isoDay(x.sourceAsOf)||!Array.isArray(x.records)||x.records.length>50000)
  throw Error("RAAS_REVIEWED_FEED_INVALID");
 const seen=new Set<string>();
 for(const r of x.records){
  if(!r||typeof r!=="object"||!/^NCT\d{8}$/.test(r.nctId)||
    !r.ticker?.trim()||!r.drug?.trim()||!r.indication?.trim()||
    !allowed.has(r.stage)||!r.metricId?.startsWith(r.stage+"-")||
    seen.has(key(r))||!provisionalReviewedGrade({
      nctId:r.nctId,ticker:r.ticker,drug:r.drug,indication:r.indication
    },r.stage,r,x.sourceAsOf))throw Error("RAAS_REVIEWED_FEED_UNVERIFIED_ROW");
  seen.add(key(r));
 }
 return x;
}
const savedReviews=parseReviewedMetricFeed(reviewData);
export function fullReviewedTrialCandidate(
 trial:{nctId:string;ticker:string;drug?:string;indication?:string},
 stage:RaasStage,stageVerified:boolean,feed:ReviewedMetricFeed=savedReviews
):ReviewedTrialCandidate{
 if(!/^NCT\d{8}$/.test(trial.nctId)||!trial.ticker?.trim()||!allowed.has(stage))
  throw Error("RAAS_REVIEWED_SCORE_TRIAL_INVALID");
 const permitted=new Set(RAAS_METRIC_CATALOG[stage].flatMap(c=>c.metrics.map(m=>m.id)));
 const selected=trial.drug?.trim()&&trial.indication?.trim()?
  feed.records.filter(r=>r.nctId===trial.nctId&&same(r.ticker,trial.ticker)&&
   same(r.drug,trial.drug||"")&&same(r.indication,trial.indication||"")&&r.stage===stage):[];
 const grades=selected.map(r=>provisionalReviewedGrade({
  nctId:r.nctId,ticker:r.ticker,drug:r.drug,indication:r.indication
 },stage,r,feed.sourceAsOf));
 if(grades.some(g=>g===null))throw Error("RAAS_REVIEWED_SCORE_INVALID_SOURCE");
 const valid=grades.filter((g):g is RaasProvisionalReviewedGrade=>g!==null);
 const ids=new Set(valid.map(g=>g.metricId));
 if(valid.length!==ids.size||valid.some(g=>!permitted.has(g.metricId)))
  throw Error("RAAS_REVIEWED_SCORE_DUPLICATE_OR_WRONG_STAGE");
 const independentReviewedCount=valid.filter(g=>g.reviewClass==="INDEPENDENT_REVIEW").length;
 const aiCrosscheckedCount=valid.filter(g=>g.reviewClass==="AI_SOURCE_CROSSCHECKED").length;
 const diagnostic=provisionalStageCoverage(stage,valid);
 if(diagnostic.rejected.length)throw Error("RAAS_REVIEWED_SCORE_INVALID_GRADE");
 return {nctId:trial.nctId,ticker:trial.ticker,stage,
  reviewedCount:valid.length,independentReviewedCount,aiCrosscheckedCount,
  missingMetricIds:[...permitted].filter(id=>!ids.has(id)),
  weightedCoveragePercent:diagnostic.weightCoveredPercent,
  observedMean:diagnostic.observedComponentMean,
  fullResearchScore:stageVerified&&independentReviewedCount===30?
   diagnostic.fullyCoveredProvisionalScore:null,
  approvedOverallScore:null,
  type:"UNVALIDATED_REVIEWED_RESEARCH_SCORE_NOT_FDA_PROBABILITY",
  grades:valid};
}
/** Surface exact-NCT stage-specific research reviews even before readout stage is
 * independently established. Never auto-classify TOP/BOTTOM or promote an observed
 * reviewed-only mean to an approved overall RAAS score.
 * Fail closed for one NCT used by multiple drug/indication programs.
 */
/** Resolve one unambiguous recorded therapy/indication for an NCT review.
 * This is a stage-specific *research identity*, not verified TOP/BOTTOM.
 */
export function uniquelyReviewedUnverifiedProgram(
 trial:{nctId:string;ticker:string},stage:RaasStage,
 feed:ReviewedMetricFeed=savedReviews
):{nctId:string;ticker:string;drug:string;indication:string}|null{
 if(!/^NCT\d{8}$/.test(trial.nctId)||!trial.ticker?.trim()||
  !allowed.has(stage))return null;
 const candidates=feed.records.filter(r=>r.nctId===trial.nctId&&
  same(r.ticker,trial.ticker)&&r.stage===stage);
 if(!candidates.length)return null;
 const programs=new Set(candidates.map(r=>JSON.stringify([norm(r.drug),norm(r.indication)])));
 if(programs.size!==1)return null;
 const first=candidates[0];
 return {nctId:trial.nctId,ticker:trial.ticker,
  drug:first.drug,indication:first.indication};
}
export function stageResearchReviewsForUnverifiedTrial(
 trial:{nctId:string;ticker:string},stage:RaasStage,
 feed:ReviewedMetricFeed=savedReviews
):ReviewedTrialCandidate|null{
 const program=uniquelyReviewedUnverifiedProgram(trial,stage,feed);
 return program?fullReviewedTrialCandidate(program,stage,false,feed):null;
}
