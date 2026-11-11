"use client";

import {useCallback,useEffect,useState} from "react";
import AlpacaStockChart from "./AlpacaStockChart";
import WtAlpacaBuySignal from "./WtAlpacaBuySignal";
import {evaluateWtAlpacaTechnicalSignal} from "../lib/wt-alpaca-buy-signal";
import WtEtradeSandboxConnect from "./WtEtradeSandboxConnect";
import focusSnapshot from "../data/p3PostDataActive.json";
import {sessionSnapshot,type WtMarket} from "../lib/wt-entry-stay-exit";
import {
  WT_ETRADE_CANDIDATES,prepareWtEtradeDraft,formatWtEtradeDraft,
  type WtAlpacaEntry,
} from "../lib/wt-etrade-order-draft";

type Feed={value:WtAlpacaEntry|null;error:string;receivedAt:number};
type Feeds=Record<string,Feed>;
type MarketFeed={value:WtMarket|null;error:string};
type Markets=Record<string,MarketFeed>;
const css={
  panel:{border:"1px solid #a5c8bc",borderRadius:12,padding:16,margin:"16px 0",background:"#f6fbf9"},
  card:{border:"1px solid #c4d4da",borderRadius:10,padding:14,background:"#fff",minWidth:0} as const,
  data:{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(145px,1fr))",gap:8,margin:"10px 0"} as const,
  chip:{border:"1px solid #c9dae0",borderRadius:7,padding:"8px 10px",fontSize:13} as const,
};

