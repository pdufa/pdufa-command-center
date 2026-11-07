import {topOnlyReport,topOnlySummary} from "../../../lib/top-only-completion";
import history from "../../../data/topOnlyResearchHistory20261107.json";
import historyIncrement from "../../../data/topOnlyHistoryIncrement20261107.json";
export const dynamic="force-dynamic";
export const maxDuration=60;
export async function GET(request:Request){
 const u=new URL(request.url),id=u.searchParams.get("nctId"),format=u.searchParams.get("format");
 if(id&&!/^NCT\d{8}$/.test(id)||format&&!["csv","metrics","json"].includes(format))return Response.json({error:"Use an exact TOP NCT and format=json|csv|metrics"},{status:400});
 const report=topOnlyReport(),rows=report.trials.filter(t=>!id||t.nctId===id);
 if(id&&!rows.length)return Response.json({error:"NCT is outside the frozen TOP-only scope"},{status:404});
 const quote=(v:unknown)=>{let s=String(v??"");if(/^[=+@-]/.test(s))s="'"+s;return '"'+s.replaceAll('"','""')+'"';};
 if(format==="csv")return new Response('\uFEFF'+[report.headers,...rows.map(t=>t.fields.map(f=>f.exportValue))].map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n',{headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store"}});
 if(format==="metrics"){
  const headers=["NCT","Metric","Name","State","Score","Original weight","Active clinical weight","Evidence","Benchmark","Assessed at","Blocker"];
  return new Response('\uFEFF'+[headers,...rows.flatMap(t=>t.metrics.map(m=>[t.nctId,m.id,m.name,m.state,m.score,m.originalWeightPercent,m.activeClinicalWeightPercent,m.sourceUrl,m.benchmarkSourceUrl,m.assessedAt,m.blocker]))].map(r=>r.map(quote).join(',')).join('\r\n')+'\r\n',{headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store"}});
 }
 const {trials,headers,...summary}=report;
 return Response.json({...summary,rows:rows.map(topOnlySummary),...(id?{trial:rows[0],history:[...history.records,...historyIncrement.records].filter(r=>r.nctId===id)}:{}),notes:["All190 fields accounted for means a sourced value or explicit missing/inapplicable/pending status, not190 verified facts.","Thirty metric dispositions are evaluated; the existing active clinical model uses five equal weights. A full30-metric score requires30 supported grades under the unchanged legacy formula.","No BOTTOM, Pipeline or other spreadsheet membership/data/formula/history is modified."]},{headers:{"Cache-Control":"no-store"}});
}
