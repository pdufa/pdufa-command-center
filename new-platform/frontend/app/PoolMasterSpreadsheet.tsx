"use client";

import {useEffect,useMemo,useState,type DragEvent} from "react";
import {POOL_PHASE_OPTIONS,togglePoolPhase,type PoolPhaseSelection,type PoolPhase} from "../lib/pool-phase-options";
import {POOL_SORT_KEYS,type PoolSortSpec,type PoolSortKey} from "../lib/pool-full-sort";
import snapshot from "../data/p3PostDataActive.json";
import focusDesignations from "../data/focusFdaDesignations.json";
import css from "./PoolMasterSpreadsheet.module.css";
import TickerChartButton from "./TickerChartButton";
import {POOL_DETAIL_FIELDS,type PoolDetailField,type PoolRegistryDetail} from "../lib/pool-registry-details";
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
type Key=PoolDetailField|"phase"|"status"|"drug"|"intervention"|"route"|"indication"
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
  {key:"route",label:"Administration route"},{key:"indication",label:"Indication / disease"},
  {key:"studyTitle",label:"Official study title"},{key:"leadSponsor",label:"Lead study sponsor"},
  {key:"studyDesign",label:"Registered trial design"},{key:"treatmentArms",label:"Arms / comparator"},
  {key:"enrollment",label:"Recorded enrollment"},{key:"eligibility",label:"Patient eligibility criteria"},
  {key:"primaryEndpoints",label:"Primary endpoints"},{key:"secondaryEndpoints",label:"Secondary endpoints"},
  {key:"reportedResults",label:"Published numeric outcome results"},
  {key:"safetyResults",label:"Reported adverse-event counts"},
  {key:"studyLocations",label:"Trial locations / countries"}]},
 {key:"dates",label:"Dates & Sources",columns:[
  {key:"start",label:"Trial start date"},{key:"primary",label:"Primary completion"},
  {key:"complete",label:"Study completion"},{key:"posted",label:"Results posted"},
  {key:"updated",label:"Source updated"},{key:"source",label:"Source URL"},
  {key:"checked",label:"Last checked"},
  {key:"milestoneDateTypes",label:"Actual / estimated milestone dates"},
  {key:"terminationReason",label:"Termination / suspension reason"},
  {key:"documentsPublications",label:"Protocols / publications"}]},
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
const COLUMN_INFO:Record<Key,string>={
 "phase": "Clinical or regulatory stage recorded by the published POOL source. Use the Phase filter to select source stages.",
 "status": "Trial recruitment or completion status, when provided by the source. A completed trial is not necessarily successful.",
 "drug": "Drug, device, or intervention under study, as reported in the source record.",
 "intervention": "Type of intervention (for example, drug or biological) if recorded.",
 "route": "How the treatment is administered, if independently documented.",
 "indication": "Condition or disease being studied; one trial may have multiple indicated conditions.",
 "start": "Recorded study start date. This is not the date of first dosing unless the source specifies it.",
 "primary": "Date when primary outcome collection ended or is expected to end.",
 "complete": "Recorded or planned study completion date; distinct from a results announcement.",
 "posted": "Date the study's results were posted to a public registry.",
 "updated": "Latest modification timestamp supplied by the source registry.",
 "source": "Link to the underlying ClinicalTrials.gov study when an exact NCT ID is known.",
 "checked": "Timestamp when the source was most recently checked for this entry.",
 "traded": "Whether the issuer is publicly traded. An unverified value is not a failure.",
 "exchange": "Stock exchange on which the issuer trades; requires current listing evidence.",
 "cap": "Market capitalization in US dollars, if a sourced value is available. Historic figures are not live quotations.",
 "capDate": "Quote as-of date, if independently recorded for the exact market-cap value. The FOCUS roster snapshot date is not the quote date.",
 "capQualified": "Whether a sourced market cap falls within $300 million to $10 billion. Historical values need rechecking.",
 "phase3": "Whether published evidence establishes Phase 3 reached or entered.",
 "publicResults": "Whether Phase 3 results are publicly available for the exact drug–indication program.",
 "fdaPath": "Evidence of an active United States FDA approval pathway.",
 "application": "Recorded stage of the FDA application, when independently documented.",
 "pdufa": "Official FDA target decision date for the specific application, if verified.",
 "designations": "FDA special designations linked to the exact program, when documented.",
 "focusQualified": "Whether this exact NCT and issuer appear in the saved FOCUS roster. Absence is not a failed qualification.",
 "reason": "Source-backed explanation for inclusion or pending eligibility checks.",
 "evidence": "Links to evidence supporting the qualification assessment; missing links require review.",
 "completeness": "Whether supporting evidence has been reviewed and how much remains missing.",
 "reviewed": "Date of the most recent saved FOCUS eligibility review.",
 "studyTitle": "Official registered title from the live ClinicalTrials.gov record. Use Load registry details for this NCT.",
 "leadSponsor": "Lead sponsor recorded in the live registry; not automatically the commercial rights holder.",
 "studyDesign": "Study type, allocation, intervention model, masking and registered purpose.",
 "treatmentArms": "Registered treatment and comparator arms; not a clinical effect estimate.",
 "enrollment": "Recorded actual or anticipated enrollment with the registry-reported type.",
 "eligibility": "Published trial inclusion and exclusion criteria, as source text.",
 "primaryEndpoints": "Prespecified primary endpoints and their time frames, not a pass/fail verdict.",
 "secondaryEndpoints": "Prespecified secondary endpoints and their time frames.",
 "reportedResults": "Only numeric group-level measurements actually posted in the official results module. Missing data are not zero.",
 "safetyResults": "Published adverse event group counts and denominators, if posted. No inferred safety ranking.",
 "studyLocations": "Registered site cities, states and countries as reported by the source.",
 "milestoneDateTypes": "Start and completion dates with the registry ACTUAL / ESTIMATED designation.",
 "terminationReason": "Registry-provided reason for termination or suspension when applicable.",
 "documentsPublications": "Source-reported publications and attached protocols / study documents."
};
const IDENTITY_INFO={ticker:"Stock ticker reported in the POOL source. A ticker alone does not establish a current listing.",company:"Company name associated with the trial in the published POOL source.",nct:"ClinicalTrials.gov identifier (NCT ID) for the exact trial; opens the official study record."} as const;
const known=(v:unknown)=>typeof v==="string"&&v.trim()?v:"Not verified";
const formatCap=(n:number)=>n.toLocaleString("en-US",{style:"currency",currency:"USD",maximumFractionDigits:0});
const focusByTrial=new Map(snapshot.records.map(r=>[r.nct+"|"+r.ticker.toUpperCase(),r]));
const designationByTrial=new Map(focusDesignations.records.map(r=>[r.nct+"|"+r.ticker.toUpperCase(),r]));
const quoteDateFor=(focus:(typeof snapshot.records)[number])=>{
 const date:unknown="marketCapAsOf" in focus?focus.marketCapAsOf:null;
 return known(date);
};
const nctOf=(r:PoolMasterRow)=>{
 const value=r.nctId||(r.id.startsWith("TRIAL|")?r.id.slice(6):"");
 return /^NCT\d{8}$/.test(value)?value:"";
};
function contentFor(row:PoolMasterRow,key:Key,details:PoolRegistryDetail|null):{text:string;url?:string}{
 const nct=nctOf(row);
 const focus=nct?focusByTrial.get(nct+"|"+row.ticker.toUpperCase()):undefined;
 const cap=focus?.marketCap??row.marketCap;
 const sourceUrl=row.sourceUrl||(nct?"https://clinicaltrials.gov/study/"+nct:undefined);
 if(POOL_DETAIL_FIELDS.includes(key as PoolDetailField)){
   if(!details||details.nctId!==nct)return{text:"Load registry details using the NCT button"};
   const value=details.fields[key as PoolDetailField];
   return{text:value||"Not reported in this registry record"};
 }
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
  case "capDate":return{text:focus?quoteDateFor(focus):known(row.capChecked)};
  case "capQualified":return{text:focus?"Pass (FOCUS snapshot)":row.capInRange===true?"Historical in range — recheck":"Not verified"};
  case "phase3":return{text:focus||/Phase 3|PHASE3/i.test(row.stage||"")?"Recorded":"Not verified"};
  case "publicResults":return{text:focus?"Yes — source in FOCUS":row.phase3Source?"Source recorded — review":"Not verified"};
  case "fdaPath":return{text:focus?"Recorded FOCUS path":"Not verified"};
  case "application":return{text:focus?focus.fdaStatus:"Not verified"};
  case "pdufa":return{text:"Not verified at exact-trial level"};
  case "designations":{const d=nct?designationByTrial.get(nct+"|"+row.ticker.toUpperCase()):undefined;
   return d?.designations.length?{text:d.designations.map(x=>x.label).join(" · "),url:d.designations[0].sourceUrl}:{text:"Not verified"};}
  case "focusQualified":return{text:focus?"In FOCUS":"Not on current FOCUS roster — unassessed"};
  case "reason":return{text:focus?"Exact NCT + ticker matches the saved FOCUS roster":"FOCUS gates not established for this record"};
  case "evidence":return focus?{text:"Results evidence",url:focus.resultsUrl}:
   row.capSource?{text:"Market-cap source",url:row.capSource}:{text:"Not verified"};
  case "completeness":return{text:focus?"FOCUS source links recorded; full evidence not assessed":"Not assessed"};
  case "reviewed":return{text:focus?snapshot.asOf:"Not assessed"};
 }
 return{text:"Not reported"};
}
export default function PoolMasterSpreadsheet({rows,loading=false,error="",selectedPhases,onPhasesChange,stageCounts,sort,onSortChange}:{rows:PoolMasterRow[];loading?:boolean;error?:string;
 selectedPhases:PoolPhaseSelection;onPhasesChange:(next:PoolPhaseSelection)=>void;
 stageCounts?:Record<string,{trials:number}>;
 sort:PoolSortSpec|null;onSortChange:(next:PoolSortSpec|null)=>void}){
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
 const resetView=()=>edit(l=>{
  const defaults=defaultLayout(view);
  return {...l,expanded:defaults.expanded,hiddenSegments:defaults.hiddenSegments,
   hiddenColumns:defaults.hiddenColumns};
 });
 const [orderEditorOpen,setOrderEditorOpen]=useState(false);
 const [reorderNotice,setReorderNotice]=useState("");
 const [phaseOpen,setPhaseOpen]=useState(false);
 const [registryByNct,setRegistryByNct]=useState<Record<string,PoolRegistryDetail>>({});
 const [registryBusy,setRegistryBusy]=useState<Record<string,boolean>>({});
 const [registryError,setRegistryError]=useState<Record<string,string>>({});
 const loadRegistry=async(nct:string)=>{
  if(!/^NCT\d{8}$/.test(nct)||registryBusy[nct])return;
  setRegistryBusy(p=>({...p,[nct]:true}));
  setRegistryError(p=>({...p,[nct]:""}));
  try{
   const response=await fetch("/api/pool-registry-details?nct="+encodeURIComponent(nct),{cache:"no-store"});
   if(!response.ok)throw Error(response.status===401?"Sign in to view source details.":"Official registry lookup unavailable.");
   const result:PoolRegistryDetail=await response.json() as PoolRegistryDetail;
   if(result.nctId!==nct||result.sourceUrl!=="https://clinicaltrials.gov/study/"+nct||
      result.total!==14||!result.fields)throw Error("Registry trial identity mismatch.");
   setRegistryByNct(p=>({...p,[nct]:result}));
  }catch(e){
   setRegistryError(p=>({...p,[nct]:e instanceof Error?e.message:"Registry lookup unavailable."}));
  }finally{setRegistryBusy(p=>({...p,[nct]:false}));}
 };
 const [latestDownloadChoice,setLatestDownloadChoice]=useState<"registered"|"discovered"|null>(null);
 const [infoKey,setInfoKey]=useState<Key|"ticker"|"company"|"nct"|null>(null);
 const updatePhases=(selection:PoolPhaseSelection)=>onPhasesChange(selection);
 const updateSort=(key:Key|"ticker"|"company"|"nct")=>{
  if(!POOL_SORT_KEYS.includes(key as PoolSortKey))return;
  onSortChange(sort?.key!==key?{key:key as PoolSortKey,direction:"asc"}:
   sort.direction==="asc"?{key:key as PoolSortKey,direction:"desc"}:null);
 };
 // Sorted server-side before pagination, retaining the published source row data.
 const sortedRows=rows;
 const sortLabel=(key:Key|"ticker"|"company"|"nct")=>sort?.key!==key?"↕":sort.direction==="asc"?"↑":"↓";
 const sortOrder=(key:Key|"ticker"|"company"|"nct")=>sort?.key!==key?"none":sort.direction==="asc"?"ascending":"descending";
 const showInfo=(key:Key|"ticker"|"company"|"nct")=>setInfoKey(previous=>previous===key?null:key);
 const infoText=infoKey===null?"":infoKey in IDENTITY_INFO
  ?IDENTITY_INFO[infoKey as keyof typeof IDENTITY_INFO]:COLUMN_INFO[infoKey as Key];
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

 const renderHeaderControls=(key:Key|"ticker"|"company"|"nct",label:string)=><span className={css.headerContents}>
  <span className={css.headerLabel}>{label}</span>
  <span className={css.headerButtons}>
   {POOL_SORT_KEYS.includes(key as PoolSortKey)&&<button type="button" className={css.sortButton}
    onClick={()=>updateSort(key)}
    aria-label={"Sort "+label+" across all POOL trials; "+(sort?.key===key?sort.direction:"unsorted")}
    title="Sort all matching POOL trials: ascending → descending → original">{sortLabel(key)}</button>}
   <button type="button" className={css.infoButton} onClick={()=>showInfo(key)}
    aria-label={"Information about "+label} aria-expanded={infoKey===key}
    aria-controls="pool-column-information" title={"Information: "+label}>ⓘ</button>
  </span>
 </span>;
 return <section aria-label="POOL Master Spreadsheet with responsive column visibility" data-pool-master="true" className={css.section}>
  <div className={css.top}>
   <div><h3>POOL Master · {3+ALL_KEYS.length} columns</h3>
    <p>All phases stay in POOL. Four existing expandable segments now include 14 additional official-registry data fields. Select Load registry details beside an NCT to retrieve its source facts on demand; absent results remain unreported. Drag segments or headings to reorder; display changes never modify source records.</p></div>
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
  <div className={css.phaseToolbar} aria-label="POOL phase selection controls">
   <button type="button" className={css.phaseButton} data-phase-active={selectedPhases===null?"all":"filtered"}
    aria-expanded={phaseOpen} aria-controls="pool-phase-checklist"
    onClick={()=>setPhaseOpen(open=>!open)}>
    <span>PHASE</span><small>{selectedPhases===null?"All Phases":selectedPhases.length+" selected"} · {phaseOpen?"Close":"Select"}</small>
   </button>
   <button type="button" className={css.phaseReset} onClick={()=>updatePhases(null)}>
    Reset Phases
   </button>
  </div>
  {phaseOpen&&<fieldset id="pool-phase-checklist" className={css.phasePanel}>
   <legend>Filter POOL trials by stage</legend>
   <div className={css.phaseSelectActions}>
    <label><input type="checkbox" checked={selectedPhases===null}
     onChange={()=>updatePhases(selectedPhases===null?[]:null)}/> All Phases (show everything)</label>
    <button type="button" className={css.phaseReset} onClick={()=>updatePhases(null)}>Reset</button>
   </div>
   <div className={css.phaseChoices}>
    {POOL_PHASE_OPTIONS.map(phase=><label key={phase}>
     <input type="checkbox" checked={selectedPhases===null||selectedPhases.includes(phase)}
      onChange={()=>updatePhases(togglePoolPhase(selectedPhases,phase as PoolPhase))}/>
     <span>{phase}</span>
     {stageCounts?.[phase]&&<small>{stageCounts[phase].trials.toLocaleString()}</small>}
    </label>)}
   </div>
   <p>Clinical phases and recorded regulatory stages are shown. Selections filter the complete published POOL before pagination.</p>
  </fieldset>}
  <div className={css.latestDownloadToolbar} role="group" aria-label="Latest-download trial highlighting">
   <button type="button" className={css.registeredButton}
    aria-pressed={latestDownloadChoice==="registered"}
    onClick={()=>setLatestDownloadChoice(current=>current==="registered"?null:"registered")}>
    <span>Newly Registered</span>
    <small>{latestDownloadChoice==="registered"?"Selected":"Highlight"}</small>
   </button>
   <button type="button" className={css.discoveredButton}
    aria-pressed={latestDownloadChoice==="discovered"}
    onClick={()=>setLatestDownloadChoice(current=>current==="discovered"?null:"discovered")}>
    <span>Newly Discovered</span>
    <small>{latestDownloadChoice==="discovered"?"Selected":"Highlight"}</small>
   </button>
  </div>
  {latestDownloadChoice!==null&&<p className={css.downloadPending} role="status">
   {latestDownloadChoice==="registered"?"Newly Registered":"Newly Discovered"} is selected.
   Verified previous-download comparison data is not yet available to this POOL view,
   so trial rows are not classified or hidden. No records have been marked new.
  </p>}
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
      <button type="button" className={css.visibilityToggle}
       aria-label={(active===columns.length?"Uncheck All":"Check All")+" columns in "+s.label}
       onClick={()=>edit(l=>{
        const allChecked=columns.every(key=>!l.hiddenColumns.includes(key));
        return {...l,hiddenColumns:allChecked
         ?[...new Set([...l.hiddenColumns,...columns])]
         :l.hiddenColumns.filter(key=>!columns.includes(key))};
       })}>{active===columns.length?"Uncheck All":"Check All"}</button>
      <button type="button" className={css.visibilityToggle}
       aria-expanded={expanded&&!hidden}
       aria-label={(expanded&&!hidden?"Hide Section":"Show Section")+" "+s.label}
       onClick={()=>edit(l=>{
        const showing=l.hiddenSegments.includes(s.key)||!l.expanded.includes(s.key);
        return {...l,hiddenSegments:l.hiddenSegments.filter(key=>key!==s.key),
         expanded:showing?[...new Set([...l.expanded,s.key])]:l.expanded.filter(key=>key!==s.key)};
       })}>{expanded&&!hidden?"Hide Section":"Show Section"}</button>
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
  <div className={css.summary} role="status">Showing 3 identity columns + {visible.length} of {ALL_KEYS.length} optional columns.
   {" "}Swipe horizontally for additional fields. {reorderNotice}
   {sort&&" Sorted by "+(sort.key in IDENTITY_INFO?sort.key:COLUMN_LOOKUP.get(sort.key as Key)?.label)+" ("+sort.direction+"), all matching POOL trials."}
  </div>
  {infoKey!==null&&<aside id="pool-column-information" className={css.infoPanel} role="note">
   <div><strong>ⓘ {infoKey in IDENTITY_INFO?infoKey==="nct"?"NCT ID":infoKey==="ticker"?"Ticker":"Company":COLUMN_LOOKUP.get(infoKey as Key)?.label}</strong>
    <p>{infoText}</p></div>
   <button type="button" onClick={()=>setInfoKey(null)} aria-label="Close column information">Close</button>
  </aside>}
  <p className={css.sortScope}>Sort arrows (↕) sort all matching POOL trials before pagination; use another tap for descending and a third to restore original order. Columns without a sortable source value show only an information button. Phase checkboxes filter the full POOL.</p>
  <div className={css.scroll} role="region" tabIndex={0} aria-label="Scrollable POOL master trial spreadsheet">
   <table className={css.table}>
    <thead><tr>
     <th scope="col" className={css.ticker} aria-sort={sortOrder("ticker")}>{renderHeaderControls("ticker","Ticker")}</th>
     <th scope="col" className={css.company} aria-sort={sortOrder("company")}>{renderHeaderControls("company","Company")}</th>
     <th scope="col" className={css.nct} aria-sort={sortOrder("nct")}>{renderHeaderControls("nct","NCT ID")}</th>
     {visible.map(c=><th scope="col" className={css.dataColumn} key={c.key} aria-sort={sortOrder(c.key)}
      draggable={orderEditorOpen} title={orderEditorOpen?"Drag to move "+c.label:c.label}
      onDragStart={event=>dragStart(event,"column",c.key)}
      onDragOver={acceptDrag}
      onDrop={event=>dropOnColumn(event,findSegment(c.key),c.key)}>
       {orderEditorOpen&&<span className={css.thDrag}>⠿</span>}
       {renderHeaderControls(c.key,c.label)}</th>)}
    </tr></thead>
    <tbody>{sortedRows.length===0&&<tr><td colSpan={3+visible.length} role="status">
       {loading?"Loading clinical POOL records…":error?
        "No clinical records loaded. Sign in or retry when the source is available.":
        "No matching clinical trials on this page."}
     </td></tr>}{sortedRows.map(row=>{
     const nct=nctOf(row);
     return <tr key={row.id}>
      <td className={css.ticker}><TickerChartButton ticker={row.ticker}/></td>
      <td className={css.company}>{known(row.company)}</td>
      <td className={css.nct}>{nct?
       <a href={"https://clinicaltrials.gov/study/"+nct} target="_blank" rel="noopener noreferrer">{nct}</a>:
       <span title={row.id}>Non-trial record</span>}
       {nct&&<div className={css.registryAction}>
        <button type="button" disabled={!!registryBusy[nct]} onClick={()=>void loadRegistry(nct)}
         aria-label={"Load official registry details for "+nct}>
         {registryBusy[nct]?"Loading registry…":registryByNct[nct]?"Refresh registry details":"Load registry details"}
        </button>
        {registryByNct[nct]&&<small>Registry: {registryByNct[nct].available}/14 fields · {registryByNct[nct].retrievedAt.slice(0,10)}</small>}
        {registryError[nct]&&<small role="alert">{registryError[nct]}</small>}
       </div>}</td>
      {visible.map(c=>{
       const data=contentFor(row,c.key,nct?registryByNct[nct]??null:null);
       return <td className={css.dataColumn} key={c.key}>{data.url?
        <a href={data.url} target="_blank" rel="noopener noreferrer">{data.text}</a>:data.text}</td>;
      })}
     </tr>;
    })}</tbody>
   </table>
  </div>
  <p className={css.foot}>New registry fields are fetched on demand from ClinicalTrials.gov and shown read-only in this web view; they are not yet stored in the 16-column Google Sheet. Missing fields are not assumed zero or scored. Qualification fields are sourced only when evidence is available. Not on the saved FOCUS roster does not mean a trial failed eligibility. POOL remains unrestricted; this is the current paginated source view, not a full export.</p>
 </section>;
}
