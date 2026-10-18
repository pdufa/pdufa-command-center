"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import type {Candidate} from "./Workspace";

type Feed="sip"|"iex";
type Market={
  ticker:string;stage?:string;provider:string;status:string;reason?:string;
  technicalScreen?:string;feed?:string;feedCoverage?:string;date?:string;
  close?:number;sma20?:number;sma50?:number;atr14?:number;rsi14?:number;
  rvol20?:number;baseLow?:number;baseHigh?:number;riskToStopPct?:number;
  change20Pct?:number;trendAboveSma20Sma50?:boolean;breakout?:boolean;
};
function fmt(v?:number,decimals=2){
  return typeof v==="number" && Number.isFinite(v)?v.toFixed(decimals):"—";
}
function price(v?:number){
  return typeof v==="number"&&Number.isFinite(v)?"$"+v.toFixed(v<1?4:2):"—";
}
function indicator(m?:Market){
  if(!m)return "NOT LOADED";
  if(m.status!=="OK")return "UNAVAILABLE";
  switch(m.technicalScreen){
    case "BREAKOUT_REVIEW":return "BREAKOUT / RESEARCH";
    case "BASE_FORMING":return "BASE FORMING";
    case "BELOW_SMA20":return "BELOW SMA20";
    case "ENTRY_RISK_OVER_8_PERCENT":return "HIGH PRICE RISK";
    default:return "WATCH";
  }
}

