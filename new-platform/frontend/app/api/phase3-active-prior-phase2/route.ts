import research from "../../../data/phase3PreDataOfficialResearch.json";
import {activePhase3Cohorts} from "../../../lib/phase3-active-cohorts";
import {sourceObservation} from "../../../lib/phase3-universal-questions";

export const dynamic="force-dynamic";
const ids=new Set([...activePhase3Cohorts.pre,...activePhase3Cohorts.post].map(x=>x.nctId));
const records=new Map(research.records.map(x=>[x.nctId,x] as const));
const csvCell=(x:unknown)=>{
 let s=x==null?"":String(x).replace(/[\r\n]+/g," ");
 if(/^[=+@-]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
const csvRow=(row:unknown[])=>row.map(csvCell).join(",");

/** Candidate predecessor records are leads to validate, not proof of program equivalence. */
export async function GET(request:Request){
 if(ids.size!==258||activePhase3Cohorts.pre.length!==235||
  activePhase3Cohorts.post.length!==23||research.records.length!==253||
  records.size!==253||research.counts.candidates!==253||
  [...records.keys()].some(x=>!ids.has(x))){
  return Response.json({error:"Active predecessor source integrity failed"},{status:503});
 }
 const rows=[...activePhase3Cohorts.pre.map(x=>({...x,sheet:"TOP" as const})),
 ...activePhase3Cohorts.post.map(x=>({...x,sheet:"BOTTOM" as const}))].map(trial=>{
  const source=records.get(trial.nctId);
  const prior=source?.priorPhase2?.matches||[];
  const posted=prior.filter(p=>p.hasResults&&p.registeredResults);
  const measured=prior.flatMap(p=>(p.registeredResults?.primary||[]).flatMap(q=>
   (q.analyses||[]).filter(a=>a.pValue!==null&&a.pValue!==undefined&&a.pValue!=="")
    .map(a=>({priorNctId:p.nctId,endpoint:q.title,pValue:String(a.pValue),modifier:a.pValueModifier||""}))));
  return {
   nctId:trial.nctId,ticker:trial.ticker,sheet:trial.sheet,
   sourceState:source?.sourceState||"NOT_IN_PRIOR_REGISTRY_SNAPSHOT",
   leadState:prior.length?"CANDIDATE_NEEDS_INDEPENDENT_MATCH_VALIDATION":"NO_SAVED_CANDIDATE",
   candidatePriorStudies:prior.map(p=>({
    nctId:p.nctId,phase:p.phase,status:p.status,trialTitle:p.title,
    resultsPosted:!!p.hasResults,primaryOutcomeCount:p.registeredResults?.primary?.length||0,
    enrollment:p.enrollment,
    sourceUrl:"https://clinicaltrials.gov/study/"+p.nctId
   })),
   postedPriorStudies:posted.length,reportedStatisticalTests:measured,
   priorEfficacyEndpointDocumented:!!sourceObservation(trial.nctId,16),
   priorLongTermOutcomeDocumented:!!sourceObservation(trial.nctId,21),
   crosswalkReview:"Candidate drug/condition identity from saved registry search only; prior population, dose, comparator, efficacy effect size, significance and directional meaning not independently adjudicated."
  };
 });
 const totals={
  activeTrials:rows.length,top:activePhase3Cohorts.pre.length,bottom:activePhase3Cohorts.post.length,
  exactNctUnique:new Set(rows.map(r=>r.nctId)).size,
  candidatePredecessorTrialCount:rows.filter(r=>r.candidatePriorStudies.length>0).length,
  candidatePriorStudyRows:rows.reduce((n,r)=>n+r.candidatePriorStudies.length,0),
  priorPostedResultsTrials:rows.filter(r=>r.postedPriorStudies>0).length,
  priorPrimaryPValueTrials:rows.filter(r=>r.reportedStatisticalTests.length>0).length,
  registeredPriorOutcomeSlots:rows.filter(r=>r.priorEfficacyEndpointDocumented).length,
  registeredExtendedFollowUpSlots:rows.filter(r=>r.priorLongTermOutcomeDocumented).length
 };
 if(totals.activeTrials!==258||totals.exactNctUnique!==258||
  totals.candidatePredecessorTrialCount!==46||totals.candidatePriorStudyRows!==67||
  totals.priorPostedResultsTrials!==20||totals.priorPrimaryPValueTrials!==13){
  return Response.json({error:"Prior Phase 2 research summary reconciliation failed"},{status:503});
 }
 const query=new URL(request.url).searchParams;
 if(query.get("format")==="csv"){
  const headers=["NCT","Ticker","Sheet","Source state","Candidate lead state",
    "Candidate Phase 2 study IDs","Posted prior results count","Prior tests reported",
    "Q16 evidence documented","Q21 extended outcome documented","Prior registry URLs"];
  const lines=[csvRow(headers),...rows.map(r=>csvRow([
   r.nctId,r.ticker,r.sheet,r.sourceState,r.leadState,
   r.candidatePriorStudies.map(p=>p.nctId).join(" | "),r.postedPriorStudies,
   r.reportedStatisticalTests.map(p=>p.priorNctId+" "+p.modifier+"p="+p.pValue).join(" | "),
   r.priorEfficacyEndpointDocumented,r.priorLongTermOutcomeDocumented,
   r.candidatePriorStudies.map(p=>p.sourceUrl).join(" | ")
  ]))];
  if(lines.length!==259)return Response.json({error:"Phase 2 CSV integrity failed"},{status:503});
  return new Response("\uFEFF"+lines.join("\r\n")+"\r\n",{
   headers:{"Content-Type":"text/csv; charset=utf-8",
    "Content-Disposition":'attachment; filename="Active-258-Phase3-Candidate-Prior-Phase2-Evidence-2026-11-06.csv"',
    "Cache-Control":"no-store"}
  });
 }
 if(query.has("format")&&query.get("format")!=="json")
  return Response.json({error:"Use format=json or csv"},{status:400});
 return Response.json({
  asOf:research.asOf,scope:"Predecessor same-drug/condition registry candidate leads, not independently verified Phase 2 efficacy, RAAS or FDA/PDUFA readiness",
  totals,rows
 },{headers:{"Cache-Control":"no-store"}});
}
