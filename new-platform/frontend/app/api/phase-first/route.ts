import {phaseFirstReport} from "../../../lib/phase-first-report";
export const dynamic="force-dynamic";
export const maxDuration=60;
export async function GET(request:Request){
 const u=new URL(request.url),scope=u.searchParams.get("scope")??"alkermes";
 if(scope!=="alkermes"&&scope!=="axsome"&&scope!=="sinovac"&&scope!=="census")return Response.json({error:"Use scope=alkermes, scope=axsome, scope=sinovac or scope=census"},{status:400});
 const report=phaseFirstReport(scope);const id=u.searchParams.get("trialId");
 if(id&&!/^(NCT|ISRCTN)\d{8}$/.test(id))return Response.json({error:"Invalid exact trial identifier"},{status:400});
 const trials=id?report.trials.filter(t=>t.trialId===id):report.trials;
 if(id&&!trials.length)return Response.json({error:"Trial not in selected source snapshot"},{status:404});
 if(u.searchParams.get("format")==="csv"){
  const headers=["Trial","NCT","Sponsor","Drug","Indication","Verified phase","Status","Program phase","Evidence completeness","FDA prediction eligibility","Available","Missing expected","Pending","Not yet expected","Not applicable","Conflicting","Source URL","Source date","Model version"];
  const escape=(v:unknown)=>{let s=v==null?"":String(v);if(/^[=+@-]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};
  const rows=trials.map(t=>[t.trialId,t.nctId,t.sponsor,t.drug,t.indication,t.phase.label,t.status,t.programPhase,
   t.evidenceCompleteness,t.fdaPrediction.status,t.evidenceCounts.AVAILABLE,t.evidenceCounts.MISSING,t.evidenceCounts.PENDING,
   t.evidenceCounts['NOT YET EXPECTED'],t.evidenceCounts['NOT APPLICABLE'],t.evidenceCounts.CONFLICTING,t.sourceUrl,t.sourceDate,t.modelVersion]);
  return new Response('\uFEFF'+[headers,...rows].map(r=>r.map(escape).join(',')).join('\r\n')+'\r\n',{headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store"}});
 }
 // Full checklists are loaded by exact identifier on expansion. Sending all
 // 762 detailed checklists would exceed the platform response-size limit.
 const output=id?trials:trials.map(t=>({...t,evidence:[],missingExpected:[],notYetExpected:[],pending:[]}));
 return Response.json({...report,detailMode:id?"EXACT_TRIAL":"SUMMARY_LOAD_DETAILS_BY_TRIAL_ID",trials:output},{headers:{"Cache-Control":"no-store"}});
}
