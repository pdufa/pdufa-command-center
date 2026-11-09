"use client";
import {useCallback,useEffect,useRef,useState} from "react";

type SourceProbe={sourceId:string;status:"MATCH"|"CHANGED"|"UNAVAILABLE";
  observedAt:string;sourceUrl:string;message:string};
type Report={schema:"MAIN_PILOT_DOCUMENTARY_REFRESH_V1";nct:string;
  observedAt:string;evidenceSnapshotAsOf:string;mode:string;
  currentness:"SOURCE_IDENTITIES_MATCH"|"PARTIALLY_UNAVAILABLE"|"REVIEW_REQUIRED";
  probes:SourceProbe[];
  cards:Array<{assessmentId:string;methodIndex:number;points:number;outOf:number;label:string}>;
  researchOnly:true;officialClinicalMethodGrades:0;independentPhaseVerified:false;
  fdaPrediction:"ABSTAIN";accuracy:"NOT_CALIBRATED";automaticClinicalRescore:false;note:string};
const frame={border:"1px solid #98b9c7",borderRadius:11,padding:13,margin:"12px 0",background:"#f4f9fb"} as const;
const caption={fontSize:12,color:"#3b5960"} as const;
function valid(input:unknown):input is Report{
  if(!input||typeof input!=="object")return false;
  const v=input as Report;
  return v.schema==="MAIN_PILOT_DOCUMENTARY_REFRESH_V1"&&v.nct==="NCT06081894"&&
    v.researchOnly===true&&v.officialClinicalMethodGrades===0&&
    v.independentPhaseVerified===false&&v.fdaPrediction==="ABSTAIN"&&
    v.accuracy==="NOT_CALIBRATED"&&v.automaticClinicalRescore===false&&
    ["SOURCE_IDENTITIES_MATCH","PARTIALLY_UNAVAILABLE","REVIEW_REQUIRED"].includes(v.currentness)&&
    Array.isArray(v.probes)&&v.probes.length===2&&
    v.probes.every(p=>["MATCH","CHANGED","UNAVAILABLE"].includes(p.status))&&
    Array.isArray(v.cards)&&v.cards.length===3&&
    ["5.1","4.2","5.3"].every((id,i)=>v.cards[i]?.assessmentId===id&&
     v.cards[i]?.methodIndex===1&&v.cards[i]?.outOf===5&&
     Number.isInteger(v.cards[i]?.points)&&v.cards[i].points>=0&&v.cards[i].points<=5)&&
    Number.isFinite(Date.parse(v.observedAt));
}
export default function PilotLiveEvidenceRefresh({nct}:{nct:string}){
  const [result,setResult]=useState<Report|null>(null);
  const [status,setStatus]=useState<"CHECKING"|"READY"|"UNAVAILABLE">("CHECKING");
  const [inProgress,setInProgress]=useState(false);
  const controller=useRef<AbortController|null>(null);
  const running=useRef(false);
  const disposed=useRef(false);
  const refresh=useCallback(async(force=false)=>{
    if(nct!=="NCT06081894"||running.current)return;
    const c=new AbortController();
    controller.current=c;running.current=true;
    setInProgress(true);setStatus("CHECKING");
    try{
      const response=await fetch("/api/predictions/medical-provisional-refresh?nct="+encodeURIComponent(nct)+(force?"&refresh=1":""),
        {cache:"no-store",signal:c.signal});
      const body:unknown=await response.json();
      if(!response.ok||!valid(body))throw Error("INVALID_LIVE_SOURCE_CHECK");
      if(!disposed.current&&!c.signal.aborted){setResult(body);setStatus("READY");}
    }catch{
      if(!disposed.current&&!c.signal.aborted){
        setResult(null);setStatus("UNAVAILABLE");
      }
    }finally{
      if(controller.current===c)controller.current=null;
      running.current=false;
      if(!disposed.current)setInProgress(false);
    }
  },[nct]);
  useEffect(()=>{
    disposed.current=false;
    void refresh(false);
    const timer=window.setInterval(()=>{
      if(document.visibilityState==="visible")void refresh(false);
    },15*60*1000);
    const onVisible=()=>{if(document.visibilityState==="visible")void refresh(false);};
    document.addEventListener("visibilitychange",onVisible);
    return ()=>{
      disposed.current=true;
      controller.current?.abort();window.clearInterval(timer);
      document.removeEventListener("visibilitychange",onVisible);
    };
  },[refresh]);
  if(nct!=="NCT06081894")return null;
  const changed=result?.currentness==="REVIEW_REQUIRED";
  const matches=result?.currentness==="SOURCE_IDENTITIES_MATCH";
  return <section aria-label="Automatic provisional research source refresh" style={frame}>
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",gap:10,flexWrap:"wrap"}}>
      <div>
        <strong>AUTOMATIC DOCUMENTARY SCORE RECHECK</strong>
        <div style={caption}>Two official public-source identity checks · every 15 minutes while the page is visible</div>
      </div>
      <button type="button" onClick={()=>{void refresh(true);}} disabled={inProgress}
        style={{padding:"8px 13px",border:"1px solid #206a77",borderRadius:8,color:"#104652",
          background:"#fff",fontWeight:700,cursor:inProgress?"progress":"pointer"}}>
        {inProgress?"Checking…":"Check sources now"}
      </button>
    </div>
    <div role="status" style={{marginTop:9,fontWeight:750,color:changed?"#944615":matches?"#075b50":"#595e62"}}>
      {status==="UNAVAILABLE"?"Source recheck unavailable — dated research snapshot remains unchanged":
        status==="CHECKING"?"Checking public trial and publication sources…":
        changed?"CHANGED SOURCE — evidence review required":
        matches?"Checked: original registry and publication identities match":
        "Partial recheck — one or more sources unavailable"}
    </div>
    {result?<div>
      <p style={{...caption,margin:"6px 0"}}>
        Checked {new Date(result.observedAt).toLocaleString()} · documentary evidence snapshot {result.evidenceSnapshotAsOf}.
        {" "}This is an automatic <strong>recalculation of the saved documentary checks</strong>, not an independent examination of newly published efficacy or safety evidence.
      </p>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(165px,1fr))",gap:8,marginTop:8}}>
        {result.cards.map(c=><div key={c.assessmentId} style={{border:"1px solid #b5d2d7",borderRadius:8,padding:10,background:"#fff"}}>
          <div style={{fontSize:12,fontWeight:750}}>Assessment {c.assessmentId} / Method 1</div>
          <div style={{fontWeight:900,fontSize:23,color:"#173d56"}}>{changed?"Review required":c.points+" / "+c.outOf}</div>
          <div style={caption}>{c.label}</div>
        </div>)}
      </div>
      <details style={{marginTop:10,fontSize:13}}>
        <summary style={{cursor:"pointer",fontWeight:700}}>Show live source identity checks and limitations</summary>
        {result.probes.map(p=><p key={p.sourceId}>
          <strong>{p.sourceId} · {p.status}</strong> — {p.message}{" "}
          <a href={p.sourceUrl} target="_blank" rel="noopener noreferrer">Original public API</a>
        </p>)}
        <p>{result.note}</p>
      </details>
    </div>:null}
    <p style={{...caption,margin:"9px 0 0"}}>
      Important: the official scientific grades remain **unscored**; FDA prediction ABSTAIN and accuracy NOT CALIBRATED.
      Newly appearing SAPs, corrected safety counts or changed regulatory filings require independent review, not automatic score increases.
      This preview does not run a background job while nobody has the page open.
    </p>
  </section>;
}
