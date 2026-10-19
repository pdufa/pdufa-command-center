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
export const suggestedWtIndicators:Record<GroupId,readonly string[]>={
 entry:["entry-score","entry-breakout","entry-dollar","entry-trigger","entry-stop"],
 stay:["stay-trend","stay-support","stay-rsi","stay-volume"],
 exit:["exit-two-close","exit-support","exit-atr-trail","exit-rsi"],
};
/** The FS button reflects the real five selected checkboxes, regardless of how they were selected. */
export function areWtSuggestedIndicatorsChecked(selected:readonly string[],group:GroupId):boolean{
 const checked=new Set(selected);
 const required=suggestedWtIndicators[group];
 return required.length>0&&required.every(key=>checked.has(key));
}
export type WtPresetFlags={fs:boolean;fa:boolean};
export function nextWtPresetFlags(flags:WtPresetFlags,mode:"FS"|"FA"):WtPresetFlags{
 return mode==="FS"?{...flags,fs:!flags.fs}:{...flags,fa:!flags.fa};
}
/** Preserve independent FS and FA states; combine their selections for display only. */
export function wtEffectivePresetKeys(manual:readonly string[],group:GroupId,flags:WtPresetFlags):string[]{
 const available=WT_GROUPS.find(item=>item.id===group)?.items.map(item=>item.key)||[];
 const selected=new Set(manual.filter(key=>available.includes(key)));
 if(flags.fs)for(const key of suggestedWtIndicators[group])selected.add(key);
 // FA intentionally has no assigned indicators.
 return available.filter(key=>selected.has(key));
}
/** Backward-compatible fallback for checklists without per-trial preset state. */
export function nextWtPresetSelection(
 selected:readonly string[],group:GroupId,mode:"FS"|"FA"
):string[]{
 if(mode==="FA")return [...selected]; // Unassigned toggle must never change indicators.
 const available=WT_GROUPS.find(item=>item.id===group)?.items.map(item=>item.key)||[];
 const keys=mode==="FS"
   ?suggestedWtIndicators[group].filter(key=>available.includes(key))
   :available;
 const selectedSet=new Set(selected);
 const fullySelected=keys.length>0&&keys.every(key=>selectedSet.has(key));
 if(fullySelected){
  const affected=new Set(keys);
  return selected.filter(key=>!affected.has(key));
 }
 return [...new Set([...selected,...keys])];
}
const verified=(text:string,source:WtObservation["source"]):WtObservation=>({text,source});
const UNAVAILABLE=verified("NOT VERIFIED","UNAVAILABLE");
/** Extract only measured numeric tokens: prices, percentage, RVOL, scores, and
 * dates. Do not paint numbers inside indicator names (SMA20, RSI14), labels
 * (20-session), or unsupported/not-scanned statuses as verified readings. */
export function wtNumericReadingParts(value:string):{text:string;numeric:boolean}[]{
 const parts:{text:string;numeric:boolean}[]=[];
 const token=/-?\$?\d[\d,]*(?:\.\d+)?(?:\/\d+)?(?:%|×)?/g;
 let previous=0;
 for(const match of value.matchAll(token)){
  const start=match.index,end=start+match[0].length;
  const before=start>0?value[start-1]:"";
  const after=value[end]||"";
  // Avoid highlighting indicator/descriptor numbers, such as SMA20 or 20d.
  if(/[a-zA-Z0-9]/.test(before)||/[a-zA-Z]/.test(after)||
     (after==="-"&&/[a-zA-Z]/.test(value[end+1]||"")))continue;
  if(start>previous)parts.push({text:value.slice(previous,start),numeric:false});
  parts.push({text:match[0],numeric:true});
  previous=end;
 }
 if(previous<value.length)parts.push({text:value.slice(previous),numeric:false});
 return parts.length?parts:[{text:value,numeric:false}];
}
type WtInfoLocation={target:"chart"|"entry"|"scores"|"reading";name:string;note:string};
/** Destination for every WT checklist choice. Links identify real panels; an
 * unsupported trading model always stays a NOT VERIFIED reading, not a signal. */
