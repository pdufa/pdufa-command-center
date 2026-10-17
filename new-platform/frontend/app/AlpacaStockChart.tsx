"use client";
import { useEffect, useMemo, useRef, useState } from "react";
type Bar={date:string;open:number;high:number;low:number;close:number;volume:number};
type Market={provider:string;programId:string;ticker:string;feed:string;coverage:string;status:string;bars:Bar[];asOf:string|null;message:string;researchOnly:boolean};
type Range="1M"|"3M"|"6M"|"1Y"|"ALL";
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
  if(i<14)atr+=tr;else if(i===14)atr=(atr+tr)/15;else atr=(atr*13+tr)/14;
  const a=rows.slice(Math.max(0,i-19),i+1),c=rows.slice(Math.max(0,i-49),i+1);
  return {...b,sma20:a.length===20?a.reduce((s,v)=>s+v.close,0)/20:null,
   sma50:c.length===50?c.reduce((s,v)=>s+v.close,0)/50:null,
   ema10:i>=9?e10:null,ema20:i>=19?e20:null,ema50:i>=49?e50:null,
   rsi:i>=14?(loss===0?(gain===0?50:100):100-100/(1+gain/loss)):null,
   macd:i>=26?macd:null,signal:i>=34?sign:null,atr:i>=14?atr:null};
 });
}
function StockPlot({bars,large,candle,studies}:{bars:Enhanced[];large:boolean;candle:boolean;studies:boolean}){
 const [hover,setHover]=useState<number|null>(null);
 const W=710,H=large?440:235,L=53,R=43,T=12,B=large?296:164,volBottom=large?348:212;
 const span=W-L-R,min=Math.min(...bars.map(b=>b.low)),max=Math.max(...bars.map(b=>b.high));
 const padding=Math.max((max-min)*.08,0.001),lo=min-padding,hi=max+padding;
 const x=(i:number)=>L+(i+.5)/bars.length*span;
 const y=(v:number)=>T+(hi-v)/(hi-lo)*(B-T);
 const barWidth=Math.max(.8,Math.min(10,(span/bars.length)*.7));
 const maxVol=Math.max(1,...bars.map(b=>b.volume));
 const drawLine=(key:"close"|"sma20"|"sma50"|"ema10"|"ema20"|"ema50")=>
  bars.map((b,i)=>{const value=b[key],previous=i?bars[i-1][key]:null;return good(value)?(i&&good(previous)?"L":"M")+x(i).toFixed(2)+","+y(value).toFixed(2):""}).join(" ");
 const target=hover===null?null:bars[hover];
 return <div className="alpaca-plot-box"><svg viewBox={"0 0 "+W+" "+H} className="alpaca-plot" role="img" aria-label="Alpaca daily candlesticks and daily volume">
  {Array.from({length:5},(_,i)=>{const yy=T+i*(B-T)/4;return <g key={i}>
    <line x1={L} x2={W-R} y1={yy} y2={yy} stroke="#e3edf4"/>
    <text x={L-5} y={yy+3} textAnchor="end" fontSize="9" fill="#596979">{fixed(hi-i*(hi-lo)/4)}</text>
   </g>})}
   {candle?bars.map((b,i)=>{const color=b.close>=b.open?"#17a365":"#d34f4b",py=Math.min(y(b.open),y(b.close));
     return <g key={b.date}><line x1={x(i)} x2={x(i)} y1={y(b.high)} y2={y(b.low)} stroke={color}/>
       <rect x={x(i)-barWidth/2} y={py} width={barWidth} height={Math.max(1,Math.abs(y(b.open)-y(b.close)))} fill={color}/></g>})
    :<path d={drawLine("close")} stroke="#02a65b" fill="none" strokeWidth={2}/>}
   {([["sma20","#1673eb"],["sma50","#f49429"],
     ...(large?[["ema10","#9562c1"],["ema20","#1a9ead"],["ema50","#ad865c"]]:[])] as [("sma20"|"sma50"|"ema10"|"ema20"|"ema50"),string][])
    .map(([key,color])=><path key={key} d={drawLine(key)} stroke={color} strokeWidth="1.2" fill="none"/>)}
   {bars.map((b,i)=>{const height=b.volume/maxVol*(volBottom-B-9);return <rect key={"v"+b.date} x={x(i)-barWidth/2}
      y={volBottom-height} width={barWidth} height={height} fill={b.close>=b.open?"#42c68b":"#ef8d88"}/>})}
   <text x={L+3} y={B+15} fontSize="10" fill="#617586">{"Daily volume "+short(bars.at(-1)?.volume||0)}</text>
   {large&&studies&&<><text x={L+3} y={H-44} fontSize="11" fill="#536778">RSI(14): {fixed(bars.at(-1)?.rsi,1)}</text>
      <text x={L+200} y={H-44} fontSize="11" fill="#536778">MACD(12,26,9): {fixed(bars.at(-1)?.macd,3)}</text>
      <text x={L+470} y={H-44} fontSize="11" fill="#536778">ATR(14): {fixed(bars.at(-1)?.atr,3)}</text></>}
   {target&&<line x1={x(hover!)} x2={x(hover!)} y1={T} y2={volBottom} stroke="#7395b4" strokeDasharray="3 2"/>}
   {Array.from({length:Math.min(6,bars.length)},(_,k)=>{const i=Math.round(k*(bars.length-1)/Math.max(1,Math.min(6,bars.length)-1));return <text
       key={k} x={x(i)} y={H-9} textAnchor="middle" fontSize="10" fill="#647483">{bars[i].date.slice(5)}</text>})}
   <rect x={L} y={T} width={span} height={volBottom-T} fill="transparent"
     onPointerMove={ev=>{const svg=ev.currentTarget.ownerSVGElement;if(!svg)return;const box=svg.getBoundingClientRect();
       const at=(ev.clientX-box.left)/box.width*W;setHover(Math.max(0,Math.min(bars.length-1,Math.floor((at-L)/span*bars.length))));}}
     onPointerLeave={()=>setHover(null)}/>
  </svg>{target&&<div className="alpaca-plot-tooltip">{target.date} | O {fixed(target.open)} H {fixed(target.high)} L {fixed(target.low)} C {fixed(target.close)} · Vol {short(target.volume)}</div>}</div>;
}
export default function AlpacaStockChart({programId,ticker,compact=false}:{programId:string;ticker:string;compact?:boolean}){
 const [range,setRange]=useState<Range>("6M"),[state,setState]=useState<Market|null>(null);
 const [error,setError]=useState(""),[expanded,setExpanded]=useState(!compact);
 const [candle,setCandle]=useState(!compact),[studies,setStudies]=useState(true);
 const [visible,setVisible]=useState(false),surface=useRef<HTMLDivElement>(null);
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
 return <section ref={surface} className="alpaca-stock-chart" aria-label={ticker+" chart from Alpaca"}>
  <header className="alpaca-header"><div><strong>{ticker} · ALPACA STOCK CHART</strong>
     <small>{programId} · {state?.feed||"FEED PENDING"} · {state?.coverage||"Provider Alpaca only"}</small></div>
   <div className="alpaca-buttons">
    {compact&&<button type="button" onClick={()=>setExpanded(v=>!v)}>{expanded?"HIDE FULL CHART":"FULL CHART"}</button>}
    <button type="button" onClick={()=>setCandle(v=>!v)}>{candle?"LINE":"CANDLES"}</button>
    <button type="button" onClick={()=>setStudies(v=>!v)}>{studies?"HIDE STUDIES":"SHOW STUDIES"}</button>
   </div></header>
  <div className="alpaca-range">{ranges.map(r=><button key={r} type="button" className={range===r?"active":""}
    aria-pressed={range===r} onClick={()=>setRange(r)}>{r}</button>)}
    <span>{latest?"Last Alpaca session "+latest.date+" | Close $"+fixed(latest.close):"Alpaca source awaiting verification"}</span></div>
  {state?.status==="OK"&&visibleBars.length?
    <><StockPlot bars={visibleBars} large={expanded} candle={candle} studies={studies}/>
     {expanded&&<div className="alpaca-values">{[
      ["SMA20",latest?.sma20],["SMA50",latest?.sma50],["EMA10",latest?.ema10],
      ["EMA20",latest?.ema20],["EMA50",latest?.ema50],["RSI14",latest?.rsi],["MACD",latest?.macd],["ATR14",latest?.atr]
     ].map(([k,v])=><span key={String(k)}>{k}: {fixed(v,2)}</span>)}</div>}
    </>:
    <div className="alpaca-missing" role="status"><strong>ALPACA · {error?"ERROR":state?.status||"LOADING"}</strong>
     <p>{error||state?.message||"Requesting market bars from Alpaca. No TradingView, Yahoo or synthetic fallback."}</p></div>}
  <footer className="alpaca-footer"><strong>Provider: Alpaca Market Data {state?.feed||""}</strong>
    <span>{state?.feed==="IEX"?"IEX only; price/volume are not consolidated SIP.":state?.coverage||"Strict Alpaca source"}</span>
    <span>Raw daily OHLCV · research only · no broker orders</span></footer>
 </section>;
}
