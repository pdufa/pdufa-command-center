"use client";
import {useEffect,useState} from "react";

const levels=Array.from({length:12},(_,i)=>i+9);
const isObj=(x:unknown):x is Record<string,unknown>=>!!x&&typeof x==="object"&&!Array.isArray(x);
const safeCount=(x:unknown):x is number=>typeof x==="number"&&Number.isSafeInteger(x)&&x>=0;
type LevelCounts={active:number;deferred:number;reviewed:number};
type Totals={
 scope:"SCIENTIFIC_LEVELS_09_TO_20";
 methodVersion:"scientific-advanced-research-queue-v1";
 programs:number;readyPrograms:number;blockedPrograms:number;
 noActiveGapPrograms:number;activeTasks:number;deferredCriteria:number;reviewedCriteria:number;
 byLevel:Record<string,LevelCounts>;
};
export function validAdvancedUniverseTotals(raw:unknown):raw is Totals{
 if(!isObj(raw)||raw.scope!=="SCIENTIFIC_LEVELS_09_TO_20"||
  raw.methodVersion!=="scientific-advanced-research-queue-v1"||
  !["programs","readyPrograms","blockedPrograms","noActiveGapPrograms",
    "activeTasks","deferredCriteria","reviewedCriteria"].every(k=>safeCount(raw[k]))||
  !isObj(raw.byLevel)||Object.keys(raw.byLevel).length!==12)return false;
 const n=raw as Record<string,unknown>;
 const total=n.programs as number,ready=n.readyPrograms as number,blocked=n.blockedPrograms as number,none=n.noActiveGapPrograms as number;
 if(ready+blocked+none!==total||!levels.every(l=>{
  const x=raw.byLevel as Record<string,unknown>;
  const count=x[String(l)];
  return isObj(count)&&safeCount(count.active)&&safeCount(count.deferred)&&safeCount(count.reviewed);
 }))return false;
 const entries=levels.map(l=>(raw.byLevel as Record<string,LevelCounts>)[String(l)]);
 return entries.reduce((sum,x)=>sum+x.active,0)===raw.activeTasks&&
  entries.reduce((sum,x)=>sum+x.deferred,0)===raw.deferredCriteria&&
  entries.reduce((sum,x)=>sum+x.reviewed,0)===raw.reviewedCriteria;
}
export function AdvancedUniverseTotalsView({data}:{data:Totals}){
 return <section aria-label="Whole-universe Levels 9 through 20 research queue totals"
  style={{border:"1px solid #a9c7be",borderRadius:8,padding:14,margin:"16px 0"}}>
  <h2>Research queue · all indexed programs · Levels 9–20</h2>
  <p>{data.programs} exact program records · {data.readyPrograms} with research tasks · {data.blockedPrograms} with unverified intake · {data.noActiveGapPrograms} without active gaps.</p>
  <p><strong>{data.activeTasks} source-review tasks</strong> · {data.deferredCriteria} not-yet-expected criteria · {data.reviewedCriteria} source-reviewed criteria.</p>
  <p>These are workflow counts, not scientific scores, FDA approval confidence, evidence quality, or completed trial predictions. Blocked programs are not counted as missing-source tasks; deferred items are not clinical failures.</p>
  <details><summary>View Levels 9–20 backlog breakdown</summary>
   <div style={{overflowX:"auto"}}><table><thead><tr><th>Level</th><th>Active tasks</th><th>Deferred</th><th>Reviewed criteria</th></tr></thead><tbody>
    {levels.map(n=>{const item=data.byLevel[String(n)];return <tr key={n}>
     <th scope="row">L{String(n).padStart(2,"0")}</th><td>{item.active}</td><td>{item.deferred}</td><td>{item.reviewed}</td>
    </tr>;})}
   </tbody></table></div>
  </details>
 </section>;
}
export default function AdvancedUniverseTotals(){
 const [data,setData]=useState<Totals|null>(null);
 const [loading,setLoading]=useState(false);
 const [message,setMessage]=useState("Loading protected research queue totals…");
 async function load(signal?:AbortSignal){
  setLoading(true);setMessage("");setData(null);
  try{
   const response=await fetch("/api/assessments",{cache:"no-store",signal});
   if(!response.ok)throw Error(response.status===401?"Sign in to view protected research queue counts.":"Research queue counts are unavailable.");
   const raw:unknown=await response.json();
   if(!isObj(raw)||raw.status!=="COMPLETE"||!validAdvancedUniverseTotals(raw.advancedResearchQueueTotals))
    throw Error("Research queue index is building or the totals are not verified.");
   if(!signal?.aborted)setData(raw.advancedResearchQueueTotals);
  }catch(error){
   if(!signal?.aborted)setMessage(error instanceof Error?error.message:"Research queue totals unavailable.");
  }finally{if(!signal?.aborted)setLoading(false);}
 }
 useEffect(()=>{const controller=new AbortController();void load(controller.signal);
  return()=>controller.abort();},[]);
 return <div aria-label="Source-review workload overview">
  <button type="button" disabled={loading} onClick={()=>void load()}>{loading?"Loading research counts…":"Refresh research counts"}</button>
  {message&&<p role="status">{message}</p>}
  {data&&<AdvancedUniverseTotalsView data={data}/>}
 </div>;
}
