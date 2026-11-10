import {createHash} from "node:crypto";
import {R91_POSTED_RESULTS_ROSTER,inspectR91CurrentPostedResults} from
 "../../../../lib/focus-r91-posted-results-reconciliation";

/** Source-only ClinicalTrials.gov exact-NCT original aggregate-results readback.
 * A parsed p value is source text, not verified statistical significance.
 */
export const runtime="nodejs";
export const dynamic="force-dynamic";
const H={
 "Cache-Control":"private, no-store, max-age=0",
 "X-Content-Type-Options":"nosniff"
} as const;
const MAX_BYTES=4_000_000;
function fail(status:number,error:string){
 return Response.json({error,
  independentClinicalGrades:0,
  prospectivelySignedSAPAuthenticated:false,
  medicallyVerifiedSafetyReconciliations:0,
  FDAForecast:"ABSTAIN"},{status,headers:H});
}
export async function GET(request:Request):Promise<Response>{
 const roster=R91_POSTED_RESULTS_ROSTER;
 if(!roster)return fail(503,"EXACT_FOCUS_REGISTRY_RESULTS_ROSTER_INTEGRITY_FAILED");
 const nct=new URL(request.url).searchParams.get("nct");
 if(!nct||!/^NCT\d{8}$/u.test(nct))return fail(400,"EXACT_FOCUS_NCT_REQUIRED");
 const row=roster.rows.find(r=>r.nct===nct);
 if(!row)return fail(404,"NCT_OUTSIDE_LOCKED_FOCUS_RESEARCH_ROSTER");
 const sourceUrl="https://clinicaltrials.gov/api/v2/studies/"+row.nct+"?format=json";
 try{
  const response=await fetch(sourceUrl,{method:"GET",cache:"no-store",
   redirect:"error",headers:{"Accept":"application/json"},
   signal:AbortSignal.timeout(12000)});
  if(!response.ok)return fail(502,"OFFICIAL_REGISTRY_AGGREGATE_RESULTS_UNAVAILABLE");
  const sizeHeader=Number(response.headers.get("content-length")??0);
  if(!Number.isFinite(sizeHeader)||sizeHeader>MAX_BYTES)
   return fail(502,"OFFICIAL_AGGREGATE_RESPONSE_TOO_LARGE");
  const raw=await response.text();
  if(raw.length>MAX_BYTES)return fail(502,"OFFICIAL_AGGREGATE_RESPONSE_TOO_LARGE");
  const sourceSHA256=createHash("sha256").update(raw,"utf8").digest("hex");
  const original:unknown=JSON.parse(raw);
  const checked=inspectR91CurrentPostedResults(row,original);
  if(!checked){
   // Strict schema diagnostics: only public field names/types and source
   // group ID shapes, never missing values invented or trial grades.
   const dict=(v:unknown):Record<string,unknown>=>
    v!==null&&typeof v==="object"&&!Array.isArray(v)?
      v as Record<string,unknown>:{};
   const keys=(v:unknown)=>Object.keys(dict(v));
   const array=(v:unknown):unknown[]=>Array.isArray(v)?v:[];
   const top=dict(original),p=dict(top.protocolSection),
    section=dict(top.resultsSection),
    outcomes=dict(section.outcomeMeasuresModule),
    flow=dict(section.participantFlowModule),
    adverse=dict(section.adverseEventsModule);
   const firstOutcome=dict(array(outcomes.outcomeMeasures)[0]);
   const firstClass=dict(array(firstOutcome.classes)[0]);
   const firstCat=dict(array(firstClass.categories)[0]);
   const firstAnalysis=dict(array(firstOutcome.analyses)[0]);
   const firstSerious=dict(array(adverse.seriousEvents)[0]);
   const firstStats=dict(array(firstSerious.stats)[0]);
   return Response.json({
    error:"AGGREGATE_SOURCE_IDENTITY_OR_SCHEMA_UNVERIFIED",
    diagnostic:{
     id:dict(p.identificationModule).nctId,
     hasResults:top.hasResults,
     resultKeys:keys(section),flowKeys:keys(flow),
     outcomeKeys:keys(outcomes),adverseKeys:keys(adverse),
     outcomeCount:array(outcomes.outcomeMeasures).length,
     firstOutcomeKeys:keys(firstOutcome),
     firstOutcomeType:firstOutcome.type,
     firstOutcomeGroups:array(firstOutcome.groups).slice(0,2).map(keys),
     firstMeasureKeys:keys(dict(array(firstCat.measurements)[0])),
     firstAnalysisKeys:keys(firstAnalysis),
     firstAnalysisGroupKinds:array(firstAnalysis.groups).slice(0,2).map(
      v=>typeof v==="string"?"string":keys(v).join(",")),
     flowGroupKeys:keys(dict(array(flow.groups)[0])),
     adverseGroupKeys:keys(dict(array(adverse.groups)[0])),
     seriousEventKeys:keys(firstSerious),
     firstSeriousStatsKeys:keys(firstStats)
    },
    independentClinicalGrades:0,medicallyVerifiedSafetyReconciliations:0,
    FDAForecast:"ABSTAIN"
   },{status:502,headers:H});
  }
  return Response.json({
   ...checked,
   sourceApiUrl:sourceUrl,sourceSHA256,
   originalResponseCharacters:raw.length,
   readbackAtUtc:new Date().toISOString(),
   independentClinicalGrades:0,
   medicallyVerifiedSafetyReconciliations:0,
   regulatorOutcome:"ABSTAIN" as const
  },{headers:H});
 }catch{
  return fail(502,"OFFICIAL_AGGREGATE_SOURCE_RETRIEVAL_FAILED");
 }
}
