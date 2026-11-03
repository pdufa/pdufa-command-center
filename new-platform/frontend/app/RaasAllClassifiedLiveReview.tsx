"use client";
import {useEffect,useMemo,useState} from "react";
import type {ReadoutClassification} from "../lib/phase3-public-readout";
import type {RegistryBenefitResearch} from "../lib/registry-benefit-research";
import {auditLiveRegistryForRaas} from "../lib/raas-live-registry-audit";
import {classifiedRaasTrials,summarizeBulkRaasSources,
 type RaasBulkRow} from "../lib/raas-all-classified-source-review";
import {parseRaasPilotFeed} from "../lib/raas-score-engine";
import {parseProspectiveSourceBaselines} from "../lib/raas-prospective-source-baselines";
import {scanRaasCurrentEvidence} from "../lib/raas-current-evidence-scan";
import pilotData from "../data/raas-pilot-observations.json";
import prospectiveData from "../data/raas-prospective-source-baselines.json";
const pilot=parseRaasPilotFeed(pilotData);
const prospective=parseProspectiveSourceBaselines(prospectiveData);
const tableStyle={width:"100%",borderCollapse:"collapse" as const,fontSize:12};
const cell={padding:"9px 10px",borderBottom:"1px solid #dce8df",textAlign:"left" as const,verticalAlign:"top" as const};
/** Scans ALL source-classified TOP/BOTTOM rows, not the entire 741 trial
 * historical census. The other NCTs have no verified issuer readout gate.
 * No background secret, live return forecast, or RAAS 0–100 approval is claimed.
 */
