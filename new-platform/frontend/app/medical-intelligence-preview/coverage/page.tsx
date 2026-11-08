import Link from "next/link";
import type {Metadata} from "next";
import type {CSSProperties} from "react";
import focus from "../../../data/p3PostDataActive.json";
import {reconcileRegistryBatch,type RegistryBatchAudit} from "../../../lib/medical-intelligence-preview";
import {findingsForNct,REVIEW_AS_OF} from "../../../lib/medical-intelligence-reviewed-findings";
import {parseRegistryResults} from "../../../lib/medical-intelligence-registry-results";

export const metadata:Metadata={
 title:"FOCUS Registry Coverage — Deep Medical Intelligence | PDUFA",
 description:"Read-only, exact-NCT, batch registry inventory of all FOCUS trials."
};
export const dynamic="force-dynamic";
const slate="#16372f",muted="#586961",line="#cbdad0",teal="#005e52";
const panel:CSSProperties={background:"#fff",border:"1px solid "+line,borderRadius:11,padding:17,marginTop:16};
const ids=focus.records.map(r=>r.nct);
const sourceUrl="https://clinicaltrials.gov/api/v2/studies";
type PostedCoverage={comparisons:number;reportedPValues:number;groups:number};
async function registryAudit():Promise<{data:RegistryBatchAudit|null;postedCoverage:Record<string,PostedCoverage>|null;error:string|null}>{
 try{
  const params=new URLSearchParams({"filter.ids":ids.join(","),pageSize:"100",format:"json"});
  const response=await fetch(sourceUrl+"?"+params.toString(),{
    headers:{Accept:"application/json"},next:{revalidate:21600},signal:AbortSignal.timeout(14000)
  });
  if(!response.ok)throw Error("ClinicalTrials.gov returned HTTP "+response.status);
  const body=await response.json();
  const data=reconcileRegistryBatch(body,ids);
  const postedCoverage:Record<string,PostedCoverage>={};
  for(const item of Array.isArray(body.studies)?body.studies:[]){
    const nct=item?.protocolSection?.identificationModule?.nctId;
    if(typeof nct!=="string"||!data.byNct[nct]||postedCoverage[nct])continue;
    try{
      const parsed=parseRegistryResults(item,nct);
      postedCoverage[nct]={
        comparisons:parsed.outcomes.reduce((n,o)=>n+o.analyses.length,0),
        reportedPValues:parsed.outcomes.reduce((n,o)=>n+o.analyses.filter(a=>a.reportedPValue!==null).length,0),
        groups:parsed.events.length
      };
    }catch{ /* A malformed result is not an FDA or trial failure. */ }
  }
  return {data,postedCoverage,error:null};
 }catch(e){return {data:null,postedCoverage:null,error:e instanceof Error?e.message:"Registry retrieval failed"};}
}
export default async function RegistryCoveragePage(){
 const {data,postedCoverage,error}=await registryAudit();
 const reportedPValues=postedCoverage?Object.values(postedCoverage).reduce((n,x)=>n+x.reportedPValues,0):null;
 const resolved=data?Object.keys(data.byNct).length:0;
 const posted=data?Object.values(data.byNct).filter(s=>s.resultsPosted).length:0;
 const reviewed=focus.records.filter(r=>findingsForNct(r.nct).length>0).length;
 const queue=[...focus.records].sort((a,b)=>(a.recordedPdufaDate||"9999").localeCompare(b.recordedPdufaDate||"9999")||a.nct.localeCompare(b.nct));
 const td:CSSProperties={padding:"10px",borderBottom:"1px solid "+line,verticalAlign:"top"};
 const th:CSSProperties={...td,textAlign:"left",background:"#eef6f0",fontSize:13};
 return <main style={{maxWidth:1390,margin:"26px auto",padding:"0 16px 42px",fontFamily:"system-ui,sans-serif",color:slate}}>
  <div style={{fontSize:12,fontWeight:750,color:teal,letterSpacing:1}}>POOL → FOCUS → INDEPENDENT INTELLIGENCE</div>
  <h1 style={{marginBottom:5}}>All-FOCUS registry coverage</h1>
  <p style={{lineHeight:1.55}}>One batch request checks all {ids.length} exact FOCUS NCT identifiers against ClinicalTrials.gov. This is the <strong>registry evidence inventory</strong>, not a completed FDA review or approval prediction.</p>
  <p style={{fontSize:13,color:muted}}>FOCUS snapshot {focus.asOf}; reviewed-source ledger {REVIEW_AS_OF}. ClinicalTrials.gov is a public registry that does not disclose all FDA review, clinical study report or manufacturing records.</p>
  <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(175px,1fr))",gap:12,marginTop:17}}>
   {[
    {label:"FOCUS NCTs requested",value:ids.length},
    {label:"Registry exact-ID matches",value:data?resolved:"Unavailable"},
    {label:"Registry results sections",value:data?posted:"Unavailable"},
    {label:"With curated source findings",value:reviewed},
    {label:"Registry p-values explicitly posted",value:reportedPValues??"Unavailable"}
   ].map(x=><div style={panel} key={x.label}><div style={{fontSize:12,color:muted}}>{x.label}</div><div style={{fontSize:27,fontWeight:750,marginTop:6}}>{x.value}</div></div>)}
  </div>
  {error&&<section role="status" style={{...panel,borderColor:"#c69586",color:"#8d352e"}}>
   <strong>Batch registry lookup unavailable</strong><p style={{fontSize:14}}>{error}. Source records remain in the FOCUS snapshot; no trial is classified as failed or absent because the lookup failed.</p>
  </section>}
  {data&&((data.missingNcts.length>0)||(data.unexpectedNcts.length>0)||(data.duplicateNcts.length>0))&&
   <section style={{...panel,borderColor:"#c69586"}}>
    <h2 style={{marginTop:0,fontSize:18}}>Reconciliation exceptions</h2>
    <p style={{fontSize:14}}>Missing exact NCT matches: {data.missingNcts.length}; unexpected/malformed IDs: {data.unexpectedNcts.length}; duplicate IDs: {data.duplicateNcts.length}. These require review and are not evidence of trial failure.</p>
    {data.missingNcts.length>0&&<div style={{fontSize:13}}>Unresolved: {data.missingNcts.join(", ")}</div>}
   </section>}
  <section style={panel}>
   <h2 style={{marginTop:0,fontSize:19}}>Phase-first trial inventory · {queue.length} FOCUS records</h2>
   <p style={{fontSize:13,color:muted}}>Clinical registry content is checked live where available; study phases and results-posting are kept separate from scientific success, FDA approval, and application-level risks. The published goal date is only the FOCUS-recorded date until independently confirmed.</p>
   <div style={{overflowX:"auto"}}>
    <table style={{width:"100%",minWidth:1120,borderCollapse:"collapse",fontSize:13}}>
     <thead><tr>
      <th style={th}>Candidate / NCT</th><th style={th}>Condition</th><th style={th}>Phase / study status</th>
      <th style={th}>Trial outcomes</th><th style={th}>Registry statistical results</th><th style={th}>Recorded goal</th><th style={th}>Independent findings</th>
     </tr></thead>
     <tbody>{queue.map(r=>{
      const study=data?.byNct[r.nct],found=findingsForNct(r.nct);
      return <tr key={r.nct}>
       <td style={td}><strong>{r.ticker}</strong><div>{r.company}</div><Link href={"/medical-intelligence-preview?nct="+r.nct}>{r.nct} · open dossier</Link></td>
       <td style={td}>{study?.conditions?.join("; ")||"Not independently retrieved"}</td>
       <td style={td}>{study?(study.phases.join(", ")||"No phase recorded"):"No source match"}<div style={{color:muted,marginTop:5}}>{study?.status||"Unavailable"}</div></td>
       <td style={td}>{study?(study.resultsPosted?"Results module present; still needs scientific review":"No public results module found; check publications and sponsor"):"Not retrieved"}<div style={{color:muted,marginTop:5}}>{study?.primaryEndpoints.length??0} registry primary endpoint(s) described</div></td>
       <td style={td}>{postedCoverage?.[r.nct] ? <><strong>{postedCoverage[r.nct].reportedPValues} reported p-value(s)</strong><div style={{color:muted,marginTop:5}}>{postedCoverage[r.nct].comparisons} registered analysis comparison(s) · {postedCoverage[r.nct].groups} AE group(s)</div></>:"Not retrieved"}</td>
       <td style={td}>{r.recordedPdufaDate||"Not recorded"}</td>
       <td style={td}>{found.length?found.length+" published, sourced finding(s); review incomplete":"No curated review yet"}</td>
      </tr>;
     })}</tbody>
    </table>
   </div>
  </section>
  <section style={panel}>
   <h2 style={{marginTop:0,fontSize:18}}>What this scan does not establish</h2>
   <p style={{lineHeight:1.6,fontSize:14}}>Counts of posted p-values are not counts of significant results, passed endpoints or FDA-accepted analyses. A trial with zero posted p-values may have numerical results in a paper, sponsor release or submission. Registry outcomes, endpoint declarations and company readouts are not FDA adjudications. Clinical data can be absent from the registry but published elsewhere. Manufacturing/CMC, inspections, confidential FDA correspondence, and application completeness require separate source investigations. A comprehensive FOCUS decision may aggregate several related NCT trials into one application-level dossier.</p>
   <p style={{marginBottom:0,fontSize:13}}><a style={{color:teal}} href="https://clinicaltrials.gov/data-api/api" target="_blank" rel="noopener noreferrer">ClinicalTrials.gov official API documentation</a> · <Link href="/medical-intelligence-preview">Return to independent dossiers</Link></p>
  </section>
 </main>;
}
