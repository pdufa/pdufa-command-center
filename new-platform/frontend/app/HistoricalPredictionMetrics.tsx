"use client";
import {useEffect,useState} from "react";

type Validation = {status?:string;counts?:Record<string,unknown>;accuracy_by_decision?:Record<string,unknown>;calibration_metrics?:unknown};
export default function HistoricalPredictionMetrics(){
 const [data,setData]=useState<Validation|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{let active=true;fetch("/api/phase3-trials/validation",{cache:"no-store"}).then(async r=>{if(!r.ok)throw new Error("Historical validation unavailable ("+r.status+")");return r.json()}).then(v=>{if(active)setData(v)}).catch(e=>{if(active)setError(String(e.message||e))});return()=>{active=false}},[]);
 const counts=data?.counts||{};
 return <section className="panel" aria-label="Historical PDUFA prediction metrics" style={{padding:16}}>
 <h2>METRICS — HISTORICAL PDUFA PREDICTIONS</h2>
 <p><strong>Benchmark 2:</strong> 10 independently selected historical FDA decisions. Target: at least 9 correct of 10 (90%). The longer-term 95% target requires a larger holdout sample.</p>
 <p><strong>Validation:</strong> {data?.status||"NOT VALIDATED"}{error?" — "+error:""}</p>
 <p><strong>Correct / scored:</strong> {String(counts.correct_predictions??"Not available")} / {String(counts.scored_predictions??"Not available")}</p>
 <p><strong>Abstentions:</strong> {String(counts.abstentions??"Not available")} · <strong>Calibration:</strong> {data?.calibration_metrics?"Reported by validation endpoint":"Not established"}</p>
 <details><summary>Verified historical validation counts</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(counts,null,2)}</pre></details>
 <details><summary>Accuracy by FDA decision (PASS / CRL / EXTENSION)</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(data?.accuracy_by_decision||{},null,2)}</pre></details>
 <p style={{fontSize:13}}>No retrospective prediction counts as validated unless its prediction was locked using pre-decision evidence and independently matched to the verified FDA outcome. Missing evidence and abstentions remain visible; they are never counted as correct.</p>
 </section>
}
