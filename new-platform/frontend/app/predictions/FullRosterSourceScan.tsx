"use client";
import {useState} from "react";
import savedSnapshot from "../../data/focus-29-registry-source-scan-20261108.json";
type TestState="SOURCE_FIELD_PRESENT"|"SOURCE_FIELD_MISSING"|"INDEPENDENT_REVIEW_REQUIRED"|"NOT_AUTOMATED";
type Row={
  nct:string;ticker:string;company:string;applicationCycles:string[];
  sourceStatus:"SOURCE_SCANNED"|"SOURCE_UNAVAILABLE";
  sourceError:string|null;registrySourceUrl:string;
  registryLastUpdate:string|null;reportedPhase:string|null;reportedStatus:string|null;
  sourceFieldPresent:number;missingRegistryFields:number;independentReviewRequired:number;notAutomated:number;
  scientificAssessment:string;prediction:string;certainty:string;
  tests:{index:number;title:string;state:TestState;summary:string;nextRequired:string;sourceUrl:string}[];
};
type Response={
  kind:string;startedAt:string;completedAt:string;status:string;
  summary:{targetTrials:number;sourceScanned:number;sourceUnavailable:number;recordedFieldChecks:number;
  missingFieldChecks:number;reviewRequiredChecks:number;nonAutomatedChecks:number;
  independentlyCompletedScientificReviews:number;calibratedFDAForecasts:number;savedToDatabase:boolean};
  rows:Row[];
};
const card={background:"#fff",border:"1px solid #b6d4c6",borderRadius:12,padding:16} as const;
const small={fontSize:12,lineHeight:1.6,color:"#52675e"} as const;
export default function FullRosterSourceScan(){
  const [data,setData]=useState<Response|null>(savedSnapshot as unknown as Response);
  const [running,setRunning]=useState(false);
  const [error,setError]=useState("");
  async function start(){
    if(running)return;
    setRunning(true);setError("");
    try{
      const response=await fetch("/api/predictions/roster-source-scan",{
        method:"POST",headers:{"Content-Type":"application/json"},
        body:"{}",cache:"no-store"
      });
      const raw:unknown=await response.json();
      if(!response.ok)throw Error("The FOCUS source scan could not complete. No trial outcome has been inferred.");
      const result=raw as Response;
      if(result.kind!=="FOCUS_29_TRIAL_SOURCE_INSPECTION_NOT_VALIDATED_FDA_ASSESSMENT"||
         !Array.isArray(result.rows)||result.rows.length!==29||
         new Set(result.rows.map(x=>x.nct)).size!==29||
         result.summary.targetTrials!==29)
        throw Error("The source scan did not return the complete exact-NCT FOCUS ledger.");
      setData(result);
    }catch(e){setError(e instanceof Error?e.message:"Source scan unavailable");}
    finally{setRunning(false);}
  }
  function download(){
    if(!data)return;
    const blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"});
    const href=URL.createObjectURL(blob);
    const anchor=document.createElement("a");
    anchor.href=href;anchor.download="focus-29-source-scan-"+data.startedAt.slice(0,10)+".json";
    document.body.appendChild(anchor);anchor.click();anchor.remove();URL.revokeObjectURL(href);
  }
  return <section style={{...card,margin:"18px 0"}} aria-label="All FOCUS trials source scanning">
    <div style={{display:"flex",gap:14,alignItems:"start",justifyContent:"space-between",flexWrap:"wrap"}}>
      <div style={{flex:"1 1 360px"}}>
        <p style={{fontSize:11,color:"#00644c",letterSpacing:1,fontWeight:800,margin:"0 0 5px"}}>29-TRIAL SOURCE COVERAGE · OPERATOR START</p>
        <h2 style={{fontSize:21,margin:"0 0 7px"}}>Run all FOCUS trial source checks</h2>
        <p style={{...small,margin:0}}>The display initially uses the dated November 8, 2026 source scan stored in the project. Press the button to rerun 12 evidence-readiness checks for each of the 29 exact NCT trials against ClinicalTrials.gov.
          This is source inspection, not completed specialist adjudication, historical calibration or an FDA probability forecast.
          Nothing runs until you select the button.</p>
      </div>
      <div style={{display:"flex",gap:8,flexWrap:"wrap",alignItems:"center"}}>
        <button type="button" onClick={()=>void start()} disabled={running}
          style={{background:"#026a52",color:"white",padding:"12px 16px",border:"1px solid #00523e",borderRadius:8,
            fontWeight:800,fontSize:14,cursor:running?"wait":"pointer",opacity:running?.7:1}}>
          {running?"Scanning all 29 trials…":"Start Full FOCUS Scan — 29 Trials"}
        </button>
        {data&&<button type="button" onClick={download}
          style={{background:"#eff8f2",color:"#005343",padding:"12px 14px",border:"1px solid #9ccabc",borderRadius:8,
            fontWeight:750,fontSize:13,cursor:"pointer"}}>Download scan results</button>}
      </div>
    </div>
    {running&&<p role="status" style={{...small,marginTop:12}}>Inspecting the official registry; the full roster may require several requests. This does not perform FDA approval prediction.</p>}
    {error&&<p role="alert" style={{color:"#a72b2b",fontSize:13}}>{error}</p>}
    {data&&<div style={{marginTop:16}}>
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(145px,1fr))",gap:9}}>
        {[
          ["Scanned records",data.summary.sourceScanned+" / "+data.summary.targetTrials],
          ["Registry unavailable",String(data.summary.sourceUnavailable)],
          ["Recorded source fields",String(data.summary.recordedFieldChecks)],
          ["Missing source fields",String(data.summary.missingFieldChecks)],
          ["Scientific sign-offs",String(data.summary.independentlyCompletedScientificReviews)],
          ["Validated FDA forecasts",String(data.summary.calibratedFDAForecasts)]
        ].map(([title,value])=><div key={title} style={{padding:12,background:"#f1f8f4",borderRadius:8}}>
          <div style={{fontSize:11,color:"#50665b"}}>{title}</div>
          <strong style={{fontSize:20}}>{value}</strong>
        </div>)}
      </div>
      <p role="status" style={small}>Scan completed {new Date(data.completedAt).toLocaleString()}.
        {" "}{data.status==="ALL_REGISTRY_SOURCES_SCANNED"?"All registry records were retrieved.":"Some registry records were unavailable; inspect their row errors."}
        {" "}The initial result is stored as a versioned source snapshot; new browser-initiated runs are downloadable but are not automatically stored in the medical database.</p>
      <div style={{maxHeight:560,overflow:"auto",border:"1px solid #dae9e0",borderRadius:9}}>
        <table style={{width:"100%",borderCollapse:"collapse",fontSize:12,minWidth:650}}>
          <thead><tr style={{position:"sticky",top:0,background:"#e8f4ed",textAlign:"left"}}>
            {["Ticker","Exact trial","Registry phase / status","Source checks","Review state"].map(h=><th key={h} style={{padding:10,borderBottom:"1px solid #b4d3c1"}}>{h}</th>)}
          </tr></thead>
          <tbody>{data.rows.map(row=><tr key={row.nct}>
            <td style={{padding:9,borderBottom:"1px solid #e0eae5",fontWeight:700}}>{row.ticker}</td>
            <td style={{padding:9,borderBottom:"1px solid #e0eae5"}}><a href={row.registrySourceUrl} target="_blank" rel="noopener noreferrer">{row.nct}</a></td>
            <td style={{padding:9,borderBottom:"1px solid #e0eae5"}}>{row.reportedPhase??"Unavailable"} · {row.reportedStatus??"Unavailable"}</td>
            <td style={{padding:9,borderBottom:"1px solid #e0eae5"}}>{row.sourceStatus==="SOURCE_SCANNED"?row.sourceFieldPresent+" fields present; "+row.missingRegistryFields+" missing":"Source unavailable"}</td>
            <td style={{padding:9,borderBottom:"1px solid #e0eae5"}}>
              <details>
                <summary style={{cursor:"pointer",color:"#79500c",fontWeight:700}}>Review required · ABSTAIN</summary>
                {row.sourceError&&<p>{row.sourceError}</p>}
                {row.tests.map(t=><div key={t.index} style={{padding:"7px 0",borderBottom:"1px dotted #ccdcd3"}}>
                  <strong>{t.index+1}. {t.title}: {t.state.replaceAll("_"," ")}</strong>
                  <p style={{lineHeight:1.55,margin:"3px 0"}}>{t.summary}</p>
                  <p style={{lineHeight:1.55,margin:"3px 0"}}>Next: {t.nextRequired}</p>
                  <a href={t.sourceUrl} target="_blank" rel="noopener noreferrer">Source</a>
                </div>)}
              </details>
            </td>
          </tr>)}</tbody>
        </table>
      </div>
      <p style={{...small,marginBottom:0}}>
        **Regulatory outcome:** Approval ABSTAIN · CRL ABSTAIN · Delay ABSTAIN · Certainty NOT VALIDATED.
        The entire clinical, statistical, CMC and FDA adjudication cannot be replaced by this public-registry source scan.
      </p>
    </div>}
  </section>;
}
