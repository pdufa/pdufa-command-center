import {activePhase3Cohorts} from "../../../lib/phase3-active-cohorts";
import {phaseFirstReport} from "../../../lib/phase-first-report";

export const dynamic="force-dynamic";
export const maxDuration=60;

/** Read-only exact-NCT bridge: no invented RAAS, efficacy or approval scores. */
export async function GET(){
 try{
  const cohort=activePhase3Cohorts;
  const report=phaseFirstReport("census");
  const byNct=new Map(report.trials.map(t=>[t.trialId,t] as const));
  const active=[...cohort.pre,...cohort.post];
  if(report.trialCount!==762||byNct.size!==762||active.length!==258||
    active.some(r=>!byNct.has(r.nctId)))
   return Response.json({error:"Active clinical rating source identity check failed"},{status:503});
  const scores=active.map(r=>{
   const trial=byNct.get(r.nctId)!;
   const scored=trial.ratingCoverage.scored;
   const eligible=trial.ratingCoverage.eligible;
   const clinicalRating=scored>0?trial.overallRating:null;
   return {
    nctId:r.nctId,cohort:r.cohort,ticker:r.ticker,
    verifiedPhase:trial.phase.label,phaseVerified:trial.phase.verified,
    clinicalRating,clinicalRatingStatus:clinicalRating===null?"NOT_SCORED":
     scored===eligible?"FULLY_COVERED":"PARTIAL_RESEARCH_RATING",
    scoredFactors:scored,eligibleFactors:eligible,
    evidenceCompleteness:trial.evidenceCompleteness,
    raasScore:trial.raasScore,
    fdaPredictionStatus:trial.fdaPrediction.status,
    sourceDate:trial.sourceDate,modelVersion:trial.modelVersion
   };
  });
  return Response.json({
   asOf:report.asOf,trialCount:scores.length,
   clinicalRated:scores.filter(s=>s.clinicalRating!==null).length,
   approvedRaasPresent:scores.filter(s=>s.raasScore!==null).length,
   scores,
   notes:[
    "Clinical rating is a reviewed, phase-applicable research grade; partial coverage must not be confused with a complete trial grade.",
    "Evidence completeness is distinct from scientific strength and is not an FDA approval probability.",
    "Unreviewed factors and RAAS scores remain null. No prior score histories or forecast freezes are altered."
   ]
  },{headers:{"Cache-Control":"no-store"}});
 }catch(e){
  return Response.json({error:"Phase-first clinical score source unavailable"},{status:503});
 }
}
