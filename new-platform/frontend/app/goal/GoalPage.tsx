"use client";
import {useEffect,useState} from "react";
import {useRouter} from "next/navigation";
import GoalDashboard, {type GoalSection,type GoalRecord} from "../GoalDashboard";
type Snapshot={
 pipeline:GoalRecord[];asOf?:string;
 sourceHealth?:{
   state?:string;
   pipelineSourceParity?:{exactPrograms?:number};
   publishedScan?:{finishedAt?:string;complete?:boolean};
 };
};
export default function GoalPage(){
 const router=useRouter();
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null);
 const [issue,setIssue]=useState("");
 useEffect(()=>{
  const controller=new AbortController();
  void fetch("/api/workspace",{cache:"no-store",signal:controller.signal})
    .then(async response=>{
      if(!response.ok)throw new Error(response.status===401?"Sign in to access GOAL.":"Published POOL/Pipeline data unavailable.");
      const raw:unknown=await response.json();
      if(!raw||typeof raw!=="object")throw new Error("Source response invalid");
      const data=raw as Partial<Snapshot>;
      if(!Array.isArray(data.pipeline)
        || !data.sourceHealth?.pipelineSourceParity
        || data.sourceHealth.pipelineSourceParity.exactPrograms!==data.pipeline.length
        || data.pipeline.some(item=>!item || typeof item.id!=="string" || typeof item.ticker!=="string"))
        throw new Error("Pipeline source parity failed; cannot display unsourced counts.");
      if(!controller.signal.aborted)setSnapshot(data as Snapshot);
    })
    .catch(e=>{if(!controller.signal.aborted)setIssue(e instanceof Error?e.message:"Source unavailable")});
  return()=>controller.abort();
 },[]);
 const onOpen=(section:GoalSection)=>{
  router.push(section==="SCANS"?"/scans":section==="RESULTS"?"/results":
    section==="RESTRICTIONS"?"/restrictions":"/pipeline");
 };
 return <main>
  {issue&&<p role="alert" className="panel" style={{margin:"16px auto",maxWidth:1200}}>GOAL source verification: {issue}. No trial counts or dates were inferred.</p>}
  <GoalDashboard
    records={snapshot?.pipeline??null}
    pipelineCount={snapshot?.pipeline.length??null}
    gemJrCount={null} gemCount={null}
    restrictions={null} impactRows={null} impactEntries={null}
    sourceAsOf={snapshot?.asOf??null}
    sourceState={snapshot?.sourceHealth?.state??null}
    scanFinishedAt={snapshot?.sourceHealth?.publishedScan?.finishedAt??null}
    scanComplete={snapshot?.sourceHealth?.publishedScan?.complete===true}
    cached={false} onOpen={onOpen}/>
 </main>;
}
