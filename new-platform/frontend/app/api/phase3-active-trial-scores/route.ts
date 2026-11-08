import {activePhase3Cohorts} from "../../../lib/phase3-active-cohorts";
import {phaseFirstReport} from "../../../lib/phase-first-report";
export const dynamic="force-dynamic";
export const maxDuration=60;

/** Legacy URL kept to avoid breaking integrations, but now returns only
 * source coverage and independent phase verification, NOT scored ratings.
 * No archived inputs, FDA probability or reliability score is used.
 */
export async function GET(){
 try{
  const cohort=activePhase3Cohorts,report=phaseFirstReport("census");
  const byNct=new Map(report.trials.map(t=>[t.trialId,t] as const));
  const active=[...cohort.pre,...cohort.post];
  if(report.trialCount!==762||byNct.size!==762||active.length!==258||
     active.some(r=>!byNct.has(r.nctId)))
    return Response.json({error:"Phase 3 source evidence identity check failed"},{status:503});
  const trials=active.map(r=>{
   const study=byNct.get(r.nctId)!;
   return {nctId:r.nctId,cohort:r.cohort,ticker:r.ticker,
    verifiedPhase:study.phase.label,phaseVerified:study.phase.verified,
    evidenceCompleteness:study.evidenceCompleteness,
    evidenceCounts:study.evidenceCounts,sourceDate:study.sourceDate,
    modelVersion:study.modelVersion,sourceUrl:study.sourceUrl,
    clinicalAssessment:"NOT_INDEPENDENTLY_ADJUDICATED",
    fdaPredictionStatus:"ABSTAIN",certaintyStatus:"NOT_VALIDATED",
    approvalProbability:null,crlProbability:null,reviewDelayProbability:null};
  });
  return Response.json({asOf:report.asOf,trialCount:trials.length,trials,
    sourceOnly:true,
    notes:["Active trial evidence coverage is not a scientific score.",
           "No historical scoring system or uncalibrated FDA probability is used.",
           "Historical trial research is preserved in read-only archives."]},{
      headers:{"Cache-Control":"no-store"}});
 }catch{
  return Response.json({error:"Phase 3 source evidence unavailable"},{status:503});
 }
}
