"use client";

import {useEffect,useState,type CSSProperties} from "react";
import {pacificToday,pipelineDayCounts,type TimelineDates} from "../lib/pipeline-timeline";

const grid:CSSProperties={display:"flex",flexWrap:"wrap",alignItems:"stretch",gap:8};
const panel:CSSProperties={border:"3px solid #0b9348",background:"#e9fff2",borderRadius:10,padding:"9px 12px",minWidth:135,flex:"1 1 175px",boxShadow:"0 0 0 1px #a6eac4"};
const note:CSSProperties={display:"block",fontSize:12,color:"#526477",lineHeight:1.5,marginTop:6};
const label:CSSProperties={fontSize:11,fontWeight:800,letterSpacing:".02em",color:"#066637"};
const value:CSSProperties={fontSize:23,fontWeight:900,color:"#065f35",lineHeight:1.4};

export function timelineDisplay(dates:TimelineDates|null|undefined,today:string){
  const d=dates||{phase3DataRelease:null,pdufaTarget:null};
  const counts=pipelineDayCounts(d,today);
  const release=counts.daysSincePhase3Release;
  const pdufa=counts.daysToPdufa;
  return {
    since:!today?"Calculating…":release===null?"Not verified":release.toLocaleString("en-US")+" days",
    until:!today?"Calculating…":pdufa===null?"Not verified":pdufa>0?pdufa.toLocaleString("en-US")+" days":
      pdufa===0?"Today":"Passed "+Math.abs(pdufa).toLocaleString("en-US")+" days ago",
    release:d.phase3DataRelease,
    pdufa:d.pdufaTarget
  };
}

/** Date source is exact-program evidence; never substitute registry completion for a Phase 3 readout. */
export default function TrialTimelineSummary({
  timeline,today,caption,compact=false
}:{
  timeline?:TimelineDates|null;
  today?:string;
  caption?:string;
  compact?:boolean;
}){
  const [localToday,setLocalToday]=useState("");
  useEffect(()=>{
    if(today)return;
    const update=()=>setLocalToday(pacificToday());
    update();
    const timer=setInterval(update,60000);
    return ()=>clearInterval(timer);
  },[today]);
  const current=today||localToday;
  const metric=timelineDisplay(timeline,current);
  return <section aria-label="Trial Phase 3 and PDUFA date counters" style={{margin:compact?"0":"12px 0",minWidth:0,flex:compact?"1 1 390px":undefined}}>
    {caption&&<p style={{...note,marginBottom:8}}>{caption}</p>}
    <div style={{...grid,flexWrap:"wrap"}}>
      <div style={{...panel,padding:compact?"6px 9px":panel.padding,minWidth:compact?112:135,flex:compact?"1 1 140px":panel.flex}}>
        <div style={label}>DAYS SINCE PHASE 3</div>
        <div style={{...value,fontSize:compact?18:23}}>{metric.since}</div>
        {metric.release
          ?<small style={note}>Public results released {metric.release.date}
            {" · "}<a target="_blank" rel="noopener noreferrer" href={metric.release.sourceUrl}>Verified source</a></small>
          :<small style={note}>{compact?"Date not verified":"Public pivotal results-release date not verified. Trial completion is not a readout."}</small>}
      </div>
      <div style={{...panel,padding:compact?"6px 9px":panel.padding,minWidth:compact?112:135,flex:compact?"1 1 140px":panel.flex}}>
        <div style={label}>DAYS TO PDUFA</div>
        <div style={{...value,fontSize:compact?18:23}}>{metric.until}</div>
        {metric.pdufa
          ?<small style={note}>FDA target {metric.pdufa.date}
            {" · "}<a target="_blank" rel="noopener noreferrer" href={metric.pdufa.sourceUrl}>Verified source</a></small>
          :<small style={note}>{compact?"Date not verified":"No source-verified FDA PDUFA target for this exact program."}</small>}
        {metric.pdufa&&current&&!compact&&<small style={note}>This is a target-date countdown, not an FDA decision outcome.</small>}
      </div>
    </div>
  </section>;
}
