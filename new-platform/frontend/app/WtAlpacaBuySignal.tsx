"use client";

import type {WtAlpacaTechnicalSignal} from "../lib/wt-alpaca-buy-signal";

function dollars(value:number|null){
  return value===null?"—":"$"+value.toFixed(2);
}

/** Research result only: NEVER an E*TRADE authorization or Alpaca brokerage order. */
export default function WtAlpacaBuySignal({
  signal,
}:{signal:WtAlpacaTechnicalSignal}){
  const ready=signal.status==="BUY_SETUP";
  const block=signal.pdufaGate!=="OUTSIDE_BLACKOUT";
  const title=ready?"BUY SETUP — TECHNICAL ONLY":
    signal.status==="WAIT"?"WAIT — TECHNICAL CHECKS NOT MET":"UNAVAILABLE — NO VERIFIED TECHNICAL SIGNAL";
  const background=ready?"#e8f8ed":signal.status==="WAIT"?"#fff8e8":"#f3f4f6";
  return <section aria-label={signal.ticker+" Alpaca technical buy signal"} data-wt-alpaca-technical-signal="read-only"
    style={{border:"1px solid #acc7b8",background,borderRadius:9,padding:12,margin:"14px 0"}}>
    <h4 style={{margin:"0 0 6px"}}>{title}</h4>
    <p style={{fontSize:13,margin:"0 0 8px"}}>
      <strong>Alpaca completed-session signal:</strong> {signal.asOf||"NOT VERIFIED"} ·
      {signal.feed?" "+signal.feed+" daily bars":" no valid source"} ·
      {signal.passed}/{signal.total} measurable criteria passed.
      {" "}A BUY setup is <strong>not a live buy authorization or approved trade</strong>.
    </p>
    <p style={{fontSize:13,margin:"0 0 8px"}}>{signal.reason}</p>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(145px,1fr))",gap:8,fontSize:13}}>
      <div><small>Technical entry reference</small><div><strong>{dollars(signal.triggerReference)}</strong></div></div>
      <div><small>Illustrative risk-stop reference</small><div><strong>{dollars(signal.riskStopReference)}</strong></div></div>
      <div><small>Recorded PDUFA countdown</small><div><strong>{signal.pdufaDays===null?"UNVERIFIED":signal.pdufaDays+" days"}</strong></div></div>
      <div><small>New-buy permission</small><div><strong>BLOCKED — NO BROKER ORDERS</strong></div></div>
    </div>
    {block&&<p role="note" style={{fontSize:13,margin:"8px 0",fontWeight:650}}>
      {signal.pdufaGate==="PRE_PDUFA_BLACKOUT"?
        "PDUFA ENTRY HOLD: Inside the standing 14-day pre-decision no-new-buy window.":
        signal.pdufaGate==="PAST_TARGET"?
        "PDUFA ENTRY HOLD: Recorded decision date has passed; outcome must be checked.":
        "PDUFA ENTRY HOLD: Exact program PDUFA date is not established."}
    </p>}
    <details style={{marginTop:10}}>
      <summary style={{cursor:"pointer",fontWeight:600}}>Show all eight Alpaca technical checks and thresholds</summary>
      {signal.checks.length>0?<div style={{overflowX:"auto",marginTop:8}}>
        <table style={{width:"100%",borderCollapse:"collapse",fontSize:12}}>
          <thead><tr><th style={{textAlign:"left"}}>Check</th><th style={{textAlign:"left"}}>Measured</th>
            <th style={{textAlign:"left"}}>Required</th><th style={{textAlign:"left"}}>Result</th></tr></thead>
          <tbody>{signal.checks.map(check=><tr key={check.key} style={{borderTop:"1px solid #d0dfe0"}}>
            <td style={{padding:"6px 4px"}}>{check.label}</td>
            <td style={{padding:"6px 4px"}}>{check.measured}</td>
            <td style={{padding:"6px 4px"}}>{check.required}</td>
            <td style={{padding:"6px 4px"}}><strong>{check.passed?"PASS":"WAIT"}</strong></td>
          </tr>)}</tbody>
        </table>
      </div>:<p>No trustworthy Alpaca history is available for these technical calculations.</p>}
    </details>
    <p style={{fontSize:11,margin:"8px 0 0"}}>Model WT_EOD_TECHNICAL_V1_UNBACKTESTED ·
      {signal.feed==="IEX"?" IEX covers only one exchange, not consolidated volume. ":" "}
      Anchored VWAP, XBI-relative strength, clinical approval odds, fresh SEC financing and cash-runway clearance
      are not verified by this eight-check model. Neither a technical BUY setup nor this page submits an order.
      Reference prices are historical calculations, <strong>not</strong> a real-time executable E*TRADE quote.</p>
  </section>;
}
