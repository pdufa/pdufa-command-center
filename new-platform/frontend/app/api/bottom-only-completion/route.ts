import {bottomOnlyReport,bottomOnlySummary} from "../../../lib/bottom-only-completion";
import originalHistory from "../../../data/bottomOnlyResearchHistory20261107.json";
import scoreHistory from "../../../data/bottomOnlyScoreHistory20261107.json";
export const dynamic="force-dynamic";
export const maxDuration=60;
const safe=(v:unknown)=>{
 let s=String(v??"");
 if(/^[=+@-]/.test(s))s="'"+s;
 return '"'+s.replaceAll('"','""')+'"';
};
const csv=(rows:unknown[][],name:string)=>new Response("\uFEFF"+rows.map(r=>r.map(safe).join(",")).join("\r\n")+"\r\n",{
 headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store",
  "Content-Disposition":'attachment; filename="'+name+'"'}
});
export async function GET(request:Request){
 try{
  const url=new URL(request.url),id=url.searchParams.get("nctId"),format=url.searchParams.get("format")||"json";
  if(id&&!/^NCT\d{8}$/.test(id)||!["json","csv","metrics","facts","rating-evidence"].includes(format))
   return Response.json({error:"Use a valid BOTTOM NCT or format json|csv|metrics|facts|rating-evidence"},{status:400});
  const report=bottomOnlyReport(),trials=report.trials.filter(t=>!id||t.nctId===id);
  if(id&&trials.length!==1)return Response.json({error:"NCT is not in the frozen BOTTOM spreadsheet"},{status:404});
  if(format==="csv")return csv([report.headers,...trials.map(t=>t.fields.map(f=>f.exportValue))],"bottom-only-190.csv");
  if(format==="metrics")return csv([
   ["NCT","Metric","Name","Active","Grade","Original weight","Active clinical weight","State","Finding","Source","Benchmark","Missing evidence"],
   ...trials.flatMap(t=>t.metrics.map(m=>[t.nctId,m.id,m.name,m.activeInClinicalModel,m.score,m.originalWeightPercent,
    m.activeClinicalWeightPercent,m.state,m.finding,m.sourceUrl,m.benchmarkSourceUrl,m.blocker]))
  ],"bottom-only-metric-dispositions.csv");
  if(format==="rating-evidence")return csv([
   ["NCT","Ticker","Factor ID","Factor","Clinical grade","Rating readiness","Source count","Question","Source date","Source URL","Evidence class","Observed evidence","Critical limitation","Benchmark needed"],
   ...trials.flatMap(t=>t.clinicalFactors.flatMap(f=>f.reviewEvidence.length?
    f.reviewEvidence.map(e=>[t.nctId,t.ticker,f.id,f.name,f.grade,f.ratingReadiness,f.reviewEvidenceCount,e.question,e.sourceDate,e.sourceUrl,e.classification,e.evidence,e.criticalLimit,f.requiredEvidence]):
    [[t.nctId,t.ticker,f.id,f.name,f.grade,f.ratingReadiness,0,"","","","NO_CURRENT_MATCH","No accepted exact-trial research evidence yet.","Not a negative finding; research or disclosure pending.",f.requiredEvidence]]))
  ],"bottom-only-115-factor-source-evidence.csv");
  if(format==="facts")return csv([
   ["NCT","Question","Classification","Evidence","Critical limitation","Source date","Source URL"],
   ...trials.flatMap(t=>t.additionalReviewedFacts.map(f=>[t.nctId,f.question,f.classification,f.evidence,f.criticalLimit,f.sourceDate,f.sourceUrl]))
  ],"bottom-only-reviewed-facts.csv");
  const {trials:all,headers,...summary}=report;
  return Response.json({...summary,rows:trials.map(bottomOnlySummary),
   ...(id?{trial:trials[0],history:[...originalHistory.records,...scoreHistory.records].filter(h=>h.nctId===id)}:{}),
   notes:[
    "190/190 accounted means observed/verified facts or explicit missing/undisclosed states, NOT 190 independently verified facts.",
    "30 metric dispositions do not mean 30 numerical grades: only the five original active clinical factors contribute to post-data clinical research scores.",
    "Results already announced are observed evidence, not pre-readout predictions; future follow-up, unpublished SAP, and regulatory filings may remain unavailable.",
    "No TOP membership, original histories, BOTTOM identities, or other scoring formulas were modified."
   ]},{headers:{"Cache-Control":"no-store"}});
 }catch(e){return Response.json({error:e instanceof Error?e.message:"BOTTOM completion source unavailable"},{status:503});}
}
