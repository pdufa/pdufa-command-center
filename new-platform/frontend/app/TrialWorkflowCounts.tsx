"use client";

import {useEffect,useState} from "react";
import Link from "next/link";
import WorkflowStageIcon, {type WorkflowStageId} from "./WorkflowStageIcon";

type Totals = Record<WorkflowStageId,number|null>;
const initial:Totals={PIPELINE:null,GEM_JR:null,GEM:null,WT:null};
const stages: {id:WorkflowStageId;label:string}[]=[
  {id:"PIPELINE",label:"PIPELINE"},
  {id:"GEM_JR",label:"GEM JR"},
  {id:"GEM",label:"GEM"},
  {id:"WT",label:"WT"},
];

function validTotal(value:unknown):value is number {
  return typeof value==="number" && Number.isSafeInteger(value) && value>=0;
}

export default function TrialWorkflowCounts() {
  const [totals,setTotals]=useState<Totals>(initial);
  const [status,setStatus]=useState("Retrieving page totals…");
  const [details,setDetails]=useState({GEM_JR:"Saved members",GEM:"Saved members"});
  useEffect(()=>{
    const controller=new AbortController();
    async function load() {
      try {
        const response=await fetch("/api/workspace/summary",{cache:"no-store",signal:controller.signal});
        if(!response.ok) throw Error("Published candidate data unavailable");
        const data=await response.json() as {asOf?:string;pipeline?:number;gemJr?:number;gem?:number};
        if(!validTotal(data.pipeline)||!validTotal(data.gemJr)||!validTotal(data.gem))throw Error("Published candidate totals invalid");
        let cached:Totals|null=null;
        try {
          const saved=JSON.parse(localStorage.getItem("pdufa_stage_totals_v1")||"null");
          if(saved && saved.asOf===data.asOf && saved.counts &&
            stages.every(({id})=>validTotal(saved.counts[id]))) {
              cached=saved.counts as Totals;
              if(saved.details && ["GEM_JR","GEM"].every(id=>["Saved members","Screen candidates"].includes(saved.details[id]))) setDetails(saved.details);
            }
        }catch{/* Browser storage may be unavailable */}
        if(controller.signal.aborted)return;
        // Use exactly the last visible count on each dashboard page when a
        // same-snapshot bar exists. Otherwise use the default unfiltered pages.
        const next:Totals=cached||{PIPELINE:data.pipeline,GEM_JR:data.gemJr,GEM:data.gem,WT:null};
        setTotals(next);
        setStatus(cached?"Latest matching dashboard page totals":"Published stage memberships");
        if(cached)return;
        const wt=await fetch("/api/program-watch-trade",{cache:"no-store",signal:controller.signal});
        if(wt.ok){
          const savedWt=await wt.json() as {watch?:unknown;trade?:unknown};
          if(Array.isArray(savedWt.watch)&&Array.isArray(savedWt.trade) && !controller.signal.aborted) {
            const trackedCount=savedWt.watch.length+savedWt.trade.length;
            setTotals(current=>({...current,WT:trackedCount}));
          }
        }
      }catch{
        if(!controller.signal.aborted)setStatus("Page totals unavailable — open dashboard to refresh");
      }
    }
    void load();
    return()=>controller.abort();
  },[]);

  return <section className="migration-workspace standalone-workflow-counts" aria-label="Pipeline through trading candidate totals">
    <div className="workflow-counts" role="group" aria-label="Current trial counts and dashboard navigation">
      {stages.map(({id,label})=><Link key={id}
        href={"/?section="+id}
        className={"workflow-count workflow-count--"+id.toLowerCase()}
        aria-label={label+": "+(totals[id]===null?"not available":totals[id]!.toLocaleString("en-US"))+" · Open "+label}>
        <span className="workflow-count-icon"><WorkflowStageIcon stage={id}/></span>
        <span className="workflow-count-copy">
          <span className="workflow-count-label">{label}</span>
          <strong className="workflow-count-number" aria-live="polite">{totals[id]===null?"—":totals[id]!.toLocaleString("en-US")}</strong>
          <span className="workflow-count-detail">{id==="PIPELINE"?"Total candidates":id==="WT"?"Tracked watch / trade":details[id]}</span>
        </span>
      </Link>)}
    </div>
    <p className="workflow-counts-meta" role="status">{status}</p>
  </section>;
}
