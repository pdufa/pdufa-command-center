"use client";
import {useEffect,useState} from "react";
type Prior={nctId:string;title:string;sourceUrl?:string;hasResults?:boolean;resultsFirstPosted?:string;registeredResults?:{primary?:{title:string;analyses?:{pValue?:string|number|null;pValueModifier?:string}[]}[];seriousEventCount?:number;otherEventCount?:number}|null;references?:{pmid?:string;type?:string;citation?:string}[]};
type Official={nctId:string;sourceState:string;error?:string;sourceUrl?:string;registry?:{title:string;status:string;resultsFirstPosted:string;hasResults:boolean;sourceUpdated:string;primaryOutcomes?:{measure:string;timeFrame:string}[];allocation:string;masking:string;enrollment?:number;phase:string[]};priorPhase2?:{state:string;query?:string;truncated?:boolean;error?:string;matches:Prior[]}};
type Research={status?:string;asOf:string;counts?:{officialRegistryRecords:number;priorStudyQueries:number;matchedPhase2PrimaryPValues:number};records:Official[]};
function pValues(p:Prior){
 const values=(p.registeredResults?.primary||[]).flatMap(o=>(o.analyses||[])
  .filter(a=>a.pValue!==null&&a.pValue!==undefined&&a.pValue!=="")
  .map(a=>(a.pValueModifier||"")+"p="+a.pValue));
 return [...new Set(values)].slice(0,6);
}
export default function Phase3OfficialResearchEvidence({nctId}:{nctId:string}){
 const [state,setState]=useState<"loading"|"pending"|"ready"|"error">("loading");
 const [data,setData]=useState<Official|null>(null);
 const [asOf,setAsOf]=useState("");
 useEffect(()=>{
  let current=true;
  import("../data/phase3PreDataOfficialResearch.json")
   .then(mod=>{
    if(!current)return;
    const r=mod.default as unknown as Research;
    const match=r.records?.find(v=>v.nctId===nctId)||null;
    setAsOf(r.asOf||"");setData(match);
    setState(match?"ready":r.status==="PENDING_OFFICIAL_SOURCE_COLLECTION"?"pending":"error");
   }).catch(()=>{if(current)setState("error")});
  return ()=>{current=false};
 },[nctId]);
 return <section data-phase3-original-research={nctId} style={{border:"1px solid #bdd4c4",borderRadius:8,padding:10,margin:"9px 0"}}>
  <h4 style={{fontSize:13,margin:"0 0 5px"}}>Original registry and previous Phase 2 evidence</h4>
  {state==="loading"&&<p>Loading original-source research…</p>}
  {state==="pending"&&<p>Source collector has not yet published this research. Existing 30-question evidence gaps remain unchanged.</p>}
  {state==="error"&&<p>Original-source research unavailable for this exact NCT. No source or trial outcome inferred.</p>}
  {state==="ready"&&data&&<>
   <p>Retrieved {asOf||"undated"}. {data.sourceState==="ERROR"?"The source lookup failed.":"Exact trial registry identity checked."}</p>
   {data.sourceState==="ERROR"?<p>Source error: {data.error||"Unavailable"}</p>:data.registry&&<>
    <p><strong>Trial:</strong> {data.registry.title}</p>
    <p><strong>Registry:</strong> {data.registry.status}; enrollment {data.registry.enrollment??"not specified"}; allocation {data.registry.allocation||"unreported"}; masking {data.registry.masking||"unreported"}.</p>
    <p><strong>Recorded primary outcome:</strong> {data.registry.primaryOutcomes?.[0]?.measure||"unavailable"}; timeframe {data.registry.primaryOutcomes?.[0]?.timeFrame||"unspecified"}.</p>
    {data.registry.hasResults&&<p style={{fontWeight:750,color:"#9b332b"}}>Registry has posted results, with recorded date {data.registry.resultsFirstPosted||"unspecified"}. This study must not be presumed unreleased. An issuer-readout check is still separate.</p>}
    <a href={data.sourceUrl||"https://clinicaltrials.gov/study/"+nctId} target="_blank" rel="noopener noreferrer">Official trial record</a>
   </>}
   <details style={{marginTop:8}}><summary style={{cursor:"pointer",fontWeight:650}}>Earlier Phase 2 research leads ({data.priorPhase2?.matches?.length||0})</summary>
    <p>These links require a single registered active drug and matching disease name. They are preliminary source leads, not evidence of identical dose, population, efficacy, or an FDA decision.</p>
    {data.priorPhase2?.state==="ERROR"&&<p>Earlier-trial search failed: {data.priorPhase2.error||"Unavailable"}.</p>}
    {data.priorPhase2?.truncated&&<p>Search returned more than one page; the candidate set may be incomplete.</p>}
    {(data.priorPhase2?.matches||[]).length===0&&<p>No conservatively matched earlier Phase 2 registration with usable evidence was retrieved.</p>}
    {(data.priorPhase2?.matches||[]).slice(0,10).map(p=><div key={p.nctId} style={{borderTop:"1px solid #d7e5da",padding:"7px 0"}}>
     <strong><a href={p.sourceUrl||"https://clinicaltrials.gov/study/"+p.nctId} target="_blank" rel="noopener noreferrer">{p.nctId}</a></strong>{" · "}{p.title}
     <p>Registry results {p.registeredResults?"posted":"not available"}{p.resultsFirstPosted?", posted "+p.resultsFirstPosted:""}.
      {p.registeredResults?" Named serious adverse-event categories: "+p.registeredResults.seriousEventCount+".":""}</p>
     {pValues(p).length>0&&<p><strong>Reported primary-analysis p-values:</strong> {pValues(p).join("; ")}. Values alone do not establish favorable direction or clinical benefit.</p>}
     {(p.references||[]).filter(x=>x.pmid).slice(0,3).map(x=><p key={x.pmid}><a href={"https://pubmed.ncbi.nlm.nih.gov/"+x.pmid+"/"} target="_blank" rel="noopener noreferrer">PubMed {x.pmid}</a>{" · "}{x.citation?.slice(0,120)}</p>)}
    </div>)}
   </details>
  </>}
 </section>;
}