export default function AlpacaTrialSelection({
  stage,records,onChoose
}:{
  stage:"GEM"|"GEM_JR";records:Candidate[];onChoose:(trial:Candidate)=>void;
}){
  const [feed,setFeed]=useState<Feed>("sip");
  const [sort,setSort]=useState("source");
  const [market,setMarket]=useState<Record<string,Market>>({});
  const [loading,setLoading]=useState(false);
  const [progress,setProgress]=useState(0);
  const [loadError,setLoadError]=useState("");
  const controller=useRef<AbortController|null>(null);
  const symbols=useMemo(()=>[...new Set(records.map(r=>r.ticker.toUpperCase()))]
    .filter(t=>/^[A-Z][A-Z0-9.-]{0,12}$/.test(t)).slice(0,80),[records]);
  useEffect(()=>()=>{
    controller.current?.abort();
  },[]);
  const displayed=useMemo(()=>{
    const items=[...records];
    const score=(r:Candidate)=>{
      const m=market[r.ticker.toUpperCase()];
      if(!m||m.status!=="OK")return Number.NEGATIVE_INFINITY;
      return sort==="rvol"?(m.rvol20??-Infinity):
        sort==="return"?(m.change20Pct??-Infinity):
        sort==="risk"?(m.riskToStopPct==null?-Infinity:-m.riskToStopPct):
        sort==="setup"?(m.technicalScreen==="BREAKOUT_REVIEW"?5:
          m.technicalScreen==="BASE_FORMING"?4:
          m.technicalScreen==="WATCH"?3:
          m.technicalScreen==="BELOW_SMA20"?2:1):0;
    };
    if(sort!=="source")items.sort((a,b)=>score(b)-score(a));
    return items;
  },[records,market,sort]);
  async function load(){
    if(loading || !symbols.length)return;
    controller.current?.abort();
    const current=new AbortController();
    controller.current=current;
    setMarket({});setProgress(0);setLoadError("");setLoading(true);
    let next=0;
    const worker=async()=>{
      while(next<symbols.length&&!current.signal.aborted){
        const symbol=symbols[next++];
        let result:Market;
        try{
          const r=await fetch("/api/trial-market/"+stage+"/"+encodeURIComponent(symbol)
            +"?feed="+feed,{cache:"no-store",signal:current.signal});
          if(!r.ok)throw Error("HTTP "+r.status);
          result=await r.json() as Market;
          if(result.ticker!==symbol||result.provider!=="ALPACA")throw Error("Provider mismatch");
        }catch{
          if(current.signal.aborted)break;
          result={ticker:symbol,status:"UNAVAILABLE",provider:"ALPACA",
                  reason:"MARKET_DATA_OR_CONNECTION_FAILED"};
        }
        if(!current.signal.aborted){
          setMarket(old=>({...old,[symbol]:result}));
          setProgress(old=>old+1);
        }
      }
    };
    try{
      await Promise.all(Array.from({length:Math.min(3,symbols.length)},worker));
      if(!current.signal.aborted&&!symbols.length)setLoadError("No supported public tickers.");
    }finally{
      if(!current.signal.aborted)setLoading(false);
    }
  }
  function changeFeed(v:Feed){
    controller.current?.abort();
    setLoading(false);setMarket({});setProgress(0);setFeed(v);
  }
  return <section className="panel" aria-label={stage+" Alpaca trial selection market data"}>
    <h3>ALPACA DATA — SELECT TRIALS TO RESEARCH</h3>
    <p className="subtle">Issuer-level market data alongside each exact clinical program.
      No position is required. These are <strong>research indicators, not BUY/SELL instructions</strong>.
      The same company's ticker may appear for several independent trials.</p>
    <div className="gem-table-controls">
      <label>Market feed{" "}
        <select value={feed} onChange={e=>changeFeed(e.target.value as Feed)}>
          <option value="sip">SIP consolidated daily (preferred)</option>
          <option value="iex">IEX single exchange (limited)</option>
        </select>
      </label>
      <label>Compare by{" "}
        <select value={sort} onChange={e=>setSort(e.target.value)}>
          <option value="source">Original trial order</option>
          <option value="setup">Technical setup</option>
          <option value="rvol">Highest relative volume</option>
          <option value="return">Strongest 20-day momentum</option>
          <option value="risk">Lowest risk to support reference</option>
        </select>
      </label>
      <button type="button" onClick={()=>void load()} disabled={loading||!symbols.length}>
        {loading?"CHECKING ALPACA…":"LOAD / REFRESH ALPACA DATA"}
      </button>
      <span aria-live="polite" role="status">{progress}/{symbols.length} unique tickers checked</span>
    </div>
    {feed==="iex"&&<p className="subtle"><strong>IEX LIMITATION:</strong> RVOL is based on
      IEX-only activity and cannot substitute for consolidated-volume confirmation.</p>}
    {!!loadError&&<p role="alert">{loadError}</p>}
    <div className="table-scroll">
      <table className="gem-source-parity-table">
        <thead><tr>
          {["Trial","Stock","PDUFA","Alpaca date","Close","SMA20","SMA50",
            "RSI14","RVOL20","ATR14","20d move","Base low–high","Risk to support",
            "Technical screen","Research"].map(h=><th key={h}>{h}</th>)}
        </tr></thead>
        <tbody>{displayed.map((r,i)=>{
          const m=market[r.ticker.toUpperCase()];
          return <tr key={r.id+"|"+i}>
            <td><strong>{r.drug||r.indication||"Unknown drug"}</strong>
              <small>{r.programId||"Program ID unavailable"} · {r.nctId||"NCT unverified"}</small></td>
            <td><strong>{r.ticker}</strong></td>
            <td>{r.pdufaDate||"—"}</td>
            <td>{m?.status==="OK"?m.date:(m?.status||"—")}</td>
            <td>{price(m?.close)}</td>
            <td>{price(m?.sma20)}</td>
            <td>{price(m?.sma50)}</td>
            <td>{fmt(m?.rsi14,1)}</td>
            <td>{fmt(m?.rvol20,2)}{m?.rvol20!=null?"×":""}</td>
            <td>{price(m?.atr14)}</td>
            <td>{fmt(m?.change20Pct,1)}{m?.change20Pct!=null?"%":""}</td>
            <td>{price(m?.baseLow)} – {price(m?.baseHigh)}</td>
            <td>{fmt(m?.riskToStopPct,1)}{m?.riskToStopPct!=null?"%":""}</td>
            <td title={m?.reason||m?.feedCoverage||"Not assessed"}>
              {indicator(m)}</td>
            <td><button type="button" onClick={()=>onChoose(r)}>
              VIEW TRIAL ↓
            </button></td>
          </tr>;
        })}</tbody>
      </table>
    </div>
    <small>Provider: Alpaca · 1-day historical bars · split adjusted · no order access.
      Technical thresholds are provisional and <strong>do not establish Phase 3 success,
      financing completion, regulatory approval odds or a trade recommendation</strong>.
      Unavailable data is never filled with estimates. Market cap filter: OFF.</small>
  </section>;
}
