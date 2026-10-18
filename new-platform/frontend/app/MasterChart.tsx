"use client";
import { useEffect, useMemo, useState } from "react";

type Technical = {
  benchmarks?: {phase3:boolean;secondFinancing:boolean;bothConfirmed:boolean;warning:string};
  tradeCall?:string; tradeReason?:string;entry?:number|null;entryCoverage?:number;
  exitRisk?:number|null;exitCoverage?:number;entryStatus?:string;exitStatus?:string;
  runwayMonths?:number|null;runwayGate?:string;runwayReason?:string;
  close?:number|null;sma20?:number|null;sma50?:number|null;rsi14?:number|null;
  rvol?:number|null;avgDollarVolume20?:number|null;closingSupport20?:number|null;
  marketDate?:string;eodFresh?:boolean;
  base?:{status:string;support:number|null;resistance:number|null;touches:number|null;widthPct:number|null;contractionRatio:number|null;volumeRatio:number|null;breakoutRvol:number|null};
  macd?:{macd:number|null;signal:number|null;bullish:boolean}|null;
  riskAlerts?:string[];
};
export type ChartRecord = {
  id:string;programId?:string;ticker:string;drug?:string;company?:string;indication?:string;
  nctId?:string;pdufaDate?:string;phase3Status?:string;phase3Date?:string;
  phase3Source?:string;fdaSource?:string;marketCap?:number|null;capInRange?:boolean;
  financingStatus?:string;financingDate?:string;financingSource?:string;
  checkStatus?:string;approvalProbability?:string;pValues?:string;
  membershipStatus?:string;firstFound?:string;lastSeen?:string;technical?:Technical;
};
type History = {id:string;programId?:string;ticker:string;drug:string;enteredOn:string;leftOn:string;reason:string;status:string;cycle:number};
type SourceStatus = {state:string;issues:string[];publishedScan?:{state?:string;complete?:boolean;finishedAt?:string}|null};
type Grade = "pass"|"hold"|"review";
type Item = {label:string;goal:string;actual?:string;grade?:Grade;source?:string};
type Panel = {code:string;title:string;tone:string;items:Item[];head?:string;size?:"compact"|"wide"};

