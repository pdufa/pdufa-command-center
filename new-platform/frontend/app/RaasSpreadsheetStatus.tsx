"use client";
import {raasSpreadsheetSummary,type RaasSpreadsheetTrial} from "../lib/raas-spreadsheet-status";

/** Small expandable summary used in each on-screen research spreadsheet. */
export default function RaasSpreadsheetStatus({trial}:{trial:RaasSpreadsheetTrial}){
 const s=raasSpreadsheetSummary(trial);
 const phase=s.stage?(s.stage==="pre"?"TOP-RAAS":"BOTTOM-RAAS"):"RAAS";
 const pending=s.approvedScore===null;
 return <details data-raas-spreadsheet-cell={trial.nctId} style={{
  minWidth:156,border:"1px solid #bdcfc5",borderRadius:7,padding:"5px 7px",
  background:"#f8fcf9",fontSize:12,color:"#223f30"}}>
  <summary style={{cursor:"pointer",fontWeight:700}}
   aria-label={phase+" for "+trial.nctId+": "+(pending?"not yet validated":s.approvedScore+" of 100")}>
   {phase} {pending?"—":s.approvedScore}/100
   <small style={{display:"block",fontWeight:400}}>
    {s.state==="INVALID_IDENTITY"?"Exact trial identity unavailable":
     s.state==="STAGE_UNVERIFIED"?"Readout stage unverified":
     s.state==="APPROVED"?"Approved current score":
     "Source coverage "+s.sourceCoveragePercent+"% ("+s.mappedAreas+"/30) · RAAS pending"}
   </small>
  </summary>
  <div style={{lineHeight:1.5,marginTop:7}}>
   {s.stage===null?<p>TOP/BOTTOM requires verified issuer readout classification.
    Registry results posting or an absent date alone cannot establish the phase.</p>:
    <div>
     <p><strong>{s.sourceCoveragePercent}% source coverage</strong> · <strong>{s.mappedAreas}/30</strong> mapped source areas · <strong>{s.missingAreas}/30</strong> without mapped sources, as of {s.sourceAsOf}. {s.sourceFactCount} source fact(s) recorded. This is evidence coverage, not an RAAS investment score. {s.approvedMetrics}/30 calibrated metric approvals.</p>
     <div role="progressbar" aria-label="RAAS evidence source coverage, not investment score"
       aria-valuemin={0} aria-valuemax={100} aria-valuenow={s.sourceCoveragePercent??0}
       style={{height:7,background:"#dbe5df",borderRadius:9,overflow:"hidden"}}>
       <div style={{width:(s.sourceCoveragePercent??0)+"%",height:"100%",background:"#357f63"}}/>
     </div>
     {s.exploratoryTimingScore!==null&&<p>Timing pilot: <strong>{s.exploratoryTimingScore}/100</strong> · research-only single metric; NOT the overall RAAS score.</p>}
    </div>}
   {pending&&<p>No approved overall RAAS score. Missing inputs are not zero and
    exploratory timing grades are excluded.</p>}
   <a href={s.stage?"/raas-worklist?"+new URLSearchParams({stage:s.stage,nctId:trial.nctId,ticker:trial.ticker,
     ...(trial.drug?{drug:trial.drug}:{}),
     ...(trial.indication?{indication:trial.indication}:{})}).toString()+"#raas-"+(s.stage==="pre"?"top":"bottom")+"-worklist":"/raas-worklist"}>
     Open detailed RAAS validation worklist · each metric and missing input</a>
   <span>{" · "}</span>
   <a href="/raas-scan">See all 60 RAAS metrics and validation gaps</a>
   <span>{" · "}</span>
   <a href="/tools#tools-phase3-release-sheets">TOP/BOTTOM evidence tables</a>
  </div>
 </details>;
}
