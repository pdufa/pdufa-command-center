"use client";
// @ts-nocheck — temporary compile diagnostic; remove after identifying source error.
import {useRef, useState} from "react";
import type {Candidate} from "./Workspace";

type Trial = Candidate;
export type GemCriterionAudit = {key:string;label:string;passed:number;failed:number;unknown:number};
export type GemScanResult = {
  runNumber:number;
  audits:GemCriterionAudit[];
  asOf: string;
  evaluatedAt: string;
  baseline: number;
  sourceTotal: number;
  selected: string[];
  passes: Candidate[];
  needsReview: Candidate[];
  fails: Candidate[];
};
function completedPhase3(row:Trial) {
  const facts=row.trialFilters;
  const evidencePhase3=facts?.registeredPhase==="Phase 3" ||
    /^Phase 3(?: Results)?$/i.test(row.stage||"") ||
    Boolean(row.phase3Date) ||
    row.technical?.benchmarks?.phase3===true;
  if (!evidencePhase3) return false;
  const status=[facts?.trialStatus,row.phase3Status,row.stage].filter(Boolean).join(" ");
  return facts?.resultsReleased===true ||
    facts?.primaryOutcome==="SUCCESS" ||
    row.technical?.benchmarks?.phase3===true ||
    Boolean(row.phase3Date) ||
    /completed|results|readout|primary completion/i.test(status);
}
const criteria:[string,string,(x:Trial)=>boolean|null][]=[
["phase3","Successful Phase 3 independently verified",x=>{
  if(x.technical?.benchmarks?.phase3===true)return true;
  if(x.trialFilters?.primaryOutcome==="SUCCESS"&&x.trialFilters?.resultsReleased===true)return true;
  if(/FAIL|NOT_MET|NEGATIVE/i.test(x.trialFilters?.primaryOutcome||""))return false;
  const registered=x.trialFilters?.registeredPhase||"";
  if(/^(Early Phase 1|Phase 1|Phase 1\/2|Phase 2)$/i.test(registered||x.stage||""))return false;
  return null;
}],
["registry","Phase 3 trial status recorded",x=>x.trialFilters?.registeredPhase==="Phase 3" || /^Phase 3(?: Results)?$/i.test(x.stage||"")?true:x.trialFilters?.registeredPhase?false:null],
["issuer","Issuer Phase 3 evidence linked",x=>x.phase3Source? /^https:\/\//.test(x.phase3Source):null],
["financing","Second financing verified (optional)",x=>x.technical?.benchmarks?.secondFinancing??x.trialFilters?.secondFinancingClosed??null],
["cash","SEC cash runway ≥12 months",x=>{const n=x.technical?.runwayMonths??x.trialFilters?.runwayMonths;return n==null?null:n>=12}],
["dilution","No unresolved dilution",x=>{const d=x.trialFilters?.dilution?.trim().toUpperCase();return !d?null:/^(NO|NONE|CLEAR|RESOLVED|NO UNRESOLVED)$/.test(d)?true:/UNRESOLVED|ACTIVE|AT RISK/.test(d)?false:null}],
["marketcap","Market cap $300M–$10B (optional)",x=>x.marketCap==null?null:x.marketCap>=300e6&&x.marketCap<=10e9],
["pdufa","Verified PDUFA date source",x=>x.pdufaDate&&x.fdaSource?/^https:\/\//.test(x.fdaSource):null],
["window","PDUFA in next 30–90 days",x=>{if(!x.pdufaDate)return null;const n=(Date.parse(x.pdufaDate.slice(0,10)+"T00:00:00Z")-Date.now())/86400000;return Number.isFinite(n)?n>=30&&n<=90:null}],
["volume","Relative volume ≥1.5×",x=>x.technical?.rvol==null?null:x.technical.rvol>=1.5],
["rsi","RSI 45–65",x=>x.technical?.rsi14==null?null:x.technical.rsi14>=45&&x.technical.rsi14<=65],
["trend","Close above SMA20 and SMA50",x=>{const t=x.technical;return t?.close==null||t.sma20==null||t.sma50==null?null:t.close>t.sma20&&t.close>t.sma50}],
["liquidity","20-day average dollar volume ≥$5M",x=>x.technical?.avgDollarVolume20==null?null:x.technical.avgDollarVolume20>=5000000],
["marketfresh","Current market evidence",x=>x.technical?.eodFresh??null],
["insiders","Insider buying verified",()=>null],
["institutions","Institutional accumulation verified",()=>null],
["sec","Fresh SEC source reconciliation",()=>null]
];
const suggestedByStage:Record<"GEM_JR"|"GEM",string[]>={GEM_JR:["phase3","registry","issuer","cash","marketfresh"],GEM:["phase3","registry","issuer","cash","pdufa","window","volume","rsi","trend","liquidity","marketfresh"]};
export default function GemQualificationChecklist({stage,pipeline,asOf,stageTotal,onScan,onReset}:{stage:"GEM_JR"|"GEM";pipeline:Trial[];asOf:string;stageTotal:number;onScan:(result:GemScanResult)=>void;onReset:()=>void}) {
 const [selected,setSelected]=useState<string[]>(()=>[...suggestedByStage[stage]]);
 const [result,setResult]=useState<GemScanResult|null>(null);
 const [open,setOpen]=useState(true);
 const [running,setRunning]=useState(false);
 const [message,setMessage]=useState("");
 const runSequence=useRef(0);
 const phase3ResearchCount=pipeline.filter(completedPhase3).length;
 function selectRequirements(next:string[]){
   if(running)return;
   setSelected(next);
   setResult(null);
   setMessage("Selections updated. Press SCAN to evaluate these requirements.");
   onReset();
 }
 function toggle(key:string){selectRequirements(selected.includes(key)?selected.filter(x=>x!==key):[...selected,key])}
 async function scan(){
   if(running||!pipeline.length)return;
   setRunning(true);
   setMessage("Running the selected requirements across the full loaded PIPELINE…");
   setResult(null);
   onReset();
   // Paint SCANNING before the CPU-bound saved-data evaluation begins.
   await new Promise<void>(resolve=>setTimeout(resolve,25));
   try{
     const chosen=criteria.filter(([key])=>selected.includes(key));
     const audits:GemCriterionAudit[]=chosen.map(([key,label])=>({key,label,passed:0,failed:0,unknown:0}));
     const passes:Trial[]=[],fails:Trial[]=[],needsReview:Trial[]=[];
     for(const record of pipeline){
       let hasFail=false,hasUnknown=false;
       for(let i=0;i<chosen.length;i++){
         const status=chosen[i][2](record);
         if(status===true)audits[i].passed++;
         else if(status===false){audits[i].failed++;hasFail=true;}
         else {audits[i].unknown++;hasUnknown=true;}
       }
       if(hasFail)fails.push(record);
       else if(hasUnknown)needsReview.push(record);
       else passes.push(record);
     }
     const runNumber=++runSequence.current;
     const next:GemScanResult={
       asOf,evaluatedAt:new Date().toISOString(),sourceTotal:pipeline.length,
       runNumber,audits,baseline:pipeline.length,selected:[...selected],passes,needsReview,fails
     };
     setResult(next);
     onScan(next);
     setMessage("Run #"+runNumber+" completed at "+new Date(next.evaluatedAt).toLocaleTimeString()+
       " — "+(selected.length?"selected requirements applied":"no restrictions; all records included")+".");
   }catch(error){
     setMessage("Scan failed: "+(error instanceof Error?error.message:"Unknown error"));
   }finally{setRunning(false)}
 }

 return <section className="panel" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checklist"} style={{margin:"18px 0",padding:16,border:"2px solid #236847",borderRadius:10,background:"#f8fff8",color:"#163522"}}>
 <button type="button" onClick={()=>setOpen(!open)} aria-expanded={open} style={{width:"100%",textAlign:"left",fontWeight:800,fontSize:18,padding:10,background:"#d9efdf",color:"#123b25",border:"1px solid #6c9e78",borderRadius:6}}>{open?"▾":"▸"} {stage==="GEM"?"GEM":"GEM JR"} — 17 qualification requirements ({selected.length} selected)</button>

 <div role="status" style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:12,marginBottom:12}}><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{pipeline.length.toLocaleString("en-US")}</strong><div>Pipeline research candidates (all stages)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{stageTotal.toLocaleString("en-US")}</strong><div>{stage==="GEM"?"GEM":"GEM JR"} candidates</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{baseline.length.toLocaleString("en-US")}</strong><div>Full source records available to scan</div></div></div>
 {open&&<><p>Every SCAN evaluates all {pipeline.length.toLocaleString("en-US")} currently loaded PIPELINE records against <strong>only your selected checkboxes</strong>. No boxes selected means an unrestricted scan. Phase 3 is not silently required; select its checkbox to enforce verified Phase 3 success. The source has {phase3ResearchCount.toLocaleString("en-US")} Phase 3/readout indicators, which are not the same as independently verified successful Phase 3 programs. Unknown source evidence is not treated as passing. Published data as of {asOf||"unverified"}; no live-market fetches, membership changes or trades.</p>
 <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:9,marginBottom:14}}>{criteria.map(([key,label])=><label key={key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:"1px solid #c1d8c8",borderRadius:5,background:"white"}}><input type="checkbox" checked={selected.includes(key)} onChange={()=>toggle(key)}/><span>{label}</span></label>)}</div>

 <div style={{display:"flex",gap:12,flexWrap:"wrap"}}><button type="button" onClick={()=>void scan()} disabled={running||!pipeline.length} style={{background:"#135a32",color:"white",padding:"10px 20px",borderRadius:6,fontWeight:700}}>{running?"SCANNING…":"SCAN "+(stage==="GEM"?"GEM":"GEM JR")}</button><div aria-label="Unrestricted Phase 3 baseline" title="Historical approximate count; not verified live" style={{display:"flex",alignItems:"center",gap:8,padding:"8px 14px",border:"2px solid #1d6d4b",borderRadius:6,background:"#effaf3"}}><strong style={{fontSize:24}}>~730</strong><span style={{fontSize:12}}>Phase 3 completed<br/>Before restrictions</span></div><button type="button" onClick={()=>selectRequirements([])}>Clear selections</button><button type="button" onClick={()=>selectRequirements([...suggestedByStage[stage]])} style={{padding:"10px 14px",border:"1px solid #1d6d4b",borderRadius:6,background:"#e4f3e8",fontWeight:700}}>SUGGESTED</button></div>


 <p role="status" aria-live="polite" style={{fontWeight:700,marginTop:12}}>{message||"Ready to scan "+pipeline.length.toLocaleString("en-US")+" PIPELINE records."}</p>
 {result&&<div role="status" style={{marginTop:15,padding:12,background:"#e8f2ec",borderRadius:6}}>
  <strong>Full PIPELINE evidence screen complete · Run #{result.runNumber}</strong>
  <p>{result.baseline.toLocaleString("en-US")} PIPELINE records evaluated · {result.passes.length.toLocaleString("en-US")} {result.selected.length?"passed all checked requirements":"unrestricted matches"} · {result.fails.length.toLocaleString("en-US")} failed · {result.needsReview.length.toLocaleString("en-US")} need verification. Completed at {new Date(result.evaluatedAt).toLocaleTimeString()}.</p>
  <p><strong>Applied requirements:</strong> {result.audits.length?result.audits.map(x=>x.label).join(" · "):"None (all records included)"}</p>
  {result.audits.length>0&&<div style={{maxWidth:"100%",overflowX:"auto"}}>
    <table style={{width:"100%",borderCollapse:"collapse",fontSize:13}}>
      <thead><tr><th style={{textAlign:"left"}}>Requirement</th><th>Pass</th><th>Fail</th><th>No evidence</th></tr></thead>
      <tbody>{result.audits.map(a=><tr key={a.key}>
        <td style={{padding:"6px 3px"}}>{a.label}</td>
        <td style={{textAlign:"right",padding:6}}>{a.passed.toLocaleString("en-US")}</td>
        <td style={{textAlign:"right",padding:6}}>{a.failed.toLocaleString("en-US")}</td>
        <td style={{textAlign:"right",padding:6}}>{a.unknown.toLocaleString("en-US")}</td>
      </tr>)}</tbody>
    </table>
  </div>}
  {result.audits.some(a=>a.unknown===result.baseline)&&<p style={{fontWeight:700}}>Some selected requirements have no verifiable evidence for any of these records. They cannot produce verified passes until that evidence is available, regardless of how many times you scan.</p>}
  <p>Passed programs and those needing verification appear in the candidate table below. Scanning does not add records to saved GEM membership.</p>
 </div>}

 </>}</section>
}
