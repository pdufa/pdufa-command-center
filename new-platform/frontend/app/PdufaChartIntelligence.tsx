"use client";

/**
 * Seven independently selectable PDUFA chart research overlays.
 * This is display-only and never converts a target date, parent NDA supplement
 * status, unvalidated RAAS metric, or missing data into a final FDA outcome.
 */
import { useEffect, useMemo, useState } from "react";
import type { FdaMilestone } from "./AlpacaStockChart";

export const PDUFA_FEATURE_OPTIONS = [
  { id: "countdown", label: "PDUFA countdown & warning windows", short: "Countdown" },
  { id: "decision", label: "Verified FDA decision tracker", short: "Decision" },
  { id: "date-history", label: "PDUFA deadline-change history", short: "Date history" },
  { id: "review-progress", label: "FDA review progress", short: "Review" },
  { id: "safety", label: "Manufacturing & safety risk flags", short: "Safety / CMC" },
  { id: "raas-snapshot", label: "Frozen RAAS prediction snapshot", short: "RAAS" },
  { id: "market-reaction", label: "Post-decision stock reaction", short: "Price reaction" }
] as const;

export type PdufaFeatureId = typeof PDUFA_FEATURE_OPTIONS[number]["id"];

export type PdufaVerifiedTargetOutcome = {
  date: string;
  outcome: "APPROVED" | "COMPLETE_RESPONSE_LETTER" | "WITHDRAWN";
  source: string;
  exactApplicationMatch: true;
};
export type RaasFrozenSnapshot = {
  capturedAt: string;
  score: number;
  modelVersion: string;
  source: string;
  exactProgramId: string;
  frozen: true;
};
export type ChartBar = {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
};

const DAYS = 86400000;
function isoTodayEastern(): string {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York", year:"numeric",month:"2-digit",day:"2-digit"
  }).formatToParts(new Date());
  const part = (name: string) => parts.find(p=>p.type===name)?.value||"";
  return part("year")+"-"+part("month")+"-"+part("day");
}
function daysBetween(a:string,b:string):number {
  return Math.round((Date.parse(b+"T00:00:00Z") - Date.parse(a+"T00:00:00Z"))/DAYS);
}
function chartCardStyle():React.CSSProperties {
  return {
    background:"#fff",color:"#263647",border:"1px solid #c8d8e4",
    borderRadius:9,padding:12,minWidth:0
  };
}
const muted:React.CSSProperties={fontSize:12,color:"#516277",lineHeight:1.5};
const strongestSource=(events:readonly FdaMilestone[],id:string)=>
  events.find(e=>e.id===id&&Boolean(e.source));
const isMeaningful=(d:unknown):d is string=>
  typeof d==="string"&&/^\d{4}-\d{2}-\d{2}$/.test(d)&&Number.isFinite(Date.parse(d+"T00:00:00Z"));
const isMatchedOutcome=(o:PdufaVerifiedTargetOutcome|undefined):o is PdufaVerifiedTargetOutcome=>
  Boolean(o&&o.exactApplicationMatch===true&&isMeaningful(o.date)&&
    /^https:\/\//.test(o.source)&&
    ["APPROVED","COMPLETE_RESPONSE_LETTER","WITHDRAWN"].includes(o.outcome));

