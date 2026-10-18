"use client";
import {useState} from "react";
type Trial = {id:string;ticker:string;phase3Status?:string;phase3Source?:string;technical?:{benchmarks?:{phase3?:boolean;secondFinancing?:boolean};runwayMonths?:number|null;rvol?:number|null;rsi14?:number|null;close?:number|null;sma20?:number|null;sma50?:number|null;eodFresh?:boolean;avgDollarVolume20?:number|null};pdufaDate?:string;fdaSource?:string;financingStatus?:string;financingSource?:string;marketCap?:number|null;capInRange?:boolean;approvalProbability?:string};
const criteria:[string,string,(x:Trial)=>boolean|null][]=[
["phase3","Successful Phase 3 independently verified",x=>x.technical?.benchmarks?.phase3??null],
["registry","Phase 3 trial status recorded",x=>x.phase3Status? /completed|active|recruit/i.test(x.phase3Status):null],
["issuer","Issuer Phase 3 evidence linked",x=>x.phase3Source? /^https:\/\//.test(x.phase3Source):null],
["financing","Second financing verified (optional)",x=>x.technical?.benchmarks?.secondFinancing??null],
["cash","SEC cash runway ≥12 months",x=>x.technical?.runwayMonths==null?null:x.technical.runwayMonths>=12],
["dilution","No unresolved dilution",()=>null],
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
export default function GemQualificationChecklist({stage,rows,universeCount,stageTotal}:{stage:"GEM_JR"|"GEM";rows:Trial[];universeCount:number;stageTotal:number}) {
 const [selected,setSelected]=useState<string[]>([]);
 const [result,setResult]=useState<{total:number;pass:number;fail:number;unknown:number;matches:Trial[]}|null>(null);
 const [open,setOpen]=useState(true);
 function toggle(key:string){setSelected(v=>v.includes(key)?v.filter(x=>x!==key):[...v,key]);setResult(null)}
 function scan(){let pass=0,fail=0,unknown=0;const matches:Trial[]=[];for(const row of rows){const checks=criteria.filter(([key])=>selected.includes(key)).map(([, ,test])=>test(row));if(checks.includes(false)){fail++;continue}if(checks.includes(null)){unknown++;continue}pass++;matches.push(row)}setResult({total:rows.length,pass,fail,unknown,matches})}
 return <section className="panel" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" qualification checklist"} style={{margin:"18px 0",padding:16,border:"2px solid #236847",borderRadius:10,background:"#f8fff8",color:"#163522"}}>
 <button type="button" onClick={()=>setOpen(!open)} aria-expanded={open} style={{width:"100%",textAlign:"left",fontWeight:800,fontSize:18,padding:10,background:"#d9efdf",color:"#123b25",border:"1px solid #6c9e78",borderRadius:6}}>{open?"▾":"▸"} {stage==="GEM"?"GEM":"GEM JR"} — 17 qualification requirements ({selected.length} selected)</button>
 <div role="status" style={{display:"flex",gap:12,flexWrap:"wrap",marginTop:12,marginBottom:12}}><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{universeCount.toLocaleString("en-US")}</strong><div>Pipeline research candidates (all stages)</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{stageTotal.toLocaleString("en-US")}</strong><div>{stage==="GEM"?"GEM":"GEM JR"} candidates</div></div><div style={{padding:"10px 14px",background:"#e4f3e8",borderRadius:6}}><strong style={{fontSize:22}}>{rows.length.toLocaleString("en-US")}</strong><div>Currently displayed / searchable</div></div></div>
 {open&&<><p>Select evidence checks, then scan the {rows.length} published candidates on this page. Missing evidence is never treated as passing. This is a saved-data audit, not a live market scan or trading authorization.</p>
 <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(230px,1fr))",gap:9,marginBottom:14}}>{criteria.map(([key,label])=><label key={key} style={{display:"flex",gap:8,alignItems:"flex-start",padding:8,border:"1px solid #c1d8c8",borderRadius:5,background:"white"}}><input type="checkbox" checked={selected.includes(key)} onChange={()=>toggle(key)}/><span>{label}</span></label>)}</div>
 <div style={{display:"flex",gap:12,flexWrap:"wrap"}}><button type="button" onClick={scan} disabled={!selected.length} style={{background:"#135a32",color:"white",padding:"10px 20px",borderRadius:6,fontWeight:700}}>SCAN {stage==="GEM"?"GEM":"GEM JR"} · {stageTotal.toLocaleString("en-US")} candidates</button><button type="button" onClick={()=>{setSelected([]);setResult(null)}}>Clear selections</button></div>
 {result&&<div role="status" style={{marginTop:15,padding:12,background:"#e8f2ec",borderRadius:6}}><strong>Saved evidence scan complete</strong><p>{result.total} checked · {result.pass} passed · {result.fail} failed · {result.unknown} unverified</p>{result.matches.length>0&&<p>Matching tickers: {result.matches.slice(0,40).map(x=>x.ticker).join(", ")}</p>}</div>}
 </>}</section>
}
