"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import AlpacaStockChart from "./AlpacaStockChart";

export type TradingTicker = {
  programId: string;
  ticker: string;
  drug?: string;
  kind: "watch" | "trade";
  pdufaDate?: string;
  financingStatus?: string;
  phase3Status?: string;
  outcome?: string;
  runwayMonths?: number | null;
  avgDollarVolume20?: number | null;
  riskAlerts?: string[];
};

type Stage = "entry" | "stay" | "exit";
type Indicator = { id: string; label: string; chartKeys?: readonly string[]; note: string };
type ChartSlot = {
  id: number;
  programId: string;
  stage: Stage;
  selected: Record<Stage, string[]>;
};
const STORAGE_KEY = "pdufa_trading_chart_layout_v1";
const MAX_CHARTS = 6;
const emptySelections = (): Record<Stage, string[]> => ({entry: [], stay: [], exit: []});
const blank = (id: number): ChartSlot => ({id, programId: "", stage: "entry", selected: emptySelections()});

// Ranked monitoring priorities, not validated trading signals. Only entries with
// chartKeys have a supported Alpaca plot. Never mislabel an ATR as a stop.
const INDICATORS: Record<Stage, readonly Indicator[]> = {
  entry: [
    {id:"structure",label:"Price structure / support",chartKeys:["entry-base","entry-breakout"],note:"Prior 10-session range is a proxy, not confirmed support"},
    {id:"vwap",label:"Anchored VWAP",note:"Event-anchored VWAP is not available in the current daily-bar feed"},
    {id:"rvol",label:"Relative volume (RVOL)",chartKeys:["entry-rvol"],note:"Chart shows raw daily volume, not full-market RVOL"},
    {id:"xbi",label:"Relative strength vs XBI",note:"Requires a separately verified XBI comparison series"},
    {id:"financing",label:"Financing / dilution risk",note:"Review SEC evidence separately"},
    {id:"clinical",label:"Clinical Phase 3 strength",note:"Review primary endpoint and source evidence"},
    {id:"cash",label:"Cash runway",note:"Use dated issuer filings; not a chart study"},
    {id:"momentum",label:"Momentum / RSI",chartKeys:["entry-rsi"],note:"RSI14 is a reading, not a validated buy signal"},
    {id:"liquidity",label:"Liquidity / bid-ask spread",note:"IEX bars do not verify a consolidated live spread"},
    {id:"pdufa",label:"PDUFA timing",note:"Use reported date with official source recheck"}
  ],
  stay: [
    {id:"atr",label:"ATR trailing-stop monitoring",chartKeys:["exit-atr-trail"],note:"ATR14 plotted only; no actual stop or fill is inferred"},
    {id:"structure",label:"Price structure / higher lows",chartKeys:["stay-support"],note:"Range proxy, not a validated higher-low detector"},
    {id:"vwap",label:"Anchored VWAP",note:"Event-anchored VWAP is not available in the current daily-bar feed"},
    {id:"volume",label:"Volume accumulation / distribution",chartKeys:["stay-volume"],note:"Raw IEX daily volume only"},
    {id:"xbi",label:"Relative strength vs XBI",note:"Requires separately verified XBI comparison data"},
    {id:"pdufa",label:"PDUFA countdown",note:"Reported date; verify against FDA source"},
    {id:"financing",label:"Financing / dilution developments",note:"Review current SEC filings"},
    {id:"clinical",label:"Clinical / FDA news",note:"Review source-verified event risk"},
    {id:"momentum",label:"Momentum / RSI",chartKeys:["stay-rsi"],note:"RSI14 reading only"},
    {id:"liquidity",label:"Liquidity / spread",note:"IEX coverage is incomplete"}
  ],
  exit: [
    {id:"atr",label:"Hard stop / ATR trailing stop",chartKeys:["exit-atr-trail"],note:"ATR14 only; no broker stop or executable exit signal"},
    {id:"pdufa",label:"PDUFA countdown",note:"Planned exit deadline must be verified"},
    {id:"structure",label:"Price structure breakdown",chartKeys:["exit-support"],note:"Prior 10-session range proxy only"},
    {id:"distribution",label:"Volume distribution",chartKeys:["exit-divergence"],note:"Raw volume; no validated distribution classifier"},
    {id:"clinical",label:"Adverse clinical / FDA news",note:"Can override technical trends after verification"},
    {id:"financing",label:"Financing / dilution event",note:"Material SEC announcement requires separate review"},
    {id:"xbi",label:"Relative strength vs XBI",note:"Unavailable without verified comparison history"},
    {id:"vwap",label:"Anchored VWAP breakdown",note:"Event-anchored VWAP not yet available"},
    {id:"momentum",label:"Momentum deterioration",chartKeys:["exit-rsi"],note:"RSI14 only; a reversal rule is not validated"},
    {id:"liquidity",label:"Liquidity deterioration",note:"Requires spread/depth coverage warning"}
  ]
};
function daysTo(raw?:string): number|null {
  if (!raw || !/^\d{4}-\d{2}-\d{2}/.test(raw)) return null;
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone:"America/Los_Angeles", year:"numeric", month:"2-digit", day:"2-digit"
  }).formatToParts(new Date());
  const p=Object.fromEntries(parts.map(x=>[x.type,x.value]));
  const a=Date.parse(raw.slice(0,10)+"T00:00:00Z");
  const b=Date.parse(p.year+"-"+p.month+"-"+p.day+"T00:00:00Z");
  return Number.isFinite(a)&&Number.isFinite(b)?Math.round((a-b)/86400000):null;
}
function validStored(value: unknown): ChartSlot[] {
  if(!Array.isArray(value)) return [];
  const result:ChartSlot[]=[];
  for(const item of value.slice(0,MAX_CHARTS)){
    if(!item||typeof item!=="object")continue;
    const v=item as Partial<ChartSlot>;
    if(!Number.isSafeInteger(v.id)||Number(v.id)<1||result.some(x=>x.id===v.id))continue;
    const stage:Stage=v.stage==="stay"||v.stage==="exit"?v.stage:"entry";
    const selected=emptySelections();
    for(const s of ["entry","stay","exit"] as const){
      const allowed=new Set(INDICATORS[s].map(x=>x.id));
      const keys=v.selected?.[s];
      selected[s]=Array.isArray(keys)?[...new Set(keys.filter((x):x is string=>typeof x==="string"&&allowed.has(x)))]:[];
    }
    result.push({id:v.id!,programId:typeof v.programId==="string"&&/^PDUFA-\d{6,}$/.test(v.programId)?v.programId:"",stage,selected});
  }
  return result;
}

