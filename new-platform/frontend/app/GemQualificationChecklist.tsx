"use client";
import {useRef, useState} from "react";
import type {Candidate} from "./Workspace";

type Trial = Candidate;
export type GemScanResult = {
  asOf: string;
  evaluatedAt: string;
  runNumber: number;
  elapsedMs: number;
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
["phase3","Successful Phase 3 independently verified",x=>x.technical?.benchmarks?.phase3===true?true:x.trialFilters?.primaryOutcome==="SUCCESS"&&x.trialFilters?.resultsReleased===true?true:null],
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
 const [result,setResult]=useState<{total:number;pass:number;fail:number;unknown:number;unrestricted:boolean;runNumber:number;elapsedMs:number;at:string}|null>(null);
 const [running,setRunning]=useState(false);
 const [runStatus,setRunStatus]=useState("");
 const runSequence=useRef(0);
 const baseline=selected.includes("phase3")?pipeline.filter(completedPhase3):pipeline;
 const unrestricted=selected.length===0;
 function changeSelections(next:string[]){
   setSelected(next);setResult(null);setRunStatus("");onReset();
 }
 function toggle(key:string){changeSelections(selected.includes(key)?selected.filter(x=>x!==key):[...selected,key])}
 async function scan(){
   if(running||!pipeline.length)return;
   setRunning(true);setResult(null);setRunStatus("Scanning the loaded PIPELINE…");onReset();
   // Allow React to paint the running status before evaluating the full source dataset.
   await new Promise<void>(resolve=>setTimeout(resolve,30));
   const start=performance.now();
   try{
     const passes:Trial[]=[],needsReview:Trial[]=[],fails:Trial[]=[];
     const tests=criteria.filter(([key])=>selected.includes(key)).map(([, ,test])=>test);
     const candidates=selected.includes("phase3")?pipeline.filter(completedPhase3):pipeline;
     for(const record of candidates){
       let failed=false,unknown=false;
       for(const test of tests){
         const verdict=test(record);
         if(verdict===false){failed=true;break}
         if(verdict===null)unknown=true;
       }
       if(failed)fails.push(record);
       else if(unknown)needsReview.push(record);
       else passes.push(record);
     }
     const runNumber=++runSequence.current;
     const evaluatedAt=new Date().toISOString();
     const elapsedMs=Math.round(performance.now()-start);
     const next:GemScanResult={
       asOf,evaluatedAt,runNumber,elapsedMs,sourceTotal:pipeline.length,
       baseline:candidates.length,selected:[...selected],passes,needsReview,fails
     };
     setResult({total:candidates.length,pass:passes.length,fail:fails.length,
       unknown:needsReview.length,unrestricted:tests.length===0,runNumber,elapsedMs,at:evaluatedAt});
     onScan(next);
     setRunStatus("Run #"+runNumber+" completed at "+new Date(evaluatedAt).toLocaleTimeString()+ " from published PIPELINE data");
   }catch(error){
     setRunStatus("Scan failed: "+(error instanceof Error?error.message:"Unknown error"));
   }finally{setRunning(false)}
 }

 return <section className="panel" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checklist"} style={{margin:"18px 0",padding:16,border:"2px solid #236847",borderRadius:10,background:"#f8fff8",color:"#163522"}}>
 <button type="button" onClick={()=>setOpen(!open)} aria-expanded={open} style={{width:"100%",textAlign:"left",fontWeight:800,fontSize:18,padding:10,background:"#d9efdf",color:"#123b25",border:"1px solid #6c9e78",borderRadius:6}}>{open?"▾":"▸"} {stage==="GEM"?"GEM":"GEM JR"} — 17 qualification requirements ({selected.length} selected)</button>

 <div role="status" style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:12,marginBottom:12}}><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{pipeline.length.toLocaleString("en-US")}</strong><div>Pipeline research candidates (all stages)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{stageTotal.toLocaleString("en-US")}</strong><div>{stage==="GEM"?"GEM":"GEM JR"} candidates</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{baseline.length.toLocaleString("en-US")}</strong><div>{selected.includes("phase3")?"Phase 3 screening records":"Full PIPELINE · no Phase 3 prerequisite"}</div></div></div>
 {open&&<><p>Select checks and press SCAN as often as needed. With every checkbox cleared, the scan includes ALL {pipeline.length.toLocaleString("en-US")} published PIPELINE records with no restrictions. With Phase 3 checked, it assesses {baseline.length.toLocaleString("en-US")} records with Phase 3 completion/readout indicators (not necessarily independently verified success). Unknown evidence stays in Needs verification, never counted as a pass. Source as of {asOf||"unverified"}; this scan uses loaded data, not fresh SEC or market requests. No stage membership changes or orders.</p>
 <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:9,marginBottom:14}}>{criteria.map(([key,label])=><label key={key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:"1px solid #c1d8c8",borderRadius:5,background:"white"}}><input type="checkbox" checked={selected.includes(key)} onChange={()=>toggle(key)}/><span>{label}</span></label>)}</div>

 <div style={{display:"flex",gap:12,flexWrap:"wrap"}}><button type="button" onClick={()=>void scan()} disabled={running||!pipeline.length} style={{background:"#135a32",color:"white",padding:"10px 20px",borderRadius:6,fontWeight:700}}>{running?"SCANNING…":result?"SCAN AGAIN ":"SCAN "}{running?"":stage==="GEM"?"GEM":"GEM JR"}</button><div aria-label="Unrestricted Phase 3 baseline" title="Historical approximate count; not verified live" style={{display:"flex",alignItems:"center",gap:8,padding:"8px 14px",border:"2px solid #1d6d4b",borderRadius:6,background:"#effaf3"}}><strong style={{fontSize:24}}>~730</strong><span style={{fontSize:12}}>Phase 3 completed<br/>Before restrictions</span></div><button type="button" onClick={()=>changeSelections([])}>Clear selections</button><button type="button" onClick={()=>changeSelections([...suggestedByStage[stage]])} style={{padding:"10px 14px",border:"1px solid #1d6d4b",borderRadius:6,background:"#e4f3e8",fontWeight:700}}>SUGGESTED</button></div>

 <div role="status" aria-live="polite" style={{marginTop:10,fontWeight:700}}>{runStatus|| (unrestricted?"No restrictions selected — SCAN will show the full PIPELINE.":"Ready to scan selected requirements.")}</div>
 {result&&<div role="status" style={{marginTop:15,padding:12,background:"#e8f2ec",borderRadius:6}}><strong>Full PIPELINE evidence screen complete · Run #{result.runNumber}</strong><p>{result.total.toLocaleString("en-US")} {result.unrestricted?"unrestricted PIPELINE records":"candidate records"} evaluated · {result.pass.toLocaleString("en-US")} {result.unrestricted?"unrestricted matches":"passed selected checks"} · {result.fail.toLocaleString("en-US")} failed · {result.unknown.toLocaleString("en-US")} need verification · {result.elapsedMs} ms</p><p>Passing and needs-verification records are displayed in the candidate table below. The scan does not promote trials into saved GEM membership.</p></div>}
 </>}</section>
}