export default function RaasAllClassifiedLiveReview({data}:{data:ReadoutClassification}){
 const trials=useMemo(()=>classifiedRaasTrials(data),[data]);
 const [rows,setRows]=useState<RaasBulkRow[]>([]);
 const [scanning,setScanning]=useState(false);
 const [completed,setCompleted]=useState(0);
 const [revision,setRevision]=useState(0);
 useEffect(()=>{
  const ctrl=new AbortController();
  setRows([]);setCompleted(0);setScanning(true);
  // Each source request is authenticated by the existing dashboard route and
  // independently validated as an exact-NCT ClinicalTrials.gov research packet.
  if(trials.length>50){
   setScanning(false);return()=>ctrl.abort();
  }
  void Promise.all(trials.map(async trial=>{
   let row:RaasBulkRow;
   try{
    const response=await fetch("/api/tools-trial-evidence?nct="+
     encodeURIComponent(trial.nctId),{cache:"no-store",signal:ctrl.signal});
    if(!response.ok)throw Error(response.status===401?"AUTH_REQUIRED":"REGISTRY_UNAVAILABLE");
    const raw=await response.json() as RegistryBenefitResearch;
    const result=auditLiveRegistryForRaas(raw,trial.nctId,trial.stage);
    row={trial,result,state:"READY",problem:null};
   }catch(error){
    if(ctrl.signal.aborted)return;
    row={trial,result:null,state:"SOURCE_UNAVAILABLE",
     problem:error instanceof Error&&error.message==="AUTH_REQUIRED"?
      "Dashboard sign-in required":"Registry unavailable or invalid source data"};
   }
   if(!ctrl.signal.aborted){
    setRows(prev=>[...prev.filter(r=>r.trial.nctId!==trial.nctId),row]);
    setCompleted(prev=>prev+1);
   }
  })).finally(()=>{if(!ctrl.signal.aborted)setScanning(false)});
  return ()=>ctrl.abort();
 },[trials,revision]);
 const ordered=useMemo(()=>trials.map(t=>rows.find(x=>x.trial.nctId===t.nctId))
  .filter((x):x is RaasBulkRow=>x!==undefined),[rows,trials]);
 const summary=summarizeBulkRaasSources(data,ordered);
 return <section data-raas-all-classified-bulk-scan="1" style={{
  border:"1px solid #c2d9c9",borderRadius:10,padding:14,margin:"12px 0",
  background:"#f8fcf9",color:"#244a35"}}>
  <div style={{display:"flex",flexWrap:"wrap",justifyContent:"space-between",alignItems:"center",gap:9}}>
   <div>
    <strong style={{fontSize:15}}>RAAS · all TOP/BOTTOM trials · live source scan</strong>
    <p style={{fontSize:12,margin:"6px 0 0"}} role="status">
     {completed}/{trials.length} classified NCTs checked
     {scanning?" · scanning current ClinicalTrials.gov records…":" · source scan ended"}
     {" · "}{data.unverified.length} other census trials lack an issuer readout classification.
    </p>
   </div>
   <button type="button" disabled={scanning} onClick={()=>setRevision(v=>v+1)}
    style={{background:"#e6f1e9",border:"1px solid #7ca28a",borderRadius:7,
      padding:"8px 12px",minHeight:40,fontWeight:700,color:"#174931"}}>
    {scanning?"Scanning…":"Rescan all classified trials"}
   </button>
  </div>
  <div style={{display:"flex",gap:12,flexWrap:"wrap",margin:"12px 0",fontSize:12}}>
   <span><strong>{summary.classified}</strong> classified (TOP {summary.top}, BOTTOM {summary.bottom})</span>
   <span><strong>{summary.registryPosted}</strong> registry results posted</span>
   <span><strong>{summary.withPrimaryMeasurements}</strong> with primary measurements</span>
   <span><strong>{summary.failed}</strong> unavailable</span>
   <span><strong>0</strong> approved overall RAAS scores</span>
  </div>
  <p style={{fontSize:12,margin:"0 0 12px",lineHeight:1.55}}>
   This runs automatically for every <strong>issuer-source-classified</strong> trial.
   A registry source is not proof of FDA approval or clinical superiority.
   The percentage below measures <strong>metric areas with source leads only</strong>,
   not a 0–100 RAAS appreciation score. Unclassified trials are not assigned
   TOP or BOTTOM ratings by guesswork.
  </p>
  <details data-raas-all-classified-rows>
   <summary style={{cursor:"pointer",fontWeight:750,fontSize:12,padding:"8px 0"}}>
    View all {trials.length} trial source assessments and missing RAAS grades ▸
   </summary>
   <div style={{overflowX:"auto",marginTop:8}}>
    <table style={tableStyle}>
     <thead><tr>
      {["Stage","Ticker / NCT","Saved + live source areas","Current registry","Primary outcomes","Serious safety terms","Overall RAAS"].map(h=><th key={h} style={cell}>{h}</th>)}
     </tr></thead>
     <tbody>{trials.map(trial=>{
      const row=ordered.find(r=>r.trial.nctId===trial.nctId);
      const saved=scanRaasCurrentEvidence(pilot,prospective,{
       nctId:trial.nctId,ticker:trial.ticker},trial.stage,pilot.sourceAsOf);
      const mapped=new Set([...saved.metricIds,...(row?.result?.preliminaryMetricLeads??[])]);
      const coverage=Math.round(mapped.size/30*100);
      return <tr key={trial.nctId} data-raas-all-classified-nct={trial.nctId}>
       <td style={cell}>{trial.stage==="pre"?"TOP":"BOTTOM"}</td>
       <td style={cell}><strong>{trial.ticker}</strong><div>{trial.nctId}</div>
        <small>{trial.company}</small></td>
       <td style={cell}><strong>{mapped.size}/30</strong> metric areas
        <div>{coverage}% source coverage only</div>
        <small>{30-mapped.size} areas still need mapped sources</small>
       </td>
       <td style={cell}>{!row?"Checking…":row.state==="SOURCE_UNAVAILABLE"?
        row.problem:row.result?.resultsPosted?"Posted outcomes located":"Protocol / no posted results"}
       </td>
       <td style={cell}>{row?.result?.primaryMeasurements??"—"}</td>
       <td style={cell}>{row?.result?.seriousAdverseEventTerms??"—"}</td>
       <td style={cell}><strong>— /100</strong><div>Not validated</div></td>
      </tr>;
     })}</tbody>
    </table>
   </div>
  </details>
  <p style={{fontSize:11,lineHeight:1.5,margin:"10px 0 0",color:"#6d6749"}}>
   Historical $300M–$10B issuer-cap census dated {data.censusDate}; source
   release classification dated {data.sourceAsOf}. This scan does not update
   the historical release-status assignments or create approved RAAS metric calibrations.
  </p>
 </section>;
}
