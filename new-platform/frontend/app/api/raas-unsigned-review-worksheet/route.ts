/** Download a fillable reviewer worksheet for one exact NCT and ticker.
 * Source facts and provisional research scores are preserved for context;
 * the editable columns are blank. This route does not accept submissions
 * and cannot sign off metric grades or FDA probabilities.
 */
import registry from "../../../public/raas-registry-evidence-index.json";
import {buildTrialMetricReviewDossier}
 from "../../../lib/raas-trial-metric-review-dossier";
export const dynamic="force-dynamic";
const headers=[
 "nctId","ticker","registrySourceHash","registrySnapshotAsOf","stage",
 "metricId","metricName","category","metricWeightPercent",
 "requiredEvidence","criticalRisk","registeredRegistrySource",
 "registrySourceLeads","registryNumericLeads","provisionalResearchFinding",
 "provisionalResearchBandNotApproved","provisionalSourceUrl","provisionalBenchmarkUrl",
 "reviewerStatus","reviewerProposedBandNotApproved","reviewerPrimarySourceUrl",
 "reviewerSourceDate","reviewerBenchmarkSourceUrl","reviewerBenchmarkContext",
 "reviewerObservedFinding","reviewerUncertaintyReview","reviewerCriticalRiskReview",
 "reviewerMethodNotes","externalIndependentAuthenticationRequired"
] as const;
const quote=(raw:unknown)=>{
 const str=String(raw??"");
 // Excel/Sheets input must not execute formulas from source names or user data.
 const safe=/^\s*[=+@-]/.test(str)?"'"+str:str;
 return '"'+safe.replaceAll('"','""')+'"';
};
export function GET(request:Request){
 const {searchParams}=new URL(request.url);
 const nctId=searchParams.get("nctId")||"";
 const ticker=searchParams.get("ticker")||"";
 if(!/^NCT\d{8}$/.test(nctId)||!/^[A-Za-z0-9.\-]{1,20}$/.test(ticker))
  return Response.json({error:"INVALID_EXACT_TRIAL_IDENTITY"},{status:400});
 const docket=buildTrialMetricReviewDossier(registry,nctId,ticker);
 if(!docket)return Response.json({error:"EXACT_NCT_TICKER_NOT_IN_RESEARCH_SNAPSHOT"},
  {status:404});
 const rows=(["pre","post"] as const).flatMap(stage=>
  docket.perStage[stage].categories.flatMap(category=>
   category.metrics.map(metric=>[
    nctId,ticker,docket.trial.sourceHash,docket.registrySnapshotAsOf,stage,
    metric.metricId,metric.name,category.name,metric.metricWeightPercent,
    metric.requiredEvidence,metric.criticalRisk,docket.trial.sourceUrl,
    metric.registryLeadCount,metric.registryRawNumericCount,
    metric.provisionalReview?.finding??"",
    metric.provisionalReview?.researchBand??"",
    metric.provisionalReview?.sourceUrl??"",
    metric.provisionalReview?.benchmarkSourceUrl??"",
    "NOT_STARTED","","","","","","","","","",
    "EXTERNAL_AUTHENTICATION_REQUIRED"
   ])));
 if(rows.length!==60||rows.some(row=>row.length!==headers.length))
  throw Error("RAAS_REVIEW_WORKSHEET_COLUMN_PARITY");
 const csv="\uFEFF"+headers.join(",")+"\r\n"+
  rows.map(row=>row.map(quote).join(",")).join("\r\n")+"\r\n";
 return new Response(csv,{status:200,headers:{
  "Content-Type":"text/csv; charset=utf-8",
  "Content-Disposition":'attachment; filename="raas-unsigned-review-'+nctId+'.csv"',
  "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"
 }});
}
