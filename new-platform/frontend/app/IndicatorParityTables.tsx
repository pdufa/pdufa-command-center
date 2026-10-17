"use client";
import {useState} from "react";
type Factor={label:string;weight:number;earned:number|null;evidence:string};
type Tech={
 close?:number|null;sma20?:number|null;sma50?:number|null;rsi14?:number|null;rvol?:number|null;
 macd?:{macd:number|null;signal:number|null;bullish:boolean}|null;
 base?:{support:number|null;resistance:number|null;status:string;touches:number|null};
 entry?:number|null;entryCoverage?:number;exitRisk?:number|null;exitCoverage?:number;
 indicatorEntry?:number|null;indicatorEntryCoverage?:number;indicatorExitRisk?:number|null;indicatorExitCoverage?:number;
 entryFactors?:Factor[];exitFactors?:Factor[];indicatorEntryFactors?:Factor[];indicatorExitFactors?:Factor[];
 marketDate?:string;eodFresh?:boolean;
};
type Signals=Partial<Record<"ENTRY"|"EXIT",{signals?:Record<string,string>;updated?:string}>>;
const fmt=(n?:number|null,d=2)=>typeof n==="number"&&Number.isFinite(n)?n.toFixed(d):"NOT VERIFIED";
const indicators=["Volume / RVOL","Bollinger (20,2)","Phase 3 AVWAP","EMA (10/20/50)",
 "RSI (14)","MACD (12/26/9)","OBV","ATR (14)"];
export default function IndicatorParityTables({tech,signals,programId}:{tech?:Tech|null;signals?:Signals;programId:string}){
 const [mode,setMode]=useState<"ENTRY"|"EXIT"|"BOTH">("BOTH");
 const modes=mode==="BOTH"?["ENTRY","EXIT"]:[mode];
 const goals:[string,string,string][]=[
  ["Base formation / support and resistance","≥2 support touches; confirm base",tech?.base?fmt(tech.base.support)+" / "+fmt(tech.base.resistance)+" · "+tech.base.status:"NOT VERIFIED"],
  ["Volume and RVOL","≥1.5× breakout RVOL",fmt(tech?.rvol,2)+"×"],
  ["20D/50D SMA","Close above rising SMA20 and SMA50",fmt(tech?.sma20)+" / "+fmt(tech?.sma50)],
  ["ATR14 / risk sizing","Verified OHLC highs/lows required","SEE ALPACA CHART — NOT IN ORIGINAL GEM SCORE"],
  ["Reward to risk","≥2:1 using verified stop and target","NOT VERIFIED"],
  ["Anchored VWAP","Price above event-anchored VWAP","NOT VERIFIED"],
  ["Relative strength vs. XBI","Stable or increasing","NOT VERIFIED"],
  ["PDUFA catalyst marker","Verified PDUFA date and deadline","SEE EXACT PROGRAM DETAILS"],
  ["RSI14","45–65 provisional",fmt(tech?.rsi14,1)],
  ["MACD(12,26,9)","Bullish preferred",tech?.macd?fmt(tech.macd.macd,3)+" / "+fmt(tech.macd.signal,3):"NOT VERIFIED"]
 ];
 const entry=tech?.indicatorEntry??tech?.entry,exit=tech?.indicatorExitRisk??tech?.exitRisk;
 const coverageE=tech?.indicatorEntryCoverage??tech?.entryCoverage??0,coverageX=tech?.indicatorExitCoverage??tech?.exitCoverage??0;
 const factorsE=tech?.indicatorEntryFactors||tech?.entryFactors||[],factorsX=tech?.indicatorExitFactors||tech?.exitFactors||[];
 return <section className="indicator-tables-separate" aria-label={programId+" Streamlit reference indicator and score tables"}>
  <header><strong>INDICATOR &amp; ENTRY/EXIT TABLES · STREAMLIT REFERENCE</strong>
    <span className="permanent-id">{programId}</span></header>
  <p>These are <strong>tables, not stock-price charts</strong>. Goals match the reference picture; Actuals require verified data. Scores reuse GEM JR/GEM weights.</p>
  <div className="table-scroll"><table className="indicator-target-matrix">
   <thead><tr><th>#</th><th>Indicator</th><th>Gold goal / target</th><th>Actual observation</th><th>Status</th></tr></thead>
   <tbody>{goals.map(([name,goal,actual],i)=><tr key={name}>
    <td>{i+1}</td><td>{name}</td><td className="gold-goal">{goal}</td><td>{actual}</td>
    <td>{actual.includes("NOT VERIFIED")||actual.includes("SEE")?"REVIEW":"OBSERVED"}</td>
   </tr>)}</tbody></table></div>
  <div className="entryexit-table-grid">{([
    ["ENTRY STRENGTH /100",entry,coverageE,factorsE],
    ["EXIT RISK /100",exit,coverageX,factorsX]
   ] as [string,number|null|undefined,number,Factor[]][]).map(([title,score,coverage,factors])=><div key={title}>
     <h4>{title}</h4><p><strong>{score==null?"UNSCORED":score+"/100"}</strong> · Evidence coverage {coverage}/100</p>
     <table><thead><tr><th>Factor</th><th>Weight</th><th>Points</th><th>Evidence</th></tr></thead><tbody>
     {factors.length?factors.map(f=><tr key={f.label}><td>{f.label}</td><td>{f.weight}</td><td>{f.earned==null?"NOT VERIFIED":f.earned}</td><td>{f.evidence}</td></tr>):
      <tr><td colSpan={4}>No verified weighted factors available</td></tr>}</tbody></table>
   </div>)}</div>
  <section className="eight-indicators">
    <h4>STREAMLIT WATCHLIST — EIGHT INDICATORS</h4>
    <div className="indicator-modes">{(["ENTRY","EXIT","BOTH"] as const).map(v=>
     <button type="button" key={v} aria-pressed={mode===v} onClick={()=>setMode(v)}>{v}</button>)}</div>
    <div className="table-scroll"><table><thead><tr><th>Mode</th><th>Indicator</th><th>Signal</th><th>Updated</th></tr></thead>
      <tbody>{modes.flatMap(v=>indicators.map(name=><tr key={v+"|"+name}>
       <td>{v}</td><td>{name}</td><td>{signals?.[v as "ENTRY"|"EXIT"]?.signals?.[name]||"NOT SCANNED"}</td>
       <td>{signals?.[v as "ENTRY"|"EXIT"]?.updated||"NOT SCANNED"}</td></tr>))}</tbody>
    </table></div>
    <p>Unpublished Streamlit scanner signals are explicitly NOT SCANNED; Alpaca raw market bars do not validate them automatically.</p>
  </section>
 </section>;
}
