"use client";

import {useEffect,useState,type CSSProperties} from "react";
import {pacificToday,pipelineDayCounts,type TimelineDates} from "../lib/pipeline-timeline";

const grid:CSSProperties={display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(190px,1fr))",gap:10};
const panel:CSSProperties={border:"1px solid #cbd7e3",background:"#f5f8fc",borderRadius:9,padding:"12px 14px",minWidth:0};
const note:CSSProperties={display:"block",fontSize:12,color:"#526477",lineHeight:1.5,marginTop:6};
const label:CSSProperties={fontSize:12,fontWeight:700,letterSpacing:".02em",color:"#425a70"};
const value:CSSProperties={fontSize:23,fontWeight:800,color:"#153c5c",lineHeight:1.5};

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
  timeline,today,caption
}:{
  timeline?:TimelineDates|null;
  today?:string;
  caption?:string;
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
  return <section aria-label="Trial Phase 3 and PDUFA date counters" style={{margin:"12px 0"}}>
    {caption&&<p style={{...note,marginBottom:8}}>{caption}</p>}
    <div style={grid}>
      <div style={panel}>
        <div style={label}>DAYS SINCE PHASE 3 READOUT</div>
        <div style={value}>{metric.since}</div>
        {metric.release
          ?<small style={note}>Public results released {metric.release.date}
            {" · "}<a target="_blank" rel="noopener noreferrer" href={metric.release.sourceUrl}>Verified source</a></small>
          :<small style={note}>Public pivotal results-release date not verified. Trial completion is not a readout.</small>}
      </div>
      <div style={panel}>
        <div style={label}>DAYS UNTIL FDA PDUFA</div>
        <div style={value}>{metric.until}</div>
        {metric.pdufa
          ?<small style={note}>FDA target {metric.pdufa.date}
            {" · "}<a target="_blank" rel="noopener noreferrer" href={metric.pdufa.sourceUrl}>Verified source</a></small>
          :<small style={note}>No source-verified FDA PDUFA target for this exact program.</small>}
        {metric.pdufa&&current&&<small style={note}>This is a target-date countdown, not an FDA decision outcome.</small>}
      </div>
    </div>
  </section>;
}
