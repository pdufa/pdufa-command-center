"use client";

import {useEffect,useMemo,useState,type DragEvent} from "react";
import snapshot from "../data/p3PostDataActive.json";
import css from "./PoolMasterSpreadsheet.module.css";
import {isGroupVisible,toggleColumnGroup} from "../lib/pool-column-visibility";
import {normalizePoolColumnOrder,reorderPoolSegment,stepPoolSegment,movePoolColumn,stepPoolColumn} from "../lib/pool-column-order";

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
type Layout={expanded:string[];hiddenSegments:string[];hiddenColumns:Key[];
 segmentOrder:string[];columnOrder:Record<string,Key[]>};
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
const GROUP_CLINICAL=["clinical","dates"] as const;
const GROUP_QUALIFICATION=["qualifiers","focus"] as const;
const DEFAULT_COLUMNS_BY_SEGMENT:Record<string,readonly Key[]>=Object.fromEntries(
 SEGMENTS.map(s=>[s.key,s.columns.map(c=>c.key)]));
const COLUMN_LOOKUP=new Map(SEGMENTS.flatMap(s=>s.columns.map(c=>[c.key,c] as const)));

const storageKey=(view:View)=>"pdufa:pool-column-layout:v1:"+view;
const defaultLayout=(view:View):Layout=>({
 expanded:view==="phone"?["focus"]:["qualifiers","focus"],
 hiddenSegments:[],hiddenColumns:[],
 ...normalizePoolColumnOrder(null,DEFAULT_COLUMNS_BY_SEGMENT,ALL_SEGMENTS)
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
   ...normalizePoolColumnOrder(candidate,DEFAULT_COLUMNS_BY_SEGMENT,ALL_SEGMENTS),
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
export default function PoolMasterSpreadsheet({rows,loading=false,error=""}:{rows:PoolMasterRow[];loading?:boolean;error?:string}){
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
 const switchIn=(key:"expanded"|"hiddenSegments"|"hiddenColumns",id:string)=>edit(l=>{
  if(key==="hiddenColumns"){
   const col=id as Key;
   return {...l,hiddenColumns:l.hiddenColumns.includes(col)
    ?l.hiddenColumns.filter(x=>x!==col):[...l.hiddenColumns,col]};
  }
  const list=l[key];
  return {...l,[key]:list.includes(id)?list.filter(x=>x!==id):[...list,id]};
 });
 const orderedSegments=useMemo(()=>layout.segmentOrder.map(key=>SEGMENTS.find(s=>s.key===key)!),[layout.segmentOrder]);
 const COLUMNS_BY_SEGMENT=layout.columnOrder;
 const visible=useMemo(()=>orderedSegments
  .filter(s=>layout.expanded.includes(s.key)&&!layout.hiddenSegments.includes(s.key))
  .flatMap(s=>(layout.columnOrder[s.key]||[]).filter(key=>!layout.hiddenColumns.includes(key))
   .map(key=>COLUMN_LOOKUP.get(key)!)),[layout,orderedSegments]);
 const clinicalVisible=isGroupVisible(layout,GROUP_CLINICAL,COLUMNS_BY_SEGMENT);
 const qualificationVisible=isGroupVisible(layout,GROUP_QUALIFICATION,COLUMNS_BY_SEGMENT);
 const toggleClinical=()=>edit(l=>({...l,...toggleColumnGroup(l,GROUP_CLINICAL,l.columnOrder)}));
 const toggleQualification=()=>edit(l=>({...l,...toggleColumnGroup(l,GROUP_QUALIFICATION,l.columnOrder)}));
 const resetView=()=>edit(()=>defaultLayout(view));
 const [orderEditorOpen,setOrderEditorOpen]=useState(false);
 const [reorderNotice,setReorderNotice]=useState("");
 const resetColumnOrder=()=>{
  edit(l=>({...l,...normalizePoolColumnOrder(null,DEFAULT_COLUMNS_BY_SEGMENT,ALL_SEGMENTS)}));
  setReorderNotice("Column and segment order restored. Existing visibility settings were kept.");
 };
 const toggleOrderEditor=()=>{
  setOrderEditorOpen(open=>!open);
  setReorderNotice("");
 };
 const shiftSegment=(id:string,direction:-1|1)=>edit(l=>({...l,...stepPoolSegment(l,id,direction)}));
 const shiftColumn=(key:Key,direction:-1|1)=>edit(l=>({...l,...stepPoolColumn(l,key,direction)}));
 const transferColumn=(key:Key,target:string)=>edit(l=>{
  const shifted={...l,...movePoolColumn(l,key,target)};
  return {...shifted,expanded:[...new Set([...shifted.expanded,target])],
   hiddenSegments:shifted.hiddenSegments.filter(s=>s!==target),
   hiddenColumns:shifted.hiddenColumns.filter(k=>k!==key)};
 });
 const dragStart=(event:DragEvent<HTMLElement>,kind:"segment"|"column",id:string)=>{
  event.dataTransfer.setData("text/plain","pool-"+kind+":"+id);
  event.dataTransfer.effectAllowed="move";
 };
 const acceptDrag=(event:DragEvent<HTMLElement>)=>{event.preventDefault();event.dataTransfer.dropEffect="move";};
 const dropOnSegment=(event:DragEvent<HTMLElement>,target:string)=>{
  event.preventDefault();
  const value=event.dataTransfer.getData("text/plain");
  if(value.startsWith("pool-segment:")){
   const source=value.slice("pool-segment:".length);
   edit(l=>({...l,...reorderPoolSegment(l,source,target)}));
   setReorderNotice("Segment order updated.");
  }else if(value.startsWith("pool-column:")){
   const key=value.slice("pool-column:".length) as Key;
   if(ALL_KEYS.includes(key)){transferColumn(key,target);setReorderNotice("Column moved into "+target+".");}
  }
 };
 const dropOnColumn=(event:DragEvent<HTMLElement>,targetSegment:string,targetKey:Key)=>{
  event.preventDefault();event.stopPropagation();
  const value=event.dataTransfer.getData("text/plain");
  if(!value.startsWith("pool-column:"))return;
  const key=value.slice("pool-column:".length) as Key;
  if(!ALL_KEYS.includes(key))return;
  edit(l=>({...l,...movePoolColumn(l,key,targetSegment,targetKey)}));
  setReorderNotice("Column order updated.");
 };
 const findSegment=(key:Key)=>layout.segmentOrder.find(id=>layout.columnOrder[id].includes(key))||"";

 return <section aria-label="POOL Master Spreadsheet with responsive column visibility" data-pool-master="true" className={css.section}>
  <div className={css.top}>
   <div><h3>POOL Master · 32 columns</h3>
    <p>All stages stay in POOL. Drag segment handles or column headings to reorder, or use move arrows on phone. Choose a segment to transfer a column. These changes affect display only.</p></div>
   <div className={css.actions} aria-label="Independent POOL column group visibility">
    <button type="button" className={css.groupButton} data-visibility={clinicalVisible?"visible":"hidden"}
     aria-pressed={clinicalVisible} onClick={toggleClinical}
     aria-label={"Clinical and Dates — "+(clinicalVisible?"Hide All":"Show All")}>
     <span>Clinical &amp; Dates</span>
     <small>{clinicalVisible?"Hide All":"Show All"}</small>
    </button>
    <button type="button" className={css.groupButton} data-visibility={qualificationVisible?"visible":"hidden"}
     aria-pressed={qualificationVisible} onClick={toggleQualification}
     aria-label={"Qualification and FOCUS — "+(qualificationVisible?"Hide All":"Show All")}>
     <span>Qualification &amp; FOCUS</span>
     <small>{qualificationVisible?"Hide All":"Show All"}</small>
    </button>
    <button type="button" className={css.resetOrder} data-editor-open={orderEditorOpen?"true":"false"}
     onClick={toggleOrderEditor} aria-pressed={orderEditorOpen} aria-expanded={orderEditorOpen}
     aria-controls="pool-column-editor" aria-label={"Column Order — "+(orderEditorOpen?"Close":"Open")+" editor"}
     title={orderEditorOpen?"Close column ordering controls":"Open column ordering controls"}>
     <span>Column Order</span>
     <small>{orderEditorOpen?"Close":"Edit"}</small>
    </button>
   </div>
  </div>
  <p className={css.viewport} data-viewport={view}>
   {view==="phone"?"Phone: data columns use 50% of viewport width; Ticker stays pinned.":
   "PC: data columns adapt from 180–260px; Ticker, Company, and NCT ID stay pinned."}
   {" "}Layouts are saved separately on this device.
   {" "}<button className={css.resetLink} type="button" onClick={resetView}>Reset {view==="phone"?"Phone":"PC"} View</button>
  </p>
  {orderEditorOpen&&<div className={css.orderEditor} id="pool-column-editor" role="region"
   aria-label="Column order editing controls">
   <div className={css.orderEditorHeading}>
    <div>
     <strong>Column ordering is enabled</strong>
     <p>Move segments or individual columns with the arrows, drag handles, or destination dropdowns.
      Columns and segments open below for editing, including currently hidden ones.</p>
    </div>
    <button type="button" className={css.resetColumnAction} onClick={resetColumnOrder}>
     Reset Column Order
    </button>
   </div>
   <p>Changes save automatically for this device’s {view==="phone"?"phone":"PC"} view. Reset restores the
    original column arrangement without changing hidden columns.</p>
  </div>}
  <p className={css.reorderHint}>{orderEditorOpen
   ?"Use the arrows or drag handles below to change order; the spreadsheet updates immediately."
   :"Tap Column Order above to show ordering controls. The button opens an editor; it does not automatically rearrange your columns."}</p>
  <div className={css.segments} role="group" aria-label="POOL column segments">
   {orderedSegments.map((s,segmentIndex)=>{
    const hidden=layout.hiddenSegments.includes(s.key),expanded=layout.expanded.includes(s.key);
    const columns=layout.columnOrder[s.key]||[];
    const active=columns.filter(k=>!layout.hiddenColumns.includes(k)).length;
    return <div key={s.key} className={css.segment} data-segment={s.key}
     onDragOver={acceptDrag} onDrop={event=>dropOnSegment(event,s.key)}>
     <div className={css.segmentHead}>
      {orderEditorOpen&&<>
       <span className={css.dragHandle} draggable="true" title="Drag to reorder segment"
        onDragStart={event=>dragStart(event,"segment",s.key)}>⠿</span>
       <div className={css.movePair} role="group" aria-label={"Reorder "+s.label+" segment"}>
        <button type="button" aria-label={"Move "+s.label+" segment left"} disabled={segmentIndex===0}
         onClick={()=>shiftSegment(s.key,-1)}>←</button>
        <button type="button" aria-label={"Move "+s.label+" segment right"} disabled={segmentIndex===orderedSegments.length-1}
         onClick={()=>shiftSegment(s.key,1)}>→</button>
       </div>
      </>}
      <button type="button" className={css.segmentToggle} aria-expanded={!hidden&&expanded}
       aria-pressed={!hidden&&expanded} disabled={hidden} onClick={()=>switchIn("expanded",s.key)}>
       {expanded&&!hidden?"▾":"▸"} {s.label} <small>{active}/{columns.length}</small>
      </button>
      <button type="button" className={css.visibilityToggle} aria-pressed={hidden}
       onClick={()=>switchIn("hiddenSegments",s.key)}>{hidden?"Restore":"Hide segment"}</button>
     </div>
     {(orderEditorOpen||(expanded&&!hidden))&&<div className={css.columnOptions}>
      {columns.map((key,columnIndex)=>{
       const c=COLUMN_LOOKUP.get(key)!;
       return <div className={css.columnOption} key={key}
        onDragOver={acceptDrag} onDrop={event=>dropOnColumn(event,s.key,key)}>
        {orderEditorOpen&&<span className={css.dragHandle} draggable="true" title={"Drag "+c.label+" to reorder"}
         onDragStart={event=>dragStart(event,"column",key)}>⠿</span>}
        <label className={css.columnCheck}>
         <input type="checkbox" checked={!layout.hiddenColumns.includes(key)}
          onChange={()=>switchIn("hiddenColumns",key)}/>
         <span>{c.label}</span>
        </label>
        {orderEditorOpen&&<>
         <div className={css.movePair} role="group" aria-label={"Reorder "+c.label}>
          <button type="button" aria-label={"Move "+c.label+" left"} disabled={columnIndex===0}
           onClick={()=>shiftColumn(key,-1)}>←</button>
          <button type="button" aria-label={"Move "+c.label+" right"} disabled={columnIndex===columns.length-1}
           onClick={()=>shiftColumn(key,1)}>→</button>
         </div>
         <select className={css.moveTo} aria-label={"Move "+c.label+" to another segment"}
          value={s.key} onChange={event=>transferColumn(key,event.target.value)}>
          {orderedSegments.map(segment=><option key={segment.key} value={segment.key}>{segment.label}</option>)}
         </select>
        </>}
       </div>;
      })}
     </div>}
    </div>;
   })}
  </div>
  <div className={css.summary} role="status">Showing 3 identity columns + {visible.length} of 29 optional columns.
   {" "}Swipe horizontally for additional fields. {reorderNotice}</div>
  <div className={css.scroll} role="region" tabIndex={0} aria-label="Scrollable POOL master trial spreadsheet">
   <table className={css.table}>
    <thead><tr>
     <th scope="col" className={css.ticker}>Ticker</th>
     <th scope="col" className={css.company}>Company</th>
     <th scope="col" className={css.nct}>NCT ID</th>
     {visible.map(c=><th scope="col" className={css.dataColumn} key={c.key}
      draggable={orderEditorOpen} title={orderEditorOpen?"Drag to move "+c.label:c.label}
      onDragStart={event=>dragStart(event,"column",c.key)}
      onDragOver={acceptDrag}
      onDrop={event=>dropOnColumn(event,findSegment(c.key),c.key)}>
       {orderEditorOpen&&<span className={css.thDrag}>⠿</span>} {c.label}</th>)}
    </tr></thead>
    <tbody>{rows.length===0&&<tr><td colSpan={3+visible.length} role="status">
       {loading?"Loading clinical POOL records…":error?
        "No clinical records loaded. Sign in or retry when the source is available.":
        "No matching clinical trials on this page."}
     </td></tr>}{rows.map(row=>{
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
