"use client";
import {useEffect,useState} from "react";

type CaseRecord = {id?:string;nct_id?:string;company?:string;drug?:string;indication?:string;predicted_decision?:string;actual_decision?:string;confidence?:number|string;science?:unknown;outcome?:unknown;missing_evidence?:unknown;status?:string};
type Validation = {status?:string;counts?:Record<string,unknown>;accuracy_by_decision?:Record<string,unknown>;calibration_metrics?:unknown;cases?:CaseRecord[]};
const shown=(v:unknown)=>v===null||v===undefined||v===""?"Not verified":typeof v==="object"?JSON.stringify(v,null,2):String(v);
export default function HistoricalPredictionMetrics(){
 const [data,setData]=useState<Validation|null>(null);
 const [error,setError]=useState("");
 useEffect(()=>{let active=true;fetch("/api/phase3-trials/validation",{cache:"no-store"}).then(async r=>{if(!r.ok)throw new Error("Historical validation unavailable ("+r.status+")");return r.json()}).then(v=>{if(active)setData(v)}).catch(e=>{if(active)setError(String(e.message||e))});return()=>{active=false}},[]);
 const counts=data?.counts||{};
 const cases=Array.isArray(data?.cases)?data.cases:[];
 return <section className="panel" aria-label="Historical PDUFA prediction metrics" style={{padding:16}}>
 <h2>METRICS — ANALYSIS BENCHMARKS</h2>
 <details open><summary style={{cursor:"pointer",fontWeight:700}}>Benchmark 2 — Historical PDUFA Prediction Accuracy</summary>
 <p>10 historical FDA decisions planned · Target: 9/10 correct (90%) · Longer-term goal: 95% on a larger independent sample.</p>
 <p><strong>Validation:</strong> {data?.status||"NOT VALIDATED"}{error?" — "+error:""}</p>
 <p><strong>Correct / scored:</strong> {shown(counts.correct_predictions)} / {shown(counts.scored_predictions)} · <strong>Abstentions:</strong> {shown(counts.abstentions)}</p>
 <p><strong>Calibration:</strong> {data?.calibration_metrics?"Reported by validation endpoint":"Not established"}</p>
 <details><summary style={{cursor:"pointer"}}>Individual eligible historical prediction records ({cases.length} available)</summary>
 {cases.length===0?<p>No eligible historical prediction records returned by the validation endpoint yet. No scores are inferred.</p>:cases.map((c,i)=><details key={c.id||c.nct_id||i} style={{margin:"8px 0",padding:"8px",border:"1px solid #aaa",borderRadius:6}}>
 <summary style={{cursor:"pointer"}}>Case {String(i+1).padStart(2,"0")} — {shown(c.company)} / {shown(c.drug)} / {shown(c.indication)}</summary>
 <p><strong>NCT:</strong> {shown(c.nct_id)} · <strong>Prediction:</strong> {shown(c.predicted_decision)} · <strong>Actual FDA decision:</strong> {shown(c.actual_decision)}</p>
 <p><strong>Confidence:</strong> {shown(c.confidence)} · <strong>Validation status:</strong> {shown(c.status)}</p>
 <details><summary>SCIENCE assessment</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{shown(c.science)}</pre></details>
 <details><summary>OUTCOME assessment</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{shown(c.outcome)}</pre></details>
 <details><summary>Missing evidence and decision requirements</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{shown(c.missing_evidence)}</pre></details>
 </details>)}
 </details>
 <details><summary style={{cursor:"pointer"}}>Benchmark calculations and validation details</summary>
 <details><summary>Verified historical validation counts</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(counts,null,2)}</pre></details>
 <details><summary>Accuracy by FDA decision (PASS / CRL / EXTENSION)</summary><pre style={{whiteSpace:"pre-wrap",overflowWrap:"anywhere"}}>{JSON.stringify(data?.accuracy_by_decision||{},null,2)}</pre></details>
 </details>
 <p style={{fontSize:13}}>Only locked pre-decision predictions with independently verified FDA outcomes count as validated. Missing cases and abstentions are never counted as correct.</p>
 </details>
 </section>
}
