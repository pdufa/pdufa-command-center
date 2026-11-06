import ledger from "../../../public/phase3-unified-classifications-2026-11-05.json";
import {auditCensus,auditPolicyRule,trialLifecycle,ENABLED_POLICY} from "../../../lib/pdufa-selected-restrictions";

export const dynamic = "force-dynamic";
export async function GET(request:Request){
 if(ledger.total!==762||ledger.rows.length!==762||new Set(ledger.rows.map(r=>r.nctId)).size!==762)
  return Response.json({error:"Phase 3 census integrity check failed"},{status:503});
 const u=new URL(request.url);
 const asOf=new Date().toISOString().slice(0,10);
 const audit=auditCensus(ledger.rows,asOf);
 if(u.searchParams.get("format")==="csv"){
  const fields=["NCT","Ticker","Registry status","Lifecycle",...ENABLED_POLICY.map(r=>r.id)];
  const safe=(s:unknown)=>{
   let v=String(s??"").replace(/[\r\n]/g," ");
   if(/^[=+@-]/.test(v))v="'"+v;
   return '"'+v.replace(/"/g,'""')+'"';
  };
  const data=ledger.rows.map(t=>[t.nctId,t.ticker,t.registryStatus,trialLifecycle(t.registryStatus),
   ...ENABLED_POLICY.map(r=>auditPolicyRule(r.id,t,asOf).status)]);
  return new Response("\uFEFF"+[fields,...data].map(r=>r.map(safe).join(",")).join("\r\n")+"\r\n",
   {headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store"}});
 }
 return Response.json({...audit,sourceCensusDate:ledger.asOf,source:"Exact-NCT 762-trial dated research census",
  policyStatus:"CONFIGURED_AUDIT_NOT_FULLY_ENFORCED",noHistoricalDeletes:true},
  {headers:{"Cache-Control":"no-store"}});
}
