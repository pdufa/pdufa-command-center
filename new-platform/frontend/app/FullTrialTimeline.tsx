"use client";

import {useEffect,useState} from "react";
import type {PipelineResearchRow} from "../lib/pipeline-research-view";
import type {TimelineDates} from "../lib/pipeline-timeline";
import TrialTimelineSummary from "./TrialTimelineSummary";
import {parseBenefitFeed,type BenefitFeed} from "../lib/benefit-assessments";

type Result={view:string;rows:PipelineResearchRow[];total:number;offset:number;limit:number};
export default function FullTrialTimeline({nctId}:{nctId:string}){
  const [timeline,setTimeline]=useState<TimelineDates|null>(null);
  const [ticker,setTicker]=useState<string|null>(null);
  const [fullTrial,setFullTrial]=useState<PipelineResearchRow|null>(null);
  const [feed,setFeed]=useState<BenefitFeed|null>(null);
  const [status,setStatus]=useState("Loading exact-program timing evidence…");
  useEffect(()=>{
    if(!/^NCT\d{8}$/.test(nctId)){setStatus("Invalid trial identifier");return;}
    const controller=new AbortController();
    setTimeline(null);
    setTicker(null);
    setFullTrial(null);
    setStatus("Loading exact-program timing evidence…");
    const params=new URLSearchParams({view:"pipeline",query:nctId,offset:"0",limit:"50"});
    void fetch("/api/scope-funnel?"+params.toString(),{
      cache:"no-store",signal:controller.signal
    }).then(async response=>{
      if(!response.ok)throw Error("Evidence source unavailable");
      return response.json() as Promise<Result>;
    }).then(result=>{
      if(controller.signal.aborted)return;
      if(result.view!=="pipeline"||result.offset!==0||result.limit!==50||!Array.isArray(result.rows))
        throw Error("Evidence response invalid");
      const exact=result.rows.filter(row=>row.nctId===nctId
        &&row.poolStatus==="EXACT_MATCH"&&row.postPhase3Evidence==="REGISTRY_COMPLETED");
      if(exact.length!==1||result.total!==1){
        setStatus("No uniquely matched Pipeline timing evidence for this NCT.");
        return;
      }
      const dates=exact[0].timeline||null;
      setTicker(exact[0].ticker||null);
      setFullTrial(exact[0]);
      setTimeline(dates);
      setStatus(dates?.phase3DataRelease||dates?.pdufaTarget?"":"Verified readout and PDUFA dates are not recorded.");
    }).catch(()=>{
      if(!controller.signal.aborted)setStatus("Pipeline timing evidence unavailable; dates withheld.");
    });
    return ()=>controller.abort();
  },[nctId]);
  useEffect(()=>{
    const controller=new AbortController();
    void fetch("/api/benefit-assessments",{cache:"no-store",signal:controller.signal})
      .then(async response=>{if(!response.ok)throw Error("BENEFIT_FEED_UNAVAILABLE");return parseBenefitFeed(await response.json());})
      .then(data=>{if(!controller.signal.aborted)setFeed(data);})
      .catch(()=>{if(!controller.signal.aborted)setFeed(null);});
    return ()=>controller.abort();
  },[]);
  return <div style={{margin:"12px 0"}} aria-label="Trial ticker and green date counters">
    <div style={{display:"flex",flexWrap:"wrap",alignItems:"center",gap:12}}>
      <strong style={{fontSize:20,color:"#113e2b",whiteSpace:"nowrap"}}>Ticker: {ticker||"Not verified"}</strong>
      <TrialTimelineSummary timeline={timeline} compact
        trial={fullTrial||{nctId,ticker:ticker||"",drug:null,indication:null}} benefitFeed={feed}/>
    </div>
    {status&&<p className="subtle" role="status">{status}</p>}
  </div>;
}
