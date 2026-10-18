"use client";
import {useState} from "react";
import type {Candidate} from "./Workspace";

type Trial = Candidate;
export type GemScanResult = {
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
export default function GemQualificationChecklist({stage,pipeline,asOf,stageTotal,onScan}:{stage:"GEM_JR"|"GEM";pipeline:Trial[];asOf:string;stageTotal:number;onScan:(result:GemScanResult)=>void}) {
 const [selected,setSelected]=useState<string[]>(()=>[...suggestedByStage[stage]]);
 const [result,setResult]=useState<{total:number;pass:number;fail:number;unknown:number;matches:Trial[]}|null>(null);
 const [open,setOpen]=useState(true);
 function toggle(key:string){setSelected(v=>v.includes(key)?v.filter(x=>x!==key):[...v,key]);setResult(null)}

 const baseline=pipeline.filter(completedPhase3);
 function scan(){
   const passes:Trial[]=[],needsReview:Trial[]=[],fails:Trial[]=[];
   for(const record of baseline){
     const checks=criteria.filter(([key])=>selected.includes(key)).map(([, ,test])=>test(record));
     if(checks.includes(false)){fails.push(record);continue}
     if(checks.includes(null)){needsReview.push(record);continue}
     passes.push(record);
   }
   const result:GemScanResult={
     asOf, evaluatedAt:new Date().toISOString(), sourceTotal:pipeline.length,
     baseline:baseline.length, selected:[...selected],passes,needsReview,fails
   };
   setResult({total:baseline.length,pass:passes.length,fail:fails.length,unknown:needsReview.length,matches:passes});
   onScan(result);
 }

 return <section className="panel" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checklist"} style={{margin:"18px 0",padding:16,border:"2px solid #236847",borderRadius:10,background:"#f8fff8",color:"#163522"}}>
 <button type="button" onClick={()=>setOpen(!open)} aria-expanded={open} style={{width:"100%",textAlign:"left",fontWeight:800,fontSize:18,padding:10,background:"#d9efdf",color:"#123b25",border:"1px solid #6c9e78",borderRadius:6}}>{open?"▾":"▸"} {stage==="GEM"?"GEM":"GEM JR"} — 17 qualification requirements ({selected.length} selected)</button>

 <div role="status" style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:12,marginBottom:12}}><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{pipeline.length.toLocaleString("en-US")}</strong><div>Pipeline research candidates (all stages)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{stageTotal.toLocaleString("en-US")}</strong><div>{stage==="GEM"?"GEM":"GEM JR"} candidates</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{baseline.length.toLocaleString("en-US")}</strong><div>Phase 3 completed · current source evidence</div></div></div>
 {open&&<><p>Select evidence checks, then scan {baseline.length.toLocaleString("en-US")} completed Phase 3 programs from the full published PIPELINE ({pipeline.length.toLocaleString("en-US")} total records). Unknown evidence stays in Needs verification, never counted as a pass. The scan runs on current loaded published records, not new live-market or SEC requests. Source as of {asOf||"unverified"}. No stage membership changes or trading orders.</p>
 <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:9,marginBottom:14}}>{criteria.map(([key,label])=><label key={key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:"1px solid #c1d8c8",borderRadius:5,background:"white"}}><input type="checkbox" checked={selected.includes(key)} onChange={()=>toggle(key)}/><span>{label}</span></label>)}</div>

 <div style={{display:"flex",gap:12,flexWrap:"wrap"}}><button type="button" onClick={scan} disabled={!selected.length} style={{background:"#135a32",color:"white",padding:"10px 20px",borderRadius:6,fontWeight:700}}>SCAN {stage==="GEM"?"GEM":"GEM JR"}</button><div aria-label="Unrestricted Phase 3 baseline" title="Historical approximate count; not verified live" style={{display:"flex",alignItems:"center",gap:8,padding:"8px 14px",border:"2px solid #1d6d4b",borderRadius:6,background:"#effaf3"}}><strong style={{fontSize:24}}>~730</strong><span style={{fontSize:12}}>Phase 3 completed<br/>Before restrictions</span></div><button type="button" onClick={()=>{setSelected([]);setResult(null)}}>Clear selections</button><button type="button" onClick={()=>{setSelected([...suggestedByStage[stage]]);setResult(null)}} style={{padding:"10px 14px",border:"1px solid #1d6d4b",borderRadius:6,background:"#e4f3e8",fontWeight:700}}>SUGGESTED</button></div>

 {result&&<div role="status" style={{marginTop:15,padding:12,background:"#e8f2ec",borderRadius:6}}><strong>Full PIPELINE evidence screen complete</strong><p>{result.total} Phase 3 records evaluated · {result.pass} verified passes · {result.fail} failed · {result.unknown} need verification</p><p>Passing and needs-verification records are displayed in the candidate table below. The scan does not promote trials into saved GEM membership.</p></div>}
 </>}</section>
}
