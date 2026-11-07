"use client";

import {useEffect,useMemo,useState} from "react";
import snapshot from "../data/p3PostDataActive.json";
import css from "./PoolMasterSpreadsheet.module.css";

export type PoolMasterRow={
 id:string;ticker:string;company?:string;drug?:string;indication?:string;
 stage?:string;status?:string;interventionType?:string;route?:string;
 startDate?:string;primaryCompletion?:string;studyCompletion?:string;
 resultsPosted?:string;sourceUpdated?:string;sourceUrl?:string;checkedAt?:string;
 marketCap?:number|null;capInRange?:boolean;capChecked?:string;capSource?:string;
 phase3Date?:string;phase3Source?:string;nctId?:string;
};
type Key="phase"|"status"|"drug"|"intervention"|"route"|"indication"
 |"start"|"primary"|"complete"|"posted"|"updated"|"source"|"checked"
 |"traded"|"exchange"|"cap"|"capDate"|"capQualified"|"phase3"|"publicResults"
 |"fdaPath"|"application"|"pdufa"|"designations"
 |"focusQualified"|"reason"|"evidence"|"completeness"|"reviewed";
type Column={key:Key;label:string};
type Segment={key:string;label:string;columns:readonly Column[]};
type View="phone"|"desktop";
type Layout={expanded:string[];hiddenSegments:string[];hiddenColumns:Key[]};
const SEGMENTS:readonly Segment[]=[
 {key:"clinical",label:"Clinical Information",columns:[
  {key:"phase",label:"Clinical phase"},{key:"status",label:"Trial status"},
  {key:"drug",label:"Drug / intervention"},{key:"intervention",label:"Intervention type"},
  {key:"route",label:"Administration route"},{key:"indication",label:"Indication / disease"}]},
 {key:"dates",label:"Dates & Sources",columns:[
  {key:"start",label:"Trial start date"},{key:"primary",label:"Primary completion"},
  {key:"complete",label:"Study completion"},{key:"posted",label:"Results posted"},
  {key:"updated",label:"Source updated"},{key:"source",label:"Source URL"},
  {key:"checked",label:"Last checked"}]},
 {key:"qualifiers",label:"Qualification",columns:[
  {key:"traded",label:"Publicly traded?"},{key:"exchange",label:"Stock exchange"},
  {key:"cap",label:"Market cap (USD)"},{key:"capDate",label:"Market cap as-of"},
  {key:"capQualified",label:"$300M–$10B qualified?"},{key:"phase3",label:"Phase 3 reached?"},
  {key:"publicResults",label:"Phase 3 results public?"},{key:"fdaPath",label:"Active FDA path?"},
  {key:"application",label:"FDA application stage"},{key:"pdufa",label:"PDUFA target date"},
  {key:"designations",label:"FDA designations"}]},
 {key:"focus",label:"FOCUS Eligibility",columns:[
  {key:"focusQualified",label:"FOCUS membership"},{key:"reason",label:"Qualification reasons"},
  {key:"evidence",label:"Qualification evidence URLs"},
  {key:"completeness",label:"Evidence completeness"},
  {key:"reviewed",label:"Last eligibility review"}]}
];
const ALL_KEYS=SEGMENTS.flatMap(s=>s.columns.map(c=>c.key));
const ALL_SEGMENTS=SEGMENTS.map(s=>s.key);
const storageKey=(view:View)=>"pdufa:pool-column-layout:v1:"+view;
const defaultLayout=(view:View):Layout=>({
 expanded:view==="phone"?["focus"]:["qualifiers","focus"],
 hiddenSegments:[],hiddenColumns:[]
});
const uniqueAllowed=(input:unknown,allowed:readonly string[])=>{
 if(!Array.isArray(input))return [];
 return [...new Set(input.filter((x):x is string=>typeof x==="string"&&allowed.includes(x)))];
};
function recoverLayout(raw:string|null,view:View):Layout{
 if(!raw)return defaultLayout(view);
 try {
  const candidate=JSON.parse(raw) as Partial<Layout>;
  return {
   expanded:uniqueAllowed(candidate.expanded,ALL_SEGMENTS),
   hiddenSegments:uniqueAllowed(candidate.hiddenSegments,ALL_SEGMENTS),
   hiddenColumns:uniqueAllowed(candidate.hiddenColumns,ALL_KEYS) as Key[],
  };
 }catch{return defaultLayout(view);}
}
const known=(v:unknown)=>typeof v==="string"&&v.trim()?v:"Not verified";
const formatCap=(n:number)=>n.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0});
const focusByTrial=new Map(snapshot.records.map(r=>[r.nct+"|"+r.ticker.toUpperCase(),r]));
const nctOf=(r:PoolMasterRow)=>{
 const value=r.nctId||(r.id.startsWith("TRIAL|")?r.id.slice(6):"");
 return /^NCT\d{8}$/.test(value)?value:"";
};
function contentFor(row:PoolMasterRow,key:Key):{text:string;url?:string}{
 const nct=nctOf(row);
 const focus=nct?focusByTrial.get(nct+"|"+row.ticker.toUpperCase()):undefined;
 const cap=focus?.marketCap??row.marketCap;
 const sourceUrl=row.sourceUrl||(nct?"https://clinicaltrials.gov/study/"+nct:undefined);
 switch(key){
  case "phase":return{text:known(row.stage)};
  case "status":return{text:known(row.status)};
  case "drug":return{text:known(row.drug)};
  case "intervention":return{text:known(row.interventionType)};
  case "route":return{text:known(row.route)};
  case "indication":return{text:known(row.indication)};
  case "start":return{text:known(row.startDate)};
  case "primary":return{text:known(row.primaryCompletion)};
  case "complete":return{text:known(row.studyCompletion)};
  case "posted":return{text:known(row.resultsPosted)};
  case "updated":return{text:known(row.sourceUpdated)};
  case "source":return{ text:sourceUrl?"Open registry source":"Not verified",url:sourceUrl};
  case "checked":return{text:known(row.checkedAt)};
  case "traded":return{text:focus?"FOCUS issuer reviewed":"Not verified"};
  case "exchange":return{text:"Not verified"};
  case "cap":return{text:typeof cap==="number"&&Number.isFinite(cap)?formatCap(cap):"Not verified"};
  case "capDate":return{text:focus?snapshot.asOf:known(row.capChecked)};
  case "capQualified":return{text:focus?"Pass (FOCUS snapshot)":row.capInRange===true?"Historical in range — recheck":"Not verified"};
  case "phase3":return{text:focus||/Phase 3|PHASE3/i.test(row.stage||"")?"Recorded":"Not verified"};
  case "publicResults":return{text:focus?"Yes — source in FOCUS":row.phase3Source?"Source recorded — review":"Not verified"};
  case "fdaPath":return{text:focus?"Recorded FOCUS path":"Not verified"};
  case "application":return{text:focus?focus.fdaStatus:"Not verified"};
  case "pdufa":return{text:"Not verified at exact-trial level"};
  case "designations":return{text:"Not verified"};
  case "focusQualified":return{text:focus?"In FOCUS":"Not on current FOCUS roster — unassessed"};
  case "reason":return{text:focus?"Exact NCT + ticker matches the saved FOCUS roster":"FOCUS gates not established for this record"};
  case "evidence":return focus?{text:"Results evidence",url:focus.resultsUrl}:
   row.capSource?{text:"Market-cap source",url:row.capSource}:{text:"Not verified"};
  case "completeness":return{text:focus?"FOCUS source links recorded; full evidence not assessed":"Not assessed"};
  case "reviewed":return{text:focus?snapshot.asOf:"Not assessed"};
 }
}
export default function PoolMasterSpreadsheet({rows}:{rows:PoolMasterRow[]}){
 const [view,setView]=useState<View>("desktop");
 const [hydrated,setHydrated]=useState(false);
 const [layouts,setLayouts]=useState<Record<View,Layout>>({
  phone:defaultLayout("phone"),desktop:defaultLayout("desktop")
 });
 useEffect(()=>{
  const media=window.matchMedia("(max-width: 640px)");
  const sync=()=>setView(media.matches?"phone":"desktop");
  sync();media.addEventListener("change",sync);
  try{
   setLayouts({
    phone:recoverLayout(window.localStorage.getItem(storageKey("phone")),"phone"),
    desktop:recoverLayout(window.localStorage.getItem(storageKey("desktop")),"desktop"),
   });
  }catch{/* Incognito storage denial keeps defaults usable. */}
  setHydrated(true);
  return()=>media.removeEventListener("change",sync);
 },[]);
 useEffect(()=>{
  if(!hydrated)return;
  try{
   for(const device of ["phone","desktop"] as const)
    window.localStorage.setItem(storageKey(device),JSON.stringify(layouts[device]));
  }catch{/* Local saving is optional. */}
 },[hydrated,layouts]);
 const layout=layouts[view];
 const edit=(fn:(l:Layout)=>Layout)=>setLayouts(p=>({...p,[view]:fn(p[view])}));
 const switchIn=(key:keyof Layout,id:string)=>edit(l=>({
  ...l,[key]:l[key].includes(id as never)?l[key].filter(x=>x!==id):[...l[key],id]
 }));
 const visible=useMemo(()=>SEGMENTS.filter(s=>layout.expanded.includes(s.key)&&!layout.hiddenSegments.includes(s.key))
   .flatMap(s=>s.columns.filter(c=>!layout.hiddenColumns.includes(c.key))),[layout]);
 return <section aria-label="POOL Master Spreadsheet with responsive column visibility" data-pool-master="true" className={css.section}>
  <div className={css.top}>
   <div><h3>POOL Master · 32 columns</h3>
    <p>All stages stay in POOL. Hide or expand entire column segments, or choose individual columns. Hidden fields still participate in research and eligibility checks.</p></div>
   <div className={css.actions}>
    <button type="button" onClick={()=>edit(()=>({expanded:[...ALL_SEGMENTS],hiddenSegments:[],hiddenColumns:[]}))}>Show all</button>
    <button type="button" onClick={()=>edit(()=>defaultLayout(view))}>Reset {view==="phone"?"phone":"PC"} view</button>
   </div>
  </div>
  <p className={css.viewport} data-viewport={view}>
   {view==="phone"?"Phone: data columns use 50% of viewport width; Ticker stays pinned.":
   "PC: data columns adapt from 180–260px; Ticker, Company, and NCT ID stay pinned."}
   {" "}Layouts are saved separately on this device.
  </p>
  <div className={css.segments} role="group" aria-label="POOL column segments">
   {SEGMENTS.map(s=>{
    const hidden=layout.hiddenSegments.includes(s.key),expanded=layout.expanded.includes(s.key);
    const active=s.columns.filter(c=>!layout.hiddenColumns.includes(c.key)).length;
    return <div key={s.key} className={css.segment} data-segment={s.key}>
     <div className={css.segmentHead}>
      <button type="button" className={css.segmentToggle} aria-expanded={!hidden&&expanded}
       disabled={hidden} onClick={()=>switchIn("expanded",s.key)}>
       {expanded&&!hidden?"▾":"▸"} {s.label} <small>{active}/{s.columns.length}</small>
      </button>
      <button type="button" className={css.visibilityToggle} aria-pressed={hidden}
       onClick={()=>switchIn("hiddenSegments",s.key)}>{hidden?"Restore":"Hide segment"}</button>
     </div>
     {expanded&&!hidden&&<div className={css.columnOptions}>
      {s.columns.map(c=><label key={c.key}>
       <input type="checkbox" checked={!layout.hiddenColumns.includes(c.key)}
        onChange={()=>switchIn("hiddenColumns",c.key)}/>
       <span>{c.label}</span>
      </label>)}
     </div>}
    </div>;
   })}
  </div>
  <div className={css.summary} role="status">Showing 3 identity columns + {visible.length} of 29 optional columns.
   {" "}Swipe horizontally for additional fields.</div>
  <div className={css.scroll} role="region" tabIndex={0} aria-label="Scrollable POOL master trial spreadsheet">
   <table className={css.table}>
    <thead><tr>
     <th scope="col" className={css.ticker}>Ticker</th>
     <th scope="col" className={css.company}>Company</th>
     <th scope="col" className={css.nct}>NCT ID</th>
     {visible.map(c=><th scope="col" className={css.dataColumn} key={c.key}>{c.label}</th>)}
    </tr></thead>
    <tbody>{rows.map(row=>{
     const nct=nctOf(row);
     return <tr key={row.id}>
      <td className={css.ticker}>{known(row.ticker)}</td>
      <td className={css.company}>{known(row.company)}</td>
      <td className={css.nct}>{nct?
       <a href={"https://clinicaltrials.gov/study/"+nct} target="_blank" rel="noopener noreferrer">{nct}</a>:
       <span title={row.id}>Non-trial record</span>}</td>
      {visible.map(c=>{
       const data=contentFor(row,c.key);
       return <td className={css.dataColumn} key={c.key}>{data.url?
        <a href={data.url} target="_blank" rel="noopener noreferrer">{data.text}</a>:data.text}</td>;
      })}
     </tr>;
    })}</tbody>
   </table>
  </div>
  <p className={css.foot}>Qualification fields are sourced only when evidence is available. Not on the saved FOCUS roster does not mean a trial failed eligibility. POOL remains unrestricted; this is the current paginated source view, not a full export.</p>
 </section>;
}
