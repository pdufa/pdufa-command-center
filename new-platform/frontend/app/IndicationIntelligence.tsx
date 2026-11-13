"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {
 buildDiseaseIndex,diseasePath,DISEASE_LEVELS,DISEASE_STORAGE_KEY,
 emptyDiseaseEdits,restoreDiseaseEdits,searchDiseases,type DiseaseEdits
} from "../lib/disease-catalog";
import {
 linkToDiseases,selectedRows,phaseCounts,uniqueTrials,PHASE_COLUMNS,
 type LinkedTrial,type IndicationTrial,type PhaseColumn
} from "../lib/indication-intelligence";
import {POOL_DETAIL_FIELDS,type PoolRegistryDetail} from "../lib/pool-registry-details";
type Feed={view:"indications";rows:IndicationTrial[];asOf:string|null;focusAsOf:string;
 focusUnmatched?:{nct:string;ticker:string;company:string}[];
 sourceState:string;totalTrials:number};
type Mode="pool"|"focus"|"indications";
const surface:React.CSSProperties={border:"1px solid #c8d8ce",borderRadius:12,padding:15,background:"#fff"};
const button:React.CSSProperties={border:"1px solid #b8d0c1",borderRadius:8,padding:"8px 10px",background:"#fff",color:"#174633",cursor:"pointer"};
const small:React.CSSProperties={fontSize:12,color:"#536a5e",lineHeight:1.5};
const label:React.CSSProperties={fontSize:12,fontWeight:700,display:"block",marginBottom:5};
const infoFields:readonly (typeof POOL_DETAIL_FIELDS[number])[]=[
 "studyTitle","studyDesign","treatmentArms","enrollment","eligibility",
 "primaryEndpoints","secondaryEndpoints","reportedResults","safetyResults",
 "documentsPublications","milestoneDateTypes","terminationReason"
];
const names:Record<string,string>={
 studyTitle:"Registered study title",studyDesign:"Trial design",treatmentArms:"Arms / comparator",
 enrollment:"Registered enrollment (not total eligible population)",eligibility:"Patient eligibility",
 primaryEndpoints:"Primary endpoints",secondaryEndpoints:"Secondary endpoints",
 reportedResults:"Posted clinical measurements (unadjudicated)",safetyResults:"Posted safety counts",
 documentsPublications:"Registered documents and publications",
 milestoneDateTypes:"Clinical milestones",terminationReason:"Reason study stopped"
};
function nctKey(t:LinkedTrial){return t.nct+"|"+t.ticker;}
export default function IndicationIntelligence({mode="indications"}:{mode?:Mode}){
 const [feed,setFeed]=useState<Feed|null>(null);
 const [error,setError]=useState("");
 const [loading,setLoading]=useState(true);
 const [edits,setEdits]=useState<DiseaseEdits>(emptyDiseaseEdits);
 const [selectedNode,setSelectedNode]=useState<string|null>(null);
 const [query,setQuery]=useState("");
 const [phase,setPhase]=useState<PhaseColumn|null>(null);
 const [focusOnly,setFocusOnly]=useState(mode==="focus");
 const [unmappedOnly,setUnmappedOnly]=useState(false);
 const [showAllNodes,setShowAllNodes]=useState(false);
 const [detail,setDetail]=useState<LinkedTrial|null>(null);
 const [registry,setRegistry]=useState<PoolRegistryDetail|null>(null);
 const [registryLoading,setRegistryLoading]=useState(false);
 const [registryError,setRegistryError]=useState("");
 useEffect(()=>{
  try{
   const saved=localStorage.getItem(DISEASE_STORAGE_KEY);
   if(saved)setEdits(restoreDiseaseEdits(JSON.parse(saved)));
  }catch{/* The checked-in MeSH catalog remains usable. */}
  const initial=new URLSearchParams(window.location.search).get("nct");
  if(initial&&/^NCT\d{8}$/.test(initial))setQuery(initial);
 },[]);
 useEffect(()=>{
  const controller=new AbortController();
  setLoading(true);
  void fetch("/api/scope-funnel?view=indications",{cache:"no-store",signal:controller.signal})
   .then(async response=>{
    if(!response.ok)throw Error(response.status===401?"Sign in to inspect POOL.":"Verified POOL source unavailable.");
    const data:Feed=await response.json();
    if(data.view!=="indications"||!Array.isArray(data.rows)||data.rows.length!==data.totalTrials)
     throw Error("Source inventory count or shape did not match");
    if(data.sourceState==="STALE")throw Error("Source inventory is stale");
    if(!controller.signal.aborted)setFeed(data);
   }).catch(reason=>{if(!controller.signal.aborted){setError(reason instanceof Error?reason.message:"POOL unavailable");setFeed(null);}})
   .finally(()=>{if(!controller.signal.aborted)setLoading(false)});
  return ()=>controller.abort();
 },[]);
 const index=useMemo(()=>buildDiseaseIndex(edits),[edits]);
 const linked=useMemo(()=>linkToDiseases(feed?.rows||[],index),[feed,index]);
 const allScope=useMemo(()=>selectedRows(linked,index,selectedNode,query,focusOnly,null)
   .filter(t=>!unmappedOnly||t.matchStatus!=="EXACT"),[linked,index,selectedNode,query,focusOnly,unmappedOnly]);
 const filtered=useMemo(()=>phase?allScope.filter(t=>
   phaseCounts([t])[phase]>0):allScope,[allScope,phase]);
 const counts=useMemo(()=>phaseCounts(allScope),[allScope]);
 const shown=useMemo(()=>{
  const seen=new Set<string>();
  return filtered.filter(t=>{const key=nctKey(t)+"|"+t.indicationText.toLowerCase();if(seen.has(key))return false;
   seen.add(key);return true;}).slice(0,75);
 },[filtered]);
 const path=selectedNode?diseasePath(selectedNode,index):[];
 const children=index.children.get(selectedNode)||[];
 const list=showAllNodes?children:children.slice(0,14);
 const suggestions=useMemo(()=>searchDiseases(query,index).slice(0,7),[query,index]);
 const focusCount=new Set(linked.filter(t=>t.focus).map(nctKey)).size;
 function chooseNode(id:string|null){setSelectedNode(id);setPhase(null);setUnmappedOnly(false);setShowAllNodes(false);}
 function openDetail(trial:LinkedTrial){setDetail(trial);setRegistry(null);setRegistryError("");}
 useEffect(()=>{
  if(!detail)return;
  const controller=new AbortController();
  setRegistryLoading(true);
  void fetch("/api/pool-registry-details?nct="+encodeURIComponent(detail.nct),{cache:"no-store",signal:controller.signal})
   .then(async response=>{if(!response.ok)throw Error("Registry detail unavailable.");
    const data:PoolRegistryDetail=await response.json();
    if(data.nctId!==detail.nct||data.sourceUrl!=="https://clinicaltrials.gov/study/"+detail.nct)
     throw Error("Exact-trial identity mismatch");
    if(!controller.signal.aborted)setRegistry(data);
   }).catch(reason=>{if(!controller.signal.aborted)setRegistryError(reason instanceof Error?reason.message:"Registry unavailable");})
   .finally(()=>{if(!controller.signal.aborted)setRegistryLoading(false)});
  return ()=>controller.abort();
 },[detail]);
 return <section aria-label="Unified indication intelligence" style={{...surface,color:"#153e2b",margin:"18px 0",maxWidth:"100%"}}>
  <header style={{display:"flex",justifyContent:"space-between",gap:10,flexWrap:"wrap",alignItems:"center"}}>
   <div><h2 style={{margin:"0 0 4px"}}>POOL · INDICATIONS · FOCUS</h2>
    <p style={{...small,margin:0}}>One source-linked disease hierarchy, phase matrix and trial assessment workspace.</p></div>
   <nav style={{display:"flex",gap:8,flexWrap:"wrap"}}>
    <Link href="/pool">POOL</Link><Link href="/indications">INDICATIONS</Link><Link href="/focus">FOCUS</Link>
   </nav>
  </header>
  <p style={small}>Master POOL source: {feed?.asOf||"Unavailable"} · Source: {feed?.sourceState||"Not verified"} · FOCUS snapshot: {feed?.focusAsOf||"Unavailable"}.
   MeSH text matches are classification leads, not verified drug–indication adjudications. No clinical probabilities are inferred.</p>
  {error&&<p role="alert" style={{color:"#9c2635"}}>{error}</p>}
  {loading&&<p role="status">Retrieving the source-linked full clinical POOL…</p>}
  {!loading&&feed&&<>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:9,marginBottom:12}}>
    <div style={surface}><strong>{uniqueTrials(linked).toLocaleString()}</strong><div style={small}>Distinct source NCT + ticker identities</div></div>
    <div style={surface}><strong>{focusCount}</strong><div style={small}>Exact FOCUS-linked identities</div></div>
    <div style={surface}><strong>{linked.filter(t=>t.matchStatus==="EXACT").length.toLocaleString()}</strong><div style={small}>Indication rows with unique exact taxonomy matches</div></div>
    <div style={surface}><strong>{linked.filter(t=>t.matchStatus!=="EXACT").length.toLocaleString()}</strong><div style={small}>Indication rows requiring taxonomy review</div></div>
   </div>
   {!!feed.focusUnmatched?.length&&<details style={{...surface,marginBottom:12}}>
    <summary style={{cursor:"pointer",fontWeight:700}}>{feed.focusUnmatched.length} FOCUS trial identities need exact POOL reconciliation</summary>
    <p style={small}>These are in the dated FOCUS roster but not matched by both NCT and ticker in the current POOL. They are not silently added to POOL or given an inferred indication.</p>
    {feed.focusUnmatched.map(item=><p key={item.nct+"|"+item.ticker} style={small}>
     <a href={"https://clinicaltrials.gov/study/"+item.nct} target="_blank" rel="noopener noreferrer">{item.nct}</a> · {item.ticker} · {item.company}</p>)}
   </details>}
   <div style={{display:"flex",flexWrap:"wrap",gap:12,alignItems:"end",marginBottom:15}}>
    <label style={{flex:"1 1 245px"}}><span style={label}>Find disease, company, drug, NCT or stage</span>
     <input aria-label="Search indications and trials" type="search" value={query} onChange={e=>setQuery(e.target.value)}
      style={{width:"100%",padding:9,border:"1px solid #b7c8bc",borderRadius:8}} placeholder="e.g. lung cancer or NCT..." /></label>
    <label style={{...small,display:"flex",gap:5,alignItems:"center"}}><input type="checkbox" checked={focusOnly} onChange={e=>setFocusOnly(e.target.checked)}/> FOCUS trials only</label>
    <label style={{...small,display:"flex",gap:5,alignItems:"center"}}><input type="checkbox" checked={unmappedOnly} onChange={e=>setUnmappedOnly(e.target.checked)}/> Unmapped indication review</label>
    <button type="button" style={button} onClick={()=>{setQuery("");chooseNode(null);setFocusOnly(mode==="focus")}}>Reset</button>
   </div>
   {query&&suggestions.length>0&&<div style={{display:"flex",gap:5,flexWrap:"wrap",marginBottom:12}}>{suggestions.map(node=>
    <button type="button" key={node.id} style={button} onClick={()=>{setQuery("");chooseNode(node.id)}}>{node.name}</button>)}</div>}
   <div style={{display:"flex",flexWrap:"wrap",gap:9,marginBottom:12}}>
    <button type="button" style={button} onClick={()=>chooseNode(null)}>All indications</button>
    {path.map(node=><button type="button" key={node.id} style={button} onClick={()=>chooseNode(node.id)}>{node.name}</button>)}
   </div>
   <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(210px,1fr))",gap:8,marginBottom:16}}>
    {Array.from({length:5},(_,level)=>{
     const parent=level===0?null:path[level-1]?.id;
     const items=level===0?index.children.get(null)||[]:parent?index.children.get(parent)||[]:[];
     return <label key={level}><span style={label}>{level+1}. {DISEASE_LEVELS[level]}</span>
      <select aria-label={"Disease hierarchy level "+(level+1)} value={path[level]?.id||""}
       disabled={!items.length} onChange={e=>chooseNode(e.target.value||parent||null)}
       style={{width:"100%",padding:8,borderRadius:8,border:"1px solid #b7c8bc"}}>
       <option value="">Select {level===0?"area":"subtype"}</option>
       {items.map(node=><option key={node.id} value={node.id}>{node.name}</option>)}
      </select></label>;
    })}
   </div>
   <div style={{overflowX:"auto",border:"1px solid #d7e3d9",borderRadius:10}}>
    <table style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:940}}>
     <thead style={{background:"#e6f2eb"}}><tr>
      <th style={{padding:10,textAlign:"left"}}>Disease hierarchy / indication</th>
      {PHASE_COLUMNS.map(([key])=><th key={key} style={{padding:7}}>{key}</th>)}
      <th>Trials</th></tr></thead>
     <tbody>
      <tr style={{background:"#f3f7f4"}}><th style={{textAlign:"left",padding:10}}>Selected branch · {selectedNode?path.at(-1)?.name:"all classifications"}</th>
       {PHASE_COLUMNS.map(([key])=><td key={key} style={{textAlign:"center",padding:7}}>
        <button type="button" style={{...button,background:phase===key?"#d1eadb":"#fff"}} onClick={()=>setPhase(phase===key?null:key)}>{counts[key]}</button>
       </td>)}<td style={{textAlign:"center"}}>{uniqueTrials(allScope)}</td></tr>
      {list.map(node=>{
       const branch=selectedRows(linked,index,node.id,query,focusOnly,null)
        .filter(t=>!unmappedOnly||t.matchStatus!=="EXACT");
       const branchCounts=phaseCounts(branch);
       return <tr key={node.id} style={{borderTop:"1px solid #e4ece5"}}>
        <th style={{textAlign:"left",padding:9,fontWeight:500}}>
         <button type="button" style={{...button,border:"none",textAlign:"left",padding:3}} onClick={()=>chooseNode(node.id)}>
          ↳ {node.name}</button></th>
        {PHASE_COLUMNS.map(([key])=><td key={key} style={{textAlign:"center"}}>
         {branchCounts[key]?<button type="button" style={button} onClick={()=>{chooseNode(node.id);setPhase(key)}}>{branchCounts[key]}</button>:"—"}</td>)}
        <td style={{textAlign:"center"}}>{uniqueTrials(branch)}</td>
       </tr>;
      })}
     </tbody>
    </table>
   </div>
   {children.length>14&&<button type="button" style={{...button,marginTop:9}} onClick={()=>setShowAllNodes(!showAllNodes)}>
    {showAllNodes?"Collapse":"Show all "+children.length+" subdivisions"}</button>}
   <p style={small}>Phase counts represent distinct NCT + ticker pairs within the selected branch. P1/2 and P2/3 have separate columns; the same trial is not double-counted within a branch. A dash can mean no exact MeSH link—not that a disease has no clinical trials.</p>
   <div style={{display:"flex",justifyContent:"space-between",flexWrap:"wrap",gap:8,alignItems:"center"}}>
    <h3 style={{margin:"8px 0"}}>Linked clinical trials ({uniqueTrials(filtered).toLocaleString()} matches)</h3>
    {phase&&<button type="button" style={button} onClick={()=>setPhase(null)}>Clear phase: {phase} ×</button>}
   </div>
   <div style={{overflowX:"auto"}}>
    <table style={{minWidth:810,width:"100%",borderCollapse:"collapse",fontSize:13}}>
     <thead><tr>{["NCT","Company / drug","Indication","Phase","FOCUS","Assessment"].map(x=>
      <th key={x} style={{padding:9,textAlign:"left",borderBottom:"1px solid #dae4da"}}>{x}</th>)}</tr></thead>
     <tbody>{shown.map((r,i)=><tr key={nctKey(r)+"|"+r.indicationText+"|"+i} style={{borderBottom:"1px solid #e7eee8"}}>
      <td style={{padding:9}}><a href={r.sourceUrl} target="_blank" rel="noopener noreferrer">{r.nct}</a></td>
      <td style={{padding:9}}><strong>{r.ticker}</strong> · {r.company||"Unverified company"}<br/>{r.drug||"Drug unrecorded"}</td>
      <td style={{padding:9}}>{r.indicationText}<br/><small style={small}>{r.matchStatus==="EXACT"?"Exact MeSH-name match":"Disease classification needs review"}</small></td>
      <td style={{padding:9}}>{r.stage}</td><td style={{padding:9}}>{r.focus?"Linked":"POOL"}</td>
      <td style={{padding:9}}><button type="button" style={button} onClick={()=>openDetail(r)}>Open details</button></td>
     </tr>)}</tbody>
    </table>
   </div>
   {filtered.length>shown.length&&<p style={small}>Showing first {shown.length} indication–trial rows. Narrow the hierarchy or search to refine. No records are deleted by filters.</p>}
   <p style={small}>No scores are calculated from registry descriptions. Changes to original trials, clinical assessments or nightly scans are outside this read-only viewer.</p>
  </>}
  {detail&&<div role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)setDetail(null)}} style={{position:"fixed",inset:0,zIndex:2000,display:"flex",justifyContent:"center",alignItems:"center",padding:12,background:"#001b1788"}}>
   <section role="dialog" aria-modal="true" aria-label="Indication-specific trial assessment" style={{...surface,width:"min(910px,100%)",maxHeight:"92dvh",overflowY:"auto",color:"#143c2b"}}>
    <header style={{display:"flex",justifyContent:"space-between",gap:8,alignItems:"start"}}>
     <div><h2 style={{margin:0}}>{detail.drug||detail.nct} · {detail.indicationText}</h2><p style={small}>{detail.company} · {detail.ticker} · {detail.stage} · {detail.nct}</p></div>
     <button type="button" style={button} onClick={()=>setDetail(null)}>Close ×</button>
    </header>
    <p><a target="_blank" rel="noopener noreferrer" href={detail.sourceUrl}>Open official exact-NCT record ↗</a>
     {detail.focus&&<> · <Link href={"/focus"}>FOCUS entry</Link></>}
     {" · "}<Link href={"/analyze-now?nct="+detail.nct}>Assessment workspace</Link></p>
    <p style={small}>Clinical stage, disease and NCT identity are recorded source leads. Subtype, biomarkers, comparative superiority, standard of care, patient-market size and regulatory success remain unverified until separately sourced. A shared drug does not transfer evidence between indications.</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:8}}>
     {[
      ["Disease and subtype",detail.indicationText],
      ["Biomarker / severity","Not independently verified"],
      ["Current treatment / competitors","Clinical review pending"],
      ["Indication-specific patient population","Not independently established"],
      ["Medical unmet need","Clinical review pending"],
      ["Assessment score / confidence","Not scored / not validated"],
      ["Regulatory and FOCUS readiness",detail.focus?"FOCUS-listed; eligibility not independently certified":"Not established"],
      ["Clinical research history","No sourced indication assessment in this viewer"]
     ].map(([title,value])=><div key={title} style={{...surface,padding:11}}><div style={label}>{title}</div><div style={{fontSize:13}}>{value}</div></div>)}
    </div>
    {registryLoading&&<p role="status">Checking official trial endpoints, safety and enrollment…</p>}
    {registryError&&<p role="alert">{registryError}</p>}
    {registry&&<><h3>Exact-trial registry observations · {registry.available}/{registry.total} reported fields</h3>
     <p style={small}>Retrieved {registry.retrievedAt}. Availability does not establish treatment benefit or scientific adjudication.</p>
     {infoFields.map(key=><details key={key} style={{borderBottom:"1px solid #dfe7df",padding:"10px 0"}}>
      <summary style={{cursor:"pointer",fontWeight:650}}>{names[key]} — {registry.fields[key]?"Source available":"Not reported in registry"}</summary>
      <p style={{fontSize:13,lineHeight:1.6}}>{registry.fields[key]||"Not in this source; may be unpublished or not yet expected at this phase."}</p>
     </details>)}
    </>}
    <p style={small}>Source updates are fetched on opening; longitudinal evidence versions and full specialist assessments must be linked from their independently verified research records before conclusions are displayed.</p>
   </section>
  </div>}
 </section>;
}
