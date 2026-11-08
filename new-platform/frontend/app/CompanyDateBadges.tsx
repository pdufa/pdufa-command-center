"use client";
import {useEffect,useState,type CSSProperties} from "react";
import {pacificToday,pipelineDayCounts,type TimelineDates} from "../lib/pipeline-timeline";
import primaryPValues from "../data/focusPrimaryEndpointPValues.json";
/** D and P counters with exact-program source-verified or explicitly recorded, unverified dates. */
const valid=(value:string|null|undefined):value is string=>
 typeof value==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(value)&&
 !Number.isNaN(Date.parse(value+"T00:00:00Z"))&&
 new Date(value+"T00:00:00Z").toISOString().slice(0,10)===value;
const dayDifference=(later:string,earlier:string)=>
 Math.round((Date.parse(later+"T00:00:00Z")-Date.parse(earlier+"T00:00:00Z"))/86400000);
export default function CompanyDateBadges({
 timeline,today,nctId,recordedReleaseDate,recordedPdufaDate,releaseSource,pdufaSource
}:{timeline?:TimelineDates|null;today?:string;nctId?:string;
 recordedReleaseDate?:string|null;recordedPdufaDate?:string|null;
 releaseSource?:string|null;pdufaSource?:string|null}){
 const [localToday,setLocalToday]=useState("");
 useEffect(()=>{if(today)return;const update=()=>setLocalToday(pacificToday());
   update();const id=setInterval(update,60000);return()=>clearInterval(id);},[today]);
 const current=today||localToday;
 const dates=timeline||{phase3DataRelease:null,pdufaTarget:null};
 const verified=pipelineDayCounts(dates,current);
 const releaseFallback=valid(recordedReleaseDate)?recordedReleaseDate:null;
 const pdufaFallback=valid(recordedPdufaDate)?recordedPdufaDate:null;
 const vals=[
  {label:"D",description:"Days since public Phase 3 data-release announcement",
   event:dates.phase3DataRelease,recorded:releaseFallback,recordedSource:releaseSource,
   count:dates.phase3DataRelease?verified.daysSincePhase3Release:
    current&&releaseFallback?dayDifference(current,releaseFallback):null},
  {label:"P",description:"Days until FDA PDUFA target (negative when past)",
   event:dates.pdufaTarget,recorded:pdufaFallback,recordedSource:pdufaSource,
   count:dates.pdufaTarget?verified.daysToPdufa:
    current&&pdufaFallback?dayDifference(pdufaFallback,current):null}
 ];
 const pRecord=nctId?primaryPValues.records.find(x=>x.nct===nctId):undefined;
 const common:CSSProperties={display:"inline-flex",alignItems:"center",gap:4,
   padding:"2px 6px",border:"1px solid #c3d8ca",borderRadius:6,
   background:"#f7fbf8",color:"#174830",textDecoration:"none",
   fontSize:12,whiteSpace:"nowrap",fontVariantNumeric:"tabular-nums"};
 return <span role="group" aria-label="D days since data release, P days to PDUFA"
 style={{display:"inline-flex",verticalAlign:"middle",marginInlineStart:7,flexWrap:"wrap",gap:5}}>
 {vals.map(b=>{
  const count=current&&b.count!==null?b.count.toLocaleString("en-US"):"—";
  const confirmed=!!b.event;
  const date=b.event?.date||b.recorded;
  const note=b.label+" · "+b.description+". "+(
   confirmed?"Independently source-verified date: "+date+".":
   date?"Date recorded in FOCUS, not independently source-verified: "+date+".":
   "No exact calendar date recorded; no estimate shown.");
  const url=confirmed?b.event?.sourceUrl:b.recordedSource;
  const readable=<><strong>{b.label}</strong><span>{count}</span></>;
  const style:CSSProperties=confirmed?common:{...common,color:"#5c6963",background:"#f5f6f5"};
  return date&&current&&b.count!==null&&url?.startsWith("https://")
   ?<a key={b.label} style={style} href={url} target="_blank" rel="noopener noreferrer"
       title={note+" Open the recorded source link."} aria-label={note}>{readable}</a>
   :<span key={b.label} style={style} title={note} aria-label={note}>{readable}</span>;
 })}
 {pRecord?.results.length?pRecord.results.map((item,i)=>{
  const note="Clinical primary endpoint p"+item.value+" · "+item.endpoint+". "+
   "Evidence recorded for exact trial "+pRecord.nct+"; not FDA approval probability.";
  return <a key={"p-"+i} href={pRecord.sourceUrl} target="_blank" rel="noopener noreferrer"
   style={common} title={note} aria-label={note}><strong>p</strong>{item.value}</a>;
 }):<span style={{...common,color:"#647569",background:"#f5f6f5"}}
  title="No source-recorded primary endpoint p-value for this exact trial" aria-label="p-value not recorded"><strong>p</strong>—</span>}
 </span>;
}
