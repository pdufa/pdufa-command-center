"use client";

/**
 * Read-only Alpaca technical STATUS sheet. One independent exact-program table
 * per FOCUS ticker; never attempts broker preview, approval, or execution.
 */
import {useEffect,useMemo,useState} from "react";
import focusSnapshot from "../data/p3PostDataActive.json";
import {WT_ETRADE_CANDIDATES} from "../lib/wt-etrade-order-draft";
import {evaluateWtAlpacaTechnicalSignal,type WtAlpacaTechnicalSignal} from "../lib/wt-alpaca-buy-signal";
import {sessionSnapshot,type WtMarket} from "../lib/wt-entry-stay-exit";

type MarketResult={data:WtMarket|null;error:string;fetchedAt:number|null};
type Markets=Record<string,MarketResult>;
const CELL={padding:"9px 10px",borderBottom:"1px solid #dce6e6",textAlign:"left" as const,verticalAlign:"top" as const};
const DATE_FMT=new Intl.DateTimeFormat("en-US",{year:"numeric",month:"short",day:"numeric",hour:"numeric",minute:"2-digit",timeZone:"America/Los_Angeles",timeZoneName:"short"});

function signalTitle(signal:WtAlpacaTechnicalSignal){
  return signal.status==="BUY_SETUP"?"TECHNICAL BUY SETUP":signal.status==="WAIT"?"WAIT":"UNAVAILABLE";
}
function pdufaGateText(signal:WtAlpacaTechnicalSignal){
  switch(signal.pdufaGate){
    case "PRE_PDUFA_BLACKOUT":return "HOLD — within 14 days of recorded PDUFA";
    case "PAST_TARGET":return "HOLD — target date passed; FDA outcome requires review";
    case "NO_VERIFIED_DATE":return "HOLD — recorded PDUFA date missing/invalid";
    case "OUTSIDE_BLACKOUT":return "Outside timing blackout; all other trade prerequisites still required";
  }
}
function reportDate(value:string|null){
  return value?value:"UNAVAILABLE";
}
function money(value:number|null){
  return value===null?"—":"$"+value.toFixed(2);
}