const unavailable = "NOT VERIFIED";
const show = (value?:string|null) => value && value.trim()?value.trim():unavailable;
const count = (value?:number|null,dec=2) => typeof value==="number" && Number.isFinite(value)?value.toFixed(dec):unavailable;
const money = (value?:number|null) => typeof value==="number" && Number.isFinite(value)?"$"+(value>=1e9?(value/1e9).toFixed(2)+"B":value>=1e6?(value/1e6).toFixed(1)+"M":value.toLocaleString("en-US")):unavailable;
const grade = (condition?:boolean|null):Grade => condition==null?"review":condition?"pass":"hold";
const observed = (label:string,goal:string,actual?:string|null,pass?:boolean|null,source?:string):Item=>({label,goal,actual:show(actual),grade:grade(pass),source});
const plain = (label:string,goal:string):Item=>observed(label,goal);
function daysUntil(d?:string){
  if(!d||!/^\d{4}-\d{2}-\d{2}$/.test(d))return null;
  const n=Date.parse(d+"T00:00:00Z"),now=new Date();
  const parts=new Intl.DateTimeFormat("en-US",{timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit"}).formatToParts(now);
  const x=Object.fromEntries(parts.filter(z=>z.type!=="literal").map(z=>[z.type,z.value]));
  const day=Date.parse(x.year+"-"+x.month+"-"+x.day+"T00:00:00Z");
  return Number.isFinite(n)&&Number.isFinite(day)?Math.round((n-day)/86400000):null;
}
function sourceLink(url?:string){return url && /^https:\/\/[^\s]+$/i.test(url)?url:undefined}
function panelRows(row:ChartRecord,history:History[],watch:string[],trade:string[],health?:SourceStatus):Panel[]{
  const t=row.technical, b=t?.base, days=daysUntil(row.pdufaDate);
  const phase=t?.benchmarks?.phase3, financing=t?.benchmarks?.secondFinancing;
  const label=trade.includes(row.programId||"")?"TRADING RESEARCH":watch.includes(row.programId||"")?"WATCH":"WAIT";
  const catalystConfirmed=Boolean(sourceLink(row.fdaSource) && /^VERIFIED/i.test(row.checkStatus||""));
  const runway=t?.runwayMonths;
  const active=history.filter(z=>z.id===row.id);
  const first=active[0],last=active[active.length-1];
  const hasScan=health?.publishedScan?.complete===true;
  const cap=row.marketCap;
  const riskNote=t?.riskAlerts?.length?t.riskAlerts.join("; "):undefined;
  return [
    {code:"A",title:"CLINICAL & FDA ANALYSIS",tone:"blue",items:[
      observed("Phase 3 Primary Endpoint","Successful, verified",show(row.phase3Status),phase==null?null:phase,row.phase3Source),
      plain("Trial Design Quality","Robust, low bias"),
      observed("P-values (Primary)","< 0.05",row.pValues),
      plain("Secondary Endpoints","Positive trend"),
      plain("Safety Profile","Acceptable risk"),
      plain("Efficacy vs. Comparator","≥75% preferred"),
      observed("FDA Approval Probability","≥75% (validated model only)",row.approvalProbability),
      plain("FDA Precedents","Supportive precedents"),
      plain("Manufacturing & CMC","No major issues"),
      plain("Regulatory Risks","Manageable"),
      plain("Competing Drugs","Superior or differentiated"),
      plain("Market Opportunity","Large, growing market")
    ]},
    {code:"B",title:"FINANCIAL & CATALYST ANALYSIS",tone:"green",items:[
      observed("Market Cap","$300M–$10B",money(cap),cap==null?null:row.capInRange),
      observed("Cash Runway","≥12 months",runway==null?t?.runwayGate:count(runway,1)+" months",runway==null?null:runway>=12),
      observed("Financing 1","Verified completed (dated)",t?.benchmarks?.secondFinancing?t?.benchmarks?.warning:undefined),
      observed("Financing 2","Verified completed (dated)",show(row.financingStatus),financing==null?null:financing,row.financingSource),
      plain("Financing Terms","No material anti-dilution"),
      plain("Shelf Registration","≥12 months"),
      plain("Warrant Overhang","Minimal"),
      plain("Debt Obligations","Manageable"),
      observed("Catalyst Date (PDUFA)","30–90 days (focus 30–60)",row.pdufaDate,days==null?null:days>=30&&days<=90,row.fdaSource),
      plain("Catalyst Type","PDUFA / Phase 3 data"),
      observed("Catalyst Timeline","Confirmed date",row.pdufaDate,catalystConfirmed?true:null),
      plain("Probability-weighted Upside","Attractive vs. downside")
    ]},
    {code:"C",title:"TECHNICAL CHART INDICATORS",tone:"purple",items:[
      observed("Price Base (Support/Resistance)","Established base, ≥2 support tests",b?count(b.support)+" / "+count(b.resistance):undefined,b&&b.touches!=null?b.touches>=2:null),
      observed("Volume + RVOL","RVOL ≥1.5× on breakout",t?.rvol==null?undefined:count(t.rvol)+"×",t?.rvol==null?null:t.rvol>=1.5),
      observed("20-day SMA","Price above, rising",t?.sma20==null?undefined:count(t.sma20),t?.close==null||t.sma20==null?null:t.close>t.sma20),
      observed("50-day SMA","Price above, rising",t?.sma50==null?undefined:count(t.sma50),t?.close==null||t.sma50==null?null:t.close>t.sma50),
      plain("ATR (14)","Used for stop placement; OHLC required"),
      plain("Risk / Reward","≥2:1 preferred; verified stop/target"),
      plain("VWAP (Anchored)","Price above VWAP (confirmed)"),
      plain("Relative Strength vs. XBI","Stable or rising"),
      observed("Catalyst Markers","PDUFA + key dates + pre-exit",row.pdufaDate),
      observed("RSI (14)","45–65 preferred (optional)",t?.rsi14==null?undefined:count(t.rsi14,1),t?.rsi14==null?null:t.rsi14>=45&&t.rsi14<=65),
      observed("MACD","Bullish confirmation (optional)",t?.macd==null?undefined:count(t.macd.macd,3)+" / "+count(t.macd.signal,3),t?.macd==null?null:t.macd.bullish)
    ]},
    {code:"D",title:"MARKET PARTICIPATION",tone:"teal",items:[
      observed("Average Daily Dollar Volume","≥$5M preferred",money(t?.avgDollarVolume20),t?.avgDollarVolume20==null?null:t.avgDollarVolume20>=5e6),
      plain("Share Volume","Typically ≥500K shares (context dependent)"),
      plain("Float","Smaller float may increase volatility"),
      plain("Short Interest","≥15% potential squeeze (higher risk)"),
      plain("Days to Cover","≥3 days (context dependent)"),
      plain("Borrow Fee","Elevated fees may signal pressure"),
      plain("Short Availability","Limited availability can increase squeeze"),
      plain("Institutional Ownership","Increasing accumulation"),
      plain("Insider Activity","Recent purchases preferred"),
      plain("Options Market","High implied volatility; inspect open interest"),
      plain("Unusual Options","Investigate significant unusual activity"),
      plain("Sector / Market Conditions","Favorable biotech sector; manageable volatility")
    ]},
    {code:"E",title:"ADDITIONAL ANALYSIS (12 KEY AREAS)",tone:"red",items:[
      plain("Clinical Trial Quality","Strong design, endpoints, statistics, low dropout"),
      plain("FDA Historical Precedents","Favorable outcomes for similar therapies"),
      plain("Competing Drugs","Clear differentiation"),
      plain("True Market Opportunity","Attractive realistic revenue potential"),
      plain("Financing Terms & Hidden Dilution","No material near-term threat"),
      plain("Valuation vs. Catalyst Upside","Attractive probability-weighted upside"),
      plain("Options Market Intelligence","Favorable positioning and liquidity"),
      plain("Borrowing & Short Pressure","Limited shares, higher fees"),
      plain("Sector & Market Conditions","Supportive sector and market"),
      plain("Event & Overnight Gap Risk","Manageable risk; plan for earnings/major events"),
      plain("Portfolio Exposure & Execution","Appropriate size; no slippage or margin overreliance"),
      plain("Historical Trading Performance","Positive win rate, acceptable drawdown")
    ]},
    {code:"F",title:"ENTRY TESTS (6)",tone:"green",items:[
      observed("Price base / breakout","Close above resistance or hold support",b?.status),
      observed("Volume confirmation","RVOL ≥1.5×",t?.rvol==null?undefined:count(t.rvol)+"×",t?.rvol==null?null:t.rvol>=1.5),
      observed("Trend alignment","Price > rising 20 SMA (prefer 50 SMA)",t?.sma20==null?undefined:"20 SMA "+count(t.sma20)),
      plain("Risk / reward","≥2:1"),
      plain("Biotech relative strength","Stable vs. XBI"),
      observed("Catalyst / fundamental","No disqualifying financing or FDA change",t?.benchmarks?.warning,t?.benchmarks?.bothConfirmed??null)
    ]},
    {code:"G",title:"ENTRY SCORE (100 POINTS)",tone:"blue",items:[
      observed("Price structure / base · 30","Breakout or strong support",b?.status),
      observed("Volume confirmation · 25","RVOL ≥1.5×",t?.rvol==null?undefined:count(t.rvol)+"×"),
      plain("Risk / reward setup · 20","≥2:1"),
      observed("SMA / trend alignment · 15","Price > rising 20/50 SMA",t?.entryStatus),
      plain("Relative strength · 10","Stable or rising vs. XBI"),
      observed("Original-system entry /100","Coverage-based, independent model",t?.entry==null?undefined:String(t.entry)+"/100 · coverage "+t.entryCoverage+"/100")
    ]},
    {code:"H",title:"EXIT RULES (Priority Order)",tone:"red",items:[
      observed("Negative FDA/clinical news","Immediate review / exit decision",riskNote),
      plain("Price hits hard stop","Exit per defined stop policy"),
      observed("PDUFA pre-event deadline","Exit before PDUFA (currently −3 days)",days==null?undefined:String(days)+" days remaining",days==null?null:days>3),
      plain("Break of support on high volume","Exit or reduce position"),
      plain("Price reaches R2 target","Take partial profits, manage remainder"),
      plain("Two closes below 20 SMA","Tighten management"),
      plain("RSI or MACD bearish divergence","Warning (not sole exit rule)")
    ]},
    {code:"I",title:"EXIT RISK SCORE (100)",tone:"purple",items:[
      plain("Proximity to stop · 30","Near stop = higher risk"),
      plain("Thesis change · 25","Negative developments"),
      observed("Catalyst countdown · 20","Approaching exit date",days==null?undefined:String(days)+" days"),
      observed("Technical breakdown · 15","Below key support",b?.status),
      observed("Momentum weakness · 10","RSI / MACD warning",t?.rsi14==null?undefined:count(t.rsi14,1)),
      observed("Original-system risk /100","Higher = more observed risk",t?.exitRisk==null?undefined:String(t.exitRisk)+"/100 · coverage "+t.exitCoverage+"/100")
    ]},
    {code:"J",title:"FINAL DECISION (WT)",tone:"green",items:[
      observed("WAIT","More data needed, not ready",label==="WAIT"?label:undefined),
      observed("WATCH","Monitor closely, no position",label==="WATCH"?label:undefined),
      plain("ENTRY REVIEW","Meets criteria; research, NOT trade authorization"),
      observed("HOLD","Position open; follow exit rules",label==="TRADING RESEARCH"?"Research tag only":undefined),
      plain("EXIT REVIEW","Prepare to close position; no orders")
    ]},
    {code:"K",title:"THREE-LEVEL NESTED CLINICAL TRIAL TABLE",tone:"purple",items:[
      observed("Level 1 · Drug / Program","Indication, mechanism, phase, sponsor",row.drug),
      observed("Level 2 · Individual Trials","Trial name, NCT, design, phase, sites, endpoints",row.nctId || (row.id.startsWith("TRIAL|")?row.id.slice(6):undefined)),
      observed("Level 3 · Trial Endpoints","Primary/secondary endpoints, p-values, results",row.phase3Status)
    ]},
    {code:"L",title:"TRACKING & RECORD KEEPING",tone:"green",items:[
      observed("Promotion Date","Record when candidate moves next stage",first?.enteredOn),
      observed("Removal Date","Record date and reason for removal",last?.leftOn),
      observed("Re-entry Date","When re-entered with new evidence",active.find(x=>x.cycle>1)?.enteredOn),
      observed("Status History","Track weekly changes and reasons",last?.status),
      plain("Trade Log","Entry, exit, size, P&L, outcome"),
      observed("Source Verification","Links to FDA, SEC, press releases",row.checkStatus)
    ]},
    {code:"M",title:"HISTORICAL PERFORMANCE ANALYSIS",tone:"blue",items:[
      plain("Win Rate","≥60% (target; not backtested)"),
      plain("Average Gain / Loss","≥20% (target; not backtested)"),
      plain("Maximum Drawdown","≤10% target"),
      plain("False Signals","<15% target"),
      plain("Out-of-Sample Results","Verify robustness"),
      plain("Trading Costs","Include commissions, fees, spreads")
    ]},
    {code:"N",title:"AUTOMATION & MONITORING",tone:"green",items:[
      observed("Nightly Scans","Run at 10 PM Pacific",health?.publishedScan?.finishedAt,hasScan?true:null),
      observed("Missing Data Alerts","Flag unavailable or stale data",health?.issues?.length?health.issues.join("; "):health?.state),
      observed("Source Verification","Confirm daily data with trusted sources",health?.state,health?.state==="COMPLETE_PUBLISHED"?true:null),
      plain("Error Handling","Auto-correct and retry; report failures"),
      plain("Data Integrity","No missing critical fields"),
      plain("Performance Alerts","Track accuracy and results")
    ]},
    {code:"O",title:"EXECUTION & RISK MANAGEMENT",tone:"teal",items:[
      plain("Position Sizing Risk","≤1–2% of portfolio per trade (illustrative)"),
      plain("Maximum Loss","Predefined from a validated stop"),
      observed("Trading Liquidity","≥$5M average daily traded $ volume",t?.avgDollarVolume20==null?undefined:money(t.avgDollarVolume20),t?.avgDollarVolume20==null?null:t.avgDollarVolume20>=5000000),
      plain("Bid/Ask Spread","Narrow relative to position size"),
      plain("Slippage","Estimate expected fill-cost impact"),
      plain("Portfolio Correlation","Avoid concentrated correlated biotech risk")
    ]},
    {code:"P",title:"CANDIDATE STATUS & WEEKLY TRACKING",tone:"purple",items:[
      observed("Date / Ticker","Current selection",(row.programId||"UNREGISTERED")+" · "+row.ticker),
      observed("Stage","Exact published membership",row.membershipStatus),
      observed("Action","Research workflow only",t?.tradeCall||label),
      observed("Reason","Evidence gaps, quality and signals",riskNote||t?.tradeReason),
      observed("Entry Score","Original observed model",t?.entry==null?undefined:String(t.entry)+"/100"),
      observed("Exit Risk Score","Original observed model",t?.exitRisk==null?undefined:String(t.exitRisk)+"/100"),
      observed("Notes / Source","Link available to verify",row.checkStatus)
    ]}
  ];
}

function MatrixPanel({value}:{value:Panel}){
  return <section className={"gold-chart-panel gold-chart-"+value.tone} aria-label={value.title}>
    <header><span className="gold-chart-index">{value.code}</span><strong>{value.code}. {value.title}</strong></header>
    <div className="gold-chart-table-wrap"><table><thead><tr><th>#</th><th>Indicator</th><th className="gold-column">Goal</th><th>Actual</th><th>Status</th><th>Source / Notes</th></tr></thead>
      <tbody>{value.items.map((item,i)=><tr key={value.code+"-"+i}><td>{i+1}</td><td>{item.label}</td><td className="gold-column">{item.goal}</td>
        <td className={item.actual===unavailable||!item.actual?"gold-chart-unknown":"gold-chart-actual"}>{item.actual||unavailable}</td>
        <td><span className={"gold-chart-state state-"+(item.grade||"review")}>{item.grade==="pass"?"PASS":item.grade==="hold"?"HOLD":"REVIEW"}</span></td><td>{sourceLink(item.source)?<a href={item.source} target="_blank" rel="noopener noreferrer">Verify source ↗</a>:<span className="gold-chart-unknown">SOURCE NOT PROVIDED</span>}</td></tr>)}</tbody>
    </table></div>
  </section>;
}
const stages=[
  {name:"PIPELINE",tone:"blue",heading:"DISCOVER & RESEARCH",bullets:["Find biotech with Phase 3 / registered trials","Evaluate clinical, market & FDA catalysts","Apply market cap $300M–$10B","Collect trial, drug, company information","Track all candidates"],goal:"High-Quality Phase 3 Pipeline"},
  {name:"GEM JR",tone:"green",heading:"DEVELOPING OPPORTUNITIES",bullets:["Strong Phase 3 data and improving profile","Verify post-Phase-3 financing","Evaluate remaining upside and catalyst timing","Track key indicators and monitor progress","Candidates can advance or be removed"],goal:"Qualified, High-Conviction Candidates"},
  {name:"GEM",tone:"purple",heading:"QUALIFIED RESEARCH",bullets:["Successful, exact-program Phase 3 and two verified closes","Independent evidence and entry gates","Identify entry, stop and target levels","Full analysis of upside, risk and market conditions","Prepare for WT research decision"],goal:"Best Risk-Reward GEM Candidates"},
  {name:"WT",tone:"red",heading:"WATCHLIST & TRADING DECISION",bullets:["Final analysis and trade decision research","WAIT / WATCH / ENTRY REVIEW / HOLD / EXIT REVIEW","Monitor until pre-catalyst exit","Track position, P&L and outcome when available","Re-enter only with new evidence"],goal:"Disciplined Trading Decisions"}
];
export default function MasterChart({records,gemJr,gem,history=[],watch,trade,sourceHealth,asOf,selectedId,onSelect,onInspect}:{records:ChartRecord[];gemJr:ChartRecord[];gem:ChartRecord[];history?:History[];watch:string[];trade:string[];sourceHealth?:SourceStatus;asOf:string;selectedId:string;onSelect:(id:string)=>void;onInspect?:(r:ChartRecord)=>void}){
  const [view,setView]=useState<"poster"|"readable">("poster");
  const [filter,setFilter]=useState("");
  // Phone/tablet default: fit chart panels to the viewport.
  // Users can still explicitly choose the wide reference poster.
  useEffect(() => {
    if (window.matchMedia("(max-width: 900px)").matches) setView("readable");
  }, []);
  const catalog=useMemo(()=>{
    const cache=new Map<string,ChartRecord>();
    for(const item of [...gem,...gemJr,...records.filter(r=>r.id.startsWith("APPLICATION|"))])if(!cache.has(item.id))cache.set(item.id,item);
    return [...cache.values()].sort((a,b)=>a.ticker.localeCompare(b.ticker)||a.id.localeCompare(b.id));
  },[gem,gemJr,records]);
  const selected=catalog.find(x=>x.id===selectedId)||catalog[0];
  const options=catalog.filter(x=>!filter||[x.ticker,x.drug,x.id].some(v=>v?.toLowerCase().includes(filter.toLowerCase()))).slice(0,150);
  const panels=useMemo(()=>selected?panelRows(selected,history,watch,trade,sourceHealth):[],[selected,history,watch,trade,sourceHealth]);
  return <div className="gold-master-container">
    <div className="gold-control-bar"><div><h2>MASTER REFERENCE CHART · PICTURE LAYOUT</h2>
      <p>Gold goals beside actual sourced observations and explicit PASS / HOLD / REVIEW</p></div>
      <div className="gold-selectors"><label>Find ticker / exact program<input value={filter} onChange={e=>setFilter(e.target.value)} placeholder="Ticker or drug"/></label>
      <label>Selected program<select value={selected?.id||""} onChange={e=>onSelect(e.target.value)}>
        {selected&&!options.some(o=>o.id===selected.id)&&<option value={selected.id}>{selected.programId||"NOT REGISTERED"} · {selected.ticker} — {selected.drug||selected.id}</option>}
        {options.map(r=><option key={r.id} value={r.id}>{r.programId||"NOT REGISTERED"} · {r.ticker} — {r.drug||r.id} ({r.id.startsWith("TRIAL|")?"TRIAL":"APPLICATION"})</option>)}
      </select></label></div>
      <div className="gold-view-buttons">{selected?.programId && onInspect && <button type="button" onClick={()=>onInspect(selected)}>Open exact program checklist ↗</button>}<button type="button" className={view==="poster"?"chosen":""} onClick={()=>setView("poster")}>Full picture layout</button>
        <button type="button" className={view==="readable"?"chosen":""} onClick={()=>setView("readable")}>Readable mobile</button></div>
    </div>
    <div className="gold-reference-scroller">
      <div className={"gold-master-poster "+(view==="readable"?"gold-master-readable":"")}>
        <header className="gold-master-banner">
          <span className="gold-bullseye">◎</span>
          <div><h2>PDUFA COMMAND CENTER — COMPLETE MASTER ANALYSIS & TRADING DECISION SYSTEM</h2>
            <p>Goals · Actual Results · Indicator Targets · Research Scoring · Final Decision Framework</p></div>
        </header>
        <div className="gold-overall-goal"><strong>OVERALL GOAL</strong><span>Find high-potential biotech stocks with strong Phase 3 evidence and upcoming FDA catalysts. Research PIPELINE → GEM JR → GEM → WT using clinical, financial, technical, market and risk analysis while preserving capital.</span><strong>10:00 PM PT · original scans</strong></div>
        <section className="gold-stage-flow">{stages.map((s,i)=><div className={"gold-stage-wrap "+s.tone} key={s.name}>
          <div className="gold-stage-box"><h3><span className="gold-stage-number">{i+1}</span>{s.name} <small>— {s.heading}</small></h3>
          <ul>{s.bullets.map(v=><li key={v}>{v}</li>)}</ul><p className="gold-stage-goal"><strong>GOAL:</strong> {s.goal}</p></div>
          {i<3&&<span className="gold-stage-arrow" aria-hidden="true">➜</span>}
        </div>)}</section>
        <div className="gold-selected-strip"><strong>PROGRAM: {selected?.ticker||"—"} — {selected?.drug||"Not selected"}</strong>
          <span><strong className="permanent-id">{selected?.programId||"NO PERMANENT ID"}</strong> · {selected?.id||"No exact program"} · Published {asOf}</span><strong>{sourceHealth?.state||"SOURCE UNKNOWN"}</strong></div>
        <div className="gold-matrix-five">{panels.slice(0,5).map(p=><MatrixPanel key={p.code} value={p}/>)}</div>
        <div className="gold-matrix-five gold-matrix-second">{panels.slice(5,10).map(p=><MatrixPanel key={p.code} value={p}/>)}</div>
        <div className="gold-matrix-five gold-matrix-third">{panels.slice(10).map(p=><MatrixPanel key={p.code} value={p}/>)}</div>
        <div className="gold-master-bottom"><span>✓ Exact-program data</span><span>✓ Gold goals</span><span>✓ Dual GEM JR / GEM</span><span>✓ Provenance checks</span><span>✓ Original scanner preservation</span></div>
        <footer className="gold-master-footer"><strong>DISCIPLINE + DATA + DILIGENCE = CONSISTENT SUCCESS</strong><small>Research only — no trading orders · Missing data never equals PASS · Original scanner: {sourceHealth?.publishedScan?.state||"NOT VERIFIED"}</small></footer>
      </div>
    </div>
    <p className="gold-master-caveat">This is an interactive recreation of the gold reference picture, not a replacement for source verification. Goal thresholds from the reference are targets, not validated trading returns. Blank indicators are labeled NOT VERIFIED; the historical benchmark and order systems remain unchanged.</p>
    {selected&&<div className="gold-reference-links">
      {sourceLink(selected.phase3Source)&&<a href={selected.phase3Source} target="_blank" rel="noopener noreferrer">Phase 3 source ↗</a>}
      {sourceLink(selected.financingSource)&&<a href={selected.financingSource} target="_blank" rel="noopener noreferrer">SEC financing source ↗</a>}
      {sourceLink(selected.fdaSource)&&<a href={selected.fdaSource} target="_blank" rel="noopener noreferrer">FDA source ↗</a>}
    </div>}
  </div>;
}
