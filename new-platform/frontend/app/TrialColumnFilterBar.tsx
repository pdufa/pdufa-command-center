"use client";
import {useMemo,type ReactNode} from "react";

export type ColumnFilterField={key:string;label:string;type?:"text"|"select";options?:readonly string[]};
export type ColumnFilterState=Record<string,string>;

/** Filter the current loaded page only. Do not infer global server-side matches. */
export function applyColumnFilters<T>(
 rows:readonly T[],values:ColumnFilterState,read:(row:T,key:string)=>string|number|null|undefined
):T[]{
 const active=Object.entries(values).filter(([,value])=>value.trim()!=="");
 if(!active.length)return [...rows];
 return rows.filter(row=>active.every(([key,entry])=>{
   const actual=read(row,key);
   const text=actual===null||actual===undefined?"":String(actual);
   const value=entry.trim().toLocaleLowerCase("en-US");
   if(value.startsWith(">=")||value.startsWith("<=")||value.startsWith(">")||value.startsWith("<")){
     const op=value.startsWith(">=")||value.startsWith("<=")?value.slice(0,2):value.slice(0,1);
     const number=Number(value.slice(op.length));
     const observed=Number(actual);
     if(!Number.isFinite(number)||!Number.isFinite(observed)||!text.trim())return false;
     return op===">="?observed>=number:op==="<="?observed<=number:op===">"?observed>number:observed<number;
   }
   return text.toLocaleLowerCase("en-US").includes(value);
 }));
}
export const activeColumnFilters=(values:ColumnFilterState)=>Object.values(values).filter(v=>v.trim()).length;

export default function TrialColumnFilterBar({title,fields,filters,onChange,hint,children}:{
 title:string;fields:readonly ColumnFilterField[];filters:ColumnFilterState;
 onChange:(next:ColumnFilterState)=>void;hint?:string;children?:ReactNode
}){
 const count=activeColumnFilters(filters);
 const available=useMemo(()=>fields.filter((v,i,a)=>a.findIndex(x=>x.key===v.key)===i),[fields]);
 return <div className="trialColumnFilterBar" style={{
   padding:"9px 11px",margin:"8px 0",border:"1px solid #a4c8b2",borderRadius:8,background:"#f1f8f3"
 }}>
   <details open>
     <summary style={{cursor:"pointer",fontWeight:750,color:"#164d31"}}>
       {title} · Column filters{count?" ("+count+" active)":""}
     </summary>
     <p style={{fontSize:12,color:"#486654",margin:"7px 0"}}>
       {hint||"Filter the currently loaded trial rows. Multiple column filters combine with AND. Sort headings still work."}
     </p>
     <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(142px,1fr))",gap:8}}>
       {available.map(field=><label key={field.key} style={{display:"grid",gap:4,fontSize:12,fontWeight:650,color:"#264e38"}}>
         {field.label}
         {field.type==="select"?<select
           aria-label={"Filter "+field.label} value={filters[field.key]||""}
           onChange={event=>onChange({...filters,[field.key]:event.target.value})}
           style={{background:"#fff",color:"#234c35",padding:"7px",border:"1px solid #8dac9a",borderRadius:5,minWidth:0}}>
           <option value="">All</option>
           {(field.options||[]).map(option=><option key={option} value={option}>{option}</option>)}
         </select>:<input type="search" aria-label={"Filter "+field.label}
           placeholder={field.key==="s"||field.key==="d"?"e.g. >=30":"Contains…"}
           value={filters[field.key]||""}
           onChange={event=>onChange({...filters,[field.key]:event.target.value})}
           maxLength={120}
           style={{background:"#fff",color:"#234c35",padding:"7px",border:"1px solid #8dac9a",borderRadius:5,minWidth:0}}/>}
       </label>)}
     </div>
   </details>
   <div style={{display:"flex",gap:10,alignItems:"center",flexWrap:"wrap",marginTop:6}}>
     <button type="button" disabled={!count} onClick={()=>onChange({})}
       style={{padding:"6px 10px",borderRadius:6,border:"1px solid #95b49f",
         background:"#fff",color:"#194b31",cursor:count?"pointer":"not-allowed"}}>
       Clear column filters
     </button>
     <small style={{color:"#506c58"}}>{count} active column filters · Source data unchanged</small>
     {children}
   </div>
 </div>;
}
