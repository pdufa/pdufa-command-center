import {phaseFirstReport} from "../../../lib/phase-first-report";
export const dynamic="force-dynamic";
export const maxDuration=60;

export async function GET(request:Request){
 const u=new URL(request.url),scope=u.searchParams.get("scope")??"alkermes";
 if(!["alkermes","axsome","sinovac","census"].includes(scope))
   return Response.json({error:"Use scope=alkermes, axsome, sinovac or census"},{status:400});
 const report=phaseFirstReport(scope as "alkermes"|"axsome"|"sinovac"|"census");
 const id=u.searchParams.get("trialId");
 if(id&&!/^(NCT|ISRCTN)\d{8}$/.test(id))
   return Response.json({error:"Invalid exact trial identifier"},{status:400});
 const trials=id?report.trials.filter(t=>t.trialId===id):report.trials;
 if(id&&!trials.length)
   return Response.json({error:"Trial not in selected source snapshot"},{status:404});
 // Active API publishes only identity, phase and source-evidence coverage;
 // historical score/rating/forecast ledgers are not imported into this path.
 const safe=(t:typeof trials[number],detailed:boolean)=>({
  trialId:t.trialId,nctId:t.nctId,ticker:t.ticker,title:t.title,sponsor:t.sponsor,
  drug:t.drug,indication:t.indication,protocol:t.protocol,phase:t.phase,
  status:t.status,programId:t.programId,programPhase:t.programPhase,
  programSourceUrl:t.programSourceUrl,
  start:t.start,phaseEntryDate:t.phaseEntryDate,phaseEntryNote:t.phaseEntryNote,
  sourceUrl:t.sourceUrl,sourceDate:t.sourceDate,retrievedAt:t.retrievedAt,
  regulatoryContext:t.regulatoryContext,
  modelVersion:t.modelVersion,evidenceCounts:t.evidenceCounts,
  evidenceCompleteness:t.evidenceCompleteness,
  missingExpected:detailed?t.missingExpected:[],
  notYetExpected:detailed?t.notYetExpected:[],
  pending:detailed?t.pending:[],
  evidence:detailed?t.evidence:[],
  pipeline:t.pipeline
 });
 if(u.searchParams.get("format")==="csv"){
  const headers=["Trial","NCT","Sponsor","Drug","Indication","Verified phase","Status",
    "Program phase","Available source items","Missing expected","Pending",
    "Not yet expected","Not applicable","Conflicting","Original source URL",
    "Source date","Evidence model version"];
  const escape=(v:unknown)=>{let s=v==null?"":String(v);if(/^[=+@-]/.test(s))s="'"+s;return '"'+s.replace(/"/g,'""')+'"';};
  const rows=trials.map(t=>[t.trialId,t.nctId,t.sponsor,t.drug,t.indication,t.phase.label,
   t.status,t.programPhase,t.evidenceCounts.AVAILABLE,t.evidenceCounts.MISSING,
   t.evidenceCounts.PENDING,t.evidenceCounts["NOT YET EXPECTED"],
   t.evidenceCounts["NOT APPLICABLE"],t.evidenceCounts.CONFLICTING,
   t.sourceUrl,t.sourceDate,t.modelVersion]);
  return new Response("\uFEFF"+[headers,...rows].map(row=>row.map(escape).join(",")).join("\r\n")+"\r\n",{
   headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store"}});
 }
 const output=trials.map(t=>safe(t,Boolean(id)));
 return Response.json({...report,
  detailMode:id?"EXACT_TRIAL":"SUMMARY_LOAD_DETAILS_BY_TRIAL_ID",
  trials:output},{headers:{"Cache-Control":"no-store"}});
}
