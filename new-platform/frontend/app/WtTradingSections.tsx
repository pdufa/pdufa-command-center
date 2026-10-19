"use client";
import {useEffect,useMemo,useRef,useState} from "react";
import type {Candidate} from "./Workspace";
import {
 WT_GROUPS,WT_CHECK_KEYS,sessionSnapshot,pdufaDays,numeric,dollars,
 type WtMarket,type WtObservation
} from "../lib/wt-entry-stay-exit";

import {chartDescriptionForWtCheck} from "../lib/wt-chart-indicator-map";

type GroupId="entry"|"stay"|"exit";
type EntryReply={
 programId:string;ticker:string;provider?:string;status:string;calculatedAt?:string;
 entryTrigger?:number;maximumEntry?:number;initialStop?:number;green?:boolean;
};
const emptyOpen:Record<GroupId,boolean>={entry:false,stay:false,exit:false};
const verified=(text:string,source:WtObservation["source"]):WtObservation=>({text,source});
const UNAVAILABLE=verified("NOT VERIFIED","UNAVAILABLE");
const good=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const pct=(v:number)=>numeric(v,2)+"%";

export default function WtTradingSections({
 programId,ticker,record,tech,autoFetch=false,checkedKeys,onCheckedKeysChange,activeGroup,compact=false
}:{
 programId:string;ticker:string;record?:Candidate;tech?:Candidate["technical"]|null;autoFetch?:boolean;
 checkedKeys?:readonly string[];onCheckedKeysChange?:(keys:string[])=>void;
 activeGroup?:GroupId;compact?:boolean;
}){
 const [expanded,setExpanded]=useState<Record<GroupId,boolean>>(emptyOpen);
 const [localChecked,setLocalChecked]=useState<string[]>([]);
 const checked=checkedKeys??localChecked;
 function updateChecked(keys:string[]){
  if(checkedKeys!==undefined)onCheckedKeysChange?.(keys);
  else setLocalChecked(keys);
 }
 const [market,setMarket]=useState<WtMarket|null>(null);
 const [entry,setEntry]=useState<EntryReply|null>(null);
 const [loaded,setLoaded]=useState(false);
 const [loading,setLoading]=useState(false);
 const [marketError,setMarketError]=useState("");
 const [entryError,setEntryError]=useState("");
 const request=useRef<AbortController|null>(null);
 const pending=useRef(false);
 useEffect(()=>()=>request.current?.abort(),[programId,ticker]);
 // Program changes remount this component with every checkbox unchecked.
 // Defer until after StrictMode effect cleanup so preview/production agree.
 useEffect(()=>{
  if(!autoFetch||!programId||!ticker)return;
  const handle=setTimeout(()=>void load(),50);
  return()=>clearTimeout(handle);
 },[autoFetch,programId,ticker]);

 async function load(){
  if(pending.current||!/^PDUFA-\d{6,}$/.test(programId)||!/^[A-Z][A-Z0-9.-]{0,12}$/.test(ticker))return;
  request.current?.abort();
  const ctrl=new AbortController();
  request.current=ctrl;
  pending.current=true;
  setLoading(true);setMarketError("");setEntryError("");
  try{
   const [bars,signal]=await Promise.allSettled([
    fetch("/api/alpaca-chart/"+encodeURIComponent(programId)+"?range=1Y",
      {cache:"no-store",signal:ctrl.signal}).then(async r=>{
       if(!r.ok)throw Error("Alpaca chart HTTP "+r.status);
       return await r.json() as WtMarket;
      }),
    fetch("/api/entry-signal/"+encodeURIComponent(programId),
      {cache:"no-store",signal:ctrl.signal}).then(async r=>{
       if(!r.ok)throw Error("Entry research HTTP "+r.status);
       return await r.json() as EntryReply;
      })
   ]);
   if(ctrl.signal.aborted)return;
   if(bars.status==="fulfilled" && bars.value.provider==="ALPACA" &&
      bars.value.programId===programId && bars.value.ticker===ticker){
    setMarket(bars.value);
    if(bars.value.status!=="OK")setMarketError(bars.value.message||bars.value.status);
   }else{
    setMarket(null);
    setMarketError("Alpaca bars unavailable for this exact Program ID.");
   }
   if(signal.status==="fulfilled" && signal.value.programId===programId && signal.value.ticker===ticker){
    setEntry(signal.value);
   }else{
    setEntry(null);
    setEntryError("Entry API did not return verified data for this exact Program ID.");
   }
  }finally{
   if(!ctrl.signal.aborted){setLoaded(true);setLoading(false);}
   pending.current=false;
  }
 }
 function toggle(group:GroupId){
  setExpanded(old=>({...old,[group]:!old[group]}));
  if(!loaded && !pending.current)void load();
 }
 const values=useMemo(()=>{
  const m=sessionSnapshot(market),asOf=m?.asOf??"NO FRESH SESSION";
  const obs=(v:string)=>verified(v+" · "+asOf,"ALPACA DAILY");
  const research=(v?:string|null)=>v&&v.trim()?verified(v,"SAVED RESEARCH"):UNAVAILABLE;
  const initial=good(entry?.initialStop)?entry!.initialStop:undefined;
  const trigger=good(entry?.entryTrigger)?entry!.entryTrigger:undefined;
  const maximum=good(entry?.maximumEntry)?entry!.maximumEntry:undefined;
  const snapEntry=good(tech?.indicatorEntry)?tech.indicatorEntry:tech?.entry;
  const snapExit=good(tech?.indicatorExitRisk)?tech.indicatorExitRisk:tech?.exitRisk;
  const days=pdufaDays(record?.pdufaDate);
  const pdufa=days==null?UNAVAILABLE:verified(record?.pdufaDate+" · "+days+" calendar days (REPORTED; source recheck required)","PROGRAM RECORD");
  const value:Record<string,WtObservation>={
   "entry-score":verified((good(snapEntry)?numeric(snapEntry,0)+"/100":"UNSCORED")+
     " · Entry API "+(entry?.status||"UNAVAILABLE")+" (research only)","SAVED RESEARCH"),
   "entry-base":m?obs("10-session base "+dollars(m.baseLow)+"–"+dollars(m.baseHigh)):UNAVAILABLE,
   "entry-breakout":m?obs(dollars(m.close)+" close vs prior high "+dollars(m.baseHigh)+" · "+(m.breakout?"ABOVE":"NOT ABOVE")):UNAVAILABLE,
   "entry-trend":m?obs("Close "+dollars(m.close)+" · SMA20 "+dollars(m.sma20)+" · SMA50 "+dollars(m.sma50)):UNAVAILABLE,
   "entry-rvol":m?obs(numeric(m.rvol20)+"×"+(m.feed==="IEX"?" (IEX partial volume)":" (SIP)")):UNAVAILABLE,
   "entry-rsi":m?obs(numeric(m.rsi14,1)):UNAVAILABLE,
   "entry-dollar":m?obs("$"+Math.round(m.avgDollarVolume20).toLocaleString("en-US")+"/day"+(m.feed==="IEX"?" (IEX only)":"")):UNAVAILABLE,
   "entry-atr":m?obs(dollars(m.atr14)):UNAVAILABLE,
   "entry-trigger":trigger!=null&&maximum!=null?verified("Trigger "+dollars(trigger)+" · Max "+dollars(maximum)+" · API snapshot","SAVED RESEARCH"):UNAVAILABLE,
   "entry-stop":initial!=null?verified("Initial reference "+dollars(initial)+" · not a broker stop"+(trigger&&trigger>initial?" · trigger-to-stop "+pct((trigger-initial)/trigger*100):""),"SAVED RESEARCH"):UNAVAILABLE,
   "stay-trend":m?obs("Close "+dollars(m.close)+" / 20d "+dollars(m.sma20)+" / 50d "+dollars(m.sma50)):UNAVAILABLE,
   "stay-support":m?obs("Close "+dollars(m.close)+" vs prior base low "+dollars(m.baseLow)+" · "+(m.supportHold?"ABOVE":"BELOW")):UNAVAILABLE,
   "stay-rsi":m?obs(numeric(m.rsi14,1)):UNAVAILABLE,
   "stay-volume":m?obs(numeric(m.rvol20)+"× vs 20 prior sessions"+(m.feed==="IEX"?" · IEX ONLY":"")):UNAVAILABLE,
   "stay-trailing":verified("NOT VERIFIED — entry fills and trailing-stop ledger unavailable","UNAVAILABLE"),
   "stay-pdufa":pdufa,
   "stay-signal":verified("NOT VERIFIED — no live position / tested HOLD rule","UNAVAILABLE"),
   "exit-score":research((good(snapExit)?numeric(snapExit,0)+"/100 · ":"UNSCORED · ")+(tech?.exitStatus||"No source-verified exit score")),
   "exit-two-close":m?obs(m.twoClosesBelowSma20?"YES — two closes below SMA20":"NO — two-close condition absent"):UNAVAILABLE,
   "exit-support":m?obs("Close "+dollars(m.close)+" vs base low "+dollars(m.baseLow)+" · "+(m.supportHold?"NO observed break":"BELOW base low")):UNAVAILABLE,
   "exit-atr-trail":m?verified("ATR14 "+dollars(m.atr14)+" · TRAIL NOT VERIFIED (no dated entry)","ALPACA DAILY"):UNAVAILABLE,
   "exit-rsi":m?obs("RSI14 "+numeric(m.rsi14,1)+" · exhaustion rule unvalidated"):UNAVAILABLE,
   "exit-plateau":verified("NOT VERIFIED — plateau model not backtested","UNAVAILABLE"),
   "exit-divergence":m?obs("Daily close change "+pct(m.changePct)+" · RVOL "+numeric(m.rvol20)+"×; divergence UNVALIDATED"):UNAVAILABLE,
   "exit-pdufa":days==null?UNAVAILABLE:verified("Reported "+record?.pdufaDate+" · provisional T−3: "+(days-3)+" days away; NOT VERIFIED","PROGRAM RECORD"),
   "exit-action":research([record?.outcome?"Reported outcome: "+record.outcome:"",
     ...(tech?.riskAlerts||[]).slice(0,3)].filter(Boolean).join(" · ")||"FDA action and dilution evidence not confirmed"),
  };
  return value;
 },[market,entry,record,tech]);
 const selectedCount=checked.length;
 const shownGroups=activeGroup?WT_GROUPS.filter(group=>group.id===activeGroup):WT_GROUPS;
 return <section className={"wt-trading-sections"+(compact?" wt-trading-compact":"")}
   aria-label={programId+" WT Entry Stay Exit research checkboxes"}>
  {!compact&&<div className="wt-trading-intro">
   <strong>WT — ENTRY / STAY / EXIT INDICATORS</strong>
   <small>{programId||"NO PROGRAM SELECTED"} · {ticker||"SELECT TICKER FOR DATA"} · {selectedCount} of {WT_CHECK_KEYS.length} selected · all off initially</small>
  </div>}
  {!compact&&<p className="subtle small">Select checkboxes to display supported indicators on this program's chart. Other checks remain data-only. Checking a box
    does not change GEM qualification, scan criteria, WT status or place orders.
    Alpaca daily prices load when a section is opened. Missing data is not estimated.</p>}
  {compact&&<p className="subtle small">Choose any of the indicators below for this trial only. Checked chart-compatible options appear on its Alpaca chart; research-only checks do not create overlays or submit orders.</p>}
  {programId&&!compact&&<p className="subtle small"><a href={"#wt-chart-"+programId}>View linked chart for {ticker||programId} ↓</a> · Only this exact program chart follows these checkboxes.</p>}
  {shownGroups.map(group=><div className="wt-check-group" key={group.id}>
    {compact?<div className="wt-check-group-title wt-checklist-visible-heading">
      <strong>{group.title} — SELECT INDICATORS</strong>
      <small>{group.items.filter(i=>checked.includes(i.key)).length}/{group.items.length} selected</small>
    </div>:<button type="button" className="wt-check-group-title"
      aria-expanded={expanded[group.id]} aria-controls={"wt-"+group.id+"-"+programId}
      onClick={()=>toggle(group.id)}>
      <span aria-hidden="true">{expanded[group.id]?"▾":"▸"}</span>
      <strong>{group.title}</strong>
      <small>{group.items.filter(i=>checked.includes(i.key)).length}/{group.items.length} selected</small>
    </button>}
    {(compact||expanded[group.id])&&<div className="wt-check-group-body" id={"wt-"+group.id+"-"+programId}>
      <div className="wt-check-grid">
       {group.items.map(item=>{
        const observation=values[item.key]||UNAVAILABLE;
        return <label key={item.key} className={"wt-check-item"+(checked.includes(item.key)?" wt-check-item-checked":"")}
         title={item.note}>
          <input type="checkbox" checked={checked.includes(item.key)}
           onChange={e=>updateChecked(e.target.checked?[...checked,item.key]:checked.filter(k=>k!==item.key))}/>
          <span><strong>{item.label}</strong>
            <span className="wt-check-observed">{observation.text}</span>
            <small>{observation.source}{observation.source==="ALPACA DAILY"&&market?" · "+market.feed+" "+market.adjustment:""}</small>
             <small className="wt-check-chart-effect">{chartDescriptionForWtCheck(item.key)}</small>
          </span>
        </label>;
       })}
      </div>
    </div>}
  </div>)}
  <div className="wt-trading-foot">
   <span role="status" aria-live="polite">{loading?"Requesting Alpaca market data…":
     !loaded?(compact?"Choose indicator checkboxes below; refresh Alpaca for readings.":"Expand a section to request data."):
     "Alpaca: "+(market?.status||"UNAVAILABLE")+(market?.asOf?" · "+market.asOf:"")+
       " · "+(market?.feed||"feed unavailable")+
       (entry?.status?" · Entry research: "+entry.status:"")}</span>
   <button type="button" className="secondary" onClick={()=>updateChecked([])}
    disabled={!selectedCount}>DESELECT ALL</button>
   <button type="button" className="secondary" onClick={()=>void load()}
    disabled={loading||!programId||!ticker}>REFRESH ALPACA</button>
  </div>
  {(marketError||entryError)&&loaded&&<p className="subtle small">
    {marketError||"Alpaca market bars available."} {entryError}
  </p>}
  <small>Research only. Alpaca IEX data covers a single exchange and cannot verify SIP
    volume thresholds; raw daily bars are not split-adjusted. No automatically
    calculated STAY, SELL, plateau, broker stop or order is implied.</small>
 </section>;
}
