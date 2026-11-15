"use client";
import {useEffect,useState} from "react";

export type NumericSortRule={column:string;direction:"asc"|"desc"};
export type NumericSortColumn={id:string;label:string};
type Preset={name:string;rules:NumericSortRule[]};
export function sortNumericRows<T>(rows:readonly T[],rules:NumericSortRule[],value:(row:T,column:string)=>number|string|null|undefined,id:(row:T)=>string):T[]{
 if(!rules.length)return [...rows];
 return [...rows].sort((a,b)=>{
  for(const rule of rules){
   const av=value(a,rule.column),bv=value(b,rule.column);
   const am=av==null||(typeof av==="number"&&!Number.isFinite(av)),bm=bv==null||(typeof bv==="number"&&!Number.isFinite(bv));
   if(am!==bm)return am?1:-1;
   if(am&&bm)continue;
   const diff=typeof av==="number"&&typeof bv==="number"?av-bv:String(av).localeCompare(String(bv),undefined,{numeric:true,sensitivity:"base"});
   if(diff)return rule.direction==="asc"?diff:-diff;
  }
  return id(a).localeCompare(id(b));
 });
}
export default function NumericSortSettings({scope,columns,onApply}:{scope:"past"|"focus";columns:NumericSortColumn[];onApply:(rules:NumericSortRule[])=>void}){
 const [open,setOpen]=useState(false);
 const [quickOpen,setQuickOpen]=useState(false);
 const [quickColumn,setQuickColumn]=useState(columns[0]?.id??"");
 const [quickDirection,setQuickDirection]=useState<"asc"|"desc">("asc");
 const [rules,setRules]=useState<NumericSortRule[]>([]);
 const [name,setName]=useState("");
 const [presets,setPresets]=useState<Preset[]>([]);
 const [chosen,setChosen]=useState("");
 const key="pdufa-numeric-sort-presets-"+scope;
 useEffect(()=>{try{const raw=localStorage.getItem(key);if(raw){const parsed=JSON.parse(raw);if(Array.isArray(parsed))setPresets(parsed)}}catch{}},[key]);
 const persist=(next:Preset[])=>{setPresets(next);try{localStorage.setItem(key,JSON.stringify(next))}catch{}};
 const available=columns.filter(c=>!rules.some(r=>r.column===c.id));
 const move=(i:number,delta:number)=>{setRules(old=>{const j=i+delta;if(j<0||j>=old.length)return old;const next=[...old];[next[i],next[j]]=[next[j],next[i]];return next})};
 const valid=rules.every(r=>columns.some(c=>c.id===r.column))&&new Set(rules.map(r=>r.column)).size===rules.length;
 return <section style={{margin:"12px 0"}}>
 <button type="button" onClick={()=>setQuickOpen(true)} aria-label="Column Sort Popup" style={{padding:"9px 14px",borderRadius:8,border:"1px solid #789987",background:"#e6f2ea",color:"#173d2b",fontWeight:700,cursor:"pointer"}}>↕ Column Sort Popup</button>
 <button type="button" onClick={()=>setOpen(true)} aria-label="Sort Display" style={{padding:"9px 14px",borderRadius:8,border:"1px solid #789987",background:"#e6f2ea",color:"#173d2b",fontWeight:700,cursor:"pointer"}}>⚙ Sort Display</button>
 {quickOpen&&<div role="dialog" aria-modal="true" aria-label="Column Sort Popup" style={{position:"fixed",inset:0,zIndex:1000,background:"#0008",display:"grid",placeItems:"center",padding:12}}>
 <div style={{background:"white",color:"#173d2b",padding:20,borderRadius:12,width:"min(460px,100%)",maxHeight:"85vh",overflowY:"auto"}}>
 <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}><h2>Column Sort Popup — {scope.toUpperCase()}</h2><button aria-label="Close column sort popup" onClick={()=>setQuickOpen(false)}>✕</button></div>
 <p>Sort the trial list by one column. For multiple priorities and saved setups, use Sort Display.</p>
 <label>Column <select aria-label="Column to sort" value={quickColumn} onChange={e=>setQuickColumn(e.target.value)}>{columns.map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select></label>
 <label style={{display:"block",marginTop:12}}>Direction <select aria-label="Column sort direction" value={quickDirection} onChange={e=>setQuickDirection(e.target.value as "asc"|"desc")}><option value="asc">Low → High / A → Z</option><option value="desc">High → Low / Z → A</option></select></label>
 <div style={{display:"flex",gap:8,justifyContent:"flex-end",marginTop:16}}><button onClick={()=>setQuickOpen(false)}>Cancel</button><button onClick={()=>{onApply([]);setRules([]);setQuickOpen(false)}}>Reset</button><button disabled={!columns.some(c=>c.id===quickColumn)} onClick={()=>{const next=[{column:quickColumn,direction:quickDirection}];setRules(next);onApply(next);setQuickOpen(false)}}>Apply Sort</button></div>
 </div></div>}
 {open&&<div role="dialog" aria-modal="true" aria-label="Sort Settings" style={{position:"fixed",inset:0,zIndex:1000,background:"#0008",display:"grid",placeItems:"center",padding:12}}>
 <div style={{background:"white",color:"#173d2b",padding:20,borderRadius:12,width:"min(660px,100%)",maxHeight:"85vh",overflowY:"auto"}}>
 <div style={{display:"flex",justifyContent:"space-between"}}><h2>Sort Settings — {scope.toUpperCase()}</h2><button aria-label="Close sorting popup" onClick={()=>setOpen(false)}>✕</button></div>
 <p>Choose any table column, then add more priorities. Already selected columns are excluded from the other dropdowns. Missing values sort last.</p>
 {rules.map((r,i)=><div key={i} style={{display:"flex",gap:8,alignItems:"center",marginBottom:10,flexWrap:"wrap"}}>
 <strong>{i+1}.</strong><select aria-label={`Priority ${i+1} column`} value={r.column} onChange={e=>setRules(old=>old.map((x,j)=>j===i?{...x,column:e.target.value}:x))}>{columns.filter(c=>c.id===r.column||!rules.some(x=>x.column===c.id)).map(c=><option key={c.id} value={c.id}>{c.label}</option>)}</select>
 <select aria-label={`Priority ${i+1} direction`} value={r.direction} onChange={e=>setRules(old=>old.map((x,j)=>j===i?{...x,direction:e.target.value as "asc"|"desc"}:x))}><option value="desc">High → Low</option><option value="asc">Low → High</option></select>
 <button disabled={i===0} onClick={()=>move(i,-1)} aria-label="Move priority up">↑</button><button disabled={i===rules.length-1} onClick={()=>move(i,1)} aria-label="Move priority down">↓</button><button onClick={()=>setRules(old=>old.filter((_,j)=>j!==i))}>Remove</button></div>)}
 <p style={{fontSize:12}}>Available additional columns: {available.length}. Add each column once; remove a rule to reuse it.</p>
 <button disabled={!available.length} onClick={()=>setRules(old=>[...old,{column:available[0].id,direction:"desc"}])}>+ Add Sorting Column</button>
 <hr/><label>Setup name <input value={name} onChange={e=>setName(e.target.value)}/></label>
 <button disabled={!name.trim()||!rules.length||!valid} onClick={()=>{persist([...presets.filter(p=>p.name!==name.trim()),{name:name.trim(),rules:rules.map(r=>({...r}))}]);setChosen(name.trim())}}>Save Setup</button>
 <div style={{marginTop:12}}><label>Saved setups <select value={chosen} onChange={e=>setChosen(e.target.value)}><option value="">Select saved setup</option>{presets.map(p=><option key={p.name}>{p.name}</option>)}</select></label>
 <button disabled={!chosen} onClick={()=>{const p=presets.find(p=>p.name===chosen);if(p){setName(p.name);setRules(p.rules.filter(r=>columns.some(c=>c.id===r.column)))}}}>Load / Edit</button>
 <button disabled={!chosen} onClick={()=>{if(window.confirm("Delete this saved sorting setup?")){persist(presets.filter(p=>p.name!==chosen));setChosen("")}}}>Delete Setup</button></div>
 <hr/><div style={{display:"flex",gap:8,justifyContent:"flex-end"}}>
 <button onClick={()=>{setRules([]);onApply([]);setOpen(false)}}>Reset Sort</button>
 <button onClick={()=>setOpen(false)}>Cancel</button>
 <button disabled={!rules.length||!valid} onClick={()=>{onApply(rules.map(r=>({...r})));setOpen(false)}}>Apply Sort</button>
 </div></div></div>}</section>;
}