export const WT_INFO_LOCATIONS:Readonly<Record<string,WtInfoLocation>>={
 "entry-score":{target:"entry",name:"ENTRY SIGNAL panel",note:"Entry score and coverage are also in SCORES below the chart"},
 "entry-base":{target:"chart",name:"CHART · 10-session high/low",note:"Range proxy, not verified multi-touch support"},
 "entry-breakout":{target:"chart",name:"CHART · prior 10-session high",note:"Reference high only; breakout status is shown in this row"},
 "entry-trend":{target:"chart",name:"CHART · SMA20 / SMA50",note:"Select this box to draw both moving averages"},
 "entry-rvol":{target:"reading",name:"HERE · RVOL20 reading",note:"Refresh Alpaca for RVOL; chart shows only raw daily volume"},
 "entry-rsi":{target:"chart",name:"CHART · RSI14",note:"Select this box to draw RSI14"},
 "entry-dollar":{target:"reading",name:"HERE · 20-day dollar volume",note:"Refresh Alpaca for the average dollar-volume value"},
 "entry-atr":{target:"chart",name:"CHART · ATR14",note:"Select this box to draw ATR14"},
 "entry-trigger":{target:"entry",name:"ENTRY SIGNAL · Trigger / Max Buy",note:"Values appear only when the entry research API verifies them"},
 "entry-stop":{target:"entry",name:"ENTRY SIGNAL · Initial Stop",note:"Research reference only; not an actual broker stop"},
 "stay-trend":{target:"chart",name:"CHART · SMA20 / SMA50",note:"Select this box to draw the moving averages"},
 "stay-support":{target:"chart",name:"CHART · prior 10-session low",note:"Only a support proxy; observed status is in this row"},
 "stay-rsi":{target:"chart",name:"CHART · RSI14",note:"Select this box to draw RSI14"},
 "stay-volume":{target:"reading",name:"HERE · Relative Volume",note:"Refresh Alpaca for the RVOL value; the chart draws raw daily volume"},
 "stay-trailing":{target:"reading",name:"HERE · Trailing Stop Status",note:"No verified position or trailing-stop ledger is available"},
 "stay-pdufa":{target:"reading",name:"HERE · PDUFA Days",note:"Reported date and remaining days, not a verified FDA deadline"},
 "stay-signal":{target:"reading",name:"HERE · HOLD Signal Status",note:"No validated position-based HOLD signal is available"},
 "exit-score":{target:"scores",name:"SCORES · Exit Risk /100",note:"Entry/exit scoring factors and source coverage below the chart"},
 "exit-two-close":{target:"chart",name:"CHART · SMA20",note:"The two-close result is also shown in this row"},
 "exit-support":{target:"chart",name:"CHART · prior 10-session low",note:"Breakdown comparison is shown in this row"},
 "exit-atr-trail":{target:"chart",name:"CHART · ATR14",note:"ATR14 is visible; no trailing stop is inferred"},
 "exit-rsi":{target:"chart",name:"CHART · RSI14",note:"RSI14 is visible; an exhaustion exit is not validated"},
 "exit-plateau":{target:"reading",name:"HERE · Plateau Status",note:"No backtested price plateau detector exists"},
 "exit-divergence":{target:"reading",name:"HERE · Price/Volume Comparison",note:"Observed price/volume only, not a validated divergence signal"},
 "exit-pdufa":{target:"reading",name:"HERE · PDUFA Exit Timing",note:"Provisional reported-date calculation, not verified exit deadline"},
 "exit-action":{target:"scores",name:"SCORES · Clinical / SEC Risk",note:"Review saved FDA and dilution alerts below the chart"}
};
const good=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const pct=(v:number)=>numeric(v,2)+"%";