export default function WtEtradeOrderPrep(){
  const [feeds,setFeeds]=useState<Feeds>({});
  const [markets,setMarkets]=useState<Markets>({});
  const [now,setNow]=useState(0);
  const [expanded,setExpanded]=useState<Record<string,boolean>>({});
  const [copyStatus,setCopyStatus]=useState("");
  useEffect(()=>{
    const controller=new AbortController();
    let busy=false;
    const refresh=async()=>{
      if(busy||document.visibilityState==="hidden")return;
      busy=true;
      try{
        await Promise.all(WT_ETRADE_CANDIDATES.map(async candidate=>{
          let value:WtAlpacaEntry|null=null,error="";
          try{
            const response=await fetch("/api/entry-signal/"+encodeURIComponent(candidate.programId),{
              cache:"no-store",signal:controller.signal,
            });
            if(!response.ok)throw new Error("Alpaca entry feed HTTP "+response.status);
            value=await response.json() as WtAlpacaEntry;
          }catch(e){
            if(controller.signal.aborted)return;
            error=e instanceof Error?e.message:"Entry research unavailable";
          }
          if(!controller.signal.aborted)setFeeds(previous=>({
            ...previous,[candidate.programId]:{value,error,receivedAt:Date.now()}
          }));
        }));
      }finally{busy=false;}
    };
    let marketBusy=false;
    const refreshMarket=async()=>{
      if(marketBusy||document.visibilityState==="hidden")return;
      marketBusy=true;
      try{
        await Promise.all(WT_ETRADE_CANDIDATES.map(async candidate=>{
          let value:WtMarket|null=null,error="";
          try{
            const response=await fetch("/api/alpaca-chart/"+encodeURIComponent(candidate.programId)+"?range=6M",{
              cache:"no-store",signal:controller.signal,
            });
            if(!response.ok)throw new Error("Alpaca chart feed HTTP "+response.status);
            const received=await response.json() as WtMarket;
            if(received.programId!==candidate.programId||received.ticker!==candidate.ticker||received.provider!=="ALPACA")
              throw new Error("Alpaca chart source or exact Program ID mismatch");
            value=received;
          }catch(e){
            if(controller.signal.aborted)return;
            error=e instanceof Error?e.message:"Alpaca chart unavailable";
          }
          if(!controller.signal.aborted)setMarkets(old=>({...old,[candidate.programId]:{value,error}}));
        }));
      }finally{marketBusy=false;}
    };
    const tick=()=>setNow(Date.now());
    tick();void refresh();void refreshMarket();
    const poll=setInterval(()=>void refresh(),30000);
    const clock=setInterval(tick,10000);
    const marketPoll=setInterval(()=>void refreshMarket(),300000);
    document.addEventListener("visibilitychange",refresh);
    document.addEventListener("visibilitychange",refreshMarket);
    document.addEventListener("visibilitychange",tick);
    return()=>{
      controller.abort();clearInterval(poll);clearInterval(clock);clearInterval(marketPoll);
      document.removeEventListener("visibilitychange",refresh);
      document.removeEventListener("visibilitychange",refreshMarket);
      document.removeEventListener("visibilitychange",tick);
    };
  },[]);

  const copy=useCallback(async (text:string,ticker:string)=>{
    try{
      await navigator.clipboard.writeText(text);
      setCopyStatus(ticker+" draft copied for review. Nothing was sent to E*TRADE.");
    }catch{setCopyStatus("Copy unavailable. Review the order fields on this page; no order was submitted.");}
  },[]);

  return <section aria-label="SVRA and CAPR E*TRADE order preparation" data-wt-etrade-prep="read-only"
    style={css.panel}>
    <h2 style={{marginTop:0}}>SVRA + CAPR · Alpaca analysis → E*TRADE limit-order drafts</h2>
    <p><strong>Two proposed purchases: one whole share each.</strong> Alpaca provides on-demand market research.
      E*TRADE live brokerage trading is not connected; a separate sandbox authorization option is below.
      No broker-side live account verification or order preview has happened. <strong>No order can be placed or approved through this page.</strong></p>
    <p style={{fontSize:13}}>Alpaca now calculates a separate eight-check, completed-session technical BUY setup or WAIT for each stock. It is unbacktested and non-executable; a technical BUY does not override the 14-day PDUFA blackout. The original strict FDA/financing/quote entry gate remains separate.</p>
    <p style={{fontSize:13}}>Drafts are prefilled with ticker, BUY action, quantity 1, LIMIT and regular-session
      day validity. A limit price is suggested only when an exact-program Alpaca entry signal passes all
      price, freshness and PDUFA safety gates. Current FOCUS source snapshot: {focusSnapshot.asOf}.
      The chart and entry checks are research, not investment advice or evidence of an E*TRADE executable quote.</p>
    <WtEtradeSandboxConnect />
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,350px),1fr))",gap:14}}>
      {WT_ETRADE_CANDIDATES.map(candidate=>{
        const source=focusSnapshot.records.find(x=>x.nct===candidate.nct&&x.ticker===candidate.ticker);
        const feed=feeds[candidate.programId];
        const market=markets[candidate.programId];
        const technical=now>0&&market?.value?sessionSnapshot(market.value,new Date(now)):null;
        const draft=prepareWtEtradeDraft(candidate,source,feed?.value||null,now);
        const technicalSignal=evaluateWtAlpacaTechnicalSignal(candidate,source,market?.value||null,now);
        return <article key={candidate.programId} style={css.card} aria-label={candidate.ticker+" proposed limit order"}>
          <h3 style={{margin:"0 0 7px"}}>{candidate.ticker} · {candidate.drug}</h3>
          <p style={{fontSize:12,margin:"0 0 12px"}}>
            <a href={"https://clinicaltrials.gov/study/"+candidate.nct} target="_blank" rel="noopener noreferrer">{candidate.nct}</a>
            {" · "}{candidate.programId} · PDUFA (recorded): {source?.recordedPdufaDate||"NOT VERIFIED"}
          </p>
          <WtAlpacaBuySignal signal={technicalSignal}/>
          <div style={css.data}>
            <div style={css.chip}><small>Broker / action</small><div><strong>E*TRADE · BUY</strong></div></div>
            <div style={css.chip}><small>Shares / order</small><div><strong>1 · LIMIT / DAY</strong></div></div>
            <div style={css.chip}><small>Suggested limit</small><div><strong>
              {draft.limitPrice===null?"NOT SET":"$"+draft.limitPrice.toFixed(2)}
            </strong></div></div>
            <div style={css.chip}><small>Broker approval</small><div><strong>NOT GIVEN</strong></div></div>
          </div>
          <div style={css.data} aria-label={candidate.ticker+" Alpaca technical observations"}>
            <div style={css.chip}><small>Alpaca last close</small><div><strong>{technical?"$"+technical.close.toFixed(2):"NOT VERIFIED"}</strong></div></div>
            <div style={css.chip}><small>20 / 50-day averages</small><div><strong>{technical?"$"+technical.sma20.toFixed(2)+" / $"+technical.sma50.toFixed(2):"UNAVAILABLE"}</strong></div></div>
            <div style={css.chip}><small>RSI14 / ATR14</small><div><strong>{technical?technical.rsi14.toFixed(1)+" / $"+technical.atr14.toFixed(2):"UNAVAILABLE"}</strong></div></div>
            <div style={css.chip}><small>RVOL20</small><div><strong>{technical?technical.rvol20.toFixed(2)+"×":"UNAVAILABLE"}</strong></div></div>
          </div>
          <p style={{fontSize:12}}>Alpaca completed-session data: {technical?technical.asOf+" · "+technical.coverage:
            (market?.error||market?.value?.message||"Checking bars / insufficient recent sessions")}.
            These EOD observations are <strong>not</strong> a verified E*TRADE order price.</p>
          <p role="status"><strong>{now===0?"CHECKING SOURCES":draft.status.replaceAll("_"," ")}</strong>
            {" — "}{now===0?"Awaiting browser market clock.":draft.reason}</p>
          <p style={{fontSize:12}}>Strict FDA/financing/quote entry gate (separate from EOD technical screening): <strong>{feed?.value?.status||"NOT AVAILABLE"}</strong>
            {feed?.error?" · "+feed.error:""}
            {feed?.value?.quote?" · "+feed.value.quote.feed+" quote":" · no fresh broker-executable price"}
          </p>
          <button type="button" onClick={()=>void copy(formatWtEtradeDraft(draft,source?.recordedPdufaDate),candidate.ticker)}>
            Copy draft details for review
          </button>{" "}
          <button type="button" onClick={()=>setExpanded(v=>({...v,[candidate.ticker]:!v[candidate.ticker]}))}>
            {expanded[candidate.ticker]?"Hide Alpaca chart":"Show Alpaca chart"}
          </button>
          {expanded[candidate.ticker]&&<div style={{marginTop:12}}>
            <AlpacaStockChart ticker={candidate.ticker} programId={candidate.programId}/>
          </div>}
        </article>;
      })}
    </div>
    {copyStatus&&<p role="status">{copyStatus}</p>}
    <p style={{fontSize:12,marginBottom:0}}>Execution safeguard: no E*TRADE order API, account token, broker preview ID,
      approval endpoint, scheduled order or live-order submission is wired to this feature.
      Production E*TRADE OAuth, independent fresh broker-side preview and separate explicit order approval
      would be required for any future live broker integration.
      The existing entry model does not permit new buys inside 14 days of the recorded FDA target.</p>
  </section>;
}