export default function TradingDashboard({tickers, tagsReady}: {tickers: readonly TradingTicker[]; tagsReady:boolean}) {
  const [charts,setCharts]=useState<ChartSlot[]>([blank(1)]);
  const [restored,setRestored]=useState(false);
  const nextId=useRef(2);
  useEffect(()=>{
    try {
      const saved=validStored(JSON.parse(localStorage.getItem(STORAGE_KEY)||"null"));
      if(saved.length){setCharts(saved);nextId.current=Math.max(...saved.map(x=>x.id))+1;}
    }catch{/* Browser storage is optional. */}
    setRestored(true);
  },[]);
  useEffect(()=>{
    if(!restored)return;
    try{localStorage.setItem(STORAGE_KEY,JSON.stringify(charts));}
    catch{/* Keep the current tab state if local storage is disabled. */}
  },[charts,restored]);

  const options=useMemo(()=>[...tickers]
    .filter(x=>x.ticker&&/^PDUFA-\d{6,}$/.test(x.programId))
    .sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.programId.localeCompare(b.programId)),
    [tickers]);
  const byId=useMemo(()=>new Map(options.map(x=>[x.programId,x])),[options]);
  const update=(id:number,patch:(old:ChartSlot)=>ChartSlot)=>
    setCharts(old=>old.map(x=>x.id===id?patch(x):x));
  function addChart(afterId?:number) {
    setCharts(old=>{
      if(old.length>=MAX_CHARTS)return old;
      const slot=blank(nextId.current++);
      const position=afterId==null?old.length:old.findIndex(x=>x.id===afterId)+1;
      const next=[...old];next.splice(position<0?old.length:position,0,slot);return next;
    });
  }
  function removeChart(id:number) {
    setCharts(old=>old.length===1?[blank(nextId.current++)]:old.filter(x=>x.id!==id));
  }
  return <section className="trading-page" aria-label="TRADING multi-chart workspace">
    <div className="sectionhead">
      <div><h2>TRADING — Multi-chart decision cockpit</h2>
        <p className="subtle">W/T programs only · ENTRY / STAY / EXIT Top 10 research · no broker orders</p></div>
      <span className="counter">{charts.length} chart{charts.length===1?"":"s"} · {options.length} W/T programs</span>
    </div>
    <div className="trading-critical-banner" role="note">
      <strong>Downside risk always visible.</strong> Source-reported FDA, financing, cash, liquidity and PDUFA
      information can be stale or incomplete. Missing evidence is never a green light.
      Alpaca IEX pricing/volume is not consolidated; chart checkboxes do not generate validated buy/sell orders.
    </div>
    <div className="trading-chart-grid">
      {charts.map((chart,index)=>{
        const record=byId.get(chart.programId);
        const list=INDICATORS[chart.stage];
        const selected=chart.selected[chart.stage];
        const chartKeys=[...new Set(list.filter(x=>selected.includes(x.id)).flatMap(x=>x.chartKeys||[]))];
        const days=daysTo(record?.pdufaDate);
        const alerts=record?.riskAlerts?.filter(Boolean)||[];
        return <article key={chart.id} className="trading-chart-card">
          <header className="trading-chart-header">
            <div><strong>CHART {index+1}</strong><small>{record?(record.kind==="watch"?"WATCH":"TRADE")+" · "+record.programId:"No ticker selected"}</small></div>
            <div className="trading-chart-actions">
              <button type="button" className="secondary" disabled={charts.length>=MAX_CHARTS}
                onClick={()=>addChart(chart.id)} aria-label={"Add chart after chart "+(index+1)}>+ ADD CHART</button>
              <button type="button" className="secondary" onClick={()=>removeChart(chart.id)}
                aria-label={"Delete chart "+(index+1)}>DELETE CHART</button>
            </div>
          </header>
          <div className="trading-chart-options">
            <label htmlFor={"trading-ticker-"+chart.id}>W/T ticker
              <select id={"trading-ticker-"+chart.id} value={record?.programId||""}
                disabled={!tagsReady} onChange={e=>update(chart.id,old=>({
                  ...old,programId:e.target.value,stage:"entry",selected:emptySelections()
                }))}>
                <option value="">— SELECT A W/T TICKER —</option>
                <optgroup label="WATCH (W)">
                  {options.filter(x=>x.kind==="watch").map(x=>
                    <option key={x.programId} value={x.programId}>{x.ticker} · {x.drug||"Drug unrecorded"} · {x.programId}</option>)}
                </optgroup>
                <optgroup label="TRADING (T)">
                  {options.filter(x=>x.kind==="trade").map(x=>
                    <option key={x.programId} value={x.programId}>{x.ticker} · {x.drug||"Drug unrecorded"} · {x.programId}</option>)}
                </optgroup>
              </select>
            </label>
            {record&&<div className="trading-active-title"><strong>{record.ticker}</strong><span>{record.drug||"Drug not recorded"}</span></div>}
          </div>
          {chart.programId&&!record&&<p className="risk-line">This program is no longer in the current W/T selection. Choose another ticker; the removed program was not substituted.</p>}
          <div className="trading-stage-tabs" role="group" aria-label={"Chart "+(index+1)+" monitoring stage"}>
            {(["entry","stay","exit"] as const).map(stage=>
              <button type="button" key={stage} className={chart.stage===stage?"trading-stage-active "+stage:""}
                aria-pressed={chart.stage===stage}
                onClick={()=>update(chart.id,old=>({...old,stage}))}>{stage.toUpperCase()}</button>)}
          </div>
          <details className="trading-indicator-controls">
            <summary>TOP 10 {chart.stage.toUpperCase()} indicators · {selected.length}/10 selected</summary>
            <p className="subtle small">None selected by default. Only supported Alpaca studies are plotted; other indicators are risk/research readings, not invented chart lines.</p>
            <div className="trading-indicator-list">
              {list.map((indicator,i)=><label key={indicator.id} title={indicator.note}>
                <input type="checkbox" checked={selected.includes(indicator.id)}
                  onChange={e=>update(chart.id,old=>{
                    const current=old.selected[old.stage];
                    const next=e.target.checked?[...current,indicator.id]:current.filter(x=>x!==indicator.id);
                    return {...old,selected:{...old.selected,[old.stage]:next}};
                  })}/>
                <span><b>{i+1}. {indicator.label}</b><small>{indicator.note}</small></span>
                <em>{indicator.chartKeys?"CHART":"RESEARCH"}</em>
              </label>)}
            </div>
            <button type="button" className="secondary" onClick={()=>update(chart.id,old=>({
              ...old,selected:{...old.selected,[old.stage]:[]}
            }))}>CLEAR {chart.stage.toUpperCase()} INDICATORS</button>
          </details>
          {record?<div className="trading-price-area">
            <AlpacaStockChart key={record.programId} ticker={record.ticker} programId={record.programId} wtIndicatorKeys={chartKeys}/>
          </div>:<div className="trading-empty-chart">
            <strong>{tagsReady&&options.length===0?"No W/T tickers currently tagged":"Choose a ticker to display its chart"}</strong>
            <span>{tagsReady?"Select an exact W/T program above to load its Alpaca chart.":"Loading W/T program choices…"}</span>
          </div>}
          <div className="trading-risk-panel" aria-label={"Chart "+(index+1)+" permanent downside risk monitor"}>
            <h3>Downside risk monitor — always visible</h3>
            <div className="trading-risk-grid">
              <div><small>FINANCING / DILUTION</small><strong>{record?.financingStatus||"UNVERIFIED"}</strong></div>
              <div><small>CLINICAL / FDA</small><strong>{record?.outcome||record?.phase3Status||"UNVERIFIED"}</strong></div>
              <div><small>CASH RUNWAY</small><strong>{typeof record?.runwayMonths==="number"?record.runwayMonths+" months":"UNVERIFIED"}</strong></div>
              <div><small>LIQUIDITY (20D $ VOL)</small><strong>{typeof record?.avgDollarVolume20==="number"?"$"+Math.round(record.avgDollarVolume20).toLocaleString("en-US"):"UNVERIFIED"}</strong></div>
              <div><small>REPORTED PDUFA</small><strong>{record?.pdufaDate||"UNVERIFIED"}{days!==null?" · T"+(days<0?"+":"−")+Math.abs(days):""}</strong></div>
              <div><small>POSITION / HARD STOP</small><strong>NOT CONNECTED</strong></div>
            </div>
            {alerts.length>0&&<ul className="trading-alerts">{alerts.map((a,i)=><li key={i}>{a}</li>)}</ul>}
            <small>Not a live position ledger; verify source dates and any alerts before trading. No validated ENTRY/STAY/EXIT call is calculated here.</small>
          </div>
          <div className="trading-chart-footer">
            <button type="button" disabled={charts.length>=MAX_CHARTS} onClick={()=>addChart(chart.id)}>+ ADD ANOTHER CHART</button>
            <button type="button" className="secondary" onClick={()=>removeChart(chart.id)}>DELETE CHART</button>
          </div>
        </article>;
      })}
    </div>
    <div className="trading-bottom-add"><button type="button" disabled={charts.length>=MAX_CHARTS}
      onClick={()=>addChart()}>+ ADD TICKER CHART BELOW ({charts.length}/{MAX_CHARTS})</button></div>
  </section>;
}
