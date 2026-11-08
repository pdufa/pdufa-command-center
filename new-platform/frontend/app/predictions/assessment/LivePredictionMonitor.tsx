"use client";
import type {ReviewMatrix} from "../../../lib/medical-review-matrix";

type MonitorProps={
  nct:string;
  review:ReviewMatrix|null;
  loading:boolean;
  refreshing:boolean;
  unavailable:boolean;
  lastCheckedAt:string|null;
  lastChange:string|null;
  refresh:()=>void;
};

const panel={border:"1px solid #82b6a8",borderRadius:13,padding:"clamp(12px,2vw,18px)",margin:"12px 0",background:"#f4faf7"} as const;
const block={border:"1px solid #b9d6cc",borderRadius:10,padding:12,background:"white"} as const;
const percent=(count:number)=>Math.round((count/800)*1000)/10;

export default function LivePredictionMonitor({
  nct,review,loading,refreshing,unavailable,lastCheckedAt,lastChange,refresh
}:MonitorProps){
  const graded=review?.counts.SCORED??0;
  const excluded=review?.counts.NOT_APPLICABLE??0;
  const pending=review?800-graded-excluded:null;
  const observed=!!review && !unavailable;
  const formattedTime=lastCheckedAt?new Date(lastCheckedAt).toLocaleTimeString(undefined,{hour:"numeric",minute:"2-digit",second:"2-digit"}):"Not yet verified";
  const stage=review?.verifiedPhase??"NOT VERIFIED";
  return <section style={panel} aria-label={"Live prediction and scientific review monitor for "+nct}>
    <div style={{display:"flex",justifyContent:"space-between",alignItems:"center",flexWrap:"wrap",gap:9}}>
      <div>
        <div style={{fontSize:12,fontWeight:800,letterSpacing:".07em",color:"#1b6e59"}}>MAIN · LIVE SCIENTIFIC REVIEW MONITOR</div>
        <h3 style={{margin:"5px 0 2px",fontSize:"clamp(18px,3vw,22px)"}}>{nct}</h3>
      </div>
      <span role="status" style={{border:"1px solid #acc8be",borderRadius:100,padding:"7px 11px",background:"#fff",fontSize:12,fontWeight:800}}>
        {loading?"CONNECTING":unavailable?"SOURCE UNAVAILABLE":refreshing?"REFRESHING":"POLLING ACTIVE"}
      </span>
    </div>
    <p style={{fontSize:13,color:"#476558",margin:"8px 0 12px"}}>
      Automatically checks the authenticated, isolated review ledger every 15 seconds while this page is visible. These are <strong>observed review records, not simulated prediction-job activity.</strong>
    </p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(170px,1fr))",gap:10}}>
      <div style={block}><div style={{fontSize:12,color:"#46665c",fontWeight:700}}>FDA PREDICTION</div>
        <div style={{fontSize:22,fontWeight:800,color:"#73522a"}}>ABSTAIN</div>
        <div style={{fontSize:12}}>Approval / CRL / delay probabilities withheld</div>
      </div>
      <div style={block}><div style={{fontSize:12,color:"#46665c",fontWeight:700}}>ACCURACY RATING</div>
        <div style={{fontSize:18,fontWeight:800,color:"#73522a"}}>NOT CALIBRATED</div>
        <div style={{fontSize:12}}>No verified historical model accuracy</div>
      </div>
      <div style={block}><div style={{fontSize:12,color:"#46665c",fontWeight:700}}>CURRENT PREDICTION RUN</div>
        <div style={{fontSize:17,fontWeight:800}}>NOT OBSERVABLE</div>
        <div style={{fontSize:12}}>The backend has no prediction-run activity feed. Polling a ledger is not a running analysis job.</div>
      </div>
    </div>
    <div style={{...block,marginTop:10}}>
      <div style={{display:"flex",justifyContent:"space-between",gap:8,flexWrap:"wrap"}}>
        <strong>Verified current-phase method reviews</strong>
        <strong>{observed?graded+" / 800":"NOT CURRENTLY VERIFIED"}</strong>
      </div>
      <progress aria-label="Verified current-phase scientific reviews" style={{width:"100%",height:14,marginTop:8}} max={800}
        value={observed?graded+excluded:0}/>
      <div style={{fontSize:13,marginTop:6}}>
        {observed?percent(graded+excluded)+"% of positions adjudicated · "+graded+" graded · "+excluded+" explicitly excluded · "+pending+" awaiting review": "Progress withheld until the isolated ledger can be read and validated."}
      </div>
      <p style={{fontSize:12,margin:"8px 0 0"}}>Current verified clinical phase: <strong>{observed?stage:"NOT VERIFIED"}</strong>. Active assessment and method ID: <strong>not reported by the existing backend</strong>.</p>
    </div>
    <div style={{display:"flex",alignItems:"center",justifyContent:"space-between",flexWrap:"wrap",gap:10,marginTop:12}}>
      <div style={{fontSize:12}}>Last successful ledger fetch: <strong>{formattedTime}</strong>
        {unavailable?<span style={{color:"#a33225"}}> · Source unavailable — previous observations are not live</span>:null}
        {lastChange&&!unavailable?<span> · Latest observed change: {lastChange}</span>:null}
      </div>
      <div style={{display:"flex",alignItems:"center",flexWrap:"wrap",gap:8}}>
        <button type="button" onClick={refresh} disabled={refreshing||loading} style={{padding:"9px 13px",borderRadius:9,background:"#e4f4ed",border:"1px solid #2e826d",fontWeight:800,color:"#215e50",cursor:"pointer"}}>
          Refresh now
        </button>
        <a href="#live-scientific-review-ledger" style={{padding:"9px 13px",borderRadius:9,background:"#e4f4ed",border:"1px solid #2e826d",fontWeight:800,color:"#215e50",textDecoration:"none"}}>
          Go to live grades ↓
        </a>
      </div>
    </div>
    <details style={{marginTop:10,borderTop:"1px solid #c7ded5",paddingTop:10}}>
      <summary style={{fontWeight:750,cursor:"pointer"}}>What updates live, and what still needs a worker feed?</summary>
      <p style={{fontSize:13}}>The monitor refreshes exact NCT reviewer phase events, method grade counts, exclusions and review/gap-event totals. It never counts retrieved sources, displayed method positions or page requests as scored tests. The engine does not yet expose a started/running/completed job ID, current method being processed, or provisional calibrated probabilities. Until a real run-event producer and prediction/calibration model are connected, those items correctly remain unavailable.</p>
    </details>
  </section>;
}
