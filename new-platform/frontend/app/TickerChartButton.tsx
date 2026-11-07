"use client";

import {useEffect, useRef, useState} from "react";
import {createPortal} from "react-dom";
import AlpacaStockChart from "./AlpacaStockChart";

const validTicker=(value:string)=>/^[A-Z][A-Z0-9.-]{0,12}$/.test(value);

/** Ticker and Ⓒ stay in the same table cell. A portal avoids sticky-column clipping. */
export default function TickerChartButton({ticker,programId}:{ticker:string;programId?:string}){
 const symbol=ticker.trim().toUpperCase();
 const [open,setOpen]=useState(false);
 const [mounted,setMounted]=useState(false);
 const button=useRef<HTMLButtonElement>(null);
 const close=()=>setOpen(false);
 useEffect(()=>setMounted(true),[]);
 useEffect(()=>{
  if(!open)return;
  const previous=document.body.style.overflow;
  document.body.style.overflow="hidden";
  const onKey=(event:KeyboardEvent)=>{if(event.key==="Escape")close()};
  document.addEventListener("keydown",onKey);
  return()=>{document.body.style.overflow=previous;document.removeEventListener("keydown",onKey);button.current?.focus()};
 },[open]);
 return <>
  <span style={{display:"inline-flex",alignItems:"center",gap:5,whiteSpace:"nowrap"}}>
   <span>{ticker.trim()||"Not verified"}</span>
   {validTicker(symbol)&&<button ref={button} type="button" aria-haspopup="dialog"
     aria-label={"Open full Alpaca chart for "+symbol} title={"Open Alpaca chart for "+symbol}
     onClick={()=>setOpen(true)}
     style={{display:"inline-flex",alignItems:"center",justifyContent:"center",
       width:25,height:25,minWidth:25,borderRadius:"50%",border:"1.5px solid #157358",
       background:"#fff",color:"#0d634c",fontSize:15,fontWeight:800,cursor:"pointer",
       padding:0,lineHeight:1}}>C</button>}
  </span>
  {mounted&&open&&createPortal(
   <div role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)close()}}
     style={{position:"fixed",inset:0,zIndex:10000,background:"rgba(8,20,31,.78)",
       display:"flex",alignItems:"center",justifyContent:"center",padding:8}}>
    <section role="dialog" aria-modal="true" aria-label={symbol+" full Alpaca stock chart"}
      style={{width:"100%",maxWidth:1450,maxHeight:"calc(100dvh - 16px)",minHeight:"min(600px,90dvh)",
        display:"flex",flexDirection:"column",background:"#fff",color:"#172d3d",
        borderRadius:12,boxShadow:"0 14px 55px #0007",overflow:"hidden"}}>
     <header style={{display:"flex",alignItems:"center",justifyContent:"space-between",
       gap:8,padding:"12px 14px",background:"#103a31",color:"#fff",flexShrink:0}}>
      <div style={{minWidth:0}}><strong style={{fontSize:17}}>{symbol} · Full Alpaca chart</strong>
       <div style={{fontSize:11,opacity:.85}}>In-page popup · No new browser window</div></div>
      <button type="button" onClick={close} autoFocus aria-label={"Close "+symbol+" chart"}
       style={{width:44,height:44,border:0,borderRadius:8,cursor:"pointer",color:"#153a30",
         background:"#fff",fontSize:23,fontWeight:700,flexShrink:0}}>×</button>
     </header>
     <div style={{overflowY:"auto",overscrollBehavior:"contain",flex:1,padding:"8px 10px 18px"}}>
      <AlpacaStockChart ticker={symbol} programId={programId}/>
      {!programId&&<p style={{fontSize:12,color:"#526477",margin:"10px 6px 0"}}>
       FDA/PDUFA markers are shown only after this exact trial is linked to a verified
       registered program. The stock chart is ticker-based; no milestones are invented.
      </p>}
     </div>
    </section>
   </div>,document.body)}
 </>;
}