export default function WtAlpacaStatusSheet(){
  const [markets,setMarkets]=useState<Markets>({});
  const [clock,setClock]=useState(0);
  const [revision,setRevision]=useState(0);
  const [refreshing,setRefreshing]=useState(false);

  useEffect(()=>{
    const controller=new AbortController();
    let busy=false;
    const refresh=async()=>{
      if(busy||document.visibilityState==="hidden")return;
      busy=true;setRefreshing(true);
      try{
        await Promise.all(WT_ETRADE_CANDIDATES.map(async candidate=>{
          let data:WtMarket|null=null,error="";
          try{
            const response=await fetch("/api/alpaca-chart/"+encodeURIComponent(candidate.programId)+"?range=6M",{
              cache:"no-store",signal:controller.signal,
            });
            if(!response.ok)throw Error("Alpaca data unavailable (HTTP "+response.status+")");
            const received=await response.json() as WtMarket;
            if(received.provider!=="ALPACA"||received.ticker!==candidate.ticker||
              received.programId!==candidate.programId||received.status!=="OK"||
              received.adjustment!=="raw"||!["IEX","SIP"].includes(received.feed))
              throw Error(received.message||"Alpaca source, exact program, feed, or raw bars could not be verified");
            data=received;
          }catch(e){
            if(controller.signal.aborted)return;
            error=e instanceof Error?e.message:"Market feed unavailable";
          }
          if(!controller.signal.aborted)setMarkets(previous=>({
            ...previous,[candidate.programId]:{data,error,fetchedAt:Date.now()}
          }));
        }));
      }finally{busy=false;if(!controller.signal.aborted)setRefreshing(false);}
    };
    const tick=()=>setClock(Date.now());
    tick();void refresh();
    const clockId=setInterval(tick,30000);
    const marketId=setInterval(()=>void refresh(),300000);
    document.addEventListener("visibilitychange",tick);
    document.addEventListener("visibilitychange",refresh);
    return()=>{
      controller.abort();clearInterval(clockId);clearInterval(marketId);
      document.removeEventListener("visibilitychange",tick);
      document.removeEventListener("visibilitychange",refresh);
    };
  },[revision]);

  const rows=useMemo(()=>WT_ETRADE_CANDIDATES.map(candidate=>{
    const focus=focusSnapshot.records.find(x=>x.ticker===candidate.ticker&&x.nct===candidate.nct);
    const stored=markets[candidate.programId];
    const signal=evaluateWtAlpacaTechnicalSignal(candidate,focus,stored?.data||null,clock);
    const observed=signal.status!=="UNAVAILABLE"&&stored?.data&&clock?
      sessionSnapshot(stored.data,new Date(clock)):null;
    return {candidate,focus,stored,signal,observed};
  }),[markets,clock]);

  return <main data-wt-status-sheet="read-only" style={{maxWidth:1500,margin:"0 auto",padding:"18px 16px 36px"}}>
    <nav aria-label="WT status navigation" style={{marginBottom:16}}>
      <a href="/wt">← Back to WT</a>
      <span style={{margin:"0 12px"}}>·</span>
      <a href="#SVRA">SVRA status</a>
      <span style={{margin:"0 12px"}}>·</span>
      <a href="#CAPR">CAPR status</a>
    </nav>
    <h1 style={{margin:"0 0 8px"}}>WT · Alpaca ticker status sheets</h1>
    <p style={{margin:"0 0 12px"}}>One independent metric sheet per ticker with Alpaca readings,
      explicit BUY thresholds, PASS/WAIT checks, data dates, and separate FDA timing safeguards.
      These eight-check technical signals are <strong>unbacktested research</strong>; they do not predict FDA approval.</p>
    <p style={{fontSize:13,margin:"0 0 16px"}}>
      <strong>Market source:</strong> Alpaca completed daily OHLCV (raw, IEX or SIP entitlement).
      <strong> FOCUS snapshot:</strong> {focusSnapshot.asOf}. <strong>Update interval:</strong> 5 minutes while this page is visible;
      a quote is not continuously streaming. <strong>Orders:</strong> disabled.
    </p>
    <div style={{display:"flex",alignItems:"center",gap:12,marginBottom:18,flexWrap:"wrap"}}>
      <button type="button" disabled={refreshing} onClick={()=>setRevision(n=>n+1)}>
        {refreshing?"Refreshing Alpaca…":"Refresh status sheets"}
      </button>
      {clock>0&&<small>Screen clock: {DATE_FMT.format(new Date(clock))} · No broker execution</small>}
    </div>

    <section aria-label="Ticker status overview" style={{overflowX:"auto",marginBottom:22}}>
      <h2 style={{fontSize:20,margin:"0 0 8px"}}>Status overview</h2>
      <table style={{width:"100%",borderCollapse:"collapse",minWidth:700,fontSize:13}}>
        <thead><tr style={{background:"#e9f1f0"}}>
          {["Ticker","Technical signal","Passed","Alpaca bar date","Recorded PDUFA","PDUFA entry rule","Order status"].map(x=>
            <th scope="col" key={x} style={CELL}>{x}</th>)}
        </tr></thead>
        <tbody>{rows.map(({candidate,signal,stored})=><tr key={candidate.programId}>
          <td style={CELL}><a href={"#"+candidate.ticker}><strong>{candidate.ticker}</strong></a></td>
          <td style={CELL}>{!stored?"LOADING":signalTitle(signal)}</td>
          <td style={CELL}>{!stored?"—":signal.status==="UNAVAILABLE"?"UNAVAILABLE":signal.passed+"/"+signal.total}</td>
          <td style={CELL}>{reportDate(signal.asOf)}</td>
          <td style={CELL}>{signal.pdufaDate||"NOT VERIFIED"}</td>
          <td style={CELL}>{pdufaGateText(signal)}</td>
          <td style={CELL}><strong>NO ORDERS</strong></td>
        </tr>)}</tbody>
      </table>
    </section>

    {rows.map(({candidate,focus,stored,signal,observed})=><section
      id={candidate.ticker} key={candidate.programId} aria-label={candidate.ticker+" full Alpaca metric status sheet"}
      style={{border:"1px solid #cbded8",background:"#fff",borderRadius:12,padding:16,margin:"20px 0",scrollMarginTop:20}}>
      <div style={{display:"flex",gap:14,alignItems:"flex-start",justifyContent:"space-between",flexWrap:"wrap"}}>
        <div>
          <h2 style={{fontSize:23,margin:"0 0 5px"}}>{candidate.ticker} · {candidate.drug}</h2>
          <small>Permanent ID: {candidate.programId} · Trial: {candidate.nct}</small>
        </div>
        <div aria-label={candidate.ticker+" technical summary"} style={{borderRadius:8,padding:"9px 12px",
          background:signal.status==="BUY_SETUP"?"#e7f4eb":signal.status==="WAIT"?"#fff5de":"#eef2f5"}}>
          <strong>{!stored?"LOADING ALPACA":signalTitle(signal)}</strong>
          <div style={{fontSize:12}}>{signal.status==="UNAVAILABLE"?"No qualifying verified readings":signal.passed+" of "+signal.total+" passed"}</div>
        </div>
      </div>
      <p style={{fontSize:13,margin:"11px 0"}}>
        <strong>Observed session:</strong> {reportDate(signal.asOf)} · <strong>Feed:</strong> {signal.feed||"UNAVAILABLE"}
        {signal.feed==="IEX"?" (single exchange, not consolidated market volume)":""}
        {" · "}<strong>Last fetched:</strong> {stored?.fetchedAt?DATE_FMT.format(new Date(stored.fetchedAt)):"PENDING"}
      </p>
      {stored?.error&&<p role="alert" style={{color:"#a22f25",fontSize:13}}>
        Source unavailable: {stored.error}. No values are estimated or fabricated.</p>}
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(155px,1fr))",gap:10,marginBottom:14}}>
        <div style={{padding:10,border:"1px solid #d8e4e4",borderRadius:8}}><small>Alpaca last close</small><div><strong>
          {observed?"$"+observed.close.toFixed(2):"UNAVAILABLE"}</strong></div></div>
        <div style={{padding:10,border:"1px solid #d8e4e4",borderRadius:8}}><small>SMA20 / SMA50</small><div><strong>
          {observed?"$"+observed.sma20.toFixed(2)+" / $"+observed.sma50.toFixed(2):"UNAVAILABLE"}</strong></div></div>
        <div style={{padding:10,border:"1px solid #d8e4e4",borderRadius:8}}><small>Entry reference / stop reference</small><div><strong>
          {money(signal.triggerReference)} / {money(signal.riskStopReference)}</strong></div></div>
        <div style={{padding:10,border:"1px solid #d8e4e4",borderRadius:8}}><small>FDA target / countdown</small><div><strong>
          {focus?.recordedPdufaDate||"UNVERIFIED"} · {signal.pdufaDays===null?"—":signal.pdufaDays+" days"}</strong></div></div>
      </div>
      <div style={{overflowX:"auto"}}>
        <table style={{width:"100%",borderCollapse:"collapse",minWidth:740,fontSize:13}}
          aria-label={candidate.ticker+" actual, threshold and status metrics"}>
          <thead><tr style={{background:"#e9f1f0"}}>
            <th scope="col" style={CELL}>#</th><th scope="col" style={CELL}>Alpaca metric</th>
            <th scope="col" style={CELL}>Actual reading</th><th scope="col" style={CELL}>BUY requirement</th>
            <th scope="col" style={CELL}>Status</th>
          </tr></thead>
          <tbody>{Array.from({length:8},(_,idx)=>{
            const check=signal.checks[idx];
            return <tr key={check?.key||idx}>
              <td style={CELL}>{idx+1}</td>
              <td style={CELL}>{check?.label||[
                "10-session base","Stabilizing lows","Confirmed close above trigger",
                "Positive moving-average trend","Relative volume (RVOL20)",
                "RSI14 momentum","20-day average dollar volume","ATR14 daily volatility",
              ][idx]}</td>
              <td style={CELL}><strong>{check?.measured||"UNAVAILABLE"}</strong></td>
              <td style={CELL}>{check?.required||"Not evaluable without verified Alpaca history"}</td>
              <td style={CELL}><strong style={{color:check?.passed?"#116b3b":check?"#875100":"#5b6570"}}>
                {!check?"UNAVAILABLE":check.passed?"PASS":"WAIT"}</strong></td>
            </tr>;
          })}</tbody>
        </table>
      </div>
      <div style={{borderTop:"1px solid #dce6e6",paddingTop:12,marginTop:14,fontSize:13}}>
        <p style={{margin:"0 0 7px"}}><strong>Overall technical signal:</strong> {signalTitle(signal)}.
          {" "}{signal.reason}</p>
        <p style={{margin:"0 0 7px"}}><strong>Separate FDA timing gate:</strong> {pdufaGateText(signal)}.</p>
        <p style={{margin:"0 0 7px"}}><strong>E*TRADE order status:</strong> NOT AUTHORIZED · NOT PREVIEWED · NOT SUBMITTED.</p>
        <p style={{margin:0}}><strong>Research limitations:</strong> Eight technical factors only.
          No verified anchored VWAP, XBI-relative strength, cash runway, SEC financing clearance, FDA approval prediction,
          or real-time broker bid/ask is inferred. A technical BUY setup cannot override the 14-day PDUFA hold.
          No E*TRADE orders are created here.</p>
      </div>
    </section>)}
    <p style={{fontSize:12}}>Each page visit reads the exact permanent Program ID and ticker from Alpaca.
      Missing, invalid or stale data is displayed as UNAVAILABLE rather than being scored zero or assumed to pass.
      <a href="/wt"> Return to WT.</a></p>
  </main>;
}