export default function WtTradingSections({
 programId,ticker,record,tech,autoFetch=false,checkedKeys,onCheckedKeysChange,activeGroup,compact=false,
 presetFlags,onPresetToggle
}:{
 programId:string;ticker:string;record?:Candidate;tech?:Candidate["technical"]|null;autoFetch?:boolean;
 checkedKeys?:readonly string[];onCheckedKeysChange?:(keys:string[])=>void;
 activeGroup?:GroupId;compact?:boolean;
 presetFlags?:WtPresetFlags;onPresetToggle?:(mode:"FS"|"FA")=>void;
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
  {compact&&<p className="subtle small">FS toggles suggested indicators; FA is an independent switch with no indicators assigned. Manual checkboxes remain available. Chart studies are for research only; no orders are placed.</p>}
  {programId&&!compact&&<p className="subtle small"><a href={"#wt-chart-"+programId}>View linked chart for {ticker||programId} ↓</a> · Only this exact program chart follows these checkboxes.</p>}
  {shownGroups.map(group=><div className="wt-check-group" key={group.id}>
    {compact?<div className="wt-check-group-title wt-checklist-visible-heading">
      <div className="wt-checklist-heading-text">
       <strong>{group.title} — SELECT INDICATORS</strong>
       <small>{group.items.filter(i=>checked.includes(i.key)).length}/{group.items.length} selected</small>
      </div>
      <div className="wt-checklist-preset-buttons" role="group" aria-label={"FS and FA independently selectable — "+ticker+" "+group.id.toUpperCase()}>
       <button type="button" className="wt-checklist-preset-button"
        aria-label={"FS — toggle suggested "+group.id.toUpperCase()+" indicators for "+ticker}
        title="FS — suggested indicators; click again to uncheck them"
        aria-pressed={areWtSuggestedIndicatorsChecked(checked,group.id)}
        onClick={()=>onPresetToggle?onPresetToggle("FS"):updateChecked(nextWtPresetSelection(checked,group.id,"FS"))}>FS</button>
       <button type="button" className="wt-checklist-preset-button"
        aria-label={"FA — unassigned independent toggle for "+ticker+" "+group.id.toUpperCase()}
        title="FA — no indicators assigned; toggle independently"
        aria-pressed={presetFlags?.fa??group.items.every(item=>checked.includes(item.key))}
        onClick={()=>onPresetToggle?.("FA")}>FA</button>
      </div>
    </div>:<button type="button" className="wt-check-group-title"
      aria-expanded={expanded[group.id]} aria-controls={"wt-"+group.id+"-"+programId}
      onClick={()=>toggle(group.id)}>
      <span aria-hidden="true">{expanded[group.id]?"▾":"▸"}</span>
      <strong>{group.title}</strong>
      <small>{group.items.filter(i=>checked.includes(i.key)).length}/{group.items.length} selected</small>
    </button>}
    {(compact||expanded[group.id])&&<div className="wt-check-group-body" id={"wt-"+group.id+"-"+programId}>
      <div className="wt-check-grid" aria-label={group.id.toUpperCase()+" WT indicator information table"}>
       {group.items.map(item=>{
        const observation=values[item.key]||UNAVAILABLE;
        const location=WT_INFO_LOCATIONS[item.key];
        const where=location.target==="chart"?"#wt-chart-"+programId:
          location.target==="entry"?"#wt-entry-info-"+programId:
          location.target==="scores"?"#wt-score-info-"+programId:
          "#wt-reading-"+programId+"-"+item.key;
        return <div key={item.key} className={"wt-check-item"+(checked.includes(item.key)?" wt-check-item-checked":"")}
         title={item.note}>
          <label className="wt-check-choice">
           <input type="checkbox" checked={checked.includes(item.key)}
            onChange={e=>updateChecked(e.target.checked?[...checked,item.key]:checked.filter(k=>k!==item.key))}/>
           <span><strong>{item.label}</strong>
             <span className="wt-check-observed">{observation.text}</span>
             <small>{observation.source}{observation.source==="ALPACA DAILY"&&market?" · "+market.feed+" "+market.adjustment:""}</small>
             <small className="wt-check-chart-effect">{chartDescriptionForWtCheck(item.key)}</small>
           </span>
          </label>
          <div className="wt-where-info" id={"wt-reading-"+programId+"-"+item.key}>
           <strong className="wt-where-heading">WHERE TO SEE INFO:</strong>
           <a className="wt-where-link" href={where}>{location.name+" →"}</a>
           <span className="wt-where-note">{location.note}</span>
           <span className="wt-where-reading"><strong>ACTUAL:</strong>{" "}
             {wtNumericReadingParts(observation.text).map((part,i)=>part.numeric?
               <strong className="wt-indicator-number" key={i}>{part.text}</strong>:
               <span key={i}>{part.text}</span>)}
           </span>
           {location.target==="reading"&&observation.source==="UNAVAILABLE"?
             <button type="button" className="wt-where-refresh" onClick={()=>void load()}
              disabled={loading||!programId||!ticker}>REFRESH ALPACA / ENTRY DATA</button>:null}
          </div>
        </div>;
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
