"use client";
import {useEffect,useState,type CSSProperties} from "react";
import {pacificToday,pipelineDayCounts,type TimelineDates} from "../lib/pipeline-timeline";
/** Exact-program, source-verified Pacific-day counters; never infer from registry completion. */
export default function CompanyDateBadges({timeline,today}:{timeline?:TimelineDates|null;today?:string}){
 const [localToday,setLocalToday]=useState("");
 useEffect(()=>{
   if(today)return;
   const update=()=>setLocalToday(pacificToday());
   update();const id=setInterval(update,60000);return()=>clearInterval(id);
 },[today]);
 const current=today||localToday;
 const dates=timeline||{phase3DataRelease:null,pdufaTarget:null};
 const {daysSincePhase3Release,daysToPdufa}=pipelineDayCounts(dates,current);
 const common:CSSProperties={display:"inline-flex",alignItems:"center",gap:4,padding:"2px 6px",
   border:"1px solid #c3d8ca",borderRadius:6,background:"#f7fbf8",color:"#174830",
   textDecoration:"none",fontSize:12,whiteSpace:"nowrap",fontVariantNumeric:"tabular-nums"};
 const badges=[
   {label:"D",count:daysSincePhase3Release,event:dates.phase3DataRelease,description:"Days since source-verified public Phase 3 data release"},
   {label:"P",count:daysToPdufa,event:dates.pdufaTarget,description:"Days until source-verified FDA PDUFA target; negative means target date passed"}
 ];
 return <span role="group" aria-label="D days since data release, P days to PDUFA"
   style={{display:"inline-flex",verticalAlign:"middle",marginInlineStart:7,flexWrap:"wrap",gap:5}}>
   {badges.map(b=>{
     const number=current&&b.count!==null?b.count.toLocaleString("en-US"):"—";
     const note=b.label+" · "+b.description+". "+(b.event?"Verified date: "+b.event.date+". Select to open the source.":"Date not source-verified.");
     const value=<><strong>{b.label}</strong><span>{number}</span></>;
     return b.event&&current&&b.count!==null
       ?<a key={b.label} href={b.event.sourceUrl} target="_blank" rel="noopener noreferrer"
           style={common} title={note} aria-label={note}>{value}</a>
       :<span key={b.label} style={{...common,color:"#647569",background:"#f5f6f5"}}
           title={note} aria-label={note}>{value}</span>;
   })}
 </span>;
}
