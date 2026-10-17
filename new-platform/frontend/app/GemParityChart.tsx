"use client";
import { useEffect, useId, useMemo, useRef, useState } from "react";

type Bar={date:string;close:number;volume:number};
type Technical={
 chartBars?:Bar[]; close?:number|null;sma20?:number|null;sma50?:number|null;
 marketDate?:string;marketSource?:string;eodFresh?:boolean;
 base?:{status?:string;support?:number|null;resistance?:number|null;touches?:number|null;
 widthPct?:number|null;contractionRatio?:number|null;volumeRatio?:number|null;breakoutRvol?:number|null};
};
type Range="1M"|"3M"|"6M"|"1Y"|"ALL";
type Plan={entry?:number;stop?:number;target?:number};
type SignalSnapshot=Partial<Record<"ENTRY"|"EXIT",{signals?:Record<string,string>;updated?:string}>>;
type DrawBar=Bar&{sma20:number|null;sma50:number|null;rollingSupport:number|null;rollingResistance:number|null};
const limits:Record<Range,number>={"1M":31,"3M":93,"6M":186,"1Y":366,"ALL":Infinity};
const colors={close:"#02a65b",sma20:"#1d78ec",sma50:"#ed982d",support:"#7f95a5",resistance:"#3184cb",entry:"#7750bd",stop:"#f04b47",target:"#00a84f"};
const good=(v:unknown):v is number=>typeof v==="number"&&Number.isFinite(v);
const price=(v?:number|null)=>good(v)?v.toFixed(v<1?3:2):"—";
const number=(v?:number|null,d=2)=>good(v)?v.toLocaleString("en-US",{maximumFractionDigits:d}):"—";
const day=(v:string)=>new Date(v+"T12:00:00Z").toLocaleDateString("en-US",{month:"short",day:"numeric",year:"numeric",timeZone:"UTC"});
function prepare(raw:Bar[]):DrawBar[]{
 const used=new Set<string>();
 const b=raw.filter(r=>r&&/^\d{4}-\d{2}-\d{2}$/.test(r.date)&&good(r.close)&&r.close>0&&good(r.volume)&&r.volume>=0&&!used.has(r.date)&&Boolean(used.add(r.date))).sort((a,z)=>a.date.localeCompare(z.date));
 return b.map((v,i)=>{
   const m20=b.slice(Math.max(0,i-19),i+1);
   const m50=b.slice(Math.max(0,i-49),i+1);
   const prev=b.slice(Math.max(0,i-20),i);
   return {...v,
    sma20:m20.length===20?m20.reduce((s,x)=>s+x.close,0)/20:null,
    sma50:m50.length===50?m50.reduce((s,x)=>s+x.close,0)/50:null,
    rollingSupport:i>=b.length-21&&prev.length===20?Math.min(...prev.map(x=>x.close)):null,
    rollingResistance:i>=b.length-21&&prev.length===20?Math.max(...prev.map(x=>x.close)):null
   };
 });
}
function Plot({ticker,data,bars,range,plan,rolling}:{ticker:string;data:Technical;bars:DrawBar[];range:Range;plan:Plan;rolling:boolean}){
 const [hover,setHover]=useState<number|null>(null);
 const unique=useId().replaceAll(":","");
 const fillId="eod-fill-"+unique,clipId="eod-clip-"+unique;
 const last=bars.at(-1);
 const cut=last?Date.parse(last.date)-limits[range]*86400000:Infinity;
 const subset=bars.filter(v=>Date.parse(v.date)>=cut);
 const W=640,H=235,L=36,R=85,T=8,B=175,VT=184,VB=216,span=W-L-R;
 const reference=rolling?[]:[
  {label:"Closing support",v:data.base?.support,color:colors.support},
  {label:"Closing resistance",v:data.base?.resistance,color:colors.resistance},
  {label:"Entry (plan)",v:plan.entry,color:colors.entry},
  {label:"Stop (plan)",v:plan.stop,color:colors.stop},
  {label:"Target (plan)",v:plan.target,color:colors.target}
 ].filter((p):p is {label:string;v:number;color:string}=>good(p.v));
 if(!subset.length)return <div className="parity-empty">No consistent source-linked saved EOD close/volume history. Choose Candles to review the external chart; missing prices are not simulated.</div>;
 const values=subset.flatMap(v=>[v.close,v.sma20,v.sma50,rolling?v.rollingSupport:null,rolling?v.rollingResistance:null].filter(good)).concat(reference.map(v=>v.v));
 const lo=Math.min(...values),hi=Math.max(...values),pad=(hi-lo)*.12||hi*.1||1,min=lo-pad,max=hi+pad;
 const X=(i:number)=>L+(subset.length>1?i/(subset.length-1):.5)*span;
 const Y=(v:number)=>T+(max-v)/(max-min)*(B-T);
 const line=(name:keyof DrawBar)=>subset.map((b,i)=>{
  const v=b[name],previous=i?subset[i-1][name]:null;
  return good(v)?(i&&good(previous)?"L":"M")+X(i).toFixed(2)+","+Y(v).toFixed(2):"";
 }).join(" ");
 let prev=-100;
 const levels=reference.slice().sort((a,b)=>b.v-a.v).map(v=>{
   const y=Y(v.v),labelY=Math.max(y,prev+13);prev=labelY;return {...v,y,labelY};
 });
 const maxVol=Math.max(1,...subset.map(v=>v.volume)),barWidth=Math.min(9,span/subset.length*.66);
 const ticks=Math.min(6,subset.length);
 const hovered=hover==null?null:subset[hover];
 return <div className="parity-svg-wrap">
   <svg viewBox={"0 0 "+W+" "+H} className="parity-svg" role="img" aria-label={ticker+" Streamlit source-saved price SMA20 SMA50 volume and support chart"}>
    <defs><linearGradient id={fillId} x1="0" y1="0" x2="0" y2="1"><stop stopColor="#00b975" stopOpacity=".10"/><stop offset="1" stopColor="#00b975" stopOpacity="0"/></linearGradient>
      <clipPath id={clipId}><rect x={L} y={T} width={span} height={B-T}/></clipPath></defs>
    {Array.from({length:5},(_,i)=>{const y=T+i*(B-T)/4;return <g key={i}>
       <line className="parity-gridline" x1={L} x2={W-R} y1={y} y2={y}/>
       <text className="parity-axis" x={L-5} y={y+3} textAnchor="end">{price(max-i*(max-min)/4)}</text>
     </g>})}
    {Array.from({length:ticks},(_,k)=>{const i=Math.round(k*(subset.length-1)/Math.max(1,ticks-1));return <g key={k}>
       <line className="parity-gridline" x1={X(i)} x2={X(i)} y1={T} y2={VB}/>
       <text className="parity-axis" x={X(i)} y={231} textAnchor="middle">{day(subset[i].date).replace(/, \d{4}/,"")}</text>
     </g>})}
    {subset.length>1&&<path d={line("close")+" L"+X(subset.length-1)+","+B+" L"+X(0)+","+B+" Z"} fill={"url(#"+fillId+")"} clipPath={"url(#"+clipId+")"}/>}
    {([
      ["close",colors.close,1.8],["sma20",colors.sma20,1.2],["sma50",colors.sma50,1.2],
      ...(rolling?[["rollingSupport",colors.support,1.6],["rollingResistance",colors.resistance,1.6]]:[])
     ] as [keyof DrawBar,string,number][]).map(([key,color,weight])=>
      <path key={key} d={line(key)} fill="none" stroke={color} strokeWidth={weight} clipPath={"url(#"+clipId+")"}/>)}
    {levels.map(v=><g key={v.label}>
      <line x1={L} x2={W-R+3} y1={v.y} y2={v.y} stroke={v.color} strokeDasharray="4 3"/>
      <rect x={W-R+4} y={v.labelY-6} width={79} height={12} rx={2} fill={v.color}/>
      <text x={W-R+7} y={v.labelY+2} fontSize={8} fill="white">{v.label.replace("Closing ","")+" "+price(v.v)}</text>
    </g>)}
    {subset.map((v,i)=>{const h=v.volume/maxVol*(VB-VT);return <rect key={v.date} x={X(i)-barWidth/2} y={VB-h} width={barWidth} height={h} fill={i>0&&v.close<subset[i-1].close?"#ef8d88":"#42c68b"}/>})}
    <text className="parity-axis" x={L+3} y={VT+7}>Volume {number(subset.at(-1)?.volume,0)}</text>
    {hovered&&<line x1={X(hover!)} x2={X(hover!)} y1={T} y2={VB} stroke="#7191a7" strokeDasharray="3 3" strokeWidth={1}/>}
    <rect x={L} y={T} width={span} height={VB-T} fill="transparent"
      onPointerMove={event=>{
       const svg=event.currentTarget.ownerSVGElement;
       if(!svg)return;
       const b=svg.getBoundingClientRect(),scaled=(event.clientX-b.left)/b.width*W;
       setHover(Math.max(0,Math.min(subset.length-1,Math.round((scaled-L)/span*(subset.length-1)))));
      }} onPointerLeave={()=>setHover(null)}/>
   </svg>
   {hovered&&<div className="parity-tooltip">{day(hovered.date)}<div><strong>{"Close $"+price(hovered.close)}</strong></div>{"Volume "+number(hovered.volume,0)}</div>}
 </div>;
}

