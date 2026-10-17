"use client";

import {useEffect,useRef,useState} from "react";

const overview="https://s3.tradingview.com/external-embedding/embed-widget-symbol-overview.js";
const advanced="https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
const studies=["MAExp@tv-basicstudies","RSI@tv-basicstudies","MACD@tv-basicstudies"];
function Widget({ticker,full}:{ticker:string;full:boolean}){
  const ref=useRef<HTMLDivElement>(null);
  useEffect(()=>{
    const host=ref.current;
    if(!host||!/^[A-Z][A-Z0-9.-]{0,12}$/.test(ticker))return;
    let mounted=false;
    let observer: IntersectionObserver|undefined;
    const mount=()=>{
    if(mounted||!host.isConnected)return;
    mounted=true;
    host.replaceChildren();
    const wrapper=document.createElement("div");
    wrapper.className="tradingview-widget-container";
    const widget=document.createElement("div");
    widget.className="tradingview-widget-container__widget";
    const credit=document.createElement("small");
    const anchor=document.createElement("a");
    anchor.href="https://www.tradingview.com/symbols/"+encodeURIComponent(ticker)+"/";
    anchor.target="_blank";
    anchor.rel="noopener noreferrer";
    anchor.textContent=full?ticker+" advanced chart by TradingView":ticker+" chart via TradingView";
    credit.appendChild(anchor);
    const script=document.createElement("script");
    script.type="text/javascript";
    script.src=full?advanced:overview;
    script.async=true;
    script.textContent=JSON.stringify(full?{
      autosize:true,symbol:ticker,interval:"D",timezone:"exchange",theme:"light",
      locale:"en",style:"1",backgroundColor:"#ffffff",gridColor:"rgba(0,0,0,0.06)",
      withdateranges:true,hide_side_toolbar:false,hide_top_toolbar:false,
      hide_volume:false,allow_symbol_change:false,save_image:true,
      details:false,hotlist:false,calendar:false,studies,
      show_popup_button:true,popup_width:"1200",popup_height:"750",
      support_host:"https://www.tradingview.com",
    }:{
      autosize:true,width:"100%",height:"100%",symbol:ticker,locale:"en",
      colorTheme:"light",backgroundColor:"#ffffff",chartType:"area",
      isTransparent:false,hideDateRanges:true,dateRanges:["1m|30"],
      symbols:[[ticker,ticker+"|1m"]],valuesTracking:"1",fontSize:"10"
    });
    wrapper.append(widget,credit,script);
    host.appendChild(wrapper);
    };
    // Streamlit observes charts before loading expensive TradingView scripts.
    if(typeof IntersectionObserver==="undefined") mount();
    else {
      observer=new IntersectionObserver(entries=>{
        if(entries.some(item=>item.isIntersecting)){
          mount();observer?.disconnect();
        }
      },{rootMargin:"150px 0px"});
      observer.observe(host);
    }
    return ()=>{observer?.disconnect();host.replaceChildren()};
  },[ticker,full]);
  return <div className={full?"wt-streamlit-advanced-widget":"wt-streamlit-compact-widget"} ref={ref}
    role="region" aria-label={ticker+(full?" full advanced TradingView chart":" compact Streamlit TradingView chart")}/>;
}
export default function WTStreamlitChart({ticker}:{ticker:string}){
 const [open,setOpen]=useState(false);
 return <section className="wt-streamlit-chart" aria-label={ticker+" original Streamlit WT charts"}>
  <div className="wt-streamlit-topbar"><strong>ATTACHED STOCK CHART · {ticker}</strong>
    <button type="button" className="wt-full-chart-button"
      aria-expanded={open} onClick={()=>setOpen(v=>!v)}>
      {open?"HIDE FULL CHART":"FULL CHART"}
    </button></div>
  <Widget ticker={ticker} full={false}/>
  {open&&<div className="wt-streamlit-advanced">
    <div className="wt-streamlit-advanced-head"><strong>{ticker} — FULL TECHNICAL CHART</strong>
      <button type="button" onClick={()=>setOpen(false)}>✕ CLOSE FULL CHART</button></div>
    <p>Candlesticks + Volume + EMA + RSI + MACD. Add other studies and drawings from the TradingView toolbar.</p>
    <Widget ticker={ticker} full={true}/>
  </div>}
  <p className="wt-streamlit-feed-note">External TradingView data may be delayed. Charts are visual references, not broker execution quotes.</p>
 </section>;
}
