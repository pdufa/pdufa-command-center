"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import {chartStudiesForWtChecks,WT_CHART_NAMES,type WtChartStudy} from "../lib/wt-chart-indicator-map";
type Bar={date:string;open:number;high:number;low:number;close:number;volume:number};
type Market={provider:string;programId:string;ticker:string;feed:string;coverage:string;status:string;bars:Bar[];asOf:string|null;message:string;researchOnly:boolean};
type Range="1M"|"3M"|"6M"|"1Y"|"ALL";
type ChartSeries=WtChartStudy|"ema10"|"ema20"|"ema50"|"macd";
const DEFAULT_SERIES:readonly ChartSeries[]=["sma20","sma50","ema10","ema20","ema50","volume","rsi","macd","atr"];
type Enhanced=Bar&{sma20:number|null;sma50:number|null;ema10:number|null;ema20:number|null;ema50:number|null;rsi:number|null;macd:number|null;signal:number|null;atr:number|null};
const ranges:Range[]=["1M","3M","6M","1Y","ALL"];
const rangeDays:Record<Range,number>={"1M":31,"3M":93,"6M":186,"1Y":366,"ALL":Infinity};
const good=(x:unknown):x is number=>typeof x==="number"&&Number.isFinite(x);
const fixed=(x:unknown,n=2)=>good(x)?x.toFixed(n):"—";
const short=(n:number)=>n>=1000000?(n/1000000).toFixed(1)+"M":n>=1000?(n/1000).toFixed(1)+"K":String(n);
function compute(raw:Bar[]):Enhanced[]{
 const rows=[...raw].filter(b=>b&&/^\d{4}-\d{2}-\d{2}$/.test(b.date)&&[b.open,b.high,b.low,b.close,b.volume].every(good)&&b.high>=Math.max(b.open,b.close,b.low)&&b.low>0).sort((a,b)=>a.date.localeCompare(b.date));
 let e10=0,e20=0,e50=0,e12=0,e26=0,sign=0,gain=0,loss=0,atr=0;
 return rows.map((b,i)=>{
  const last=rows[i-1],p=b.close;
  e10=i?e10+(2/11)*(p-e10):p;e20=i?e20+(2/21)*(p-e20):p;
  e50=i?e50+(2/51)*(p-e50):p;e12=i?e12+(2/13)*(p-e12):p;
  e26=i?e26+(2/27)*(p-e26):p;const macd=e12-e26;
  sign=i?sign+(2/10)*(macd-sign):macd;
  const g=last?Math.max(p-last.close,0):0,l=last?Math.max(last.close-p,0):0;
  if(i<=14){gain+=g;loss+=l;if(i===14){gain/=14;loss/=14;}}
  else{gain=(gain*13+g)/14;loss=(loss*13+l)/14;}
  const tr=last?Math.max(b.high-b.low,Math.abs(b.high-last.close),Math.abs(b.low-last.close)):b.high-b.low;
  if(i<13)atr+=tr;else if(i===13)atr=(atr+tr)/14;else atr=(atr*13+tr)/14;
  const a=rows.slice(Math.max(0,i-19),i+1),c=rows.slice(Math.max(0,i-49),i+1);
  return {...b,sma20:a.length===20?a.reduce((s,v)=>s+v.close,0)/20:null,
   sma50:c.length===50?c.reduce((s,v)=>s+v.close,0)/50:null,
   ema10:i>=9?e10:null,ema20:i>=19?e20:null,ema50:i>=49?e50:null,
   rsi:i>=14?(loss===0?(gain===0?50:100):100-100/(1+gain/loss)):null,
   macd:i>=26?macd:null,signal:i>=34?sign:null,atr:i>=13?atr:null};
 });
}
export function StockPlot({bars,large,candle,visibleStudies}:{bars:Enhanced[];large:boolean;candle:boolean;visibleStudies:ReadonlySet<ChartSeries>}){
 const [hover,setHover]=useState<number|null>(null);
 // Reserve an inner right gutter for labels attached to the actual plotted lines.
 // A dedicated internal gutter keeps SVG labels visible even with clipping.
 const W=710,L=53,R=164,T=12,B=large?296:164;
 const showVol=visibleStudies.has("volume");
 const showRsi=large&&visibleStudies.has("rsi");
 const showMacd=large&&visibleStudies.has("macd");
 const showAtr=large&&visibleStudies.has("atr");
 const panels=[showRsi?"rsi":null,showMacd?"macd":null,showAtr?"atr":null].filter((k):k is string=>Boolean(k));
 const volBottom=B+(showVol?62:15);
 const panelTop=(key:string)=>volBottom+12+panels.indexOf(key)*88;
 const H=volBottom+panels.length*88+25;
 const span=W-L-R,min=Math.min(...bars.map(b=>b.low)),max=Math.max(...bars.map(b=>b.high));
 const padding=Math.max((max-min)*.08,0.001),lo=min-padding,hi=max+padding;
 const x=(i:number)=>L+(i+.5)/bars.length*span;
 const y=(v:number)=>T+(hi-v)/(hi-lo)*(B-T);
 const barWidth=Math.max(.8,Math.min(10,(span/bars.length)*.7));
 const maxVol=Math.max(1,...bars.map(b=>b.volume));
 const drawLine=(key:"close"|"sma20"|"sma50"|"ema10"|"ema20"|"ema50")=>
  bars.map((b,i)=>{const value=b[key],previous=i?bars[i-1][key]:null;return good(value)?(i&&good(previous)?"L":"M")+x(i).toFixed(2)+","+y(value).toFixed(2):""}).join(" ");
 const target=hover===null?null:bars[hover];
 const rsiY=(r:number)=>panelTop("rsi")+12+(100-r)/100*57;
 const mValues=bars.flatMap(b=>[b.macd,b.signal].filter(good));
 const mMax=Math.max(0.001,...mValues.map(Math.abs));
 const mY=(v:number)=>panelTop("macd")+10+(mMax-v)/(2*mMax)*57;
 const atrMax=Math.max(0.001,...bars.map(b=>b.atr).filter(good));
 const atrY=(v:number)=>panelTop("atr")+72-v/atrMax*57;
 const prior10=bars.length>=11?bars.slice(-11,-1):[];
 const rangeHigh=prior10.length===10?Math.max(...prior10.map(b=>b.high)):null;
 const rangeLow=prior10.length===10?Math.min(...prior10.map(b=>b.low)):null;
 const indicatorPath=(key:"rsi"|"macd"|"signal"|"atr",scale:(v:number)=>number)=>bars.map((b,i)=>{
   const v=b[key],prior=i?bars[i-1][key]:null;
   return good(v)?(i&&good(prior)?"L":"M")+x(i).toFixed(2)+","+scale(v).toFixed(2):"";
 }).join(" ");
 const avgStyles=[
   ["sma20","SMA20","#1673eb"],["sma50","SMA50","#f49429"],
   ["ema10","EMA10","#9562c1"],["ema20","EMA20","#1a9ead"],
   ["ema50","EMA50","#ad865c"]
 ] as const;
 // Every line gets a matching name near its most recent endpoint. Spread
 // overlapping labels vertically, with short leaders back to the actual line.
 const last=bars.at(-1);
 const priceLabels=[
   ...(last?[{name:candle?"CLOSE":"PRICE",color:"#137d50",value:last.close}]:[]),
   ...(last?avgStyles.filter(([key])=>visibleStudies.has(key))
     .filter(([key])=>good(last[key]))
     .map(([key,name,color])=>({name,color,value:last[key] as number})):[]),
   ...(visibleStudies.has("range")&&rangeHigh!==null&&rangeLow!==null?[
     {name:"Prior 10D high",color:"#803770",value:rangeHigh},
     {name:"Prior 10D low",color:"#226d68",value:rangeLow}
   ]:[])
 ];
 const orderedLabels=priceLabels.map(label=>({...label,fromY:y(label.value)}))
   .sort((a,b)=>a.fromY-b.fromY);
 const labelGap=17,labelMin=T+10,labelMax=B-10;
 // Forward/backward packing means all labels stay inside the chart even when
 // several moving averages converge at nearly the same price.
 const finalLabels=orderedLabels.map(label=>({...label,at:label.fromY}));
 let lastLabelY=labelMin-labelGap;
 for(const label of finalLabels){
   label.at=Math.max(labelMin,label.fromY,lastLabelY+labelGap);
   lastLabelY=label.at;
 }
 if(finalLabels.length){
   let nextY=labelMax+labelGap;
   for(let i=finalLabels.length-1;i>=0;i--){
     const label=finalLabels[i];
     label.at=Math.min(label.at,nextY-labelGap,labelMax);
     nextY=label.at;
   }
 }
 const labelStart=W-R+12;
 const endpoint=x(bars.length-1);
 // A fixed-size HTML key below the responsive SVG stays legible on phones,
 // where SVG text is scaled down together with the plotted lines.
 const panelLineLabels=[
   ...(showVol?[{name:"Daily volume",color:"#45846b",display:short(last?.volume||0)}]:[]),
   ...(showRsi&&good(last?.rsi)?[{name:"RSI14",color:"#8e54a8",display:fixed(last.rsi,1)}]:[]),
   ...(showMacd&&good(last?.macd)?[{name:"MACD",color:"#1e9d8f",display:fixed(last.macd,3)}]:[]),
   ...(showMacd&&good(last?.signal)?[{name:"Signal",color:"#d08a2f",display:fixed(last.signal,3)}]:[]),
   ...(showAtr&&good(last?.atr)?[{name:"ATR14",color:"#ad6632",display:fixed(last.atr,3)}]:[])
 ];
 const lineKey=[
   ...priceLabels.map(item=>({name:item.name,color:item.color,display:fixed(item.value)})),
   ...panelLineLabels
 ];
 return <div className="alpaca-plot-box"><svg viewBox={"0 0 "+W+" "+H} className="alpaca-plot" role="img" aria-label={visibleStudies.size?"Alpaca daily price with selected indicators":"Alpaca daily price only — no technical indicators"}>
  {Array.from({length:5},(_,i)=>{const yy=T+i*(B-T)/4;return <g key={i}>
    <line x1={L} x2={W-R} y1={yy} y2={yy} stroke="#e3edf4"/>
    <text x={L-5} y={yy+3} textAnchor="end" fontSize="9" fill="#596979">{fixed(hi-i*(hi-lo)/4)}</text>
   </g>})}
   {candle?bars.map((b,i)=>{const color=b.close>=b.open?"#17a365":"#d34f4b",py=Math.min(y(b.open),y(b.close));
     return <g key={b.date}><line x1={x(i)} x2={x(i)} y1={y(b.high)} y2={y(b.low)} stroke={color}/>
       <rect x={x(i)-barWidth/2} y={py} width={barWidth} height={Math.max(1,Math.abs(y(b.open)-y(b.close)))} fill={color}/></g>})
    :<path d={drawLine("close")} stroke="#02a65b" fill="none" strokeWidth={2}/>}
   {avgStyles.filter(([key])=>visibleStudies.has(key))
     .map(([key,,color])=><path key={key} d={drawLine(key)} stroke={color} strokeWidth="1.5" fill="none"/>)}
   {visibleStudies.has("range")&&rangeHigh!==null&&rangeLow!==null&&<>
     <line x1={L} x2={W-R} y1={y(rangeHigh)} y2={y(rangeHigh)} stroke="#aa4f9c" strokeDasharray="5 3" strokeWidth="1.5"/>
     <line x1={L} x2={W-R} y1={y(rangeLow)} y2={y(rangeLow)} stroke="#257d76" strokeDasharray="5 3" strokeWidth="1.5"/>
    </>}
   {finalLabels.map(({name,color,value,fromY,at})=><g key={"name-"+name}
      aria-label={name+" "+fixed(value)}>
      <path d={"M"+endpoint+","+fromY+" L"+(labelStart-5)+","+at}
        stroke={color} strokeWidth="1.6" fill="none" opacity="0.9"/>
      <rect x={labelStart-5} y={at-11} width={151} height={18}
        rx="4" fill="#ffffff" stroke={color} strokeWidth="1.3"/>
      <text x={labelStart+2} y={at+2} fontSize="12" fontWeight="800"
        fill="#17344b">{name}</text>
      <title>{name+" "+fixed(value)}</title>
    </g>)}
   {showVol&&bars.map((b,i)=>{const height=b.volume/maxVol*(volBottom-B-9);return <rect key={"v"+b.date} x={x(i)-barWidth/2}
      y={volBottom-height} width={barWidth} height={height} fill={b.close>=b.open?"#42c68b":"#ef8d88"}/>})}
   {showVol&&<text x={L+3} y={B+15} fontSize="10" fill="#617586">{"Daily volume "+short(bars.at(-1)?.volume||0)}</text>}
   {showRsi&&<g>
      <line x1={L} x2={W-R} y1={rsiY(70)} y2={rsiY(70)} stroke="#ccaba0" strokeDasharray="3 2"/>
      <line x1={L} x2={W-R} y1={rsiY(30)} y2={rsiY(30)} stroke="#a0bdaf" strokeDasharray="3 2"/>
      <text x={L+4} y={panelTop("rsi")+9} fontSize="10" fill="#586a78">RSI14: {fixed(bars.at(-1)?.rsi,1)} (70/30)</text>
      <path d={indicatorPath("rsi",rsiY)} fill="none" stroke="#8e54a8" strokeWidth={1.5}/>
      {good(last?.rsi)&&<text x={labelStart} y={rsiY(last.rsi)+3}
        fontSize="9" fontWeight="700" fill="#8e54a8" stroke="#fff"
        strokeWidth="2.5" paintOrder="stroke">RSI14</text>}
     </g>}
    {showMacd&&<g>
      <line x1={L} x2={W-R} y1={mY(0)} y2={mY(0)} stroke="#b2becb"/>
      <text x={L+4} y={panelTop("macd")+9} fontSize="10" fill="#586a78">MACD(12,26,9): {fixed(bars.at(-1)?.macd,3)}</text>
      <path d={indicatorPath("macd",mY)} fill="none" stroke="#1e9d8f" strokeWidth={1.5}/>
      <path d={indicatorPath("signal",mY)} fill="none" stroke="#d08a2f" strokeWidth={1.2}/>
      {good(last?.macd)&&<text x={labelStart} y={mY(last.macd)+3}
        fontSize="9" fontWeight="700" fill="#1e9d8f" stroke="#fff"
        strokeWidth="2.5" paintOrder="stroke">MACD</text>}
      {good(last?.signal)&&<text x={labelStart}
        y={mY(last.signal)+3+(good(last?.macd)&&Math.abs(mY(last.macd)-mY(last.signal))<12?12:0)}
        fontSize="9" fontWeight="700" fill="#d08a2f" stroke="#fff"
        strokeWidth="2.5" paintOrder="stroke">Signal</text>}
     </g>}
    {showAtr&&<g>
      <text x={L+4} y={panelTop("atr")+9} fontSize="10" fill="#586a78">ATR14: {fixed(bars.at(-1)?.atr,3)} · no trailing stop implied</text>
      <path d={indicatorPath("atr",atrY)} fill="none" stroke="#ad6632" strokeWidth={1.6}/>
      {good(last?.atr)&&<text x={labelStart} y={atrY(last.atr)+3}
        fontSize="9" fontWeight="700" fill="#ad6632" stroke="#fff"
        strokeWidth="2.5" paintOrder="stroke">ATR14</text>}
     </g>}
   {target&&<line x1={x(hover!)} x2={x(hover!)} y1={T} y2={volBottom} stroke="#7395b4" strokeDasharray="3 2"/>}
   {Array.from({length:Math.min(6,bars.length)},(_,k)=>{const i=Math.round(k*(bars.length-1)/Math.max(1,Math.min(6,bars.length)-1));return <text
       key={k} x={x(i)} y={H-9} textAnchor="middle" fontSize="10" fill="#647483">{bars[i].date.slice(5)}</text>})}
   <rect x={L} y={T} width={span} height={volBottom-T} fill="transparent"
     onPointerMove={ev=>{const svg=ev.currentTarget.ownerSVGElement;if(!svg)return;const box=svg.getBoundingClientRect();
       const at=(ev.clientX-box.left)/box.width*W;setHover(Math.max(0,Math.min(bars.length-1,Math.floor((at-L)/span*bars.length))));}}
     onPointerLeave={()=>setHover(null)}/>
  </svg>
  <div className="alpaca-line-key" aria-label="Labels for the lines actually shown on the Alpaca chart">
    {lineKey.map(item=><span key={item.name} className="alpaca-line-key-item"
      style={{borderLeftColor:item.color}}>
      <strong>{item.name}</strong> <span>{item.display}</span>
    </span>)}
  </div>
  {target&&<div className="alpaca-plot-tooltip">{target.date} | O {fixed(target.open)} H {fixed(target.high)} L {fixed(target.low)} C {fixed(target.close)} · Vol {short(target.volume)}</div>}</div>;
}
export default function AlpacaStockChart({programId,ticker,compact=false,wtIndicatorKeys}:{programId:string;ticker:string;compact?:boolean;wtIndicatorKeys?:readonly string[]}){
 const [range,setRange]=useState<Range>("6M"),[state,setState]=useState<Market|null>(null);
 const [error,setError]=useState(""),[expanded,setExpanded]=useState(!compact);
 const [candle,setCandle]=useState(!compact),[studies,setStudies]=useState(true);
 const [visible,setVisible]=useState(false),surface=useRef<HTMLDivElement>(null);
 const wtControlled=wtIndicatorKeys!==undefined;
 const visibleStudies=useMemo<ReadonlySet<ChartSeries>>(()=>new Set<ChartSeries>(
  wtControlled?chartStudiesForWtChecks(wtIndicatorKeys):studies?DEFAULT_SERIES:[]
 ),[wtControlled,wtIndicatorKeys,studies]);
 useEffect(()=>{const host=surface.current;if(!host)return;
   if(typeof IntersectionObserver==="undefined"){setVisible(true);return}
   const obs=new IntersectionObserver(x=>{if(x.some(y=>y.isIntersecting)){setVisible(true);obs.disconnect()}},{rootMargin:"200px 0px"});
   obs.observe(host);return()=>obs.disconnect()},[]);
 useEffect(()=>{if(!visible||!/^PDUFA-\d{6,}$/.test(programId))return;
   const ctrl=new AbortController();setError("");setState(null);
   fetch("/api/alpaca-chart/"+encodeURIComponent(programId)+"?range="+range,{cache:"no-store",signal:ctrl.signal})
    .then(async response=>{if(!response.ok)throw Error("Alpaca endpoint: HTTP "+response.status);return response.json() as Promise<Market>})
    .then(d=>{if(ctrl.signal.aborted)return;if(d.provider!=="ALPACA"||d.programId!==programId||d.ticker!==ticker)throw Error("Provider or Program ID mismatch");setState(d)})
    .catch(e=>{if(!ctrl.signal.aborted)setError(String(e))});
   return()=>ctrl.abort();
 },[visible,programId,ticker,range]);
 const all=useMemo(()=>compute(state?.bars||[]),[state?.bars]);
 const latest=all.at(-1),cut=latest?Date.parse(latest.date)-rangeDays[range]*86400000:Infinity;
 const visibleBars=all.filter(x=>Date.parse(x.date)>=cut);
 // WT selections govern *both* plotted studies and readout chips. Keep
 // original readouts for other pages that use their independent chart controls.
 const studyReadouts:readonly [ChartSeries,string,number|null|undefined][]=[
  ["sma20","SMA20",latest?.sma20],["sma50","SMA50",latest?.sma50],
  ["ema10","EMA10",latest?.ema10],["ema20","EMA20",latest?.ema20],
  ["ema50","EMA50",latest?.ema50],["rsi","RSI14",latest?.rsi],
  ["macd","MACD",latest?.macd],["atr","ATR14",latest?.atr]
 ];
 const visibleReadouts=studyReadouts.filter(([key])=>!wtControlled||visibleStudies.has(key));
 return <section ref={surface} className="alpaca-stock-chart" aria-label={ticker+" chart from Alpaca"}>
  <header className="alpaca-header"><div><strong>{ticker} · ALPACA STOCK CHART</strong>
     <small>{programId} · {state?.feed||"FEED PENDING"} · {state?.coverage||"Provider Alpaca only"}</small></div>
   <div className="alpaca-buttons">
    {compact&&<button type="button" onClick={()=>setExpanded(v=>!v)}>{expanded?"HIDE FULL CHART":"FULL CHART"}</button>}
    <button type="button" onClick={()=>setCandle(v=>!v)}>{candle?"LINE":"CANDLES"}</button>
    {!wtControlled&&<button type="button" onClick={()=>setStudies(v=>!v)}>{studies?"HIDE STUDIES":"SHOW STUDIES"}</button>}
   </div></header>
  {wtControlled&&<div className="alpaca-wt-indicator-status" role="status">WT checkbox chart controls · {visibleStudies.size?([...visibleStudies].map(key=>key in WT_CHART_NAMES?WT_CHART_NAMES[key as WtChartStudy]:key).join(" · ")):"No studies selected — price chart only"} · Research only</div>}
  <div className="alpaca-range">{ranges.map(r=><button key={r} type="button" className={range===r?"active":""}
    aria-pressed={range===r} onClick={()=>setRange(r)}>{r}</button>)}
    <span>{latest?"Last Alpaca session "+latest.date+" | Close $"+fixed(latest.close):"Alpaca source awaiting verification"}</span></div>
  {state?.status==="OK"&&visibleBars.length?
    <><StockPlot bars={visibleBars} large={expanded} candle={candle} visibleStudies={visibleStudies}/>
     {expanded&&visibleReadouts.length>0&&<div className="alpaca-values">{visibleReadouts.map(([key,label,value])=>
       <span key={key}>{label}: {fixed(value,2)}</span>)}</div>}
    </>:
    <div className="alpaca-missing" role="status"><strong>ALPACA · {error?"ERROR":state?.status||"LOADING"}</strong>
     <p>{error||state?.message||"Requesting market bars from Alpaca. No TradingView, Yahoo or synthetic fallback."}</p></div>}
  <footer className="alpaca-footer"><strong>Provider: Alpaca Market Data {state?.feed||""}</strong>
    <span>{state?.feed==="IEX"?"IEX only; price/volume are not consolidated SIP.":state?.coverage||"Strict Alpaca source"}</span>
    <span>Raw daily OHLCV · research only · no broker orders</span></footer>
 </section>;
}