function OriginalTradingView({ticker,range}:{ticker:string;range:Range}){
 const root=useRef<HTMLDivElement>(null);
 useEffect(()=>{
   const host=root.current;
   if(!host)return;
   host.replaceChildren();
   // Exact widget script/settings used in Streamlit gem_reference_frontend/dashboard.js.
   const child=document.createElement("div");
   child.className="tradingview-widget-container__widget";child.style.height="100%";
   host.appendChild(child);
   const script=document.createElement("script");
   script.src="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
   script.async=true;
   script.textContent=JSON.stringify({
     autosize:true,symbol:ticker,interval:"D",range:range==="ALL"?"ALL":range,
     timezone:"America/Los_Angeles",theme:"light",style:"1",locale:"en",
     enable_publishing:false,hide_top_toolbar:false,allow_symbol_change:false,
     save_image:false,studies:["MASimple@tv-basicstudies"],
     support_host:"https://www.tradingview.com"
   });
   host.appendChild(script);
   return ()=>{host.replaceChildren()};
 },[ticker,range]);
 return <div className="parity-external" ref={root} role="region"
   aria-label={ticker+" TradingView external candles; may be delayed"} />;
}
function StreamlitWatchlistSignalTable({signals}:{signals?:SignalSnapshot}){
 const [mode,setMode]=useState<"ENTRY"|"EXIT"|"BOTH">("BOTH");
 const names=["Volume / RVOL","Bollinger (20,2)","Phase 3 AVWAP",
  "EMA (10/20/50)","RSI (14)","MACD (12/26/9)","OBV","ATR (14)"];
 const modes=mode==="BOTH"?["ENTRY","EXIT"]:[mode];
 return <details className="parity-eight">
  <summary>STREAMLIT WATCHLIST SIGNALS — EIGHT ENTRY / EXIT INDICATORS</summary>
  <p>Identical Streamlit indicator labels and mode selector. These signals require the separate validated intraday watchlist scanner. Without its published output, Streamlit marks them NOT SCANNED; an EOD chart cannot manufacture them.</p>
  <div className="parity-signal-modes" role="group" aria-label="Watchlist indicator mode">
   {(["ENTRY","EXIT","BOTH"] as const).map(v=><button type="button" key={v}
    aria-pressed={mode===v} onClick={()=>setMode(v)}>{v}</button>)}
  </div>
  <div className="parity-check-table"><table><thead><tr><th>Indicator</th><th>Signal</th><th>Updated</th></tr></thead><tbody>
   {modes.flatMap(m=>names.map(name=><tr key={m+"|"+name}>
     <td>{mode==="BOTH"?m+" | "+name:name}</td>
     <td>{signals?.[m as "ENTRY"|"EXIT"]?.signals?.[name]||"NOT SCANNED"}</td>
     <td>{signals?.[m as "ENTRY"|"EXIT"]?.updated||"NOT SCANNED"}</td>
   </tr>))}
  </tbody></table></div>
 </details>;
}
export default function GemParityChart({ticker,programKey,data,watchlistSignals}:{ticker:string;programKey:string;data?:Technical|null;watchlistSignals?:SignalSnapshot}){
 const [range,setRange]=useState<Range>("6M"),[mode,setMode]=useState<"saved"|"tv">("saved");
 const [plan,setPlan]=useState<Plan>({}),[editing,setEditing]=useState(false);
 const [draft,setDraft]=useState({entry:"",stop:"",target:""}),[error,setError]=useState("");
 const sourceKey=programKey||ticker;
 const key="gem_chart_plan_"+sourceKey;
 const bars=useMemo(()=>prepare(data?.chartBars||[]),[data?.chartBars]);
 useEffect(()=>{
   setPlan({});setEditing(false);
   try{
     const value=JSON.parse(localStorage.getItem(key)||"{}");
     if(value&&typeof value==="object")setPlan(Object.fromEntries(
       (["entry","stop","target"] as const).filter(k=>good(value[k])&&value[k]>0).map(k=>[k,value[k]])
     ));
   }catch{/* no browser storage */}
 },[key]);
 const save=(next:Plan)=>{
   setPlan(next);try{localStorage.setItem(key,JSON.stringify(next));}catch{setError("Browser did not save chart levels.");}
 };
 const saveDraft=()=>{
   const next:Plan={};
   for(const k of ["entry","stop","target"] as const){
     if(draft[k]==="")continue;
     const v=Number(draft[k]);
     if(!good(v)||v<=0){setError("All levels must be positive numbers.");return;}
     next[k]=v;
   }
   if(good(next.entry)&&((good(next.stop)&&next.stop>=next.entry)||(good(next.target)&&next.target<=next.entry))){
     setError("Use a stop below entry and target above entry.");return;
   }
   setError("");save(next);setEditing(false);
 };
 const base=data?.base;
 const checks=[
  ["Closing support / resistance",base?"$"+price(base.support)+" / $"+price(base.resistance):"NOT AVAILABLE","20 previous sessions, approximate closing zones"],
  ["Separated support tests",number(base?.touches,0),"Within 3% of closing low, at least 3 sessions apart; prefer 2+"],
  ["Range width",number(base?.widthPct)+"%","Illustrative ≤18%, unvalidated"],
  ["Price-range contraction",number(base?.contractionRatio)+"×","Latest 5 close-range vs preceding 10; ≤0.75×"],
  ["Volume dry-up",number(base?.volumeRatio)+"×","Latest 5 average volume vs preceding 15; ≤0.85×"],
  ["Breakout volume",number(base?.breakoutRvol)+"×","Latest volume vs preceding 20; 1.5× illustrative"]
 ];
 return <section className="parity-chart" aria-label={ticker+" GEM/WT identical Streamlit chart"}>
  <header className="parity-heading"><strong>{ticker+" — "+range+" Trading Chart"}</strong>
   <div className="parity-ranges">{(["1M","3M","6M","1Y","ALL"] as Range[]).map(v=>
     <button key={v} type="button" className={range===v?"active":""} aria-pressed={range===v} onClick={()=>setRange(v)}>{v}</button>)}</div>
  </header>
  <div className="parity-body">
    <div className="parity-subtitle"><strong>{ticker}</strong><span className="price">{"Close "+price(data?.close)}</span>
     <span className="pill-note">{data?.eodFresh?"Saved EOD":"Saved EOD · stale / unverified"} · {data?.marketDate||"UNKNOWN"}</span></div>
    <div className="parity-legend">
      {([["Close",colors.close],["SMA20 "+price(data?.sma20),colors.sma20],["SMA50 "+price(data?.sma50),colors.sma50]] as [string,string][]).map(([label,c])=>
       <span key={label}><i style={{borderColor:c}}/>{label}</span>)}
    </div>
    {mode==="saved"?<Plot ticker={ticker} data={data||{}} bars={bars} range={range} plan={plan} rolling={false}/>:
      <OriginalTradingView ticker={ticker} range={range}/>} 
    <div className="parity-caption"><span>{mode==="saved"?bars.length+" saved sessions · closes and volume only":"External TradingView · may be delayed"}</span>
      <span className="parity-actions">
        <button type="button" onClick={()=>setMode(old=>old==="saved"?"tv":"saved")}>{mode==="saved"?"Candles":"Saved EOD"}</button>
        <button type="button" onClick={()=>{setError("");setDraft({entry:plan.entry?.toString()||"",stop:plan.stop?.toString()||"",target:plan.target?.toString()||""});setEditing(true)}}>Reference levels</button>
        <a href={"https://www.tradingview.com/chart/?symbol="+encodeURIComponent(ticker)} target="_blank" rel="noopener noreferrer">Open chart ↗</a>
      </span>
    </div>
    {editing&&<div className="parity-plan" role="group" aria-label={"Reference levels for "+sourceKey}>
      <strong>Chart reference levels · {sourceKey}</strong><p>Browser-saved per exact program, never an actual broker stop/order or input to GEM scores.</p>
      <div className="parity-plan-fields">{(["entry","stop","target"] as const).map(k=>
        <label key={k}>{k.toUpperCase()+" ($)"}<input type="number" min="0.0001" step="any" value={draft[k]} onChange={e=>setDraft(old=>({...old,[k]:e.target.value}))}/></label>)}</div>
      {error&&<p role="alert">{error}</p>}
      <div className="parity-actions"><button onClick={()=>{save({});setEditing(false)}}>Clear levels</button><button onClick={()=>setEditing(false)}>Cancel</button><button onClick={saveDraft}>Save levels</button></div>
    </div>}
  </div>
  <StreamlitWatchlistSignalTable signals={watchlistSignals}/>
  <details className="parity-base"><summary><strong>20-SESSION BASE FORMATION — DAILY-CLOSE OBSERVATIONS</strong> · {base?.status||"NOT AVAILABLE"}</summary>
   <p>Closing support and resistance use the preceding 20 closes at each session and appear only in the most recent 21 sessions. No future-price lookahead.</p>
   <Plot ticker={ticker} data={data||{}} bars={bars} range={range} plan={{}} rolling={true}/>
   <div className="parity-check-table"><table><thead><tr><th>Check</th><th>Observed</th><th>Interpretation</th></tr></thead>
   <tbody>{checks.map(([label,actual,description])=><tr key={label}><td>{label}</td><td>{actual}</td><td>{description}</td></tr>)}</tbody></table></div>
   <p>{"Source: "+(data?.marketSource||"UNVERIFIED")+" · EOD: "+(data?.marketDate||"UNKNOWN")+" · "+(data?.eodFresh?"RECENT":"STALE / UNVERIFIED")}. ATR, VWAP and real stops require separate high/low, intraday and broker data.</p>
  </details>
 </section>;
}