export default function PdufaChartIntelligence({
  programId,ticker,enabledFeatures,officialEvents,bars=[],marketStatus,
  verifiedTargetOutcome,raasSnapshot
}:{
  programId:string;ticker:string;enabledFeatures:readonly string[];
  officialEvents:readonly FdaMilestone[];bars?:readonly ChartBar[];
  marketStatus?:string;verifiedTargetOutcome?:PdufaVerifiedTargetOutcome;
  raasSnapshot?:RaasFrozenSnapshot;
}) {
  const [today,setToday]=useState<string|null>(null);
  const [reactionSessions,setReactionSessions]=useState<1|3|5>(3);
  useEffect(()=>setToday(isoTodayEastern()),[]);
  const selected=(name:PdufaFeatureId)=>enabledFeatures.includes(name);
  const target=strongestSource(officialEvents,"verified-cytk-2026-pdufa")||
    officialEvents.find(e=>e.planned&&isMeaningful(e.date)&&Boolean(e.source));
  const actualOutcome=isMatchedOutcome(verifiedTargetOutcome)?verifiedTargetOutcome:undefined;
  const days=target&&today?daysBetween(today,target.date):null;
  const warning=days===null?"Date pending":days<0?"Target date has passed — verify the actual FDA action":
    days===0?"Target date today — no FDA decision implied":
    days<=1?"Within 1-day warning window":days<=3?"Within 3-day warning window":
    days<=7?"Within 7-day warning window":days<=14?"Within 14-day warning window":
    days<=30?"Within 30-day warning window":"Outside the 30-day warning window";
  const accepted=strongestSource(officialEvents,"verified-cytk-2026-snda");
  const trialDisclosure=strongestSource(officialEvents,"verified-cytk-2026-maple-data");
  const raasVerified=raasSnapshot&&raasSnapshot.frozen===true&&
    raasSnapshot.exactProgramId===programId&&
    Number.isFinite(raasSnapshot.score)&&raasSnapshot.score>=0&&raasSnapshot.score<=100&&
    /^https:\/\//.test(raasSnapshot.source);
  const prices=useMemo(()=>[...bars].filter(b=>isMeaningful(b.date)&&
    Number.isFinite(b.close)&&b.close>0).sort((a,b)=>a.date.localeCompare(b.date)),[bars]);
  const reaction=useMemo(()=>{
    if(!actualOutcome||prices.length===0)return null;
    const before=[...prices].filter(b=>b.date<actualOutcome.date).at(-1);
    const post=prices.filter(b=>b.date>actualOutcome.date);
    const after=post[reactionSessions-1];
    if(!before||!after)return null;
    return {before,after,delta:100*(after.close/before.close-1)};
  },[prices,actualOutcome,reactionSessions]);
  if(!enabledFeatures.length)return null;
  return <div data-pdufa-chart-intelligence={programId}
    style={{padding:"12px",borderTop:"1px solid #d4e1ed",background:"#f5f9fc"}}>
    <div style={{display:"flex",alignItems:"center",gap:8,justifyContent:"space-between",flexWrap:"wrap",marginBottom:11}}>
      <strong style={{fontSize:14}}>PDUFA CHART INTELLIGENCE · {ticker}</strong>
      <span style={{fontSize:12,color:"#526477"}}>{enabledFeatures.length} of 7 sections enabled</span>
    </div>
    <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(240px,1fr))",gap:10}}>
    {selected("countdown")&&<section style={chartCardStyle()} aria-label="PDUFA countdown">
      <strong>1 · PDUFA countdown & alerts</strong>
      <p style={{margin:"8px 0",fontSize:20,fontWeight:800,color:"#1d4660"}}>
        {target&&days!==null?days>=0?days+" calendar days":Math.abs(days)+" days after target":"Target date pending"}
      </p>
      <p style={{...muted,margin:"5px 0"}}>{target?"Sourced target: "+target.date:"No verified target date"}</p>
      <p style={{...muted,fontWeight:700,margin:"6px 0"}}>{warning}</p>
      <small style={{color:"#53677b"}}>On-chart warning windows: 30 · 14 · 7 · 3 · 1 days. No push or email notification is sent.</small>
    </section>}
    {selected("decision")&&<section style={chartCardStyle()} aria-label="FDA decision tracker">
      <strong>2 · Verified FDA decision</strong>
      {actualOutcome?<>
        <p style={{margin:"9px 0",fontWeight:750}}>{actualOutcome.outcome.replaceAll("_"," ")} · {actualOutcome.date}</p>
        <a target="_blank" rel="noopener noreferrer" href={actualOutcome.source}>Original FDA action evidence</a>
      </>:<>
        <p style={{margin:"9px 0",fontWeight:750}}>Awaiting source-verified MAPLE-HCM FDA decision</p>
        <p style={muted}>The original MYQORZO approval and other parent-NDA supplement records are not counted as the decision on this target application. A passed PDUFA date alone is not a CRL or extension.</p>
      </>}
    </section>}
    {selected("date-history")&&<section style={chartCardStyle()} aria-label="PDUFA deadline change history">
      <strong>3 · Deadline-change history</strong>
      <p style={{margin:"9px 0 5px"}}><strong>Recorded target:</strong> {target?.date||"Not available"}</p>
      {target?.source&&<p style={{...muted,margin:"0 0 6px"}}><a href={target.source} target="_blank" rel="noopener noreferrer">Original target-date source</a></p>}
      <p style={muted}>No separately documented revision to this exact supplemental review's target date is currently integrated. An edited chart date does not alter the authoritative target or create an extension.</p>
    </section>}
    {selected("review-progress")&&<section style={chartCardStyle()} aria-label="FDA review progress">
      <strong>4 · FDA review progress</strong>
      <div style={{fontSize:13,marginTop:8,lineHeight:1.7}}>
        <div>{accepted?"✓":"○"} Filing acceptance disclosed: {accepted?.date||"No connected evidence"}</div>
        <div>{trialDisclosure?"✓":"○"} Additional trial data disclosed: {trialDisclosure?.date||"No connected evidence"}</div>
        <div>○ Current supplemental review conclusion: {actualOutcome?"FDA action verified":"Awaiting verification"}</div>
      </div>
      <p style={muted}>Only disclosed steps are shown. FDA's internal review percentage is not observable from these events.</p>
    </section>}
    {selected("safety")&&<section style={chartCardStyle()} aria-label="Manufacturing and safety">
      <strong>5 · Manufacturing & safety flags</strong>
      <p style={{margin:"9px 0",fontWeight:700}}>No current application-specific CMC or inspection finding verified in connected chart evidence</p>
      <p style={muted}>This is an evidence gap, <strong>not a safety clearance</strong>. Original product labeling and REMS history must not be presented as a new finding against the supplemental review.</p>
    </section>}
    {selected("raas-snapshot")&&<section style={chartCardStyle()} aria-label="RAAS prediction snapshot">
      <strong>6 · Frozen RAAS prediction snapshot</strong>
      {raasVerified&&raasSnapshot?<>
        <p style={{margin:"9px 0",fontSize:19,fontWeight:800}}>{raasSnapshot.score}/100</p>
        <p style={muted}>Frozen {raasSnapshot.capturedAt} · Model {raasSnapshot.modelVersion}</p>
        <a href={raasSnapshot.source} target="_blank" rel="noopener noreferrer">Frozen score evidence</a>
      </>:<>
        <p style={{margin:"9px 0",fontWeight:700}}>No validated, frozen pre-decision RAAS snapshot linked to {programId}</p>
        <p style={muted}>Do not substitute candidate-assessment scores, partial timing metrics, or post-decision ratings for a historical forecast.</p>
        <a href="/raas-worklist">Review RAAS evidence worklist</a>
      </>}
    </section>}
    {selected("market-reaction")&&<section style={chartCardStyle()} aria-label="FDA decision stock reaction">
      <strong>7 · Post-decision market reaction</strong>
      <div style={{display:"flex",gap:6,marginTop:9,flexWrap:"wrap"}}>
        {([1,3,5] as const).map(n=><button type="button" key={n}
          aria-pressed={reactionSessions===n} onClick={()=>setReactionSessions(n)}
          style={{padding:"6px 9px",borderRadius:6,fontSize:12,border:"1px solid #a4b7c6",
            background:reactionSessions===n?"#dcecfb":"white",color:"#24415a",fontWeight:700}}>
          {n} session{n>1?"s":""}
        </button>)}
      </div>
      {reaction?<>
        <p style={{fontSize:19,fontWeight:800,margin:"8px 0"}}>{reaction.delta>=0?"+":""}{reaction.delta.toFixed(2)}%</p>
        <p style={muted}>Prior close: {reaction.before.date} · ${reaction.before.close.toFixed(2)}.
          After {reactionSessions} trading session{reactionSessions>1?"s":""}: {reaction.after.date} · ${reaction.after.close.toFixed(2)}.</p>
        <small style={{color:"#53677b"}}>Unadjusted Alpaca closing prices, excluding dividends/corporate action adjustments unless provided by the feed.</small>
      </>:<p style={{...muted,margin:"8px 0"}}>
        {!actualOutcome?"Awaiting a verified FDA action tied to the exact supplemental application.":
          marketStatus!=="OK"?"Awaiting authenticated Alpaca market bars.":
          "Insufficient before/after Alpaca trading sessions in the chosen chart range."}
        {" "}No synthetic price reaction is calculated.
      </p>}
      <p style={{...muted,marginBottom:0}}>Use the chart's ALL range for historical comparison when a verified decision becomes available.</p>
    </section>}
    </div>
    <p style={{fontSize:11,color:"#65768a",margin:"10px 0 0"}}>
      Research display only. Enabled overlays do not imply that FDA evidence or a validated RAAS score exists.
      The underlying FDA records and historical prediction evidence cannot be edited here.
    </p>
  </div>;
}
