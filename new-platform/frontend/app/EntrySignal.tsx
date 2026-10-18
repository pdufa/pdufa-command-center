"use client";
import { useEffect, useState } from "react";
import "./entry-signal.css";

type Check = {label:string;pass:boolean;actual?:number;target?:number;rule:string};
type Signal = {programId:string;ticker:string;status:string;green:boolean;message:string;
  checks:Check[];entryTrigger?:number;maximumEntry?:number;initialStop?:number;
  signalSession?:string;entrySession?:string;entryOpen?:string;entryClose?:string;historyFeed:string;adjustment:string;
  calculatedAt:string;disclaimer:string;secondFinancingOptional?:boolean;secondFinancingVerified?:boolean;anchorType?:string;
  quote?:{bid:number;ask:number;asOf:string;feed:string}};
const price=(value?:number)=>typeof value==="number"&&Number.isFinite(value)?"$"+value.toFixed(value<1?4:2):"—";

export default function EntrySignal({programId,ticker}:{programId:string;ticker:string}) {
  const [received,setData]=useState<Signal|null>(null),[error,setError]=useState("");
  const data=received?.programId===programId&&received?.ticker===ticker?received:null;
  const [clock,setClock]=useState(()=>Date.now());
  useEffect(()=>{
    const tick=()=>setClock(Date.now());
    const timer=setInterval(tick,1000);
    document.addEventListener("visibilitychange",tick);
    return()=>{clearInterval(timer);document.removeEventListener("visibilitychange",tick);};
  },[]);
  useEffect(()=>{
    const ctrl=new AbortController();let busy=false;
    setData(null);setError("");
    const refresh=async()=>{
      if(busy||document.visibilityState==="hidden")return;
      busy=true;
      try {
        const response=await fetch("/api/entry-signal/"+encodeURIComponent(programId),{cache:"no-store",signal:ctrl.signal});
        if(!response.ok)throw Error("Entry calculation unavailable (HTTP "+response.status+")");
        const value:Signal=await response.json();
        if(value.programId!==programId||value.ticker!==ticker)throw Error("Entry identity could not be verified");
        if(!ctrl.signal.aborted){setData(value);setError("");}
      }catch(e){if(!ctrl.signal.aborted){setData(null);setError(String(e));}}
      finally{busy=false;}
    };
    void refresh();const timer=setInterval(()=>void refresh(),30000);
    document.addEventListener("visibilitychange",refresh);
    return()=>{ctrl.abort();clearInterval(timer);document.removeEventListener("visibilitychange",refresh);};
  },[programId,ticker]);
  // A green light expires locally even when connectivity or browser timers pause.
  const stamp=data?.calculatedAt?Date.parse(data.calculatedAt):0;
  const quoteStamp=data?.quote?.asOf?Date.parse(data.quote.asOf):0;
  const marketOpen=data?.entryOpen?Date.parse(data.entryOpen):Infinity;
  const marketClose=data?.entryClose?Date.parse(data.entryClose):0;
  const green=Boolean(!error&&data?.green&&data.status==="BUY"&&clock-stamp>=0&&clock-stamp<60000
    &&clock-quoteStamp>=0&&clock-quoteStamp<60000&&clock>=marketOpen&&clock<marketClose);
  const label=green?"BUY — ENTRY CONDITIONS PASSED":error?"ENTRY UNAVAILABLE":!data?"CALCULATING ENTRY":
    data.status==="READY_NEXT_SESSION"?"SETUP CONFIRMED — WAIT FOR NEXT SESSION":
    data.status==="WAIT"?"WAIT — ENTRY NOT CONFIRMED":"ENTRY UNAVAILABLE";
  return <section className={"entry-signal "+(green?"entry-signal-green":data?.status==="WAIT"||data?.status==="READY_NEXT_SESSION"?"entry-signal-wait":"entry-signal-missing")}
    aria-label={ticker+" calculated buy signal"} aria-live="polite">
    <div className="entry-signal-title"><span className="entry-signal-light" aria-hidden="true"/><strong>{label}</strong></div>
    <p>{error||data?.message||"Checking this exact program’s Phase 3, dilution evidence and Alpaca market data."}</p>
    {data?.secondFinancingOptional&&<p className="subtle small">Second financing: {data.secondFinancingVerified?"SEC verified":"not verified"} · OPTIONAL for this signal. VWAP anchor: {data.anchorType==="PHASE3_READOUT"?"verified Phase 3 results":"verified financing when available"}. Cash and dilution risks still require review.</p>}
    {data?.entryTrigger!=null&&<div className="entry-signal-prices">
      <span>ENTRY TRIGGER<strong>{price(data.entryTrigger)}</strong></span>
      <span>MAXIMUM BUY<strong>{price(data.maximumEntry)}</strong></span>
      <span>INITIAL STOP<strong>{price(data.initialStop)}</strong></span>
    </div>}
    {data?.entrySession&&<p className="small">Entry session: {data.entrySession} · Setup from completed session: {data.signalSession}
      {data.quote?" · Live "+data.quote.feed+" bid "+price(data.quote.bid)+" / ask "+price(data.quote.ask):" · Live price confirmation pending"}</p>}
    {!!data?.checks?.length&&<details><summary>Entry checks · {data.checks.filter(c=>c.pass).length}/{data.checks.length} passed</summary>
      <ul>{data.checks.map(c=><li key={c.label}><strong>{c.pass?"✓ PASS":"— WAIT"} · {c.label}</strong><span>{c.rule}</span>
        {c.actual!=null&&<small>Observed: {c.actual.toFixed(4)} · threshold: {c.target?.toFixed(4)}</small>}</li>)}</ul>
    </details>}
    <small>{data?.disclaimer||"Initial entry rules; not backtested. No automatic orders."} Stops can fill below their stated level.
      {data?" · Alpaca SIP history · split adjusted · "+new Date(data.calculatedAt).toLocaleString():""}</small>
  </section>;
}
