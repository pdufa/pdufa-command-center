import {activePhase3Cohorts,type ActivePhase3Trial} from "../../../lib/phase3-active-cohorts";
export const dynamic="force-dynamic";
const safe=(v:unknown)=>{
 let s=String(v??"").replace(/[\r\n]/g," ");
 if(/^[\s]*[=+@-]/.test(s))s="'"+s;
 return '"'+s.replace(/"/g,'""')+'"';
};
export async function GET(request:Request){
 const u=new URL(request.url),view=u.searchParams.get("view")||"all";
 if(!["pre","post","all"].includes(view))return Response.json({error:"View must be pre, post or all."},{status:400});
 const cohort=activePhase3Cohorts;
 const rows:ActivePhase3Trial[]=view==="pre"?cohort.pre:view==="post"?cohort.post:[...cohort.pre,...cohort.post];
 if(u.searchParams.get("format")==="csv"){
  const headers=["NCT","Ticker","Company","Drug","Indication","Registry status","Pre/Post","Source classification",
   "Outcome","Readout verification","Readout date","Readout source","Registry source","Source snapshot date","Correction applied"];
  const data=rows.map(r=>[r.nctId,r.ticker,r.company,r.drug||r.registeredInterventions||"",
   r.indication||"",r.registryStatus,r.cohort,r.classificationCode,r.readoutOutcome,r.evidenceBasis,
   r.readoutSourceDate||"",r.readoutEvidenceUrl||"",r.registrySourceUrl,cohort.sourceAsOf,
   r.correctionApplied?"YES":"NO"]);
  return new Response("\uFEFF"+[headers,...data].map(r=>r.map(safe).join(",")).join("\r\n")+"\r\n",
   {headers:{"Content-Type":"text/csv; charset=utf-8","Cache-Control":"no-store",
    "Content-Disposition":'attachment; filename="pdufa-active-phase3-'+view+'-2026-11-06.csv"'}});
 }
 return Response.json({
  asOf:cohort.asOf,sourceAsOf:cohort.sourceAsOf,source:"762 exact-NCT Phase 3 census reconciled to issuer and registry evidence",
  totalPool:cohort.totalPool,activeTotal:cohort.activeTotal,
  counts:cohort.counts,promotedNcts:cohort.promotedNcts,
  view,trialCount:rows.length,rows,
  notes:["Pre-data means no verified public results in this dated evidence snapshot, not proof that results are unavailable.",
   "Registry-posted results and issuer announcements are identified separately.",
   "501 completed/terminated/withdrawn and 3 unknown trials are retained outside these two active-study sheets.",
   "These are active-study classifications, not verified FDA/PDUFA Pipeline eligibility. Historical RAAS grades are unchanged."]},
  {headers:{"Cache-Control":"no-store"}});
}
