"use client";

import {useEffect,useState} from "react";
import Link from "next/link";
import WorkflowStageIcon from "./WorkflowStageIcon";

function validTotal(value:unknown):value is number {
  return typeof value==="number" && Number.isSafeInteger(value) && value>=0;
}

// Standalone trial pages must not resurrect archived GEM JR, GEM or WT stages.
export default function TrialWorkflowCounts() {
  const [count,setCount]=useState<number|null>(null);
  const [status,setStatus]=useState("Retrieving published Pipeline count…");
  useEffect(()=>{
    const controller=new AbortController();
    async function load(){
      try{
        const response=await fetch("/api/workspace/summary",{cache:"no-store",signal:controller.signal});
        if(!response.ok)throw Error("Published candidate data unavailable");
        const data=await response.json() as {asOf?:string;pipeline?:number};
        if(!validTotal(data.pipeline))throw Error("Published candidate total invalid");
        let shown=data.pipeline;
        try{
          const saved=JSON.parse(localStorage.getItem("pdufa_stage_totals_v1")||"null");
          if(saved?.asOf===data.asOf && validTotal(saved?.counts?.PIPELINE))shown=saved.counts.PIPELINE;
        }catch{/* Browser cache is optional and untrusted */}
        if(controller.signal.aborted)return;
        setCount(shown);
        setStatus("Published Pipeline source total · not fully qualified post–Phase 3");
      }catch{
        if(!controller.signal.aborted)setStatus("Pipeline source total unavailable");
      }
    }
    void load();
    return()=>controller.abort();
  },[]);
  return <section className="migration-workspace standalone-workflow-counts" aria-label="Current Pipeline source total">
    <div className="workflow-counts" role="group" aria-label="Current Pipeline count and navigation">
      <Link href="/pipeline" className="workflow-count workflow-count--pipeline"
        aria-label={"PIPELINE: "+(count===null?"not available":count.toLocaleString("en-US"))+" · Open Pipeline"}>
        <span className="workflow-count-icon"><WorkflowStageIcon stage="PIPELINE"/></span>
        <span className="workflow-count-copy">
          <span className="workflow-count-label">PIPELINE</span>
          <strong className="workflow-count-number" aria-live="polite">{count===null?"—":count.toLocaleString("en-US")}</strong>
          <span className="workflow-count-detail">Published source records; post–Phase 3 qualification requires verification</span>
        </span>
      </Link>
    </div>
    <p className="workflow-counts-meta" role="status">{status}</p>
  </section>;
}
