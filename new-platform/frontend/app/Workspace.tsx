"use client";

import { Fragment, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import MasterChart from "./MasterChart";
import AlpacaStockChart from "./AlpacaStockChart";
import EntrySignal from "./EntrySignal";
import IndicatorParityTables from "./IndicatorParityTables";
import FullTrialDownload from "./FullTrialDownload";
import PublishedScansPanel from "./PublishedScansPanel";
import PipelineData from "./PipelineData";
import TrialQualificationFilters from "./TrialQualificationFilters";
import TrialFields from "./TrialFields";
import GemQualificationChecklist, {type GemScanResult} from "./GemQualificationChecklist";
import { filterPipelineRows, pipelineAvailability, PIPELINE_STAGES as STAGES, trialId } from "../lib/pipeline-data";
import { activeTrialFilters, EMPTY_TRIAL_FILTERS, trialFilterSummary, type TrialFilterFacts, type TrialFilterValues } from "../lib/trial-filters";

type Stage = "PIPELINE" | "GEM_JR" | "GEM";
type Factor = { label: string; weight: number; earned: number | null; evidence: string };
type ResearchTechnical = {
  benchmarks?: { phase3: boolean; secondFinancing: boolean; bothConfirmed: boolean; warning: string; readoutDate: string; firstClose: string; secondClose: string };
  tradeCall?: string; tradeReason?: string;
  marketDate?: string; marketSource?: string; eodFresh?: boolean;
  chartBars?: {date:string;close:number;volume:number}[];
  close?: number | null; sma20?: number | null; sma50?: number | null;
  rsi14?: number | null; rvol?: number | null; avgDollarVolume20?: number | null;
  closingSupport20?: number | null; macd?: { macd: number | null; signal: number | null; bullish: boolean } | null;
  base?: { status: string; support: number | null; resistance: number | null; touches: number | null; widthPct: number | null; contractionRatio: number | null; volumeRatio: number | null; breakoutRvol: number | null };
  indicatorEntry?: number | null; indicatorEntryCoverage?: number; indicatorEntryObservedPoints?: number; indicatorExitRisk?: number | null; indicatorExitCoverage?: number; indicatorExitObservedPoints?: number; indicatorEntryFactors?: Factor[]; indicatorExitFactors?: Factor[]; indicatorDisclaimer?: string; indicatorModel?: string;
  dataGaps?: string; entry?: number | null; entryCoverage?: number; entryStatus?: string;
  exitRisk?: number | null; exitCoverage?: number; exitStatus?: string;
  entryFactors?: Factor[]; exitFactors?: Factor[];
  runwayMonths?: number | null; runwayGate?: string; runwayReason?: string; runwaySource?: string; runwayAsOf?: string;
  riskAlerts?: string[]; researchOnly?: boolean;
};

export type Candidate = {
  id: string; programId?: string; eventKey?: string; ticker: string; company?: string;
  drug?: string; indication?: string; nctId?: string; pdufaDate?: string;
  priorityReview?: {status: string; source?: string; designationDate?: string};
  phase3Date?: string; phase3Status?: string; phase3Source?: string;
  stage?: string; outcome?: string; marketCap?: number | null; capInRange?: boolean;
  capChecked?: string; capSource?: string; financingStatus?: string; financingDate?: string;
  financingSource?: string; financingEvidence?: string; fdaSource?: string;
  lastChecked?: string; approvalProbability?: string; checkStatus?: string;
  pValues?: string; evidenceSummary?: string; signal?: string;
  membershipStatus?: string; firstFound?: string; lastSeen?: string; candidateLinked?: boolean;
  listAddedOn?: string; listRemovedOn?: string;
  technical?: ResearchTechnical;
  trialFilters?: TrialFilterFacts;
};
type StageHistory = { id: string; programId?: string; ticker: string; drug: string; enteredOn: string; leftOn: string; reason: string; status: string; cycle: number };
type StageData = { asOf?: string; rows: Candidate[]; history?: StageHistory[] };
type Snapshot = {
  mode: string; asOf: string; disclaimer: string;
  marketCapRange: { min: number; max: number };
  pipeline: Candidate[]; members: { GEM_JR: StageData; GEM: StageData };
  trialFilterSchema?: number;
  sourceHealth?: { state: string; issues: string[]; clinicalRows: number; regulatoryRows: number; pipelineSourceParity?: {exactPrograms:number;clinicalAndResults:number;regulatoryPrograms:number;comparison:string}; publishedScan?: { state?: string; finishedAt?: string; complete?: boolean; sources?: Record<string,{status?:string;finished_at?:string}> } | null };
};
type Nav = "PIPELINE" | "GEM_JR" | "GEM" | "MASTER" | "SCANS" | "WT";
type TopNav = "PDUFA" | "CALENDAR";
type Tags = { watch: string[]; trade: string[] };
type PipelineSelection = { stages: string[]; dates: string[]; query: string; onlyBand: boolean; trial: TrialFilterValues; asOf?: string };
const TAG_KEY = "pdufa_new_program_watch_trade_v1";
const LEGACY_TAG_KEY = "pdufa_new_watch_trade_v1";
const BANDS = ["0–30 DAYS", "31–60 DAYS", "61–90 DAYS", "+90 DAYS", "NO PDUFA YET", "PAST / RECHECK"];

function dateTodayPT() {
  const x = new Intl.DateTimeFormat("en-US", { timeZone: "America/Los_Angeles", year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date());
  const parts = Object.fromEntries(x.filter(part => part.type !== "literal").map(part => [part.type, part.value]));
  return parts.year + "-" + parts.month + "-" + parts.day;
}
function daysAway(raw?: string) {
  if (!raw || !/^\d{4}-\d{2}-\d{2}$/.test(raw.slice(0, 10))) return null;
  const d = Date.parse(raw.slice(0, 10) + "T00:00:00Z");
  const today = Date.parse(dateTodayPT() + "T00:00:00Z");
  const n = Math.round((d - today) / 86400000);
  return Number.isFinite(n) ? n : null;
}
function dateBand(c: Candidate) {
  const n = daysAway(c.pdufaDate);
  if (n === null) return "NO PDUFA YET";
  return n < 0 ? "PAST / RECHECK" : n <= 30 ? "0–30 DAYS" : n <= 60 ? "31–60 DAYS" : n <= 90 ? "61–90 DAYS" : "+90 DAYS";
}
function money(value?: number | null) {
  return value == null ? "NOT VERIFIED" : "$" + (value >= 1e9 ? (value / 1e9).toFixed(2) + "B" : (value / 1e6).toFixed(0) + "M");
}
function stated(value?: string | null, fallback = "NOT VERIFIED") {
  return value && value.trim() ? value.trim() : fallback;
}
function evidence(url?: string) { return url && /^https:\/\/[^\s]+$/.test(url) ? url : undefined; }
function trialSheetUrl(record: Candidate) {
  const nct = trialId(record);
  return nct ? "/trial/" + encodeURIComponent(nct) : "";
}
function uniqueRows(rows: Candidate[]) {
  const seen = new Set<string>();
  return rows.filter(row => { if (!row.id || seen.has(row.id)) return false; seen.add(row.id); return true; });
}
function scoreNum(number?: number | null, digits = 2, suffix = "") {
  return typeof number === "number" && Number.isFinite(number) ? number.toFixed(digits) + suffix : "NOT VERIFIED";
}

type EligibilityTone = "review" | "hold" | "warning";
type CandidateDecision = { title: string; reason: string; tone: EligibilityTone };
function candidateDecision(record: Candidate | null, stage: "GEM_JR" | "GEM"): CandidateDecision {
  if (!record) return {title: "NO PROGRAM SELECTED", reason: "Select an exact program to review its source-verified entry benchmarks.", tone: "review"};
  const prefix = stage === "GEM_JR" ? "GEM JR research" : "GEM research";
  const tech = record.technical;
  if (record.candidateLinked === false) return {
    title: "PROGRAM LINK NOT VERIFIED",
    reason: prefix + ": the exact program linkage has not been confirmed. Entry eligibility is withheld.",
    tone: "hold"
  };
  if (!tech) return {
    title: "ELIGIBILITY UNVERIFIED",
    reason: prefix + ": current clinical, financing, and market research evidence is unavailable. No trade clearance.",
    tone: "hold"
  };
  const hardExit = tech.exitStatus?.startsWith("HARD EXIT WARNING") ||
    tech.entryStatus?.startsWith("NO NEW ENTRY") ||
    tech.tradeCall?.startsWith("EXIT RISK") ||
    (tech.riskAlerts || []).some(alert =>
      /FDA decision within 3 days|FDA event already resolved|New or unresolved dilution/i.test(alert));
  if (hardExit) return {
    title: "HARD EXIT / NO NEW ENTRY",
    reason: stated(tech.exitStatus || tech.tradeReason, "Recorded FDA, dilution, or market risk requires immediate review."),
    tone: "warning"
  };
  const benchmark = tech.benchmarks;
  if (benchmark?.phase3 !== true) {
    return {
      title: "PHASE 3 ELIGIBILITY NOT VERIFIED",
      reason: prefix + ": independently verified successful Phase 3 evidence is required. "
        + "Second financing is optional; this does not clear cash, dilution or other trading risks.",
      tone: "hold"
    };
  }
  if (tech.entryStatus?.startsWith("NOT ELIGIBLE")) return {
    title: "ENTRY NOT CLEARED",
    reason: stated(tech.entryStatus) + ". Verified benchmarks do not override clinical risk.",
    tone: "warning"
  };
  if (tech.entryStatus?.startsWith("UNAVAILABLE") || tech.tradeCall?.startsWith("WAIT — SOURCE RECHECK")) return {
    title: "SOURCES REQUIRE RECHECK",
    reason: prefix + ": Phase 3 is verified, but source freshness or other required inputs have not cleared review.",
    tone: "hold"
  };
  return {
    title: "PHASE 3 VERIFIED · ENTRY REVIEW",
    reason: prefix + ": successful Phase 3 verified. Second financing is OPTIONAL (" +
      (benchmark?.secondFinancing === true ? "verified" : "not verified") + "). " +
      "Cash runway, dilution, market evidence, exit overrides and manual review remain separate safeguards.",
    tone: "review"
  };
}
function EvidenceCoverage({label, coverage, compact=false}: {label:string;coverage?:number|null;compact?:boolean}) {
  // Do not silently translate missing observations to zero or imply that
  // evidence coverage measures likelihood of FDA approval or trade success.
  const amount = typeof coverage === "number" && Number.isFinite(coverage) && coverage >= 0 && coverage <= 100
    ? coverage : null;
  return <div className={compact ? "gem-evidence-meter gem-evidence-meter-small" : "gem-evidence-meter"}>
    <div className="gem-evidence-meter-label"><strong>{label}</strong><span>{amount === null ? "NOT REPORTED" : amount + "/100"}</span></div>
    <div className="gem-evidence-meter-track"
      role={amount === null ? undefined : "progressbar"}
      aria-label={label + " weighted evidence coverage"}
      aria-valuemin={amount === null ? undefined : 0}
      aria-valuemax={amount === null ? undefined : 100}
      aria-valuenow={amount === null ? undefined : amount}>
      <span style={{width: amount === null ? "0%" : amount + "%"}} />
    </div>
    {!compact && <small>{amount === null ? "No published coverage figure." :
      "Weighted evidence observed; not a probability of approval or a trading signal."}</small>}
  </div>;
}
function Goals({ record }: { record: Candidate | null }) {
  const tech = record?.technical;
  const pass = (value?: boolean) => value === true;
  const rows: [string,string,string,boolean][] = [
    ["Market capitalization", money(record?.marketCap), "$300M–$10B",pass(record?.capInRange)],
    ["Phase 3 verified positive", tech?.benchmarks?.phase3 ? "PASS — source checked" : stated(record?.phase3Status), "Exact successful primary endpoint + source", pass(tech?.benchmarks?.phase3)],
    ["Second financing (OPTIONAL)", tech?.benchmarks?.secondFinancing ? "VERIFIED — SEC reviewed" : "NOT VERIFIED — MONITOR RISK", "Not required for GEM/GEM JR research eligibility; assess cash and dilution separately", pass(tech?.benchmarks?.secondFinancing)],
    ["SEC cash-only runway", tech?.runwayMonths == null ? stated(tech?.runwayGate) : scoreNum(tech.runwayMonths,1," months"), "≥12 months; source current and reconciled", pass(tech?.runwayGate?.startsWith("PASS"))],
    ["EOD closing price", scoreNum(tech?.close,2," USD"), "Compare SMA20 and SMA50; not executable quote", false],
    ["SMA20 / SMA50", scoreNum(tech?.sma20)+" / "+scoreNum(tech?.sma50), "Close above SMA20 & SMA50", false],
    ["Relative volume", scoreNum(tech?.rvol,2,"×"), "≥1.5× provisional", (tech?.rvol??0)>=1.5],
    ["RSI(14)", scoreNum(tech?.rsi14,1), "45–65 provisional", tech?.rsi14 != null && tech.rsi14>=45 && tech.rsi14<=65],
    ["20D traded dollar volume", tech?.avgDollarVolume20 == null ? "NOT VERIFIED" : "$"+Math.round(tech.avgDollarVolume20).toLocaleString("en-US"), "≥$5M/day", (tech?.avgDollarVolume20??0)>=5000000],
    ["Closing support proxy", scoreNum(tech?.closingSupport20,2), "Verify 20 prior sessions; not a hard stop", false],
    ["Base formation", stated(tech?.base?.status), "2+ separate tests; width ≤18%; volume review", false],
    ["Entry strength / coverage", tech?.entry == null ? stated(tech?.entryStatus,"UNAVAILABLE") : tech.entry+"/100 · "+tech.entryCoverage+"/100 observed", "Only when ≥50/100 evidence coverage and all gates pass", false],
    ["Exit risk / coverage", tech?.exitRisk == null ? stated(tech?.exitStatus,"UNAVAILABLE") : tech.exitRisk+"/100 · "+tech.exitCoverage+"/100 observed", "PDUFA −3 and hard-exit warnings override scores", false],
  ];
  return <div className="goal-table">
    <div className="goal-grid goal-header"><span>Indicator</span><span>Observed / status</span><span>Goal / rule</span></div>
    {rows.map(([label, observed, goal, verified])=><div key={label} className="goal-grid">
      <span className="goal-row-heading">{label}</span>
      <span className={verified ? "verified" : "unknown-value"}><small className="goal-mini-label">Observed / status</small>{observed}</span>
      <span className="gold-goal"><small className="goal-mini-label">Goal / rule</small>{goal}</span>
    </div>)}
  </div>;
}
function TechnicalPanel({ record }: { record: Candidate }) {
  const x = record.technical;
  if (!x) return <p className="subtle">Saved market/SEC observations are unavailable for this exact program.</p>;
  return <div className="research-technical">
    <h3>Evidence-gated entry / exit monitor</h3>
    <p className="risk-line"><strong>{stated(x.tradeCall,"NO VERIFIED MARKET ASSESSMENT")}</strong> · {stated(x.tradeReason)}</p>
    <div className="research-score-cards">
      <div><strong>Entry /100</strong><span>{x.entry == null ? "UNSCORED" : x.entry}</span><small>Evidence coverage {x.entryCoverage??0}/100</small></div>
      <div><strong>Exit risk /100</strong><span>{x.exitRisk == null ? "UNSCORED" : x.exitRisk}</span><small>Evidence coverage {x.exitCoverage??0}/100</small></div>
      <div><strong>Market snapshot</strong><span>{x.eodFresh ? "RECENT EOD" : "STALE / REVIEW"}</span><small>{stated(x.marketDate,"No verified session")}</small></div>
    </div>
    <div className="research-facts-grid">
      <p><strong>Entry:</strong> {stated(x.entryStatus)}</p>
      <p><strong>Exit:</strong> {stated(x.exitStatus)}</p>
      <p><strong>Closing base:</strong> {stated(x.base?.status)} · support {scoreNum(x.base?.support,2)} / resistance {scoreNum(x.base?.resistance,2)}</p>
      <p><strong>MACD:</strong> {scoreNum(x.macd?.macd,3)} · Signal {scoreNum(x.macd?.signal,3)} (close-based; no intraday VWAP)</p>
      <p><strong>SEC cash runway:</strong> {stated(x.runwayGate)} · {stated(x.runwayReason)}</p>
    </div>
    {x.riskAlerts?.length ? <div className="risk-warnings"><strong>Source warnings</strong><div className="risk-alert-grid">{x.riskAlerts.map(alert=><p key={alert}>{alert}</p>)}</div></div> : null}
    <details><summary>All weighted scoring factors and missing evidence</summary>
      <div className="score-factor-groups">{([["Entry strength",x.entryFactors||[]],["Exit risk",x.exitFactors||[]]] as [string,Factor[]][]).map(([name,items])=>
        <div key={name}><h4>{name}</h4><div className="factor-item-grid">{items.map(item=><div className="score-factor" key={item.label}><strong>{item.label}</strong>
          <span>{item.earned==null ? "NOT AVAILABLE" : item.earned} / {item.weight}</span>
          <small>{item.evidence}</small></div>)}</div></div>)}</div>
    </details>
    <p className="subtle small">GEM membership and numerical scores do not authorize trading. No order, stop, ATR, spread or position is inferred. {stated(x.dataGaps,"Missing observations remain unscored.")}</p>
    {evidence(x.marketSource) && <a target="_blank" rel="noopener noreferrer" href={x.marketSource}>Saved market source ↗</a>}
    {evidence(x.runwaySource) && <a target="_blank" rel="noopener noreferrer" href={x.runwaySource}>SEC cash runway evidence ↗</a>}
  </div>;
}

type WTResearchReply = {
  programId: string; exactKey?: string;
  source: string; technical: ResearchTechnical | null; asOf?: string;
  scope?: string; missingSources?: string[];
  watchlistSignals?: Partial<Record<"ENTRY"|"EXIT",{signals?:Record<string,string>;updated?:string}>>;
};
function WTIndicatorDetails({programId, record, ticker}: {programId:string;record?:Candidate;ticker:string}) {
  const [reply,setReply] = useState<WTResearchReply|null>(null);
  const [error,setError] = useState("");
  useEffect(()=>{
    const ctrl=new AbortController();
    setReply(null);
    setError("");
    fetch("/api/wt-research/"+encodeURIComponent(programId),{
      cache:"no-store",signal:ctrl.signal
    }).then(async result=>{
      if(!result.ok)throw Error("WT indicator feed returned "+result.status);
      return await result.json() as WTResearchReply;
    }).then(x=>{if(!ctrl.signal.aborted){
      if(x.programId!==programId|| (record && x.exactKey!==record.id)) {
        setError("Program identity mismatch; scores withheld.");return;
      }
      setReply(x);
    }}).catch(e=>{if(!ctrl.signal.aborted)setError(String(e));});
    return ()=>ctrl.abort();
  },[programId,record?.id]);
  const x=reply?.technical;
  const observed=(v?:number|null)=>typeof v==="number"&&Number.isFinite(v)?v.toString()+"/100":"UNSCORED";
  return <section className="wt-score-details" aria-label={programId+" indicator entry and exit research"}>
    <div className="wt-indicator-title"><h3>WT INDICATOR ENTRY &amp; EXIT SCORES</h3>
      <span className="permanent-id">{programId}</span></div>
    <IndicatorParityTables programId={programId} tech={x} signals={reply?.watchlistSignals}/>
    <p className="subtle">Uses GEM JR / GEM’s original EOD indicator calculations and factor weights. Indicator strength is separate from verified Phase 3 eligibility and does not authorize a trade. Second financing is optional.</p>
    {error ? <p className="risk-line">Indicator lookup failed: {error}. Scores withheld.</p>
    : !reply ? <p className="subtle">Checking verified price, volume, trend, technical risks and source dates…</p>
    : !x ? <p className="risk-line">Current exact-program indicator evidence unavailable. Scores withheld.</p>
    : <>
      <div className="research-score-cards wt-observed-scores">
        <div><strong>Indicator entry /100</strong>
          <span>{observed(x.indicatorEntry)}</span>
          <small>Evidence coverage {x.indicatorEntryCoverage??0}/100 · {x.indicatorEntry==null? "Observed points "+(x.indicatorEntryObservedPoints??0)+" (partial, not a validated /100 score)":"GEM weighted score"}</small></div>
        <div><strong>Indicator exit risk /100</strong>
          <span>{observed(x.indicatorExitRisk)}</span>
          <small>Evidence coverage {x.indicatorExitCoverage??0}/100 · {x.indicatorExitRisk==null? "Observed points "+(x.indicatorExitObservedPoints??0)+" (partial, not a validated /100 score)":"GEM weighted score"}</small></div>
        <div><strong>Verified market snapshot</strong>
          <span>{x.eodFresh?stated(x.marketDate,"CHECK DATE"):"STALE / MISSING"}</span>
          <small>{x.eodFresh?"Recent, source-consistent EOD":"Unverified / old observations"}</small></div>
      </div>
      <p className="wt-indicator-eligibility"><strong>Clinical entry / source-risk gate:</strong> {stated(x.entryStatus,"NOT VERIFIED")}</p>
      <p><strong>Exit overrides:</strong> {stated(x.exitStatus,"NOT VERIFIED")}{x.riskAlerts?.length?" · "+x.riskAlerts.join("; "):""}</p>
      <details className="wt-factors"><summary>Expand indicator scoring factors, weights, actual evidence and gaps</summary>
        <div className="score-factor-groups">{([
          ["Entry indicators",x.indicatorEntryFactors||[]],
          ["Exit indicators",x.indicatorExitFactors||[]],
        ] as [string,Factor[]][]).map(([title,items])=><div key={title}>
          <h4>{title}</h4>
          {items.length ? <div className="factor-item-grid">{items.map(f=><div className="score-factor" key={f.label}>
            <strong>{f.label}</strong><span>{f.earned==null?"NOT VERIFIED":f.earned} / {f.weight}</span>
            <small>{f.evidence}</small></div>)}</div> : <p className="subtle">No verified EOD observations yet.</p>}
        </div>)}</div>
      </details>
      {record && <details className="wt-factors"><summary>Original GEM eligibility entry / exit monitor (same Program ID)</summary>
        <TechnicalPanel record={{...record,technical:x}} />
      </details>}
      <p className="subtle small">Source: {stated(reply.source)}. {stated(reply.scope)} {stated(x.indicatorDisclaimer)}
        Missing ATR, real stops, VWAP, spread, and reward/risk are not scored.
        {reply.missingSources?.length?" Missing upstream files: "+reply.missingSources.join(", "):""}
      </p>
      {evidence(x.marketSource)&&<a href={x.marketSource} target="_blank" rel="noopener noreferrer">Market data source ↗</a>}
    </>}
  </section>;
}

function PriorityIndicators({ record }: { record: Candidate }) {
  const t = record.technical;
  const pdufaDays = daysAway(record.pdufaDate);
  const observations: [string,string,string][] = [
    ["Support / resistance / base", t?.base ? scoreNum(t.base.support)+" / "+scoreNum(t.base.resistance)+" · "+t.base.status : "NOT VERIFIED", "≥2 separated support touches; verify 20-session base"],
    ["Volume and relative volume", scoreNum(t?.rvol,2,"×")+" · "+(t?.avgDollarVolume20 == null ? "liquidity unknown" : money(t.avgDollarVolume20)), "RVOL ≥1.5× breakout; average $ volume ≥$5M"],
    ["SMA20 and SMA50", scoreNum(t?.sma20)+" / "+scoreNum(t?.sma50), "Close above rising SMA20 and SMA50"],
    ["ATR(14)", "NOT AVAILABLE — no verified high/low bars", "Size volatility-based stop; no fixed ATR target"],
    ["Reward / risk", "NOT AVAILABLE — no validated stop and target", "Prefer ≥2:1 after costs; define hard stop before entry"],
    ["VWAP / anchored VWAP", "NOT AVAILABLE — intraday / anchor data missing", "Price above significant VWAP level"],
    ["Relative strength vs XBI", "NOT AVAILABLE — benchmark data missing", "Outperform XBI across matched periods"],
    ["Catalyst / PDUFA markers", record.pdufaDate ? record.pdufaDate+" · "+(pdufaDays??"—")+" days (reported)" : "NOT VERIFIED", "Verify date; pre-PDUFA exit at −3 days"],
    ["RSI(14)", scoreNum(t?.rsi14,1), "45–65 provisional; optional filter"],
    ["MACD", scoreNum(t?.macd?.macd,3)+" vs "+scoreNum(t?.macd?.signal,3), "Bullish crossover preferred; optional confirmation"],
  ];
  return <details className="priority-panel"><summary>Chart indicators — strict priority 1–10 and target levels</summary>
    <div className="priority-scroll"><table><thead><tr><th>Priority</th><th>Observed</th><th>Gold target</th></tr></thead><tbody>
      {observations.map(([name,value,goal],i)=><tr key={name}><td><strong>{i+1}. {name}</strong></td>
        <td>{value}</td><td><span className="gold-goal">{goal}</span></td></tr>)}
    </tbody></table></div>
    <p className="subtle small">The market feed contains close/volume observations only. Intraday ATR, spread, actual stops, anchored VWAP and XBI comparisons are not fabricated.</p>
  </details>;
}
function GemInlineSection({title,description,open,onToggle,children}:{
  title:string;description:string;open:boolean;onToggle:()=>void;children:ReactNode
}) {
  return <section className={"gem-inline-section"+(open?" gem-inline-section-open":"")}>
    <button type="button" className="gem-inline-section-trigger" onClick={onToggle} aria-expanded={open}>
      <span className="gem-inline-section-heading"><span aria-hidden="true">{open?"▾":"▸"}</span> {title}</span>
      <small>{description}</small>
    </button>
    {open && <div className="gem-inline-section-content">{children}</div>}
  </section>;
}

function SourceDetails({ record }: { record: Candidate }) {
  return (
    <div className="program-details">
      <div className="trial-details">
        <div><strong>Permanent Program ID</strong><span className="permanent-id">{stated(record.programId,"REGISTRY UNAVAILABLE")}</span></div>
        <div><strong>Exact Pipeline source key</strong><span>{record.id}</span></div>
        {record.listAddedOn !== undefined && <div><strong>Date added to this list</strong><span>{stated(record.listAddedOn,"NOT RECORDED")}</span></div>}
        {record.listRemovedOn !== undefined && <div><strong>Date removed from this list</strong><span>{stated(record.listRemovedOn,"— Still listed")}</span></div>}
        <div><strong>Drug / indication</strong><span>{stated(record.drug)} / {stated(record.indication)}</span></div>
        <div><strong>ClinicalTrials.gov NCT</strong><span>{trialSheetUrl(record)
          ? <a href={trialSheetUrl(record)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">{trialId(record)} · OPEN FULL TRIAL SHEET ↗</a>
          : "NO EXACT TRIAL LINKED"}</span></div>
        <div><strong>Phase 3</strong><span>{stated(record.phase3Status)} · {stated(record.phase3Date, "date unavailable")}</span></div>
        <div><strong>Second financing</strong><span>{stated(record.financingStatus)} · {stated(record.financingDate, "date unavailable")}</span></div>
        <div><strong>PDUFA</strong><span>{stated(record.pdufaDate)}</span></div>
        <div><strong>Market cap</strong><span>{money(record.marketCap)} · {record.capInRange ? "Within $300M–$10B" : "Unknown / outside preferred band"}</span></div>
        <div><strong>Source verification</strong><span>{stated(record.checkStatus)} · {stated(record.lastChecked)}</span></div>
      </div>
      <div className="source-links">
        {evidence(record.phase3Source) && <a href={record.phase3Source} target="_blank" rel="noopener noreferrer">Phase 3 source ↗</a>}
        {evidence(record.financingSource) && <a href={record.financingSource} target="_blank" rel="noopener noreferrer">SEC financing ↗</a>}
        {evidence(record.fdaSource) && <a href={record.fdaSource} target="_blank" rel="noopener noreferrer">FDA evidence ↗</a>}
      </div>
      <p className="subtle small">Missing data is not a pass. Nested hierarchy: ticker → drug/program → source trial/evidence. Program membership is not trade authorization.</p>
    </div>
  );
}
function Drilldown({ rows }: { rows: Candidate[] }) {
  const grouped = useMemo(() => {
    const map = new Map<string, Candidate[]>();
    uniqueRows(rows).forEach(item => map.set(item.ticker, [...(map.get(item.ticker) || []), item]));
    return [...map].sort(([a], [b]) => a.localeCompare(b));
  }, [rows]);
  return <div className="nested-records">
    {grouped.map(([ticker, companies]) => (
      <details key={ticker} className="drill-company">
        <summary><strong>{ticker}</strong><span>{companies.length} exact program{companies.length === 1 ? "" : "s"}</span></summary>
        <div className="drill-program-grid">{companies.map(item => (
          <details key={item.id} className="drill-program">
            <summary><strong>{stated(item.drug)}</strong><span><strong className="permanent-id">{stated(item.programId)}</strong> · {stated(item.indication, "program research")} · {stated(item.pdufaDate, "no date")}</span></summary>
            <div className="drill-evidence"><strong>Trial details and verification</strong>
              {trialSheetUrl(item) && <a href={trialSheetUrl(item)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">OPEN FULL TRIAL SHEET · {trialId(item)} ↗</a>}
              <SourceDetails record={item} />
            </div>
          </details>
        ))}</div>
      </details>
    ))}
    {grouped.length === 0 && <p className="subtle">No exact-program records match these filters.</p>}
  </div>;
}

export default function Workspace({ onInspect }: { onInspect: (ticker: string, stage: Stage, programId?: string) => void }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [gemScans,setGemScans]=useState<Partial<Record<"GEM_JR"|"GEM",GemScanResult>>>({});
  const [fetchVersion, setFetchVersion] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState("");
  const [top, setTop] = useState<TopNav>("PDUFA");
  const [nav, setNav] = useState<Nav>("PIPELINE");
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  // Each GEM table shows up to 10 rows around its independently selected
  // candidate. Previous / Next move exactly one source-ordered row at a time.
  // The complete list remains available to nested clinical trial drilldowns.
  const highlightedGemRow=useRef<HTMLTableRowElement|null>(null);
  const gemTableScrollViewport=useRef<HTMLDivElement|null>(null);
  const [gemTrialExpanded,setGemTrialExpanded]=useState<Record<"GEM_JR"|"GEM",boolean>>({GEM_JR:false,GEM:false});
  const [gemTrialSections,setGemTrialSections]=useState<Record<string,boolean>>({});
  // Mobile-only qualification criteria: initially collapsed for both stages.
  // On desktop CSS keeps the complete criteria visible, regardless of this state.
  const [gemCriteriaExpanded,setGemCriteriaExpanded]=useState<Record<"GEM_JR"|"GEM",boolean>>({GEM_JR:false,GEM:false});
  const [masterProgram, setMasterProgram] = useState("");
  const [stageFilters, setStageFilters] = useState<string[]>([]);
  const [dateFilters, setDateFilters] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [onlyBand, setOnlyBand] = useState(false);
  const [trialFilters, setTrialFilters] = useState<TrialFilterValues>({ ...EMPTY_TRIAL_FILTERS });
  const [displayFilters, setDisplayFilters] = useState<PipelineSelection | null>(null);
  const [displayVersion, setDisplayVersion] = useState(0);
  const pipelineDataRef = useRef<HTMLDivElement>(null);
  const [gemQuery, setGemQuery] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [tags, setTags] = useState<Tags>({ watch: [], trade: [] });
  const [tagsReady, setTagsReady] = useState(false);
  const [legacyTags, setLegacyTags] = useState<Tags>({watch:[],trade:[]});
  const [storedIdentities,setStoredIdentities] = useState<{programId:string;id:string;ticker:string;drug:string}[]>([]);
  const [wtStatus, setWtStatus] = useState("Loading saved W/T labels…");
  const wtVersion = useRef(0);
  const wtCurrent = useRef<Tags>({ watch: [], trade: [] });
  const wtQueue = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    const ctrl = new AbortController();
    let retryTimer: ReturnType<typeof setTimeout> | null = null;
    // Render's free web service can take longer than Vercel's 30s upstream
    // timeout to restart. Retry only transient failures, without inventing
    // replacement Pipeline/GEM data or overwriting an already loaded snapshot.
    const retryDelays = [0, 3000, 8000, 15000, 20000];
    async function loadPublishedSources() {
      for (let attempt = 0; attempt < retryDelays.length && !ctrl.signal.aborted; attempt++) {
        if (attempt > 0) {
          setFetchError("Reconnecting to published sources… attempt " + (attempt + 1) + "/" + retryDelays.length + ". Saved WT selections are unchanged.");
          await new Promise<void>(resolve => {
            retryTimer = setTimeout(resolve, retryDelays[attempt]);
          });
          retryTimer = null;
          if (ctrl.signal.aborted) return;
        }
        try {
          const response = await fetch("/api/workspace", { cache: "no-store", signal: ctrl.signal });
          if (!response.ok) {
            const transient = [502, 503, 504].includes(response.status);
            if (transient && attempt < retryDelays.length - 1) continue;
            const details = await response.json().catch(() => ({})) as {error?:string};
            throw new Error("Published source unavailable: " + response.status +
              (details.error ? " — " + details.error : ". Check backend health and configuration."));
          }
          const data: Snapshot = await response.json();
          if (!ctrl.signal.aborted) {
            setSnapshot(data);
            setFetchError("");
            setRefreshing(false);
          }
          return;
        } catch (error) {
          if (ctrl.signal.aborted) return;
          const permanent = error instanceof Error && error.message.startsWith("Published source unavailable:");
          if (permanent || attempt === retryDelays.length - 1) {
            setFetchError(String(error));
            setRefreshing(false);
            return;
          }
        }
      }
    }
    void loadPublishedSources();
    return () => {
      ctrl.abort();
      if (retryTimer !== null) clearTimeout(retryTimer);
    };
  }, [fetchVersion]);
  useEffect(() => {
    let local: Tags = {watch:[],trade:[]};
    try {
      const saved = JSON.parse(localStorage.getItem(TAG_KEY)||"{}");
      const valid=(v: unknown)=>typeof v==="string" && /^PDUFA-[0-9]{6,}$/.test(v);
      if(Array.isArray(saved.watch)&&Array.isArray(saved.trade)){
        const trade = [...new Set<string>(saved.trade.filter(valid))];
        local={watch:[...new Set<string>(saved.watch.filter(valid))].filter(v=>!trade.includes(v)),trade};
      }
      const legacy=JSON.parse(localStorage.getItem(LEGACY_TAG_KEY)||"{}");
      if(Array.isArray(legacy.watch)&&Array.isArray(legacy.trade)){
        setLegacyTags({watch:legacy.watch.filter((v:unknown)=>typeof v==="string"),trade:legacy.trade.filter((v:unknown)=>typeof v==="string")});
      }
    } catch { /* local storage may be disabled */ }
    wtCurrent.current=local;setTags(local);
    let cancelled=false;
    async function restore(){
      try {
        const response=await fetch("/api/program-watch-trade",{cache:"no-store"});
        if(!response.ok) throw Error("Program WT storage unavailable");
        const remote=await response.json();
        if(!Array.isArray(remote.watch)||!Array.isArray(remote.trade)||!Number.isSafeInteger(remote.version)) throw Error("Invalid WT data");
        if(cancelled)return;
        wtVersion.current=remote.version;
        const canonical: Tags={watch:remote.watch,trade:remote.trade};
        wtCurrent.current=canonical;setTags(canonical);
        setStoredIdentities(Array.isArray(remote.identities)?remote.identities:[]);
        setLegacyTags(prev=>({
          watch:[...new Set([...(remote.legacy?.watch||[]),...prev.watch])],
          trade:[...new Set([...(remote.legacy?.trade||[]),...prev.trade])]
        }));
        setWtStatus("Permanent program selections saved in Neon PostgreSQL; old ticker-only tags retained separately");
      } catch {
        if(!cancelled)setWtStatus("WT database unavailable — local program selections not synchronized");
      } finally {
        if(!cancelled)setTagsReady(true);
      }
    }
    void restore();
    return()=>{cancelled=true};
  },[]);
  useEffect(() => {
    if (!tagsReady) return;
    try { localStorage.setItem(TAG_KEY, JSON.stringify(tags)); } catch { /* keep current memory */ }
  }, [tags, tagsReady]);
  function mark(programId: string,kind: "watch"|"trade"|"clear"){
    if(!tagsReady||!/^PDUFA-[0-9]{6,}$/.test(programId)){
      setWtStatus("Unable to select this program: permanent Neon ID not available");
      return;
    }
    const prev=wtCurrent.current;
    const updated: Tags={
      watch:kind==="watch"?[...new Set([...prev.watch.filter(v=>v!==programId),programId])].sort():prev.watch.filter(v=>v!==programId),
      trade:kind==="trade"?[...new Set([...prev.trade.filter(v=>v!==programId),programId])].sort():prev.trade.filter(v=>v!==programId)
    };
    wtCurrent.current=updated;setTags(updated);setWtStatus("Saving permanent Program IDs to Neon…");
    wtQueue.current=wtQueue.current.catch(()=>{}).then(async()=>{
      const response=await fetch("/api/program-watch-trade",{
        method:"PUT",headers:{"Content-Type":"application/json"},
        body:JSON.stringify({...updated,version:wtVersion.current})
      });
      if(!response.ok){setWtStatus(response.status===409?"Program selection conflict — reload this page": "Program selection save failed — local changes unsynchronized");return;}
      const remote=await response.json();
      wtVersion.current=remote.version;
      setWtStatus("Permanent Program IDs saved in Neon PostgreSQL");
    }).catch(()=>setWtStatus("Program selection save failed — local changes unsynchronized"));
  }

  const pipeline = snapshot?.pipeline || [];
  const availability = useMemo(() => pipelineAvailability(pipeline, { query, onlyBand, trial: trialFilters, asOf: snapshot?.asOf }, dateBand, STAGES, BANDS), [pipeline, onlyBand, query, trialFilters, snapshot?.asOf]);
  const possible = availability.rows;
  const qualificationBase = useMemo(() => filterPipelineRows(pipeline, { query, onlyBand, stages: stageFilters, dates: dateFilters }, dateBand), [pipeline, query, onlyBand, stageFilters, dateFilters]);
  const counted = useMemo(() => filterPipelineRows(possible, { stages: stageFilters, dates: dateFilters }, dateBand), [possible, stageFilters, dateFilters]);
  const displayed = useMemo(() => displayFilters ? filterPipelineRows(pipeline, displayFilters, dateBand) : [], [pipeline, displayFilters]);
  const selectionKey = (selection: PipelineSelection) => JSON.stringify([
    [...selection.stages].sort(), [...selection.dates].sort(), selection.query, selection.onlyBand, selection.trial,
  ]);
  const draftKey = selectionKey({ stages: stageFilters, dates: dateFilters, query, onlyBand, trial: trialFilters });
  const appliedKey = displayFilters ? selectionKey(displayFilters) : "";
  const selectionsChanged = displayFilters !== null && draftKey !== appliedKey;

  useEffect(() => {
    if (displayVersion) pipelineDataRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, [displayVersion]);

  function displayTrials() {
    setDisplayFilters({ stages: [...stageFilters], dates: [...dateFilters], query, onlyBand, trial: { ...trialFilters }, asOf: snapshot?.asOf });
    setDisplayVersion(value => value + 1);
  }
  function clearPipelineSelections() {
    setStageFilters([]);
    setDateFilters([]);
    setQuery("");
    setOnlyBand(false);
    setTrialFilters({ ...EMPTY_TRIAL_FILTERS });
    setDisplayFilters(null);
    setDisplayVersion(0);
  }
  const byProgram = useMemo(() => {
    const m=new Map<string,Candidate>();
    for(const r of [...(snapshot?.members.GEM.rows||[]),...(snapshot?.members.GEM_JR.rows||[]),...pipeline]){
      if(r.programId&&!m.has(r.programId))m.set(r.programId,r);
    }
    return m;
  },[snapshot,pipeline]);
  const byTicker = useMemo(() => {
    const m = new Map<string, Candidate[]>();
    [...pipeline, ...(snapshot?.members.GEM_JR.rows || []), ...(snapshot?.members.GEM.rows || [])].forEach(r => {
      if (r.ticker && !m.get(r.ticker)?.some(other => other.id === r.id)) m.set(r.ticker, [...(m.get(r.ticker)||[]), r]);
    });
    return m;
  }, [snapshot, pipeline]);

  function toggleFilter(current: string[], item: string, setter: (value: string[])=>void) {
    setter(current.includes(item) ? current.filter(v => v !== item) : [...current, item]);
  }
  const stageCounts = availability.stageCounts;
  const dateCounts = availability.dateCounts;

  function wtButton(record: Candidate,kind:"watch"|"trade"){
    const id=record.programId||"";
    const current=tags[kind].includes(id);
    return <button type="button" className={current?"wt-active":"wt-btn"}
      disabled={!tagsReady||!/^PDUFA-[0-9]{6,}$/.test(id)} aria-pressed={current}
      onClick={()=>mark(id,current?"clear":kind)}
      title={id?(kind==="watch"?"Watch ":"Trading research ")+id:"Permanent ID unavailable"}>
      {kind==="watch"?"W":"T"}{current?" ✓":""}
    </button>;
  }
  function selectCandidate(record: Candidate, stage: Stage) { onInspect(record.ticker,stage,record.programId); }
  useEffect(()=>{
    if (nav!=="GEM" && nav!=="GEM_JR") return;
    if (!selected[nav]) return;
    const row=highlightedGemRow.current;
    const viewport=gemTableScrollViewport.current;
    if (!row || !viewport) return;
    // Scroll only the table viewport, not the full page or its wide
    // horizontal table position. Keep PREVIOUS / NEXT on screen.
    const bounds=viewport.getBoundingClientRect();
    const position=row.getBoundingClientRect();
    const stickyHeader=viewport.querySelector("thead")?.getBoundingClientRect().height || 38;
    if (position.top<bounds.top+stickyHeader+6) {
      viewport.scrollBy({top:position.top-bounds.top-stickyHeader-8,behavior:"smooth"});
    } else if (position.bottom>bounds.bottom-6) {
      viewport.scrollBy({top:position.bottom-bounds.bottom+8,behavior:"smooth"});
    }
  },[nav,selected.GEM,selected.GEM_JR,gemQuery]);

  function gemBlock(stage: "GEM_JR" | "GEM") {
    const group = snapshot?.members[stage];
    const scanned=gemScans[stage];
    // Only a current GEM JR scan may supply GEM input. Never silently
    // substitute saved GEM JR membership if no scan is available.
    const juniorScan=gemScans.GEM_JR;
    const currentJuniorScan=juniorScan && juniorScan.asOf===snapshot?.asOf && juniorScan.sourceTotal===pipeline.length ? juniorScan : null;
    // A screen is an unsaved research view, never a change to saved membership.
    // Re-run after published source refresh; never reuse results from another snapshot.
    const activeScan=scanned && scanned.asOf===snapshot?.asOf && scanned.sourceTotal===pipeline.length ? scanned : null;
    const scanStatuses=activeScan?new Map<string,"PASS"|"NEEDS VERIFICATION">([
      ...activeScan.passes.map(r=>[r.id,"PASS"] as const),
      ...activeScan.needsReview.map(r=>[r.id,"NEEDS VERIFICATION"] as const)
    ]):null;
    const viewRows=activeScan?[...activeScan.passes,...activeScan.needsReview]:(group?.rows||[]);
    const rows=viewRows.filter(r=>r.ticker.toLowerCase().includes(gemQuery.toLowerCase()) || (r.drug||"").toLowerCase().includes(gemQuery.toLowerCase()));
    const focusedIndex = Math.max(0,rows.findIndex(r=>r.id===selected[stage]));
    const chosen = rows[focusedIndex] || null;
    // Track the exact current stage-membership cycle (including re-entry).
    // No clinical readout, FDA date or scan-last-seen date is substituted.
    const historyById = new Map<string,StageHistory[]>();
    for(const period of group?.history||[]){
      historyById.set(period.id,[...(historyById.get(period.id)||[]),period]);
    }
    const listDates = (record:Candidate) => {
      if(activeScan)return {added:"",removed:""};
      const active = (historyById.get(record.id)||[]).filter(period=>!period.leftOn && period.status==="ACTIVE")
        .sort((a,b)=>b.cycle-a.cycle)[0];
      return {added:active?.enteredOn || record.firstFound || "",removed:""};
    };
    const visibleCount = Math.min(rows.length,10);
    const firstVisible = Math.max(0,Math.min(focusedIndex-4,rows.length-visibleCount));
    const visibleRows = rows.slice(firstVisible,firstVisible+visibleCount);
    // A newly opened row starts with only its chart expanded. Collapsing it
    // or moving to another row discards previously opened detail subsections.
    const resetOpenSections = (record:Candidate,section?:string) => {
      setGemTrialSections(current=>{
        const reset=Object.fromEntries(Object.entries(current).filter(([key])=>!key.startsWith(stage+"|")));
        if(section && section!=="chart") reset[stage+"|"+record.id+"|"+section]=true;
        return reset;
      });
    };
    const moveRow = (delta:-1|1) => {
      const next = rows[focusedIndex+delta];
      if(next){
        resetOpenSections(next);
        setSelected(current=>({...current,[stage]:next.id}));
        setGemTrialExpanded(current=>({...current,[stage]:true}));
      }
    };
    const selectTrial = (record:Candidate,section?:string) => {
      const same = chosen?.id===record.id && (selected[stage]===record.id || !selected[stage] && focusedIndex===0);
      const opening = Boolean(section) || !same || !gemTrialExpanded[stage];
      resetOpenSections(record,opening?section:undefined);
      setSelected(current=>({...current,[stage]:record.id}));
      setGemTrialExpanded(current=>({...current,[stage]:opening}));
    };
    // The first (Alpaca stock chart) section opens automatically for every
    // selected program, while a user's explicit collapse remains respected.
    const isSectionOpen=(section:string)=>{
      if(!chosen) return false;
      const key=stage+"|"+chosen.id+"|"+section;
      return section==="chart" ? gemTrialSections[key] !== false : gemTrialSections[key] === true;
    };
    const toggleSection=(section:string)=>{
      if(!chosen) return;
      const key=stage+"|"+chosen.id+"|"+section;
      setGemTrialSections(current=>({...current,[key]: !(section==="chart" ? current[key] !== false : current[key] === true)}));
    };
    return <section className={"gem-section " + (stage==="GEM" ? "gem-purple" : "gem-blue")} key={stage}>
      <div className="gem-heading">
        <div><h2>{stage==="GEM"?"GEM":"GEM JR"} · Candidate research</h2>
          <p>{stage==="GEM"?"Successful Phase 3 qualifies for review; second financing optional, dilution safeguards retained":"Early evidence watchlist; not GEM-qualified by ticker alone"}</p></div>
        <span className="gem-count">{rows.length} {activeScan?(activeScan.sourceKind==="GEM_JR"?"GEM JR input scan results":"PIPELINE scan results"):"saved programs"} · {stated(activeScan?.asOf||group?.asOf, "snapshot undated")}</span>
      </div>
      <GemQualificationChecklist stage={stage} pipeline={pipeline} asOf={snapshot?.asOf||""} stageTotal={group?.rows?.length || 0} gemJrScan={currentJuniorScan}
        onReset={()=>setGemScans(current=>{
          // Changing GEM JR criteria invalidates both its old scan and any GEM
          // result derived from that old upstream candidate pool.
          if(stage==="GEM_JR")return current.GEM_JR||current.GEM?{}:current;
          if(!current.GEM)return current;
          const next={...current};delete next.GEM;return next;
        })}
        onScan={result=>{
          setGemScans(current=>stage==="GEM_JR"?{GEM_JR:result}:{...current,GEM:result});
          setGemQuery("");
          setGemTrialExpanded(current=>({...current,[stage]:false}));
          setGemTrialSections(current=>Object.fromEntries(Object.entries(current).filter(([key])=>!key.startsWith(stage+"|"))));
        }} />
      {activeScan && <div className="panel" role="status" aria-live="polite" style={{marginBottom:12,padding:14,border:"1px solid #76947d",borderRadius:7,background:"#f3fcf5"}}>
        <strong>{activeScan.sourceKind==="GEM_JR"?"GEM JR INPUT":"PIPELINE"} SCREEN RESULTS — {stage==="GEM"?"GEM":"GEM JR"} · RUN #{activeScan.runNumber}</strong>
        <p><strong>{(activeScan.passes.length+activeScan.needsReview.length).toLocaleString("en-US")} TOTAL COMBINED CANDIDATES</strong> · intersection of all checked requirements (AND), no duplicate counting. Of {activeScan.baseline.toLocaleString("en-US")} {activeScan.sourceKind==="GEM_JR"?"GEM JR scan candidates":"PIPELINE records"} assessed: {activeScan.passes.length.toLocaleString("en-US")} verified matches · {activeScan.needsReview.length.toLocaleString("en-US")} need evidence verification · {activeScan.fails.length.toLocaleString("en-US")} excluded.</p>
        <p className="subtle">Checked requirements: {activeScan.audits.map(a=>a.label).join("; ")||"None — unrestricted"}. Only programs satisfying every selected check or needing verification are included in the table, never a sum of independent criterion totals. Nothing is automatically added to GEM membership. Source {stated(activeScan.asOf)}; run finished {new Date(activeScan.evaluatedAt).toLocaleString()}.</p>
        <button type="button" className="secondary" onClick={()=>setGemScans(current=>{const next={...current};delete next[stage];return next})}>SHOW SAVED {stage==="GEM"?"GEM":"GEM JR"} LIST</button>
      </div>}
      {chosen && <div className="gem-decision-band" aria-label={stage==="GEM"?"GEM candidate eligibility and evidence coverage":"GEM JR candidate eligibility and evidence coverage"}>
        <div className="gem-decision-summary">
          <span className="gem-decision-program">{chosen.ticker} · {stated(chosen.programId, "PROGRAM ID UNVERIFIED")} · {stage==="GEM"?"GEM":"GEM JR"}</span>
          <strong className={"gem-eligibility gem-eligibility-"+candidateDecision(chosen,stage).tone}>
            {candidateDecision(chosen,stage).title}
          </strong>
          <p>{candidateDecision(chosen,stage).reason}</p>
          <small>Entry decision: {stated(chosen.technical?.entryStatus)} · Exit override: {stated(chosen.technical?.exitStatus)}</small>
        </div>
        <div className="gem-decision-evidence">
          <EvidenceCoverage label="ENTRY EVIDENCE" coverage={chosen.technical?.entryCoverage} />
          <EvidenceCoverage label="EXIT EVIDENCE" coverage={chosen.technical?.exitCoverage} />
        </div>
      </div>}
      <div className="gem-body">
        <aside className="gem-criteria gem-criteria-responsive" data-open={gemCriteriaExpanded[stage]?"true":"false"}>
          <h3 className="gem-criteria-desktop-heading">Qualification criteria</h3>
          <button type="button" className="gem-criteria-mobile-trigger"
            aria-expanded={gemCriteriaExpanded[stage]} aria-controls={"gem-criteria-content-"+stage}
            onClick={()=>setGemCriteriaExpanded(current=>({...current,[stage]:!current[stage]}))}>
            <span>Qualification criteria</span>
            <span className="gem-criteria-trigger-state" aria-hidden="true">{gemCriteriaExpanded[stage]?"− Hide ▲":"+ Show ▼"}</span>
          </button>
          <div className="gem-criteria-collapsible-content" id={"gem-criteria-content-"+stage}>
            <p className="subtle">Source observations beside target levels for the selected program.</p>
            <Goals record={chosen} />
          </div>
        </aside>
        <div className="gem-table-panel">
          <div className="sectionhead gem-table-heading">
            <h3>{activeScan?"COMBINED SCREEN RESULTS · passed all checks or require evidence review · not saved stage membership":"GEM CANDIDATE TABLE · published membership · exact permanent program IDs"}</h3>
            <div className="gem-table-controls" aria-label={(stage==="GEM"?"GEM":"GEM JR")+" table rows"}>
              <span className="gem-table-visible" role="status" aria-live="polite">
                Selected row {rows.length?focusedIndex+1:0} of {rows.length} · {chosen?.ticker||"No candidate"}
              </span>
              <button type="button" className="secondary" disabled={focusedIndex<=0||!rows.length}
                onClick={()=>moveRow(-1)} aria-label="Select previous candidate row">↑ PREVIOUS ROW</button>
              <button type="button" className="secondary" disabled={focusedIndex>=rows.length-1||!rows.length}
                onClick={()=>moveRow(1)} aria-label="Select next candidate row">↓ NEXT ROW</button>
            </div>
          </div>
          <div className="table-scroll gem-row-scroller" ref={gemTableScrollViewport} aria-label={(stage==="GEM"?"GEM":"GEM JR")+" candidates scrollable table"}>
            <table className="gem-source-parity-table">
              <thead><tr>
                {["#","Program ID","W","T","Ticker","Date Added","Date Removed","Eligibility","Company","Indication","Phase","P3 Readout","PDUFA","Financing Status","Cash Runway","Market Cap","PoA","Short Int.","Entry Score","Entry Evidence","Exit Risk","Exit Evidence","Status","Trend (source)","Details"].map(h=><th key={h}>{h}</th>)}
              </tr></thead>
              <tbody>{visibleRows.map((r,i)=><Fragment key={r.id}><tr
                ref={chosen?.id===r.id && selected[stage] ? highlightedGemRow : undefined}
                className={chosen?.id===r.id?"selected-record gem-focused-row":"gem-selectable-row"}
                aria-selected={chosen?.id===r.id} tabIndex={0}
                onClick={event=>{
                  if ((event.target as HTMLElement).closest("a,button,input,select,textarea,label")) return;
                  selectTrial(r);
                }}
                onKeyDown={event=>{
                  if (event.target!==event.currentTarget) return;
                  if(event.key==="Enter"||event.key===" "){
                    event.preventDefault();
                    selectTrial(r);
                  }
                }}
                aria-expanded={chosen?.id===r.id && gemTrialExpanded[stage]}
                aria-label={"Trial "+r.ticker+" · click to expand or collapse stock details"}>
                <td className="numeric">{firstVisible+i+1}</td>
                <td><strong className="permanent-id">{stated(r.programId)}</strong></td>
                <td>{wtButton(r,"watch")}</td>
                <td>{wtButton(r,"trade")}</td>
                <td><button type="button" className="ticker-select" aria-expanded={chosen?.id===r.id && gemTrialExpanded[stage]} onClick={()=>selectTrial(r)}>{r.ticker} {chosen?.id===r.id && gemTrialExpanded[stage]?"▾":"▸"}</button></td>
                <td title="First confirmed appearance in this GEM-stage membership cycle">{stated(listDates(r).added,"NOT RECORDED")}</td>
                <td title="No removal date while the exact program remains active in this list">—</td>
                <td>{activeScan?<span className="gem-table-eligibility" style={{background:scanStatuses?.get(r.id)==="PASS"?"#d7f7e4":"#fff0d8",color:"#232323",padding:"5px 7px",borderRadius:5}}>{scanStatuses?.get(r.id)}</span>:<span className={"gem-table-eligibility gem-eligibility-"+candidateDecision(r,stage).tone}
                  title={candidateDecision(r,stage).reason}>{candidateDecision(r,stage).title}</span>}</td>
                <td>{stated(r.company,"—")}</td>
                <td title={stated(r.drug)}>{trialSheetUrl(r)
                  ? <a href={trialSheetUrl(r)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">{stated(r.indication,"—")} ↗<small>{trialId(r)} · Full trial sheet</small></a>
                  : stated(r.indication,"—")}</td>
                <td>{stated(r.stage,"P3")}</td>
                <td>{stated(r.phase3Date,"—")}</td>
                <td title={stated(r.fdaSource,"FDA date unverified")}>{stated(r.pdufaDate,"—")}</td>
                <td>{stated(r.financingStatus,"—")}</td>
                <td title={stated(r.technical?.runwayReason)}>{r.technical?.runwayMonths == null?"—":r.technical.runwayMonths.toFixed(1)+" mo"}</td>
                <td>{money(r.marketCap)}</td>
                <td>{stated(r.approvalProbability,"—")}</td>
                <td>—</td>
                <td title={stated(r.technical?.entryStatus)}>{r.technical?.entry??"—"}</td>
                <td><EvidenceCoverage label="Entry" coverage={r.technical?.entryCoverage} compact /></td>
                <td title={stated(r.technical?.exitStatus)}>{r.technical?.exitRisk??"—"}</td>
                <td><EvidenceCoverage label="Exit" coverage={r.technical?.exitCoverage} compact /></td>
                <td>{r.candidateLinked===false?"UNLINKED":stated(r.membershipStatus||r.phase3Status,"—")}</td>
                <td><button type="button" className="secondary" onClick={()=>selectTrial(r,"chart")}>Alpaca chart ↓</button></td>
                <td>
                  {trialSheetUrl(r) && <a href={trialSheetUrl(r)} target="_blank" rel="noopener noreferrer" className="trial-sheet-link">Full trial sheet ↗</a>}
                  <button type="button" className="record-select" onClick={()=>selectTrial(r,"overview")}>Research details ↓<small>{stated(r.drug)} · {r.id}</small></button>
                </td>
              </tr>
              {chosen?.id===r.id && gemTrialExpanded[stage] && <tr className="gem-inline-detail-row">
                <td colSpan={25}>
                  <div className="gem-inline-detail-panel" aria-label={r.ticker+" expandable clinical trial and stock details"}>
                    <div className="gem-inline-detail-header">
                      <div><strong>TRIAL · {stated(r.drug,r.ticker)} · {r.ticker}</strong>
                        <small>{stated(r.programId)} · {stated(r.nctId,"NO EXACT NCT")} · {stated(r.indication)}</small>
                        <small>{activeScan?"Screen only — no stage membership added":"Added to this list: "+stated(listDates(r).added,"NOT RECORDED")+" · Removed: — (active)"}</small>
                        <span>Selected gold row · expand any detail category below</span></div>
                      <button type="button" className="secondary" onClick={()=>setGemTrialExpanded(current=>({...current,[stage]:false}))}>
                        COLLAPSE TRIAL ↑
                      </button>
                    </div>
                    <div className="gem-inline-sections">
                      <GemInlineSection title="Stock price / Alpaca chart" description="Saved close and volume evidence for this exact permanent program"
                        open={isSectionOpen("chart")} onToggle={()=>toggleSection("chart")}>
                        {r.programId ? <><EntrySignal programId={r.programId} ticker={r.ticker}/><AlpacaStockChart key={r.programId} programId={r.programId} ticker={r.ticker} /></>
                          : <p className="subtle">Alpaca chart awaits a verified permanent Program ID.</p>}
                      </GemInlineSection>
                      <GemInlineSection title="Stock / program details" description="Company, drug, trial identity, SEC financing, FDA evidence"
                        open={isSectionOpen("overview")} onToggle={()=>toggleSection("overview")}>
                        <SourceDetails record={{...r,listAddedOn:listDates(r).added,listRemovedOn:listDates(r).removed}}/>
                        <div className="gem-inline-detail-actions">
                          <button type="button" onClick={()=>{setMasterProgram(r.id);setNav("MASTER");window.scrollTo({top:0,behavior:"smooth"});}}>Gold Master Chart ↗</button>
                          <button type="button" onClick={()=>selectCandidate(r,stage)}>Open autosaved checklist ↗</button>
                        </div>
                      </GemInlineSection>
                      <GemInlineSection title="Clinical trial full record" description="Exact NCT registry fields, results and reported p-values"
                        open={isSectionOpen("trial")} onToggle={()=>toggleSection("trial")}>
                        {trialSheetUrl(r) ? <TrialFields key={r.id} row={r} onClose={()=>toggleSection("trial")}/>
                          : <p className="subtle">No exact NCT clinical-trial record linked to this program. Missing registry evidence is not inferred.</p>}
                      </GemInlineSection>
                      <GemInlineSection title="Entry and exit scores" description="Weighted evidence, completeness and risk overrides"
                        open={isSectionOpen("scores")} onToggle={()=>toggleSection("scores")}>
                        <TechnicalPanel record={r}/>
                      </GemInlineSection>
                      <GemInlineSection title="Indicators / targets" description="Market indicators, goal comparison and source gaps"
                        open={isSectionOpen("indicators")} onToggle={()=>toggleSection("indicators")}>
                        <IndicatorParityTables programId={r.programId||"UNREGISTERED"} tech={r.technical}/>
                        <PriorityIndicators record={r}/>
                      </GemInlineSection>
                    </div>
                  </div>
                </td>
              </tr>}
              </Fragment>)}</tbody></table>
            {!rows.length && <p className="subtle">{activeScan?"No passed or needs-verification pipeline records for these selections. Try SUGGESTED or reduce the restrictions; failed records are counted above.":"No matching saved GEM candidates."}</p>}
          </div>

        </div>
      </div>
      <details className="nested-expander">
        <summary>Historical stage transitions — recorded entries, departures and re-entries ({group?.history?.length||0})</summary>
        <div className="table-scroll"><table><thead><tr><th>Program ID</th><th>Ticker</th><th>Drug</th><th>Date Added</th><th>Date Removed</th><th>Cycle</th><th>Reason / status</th></tr></thead>
          <tbody>{(group?.history||[]).map((t,i)=><tr key={t.id+"|"+t.cycle+"|"+i}><td className="permanent-id">{stated(t.programId)}</td><td>{t.ticker}</td><td>{t.drug}</td><td>{stated(t.enteredOn,"Not recorded")}</td>
            <td>{stated(t.leftOn,"Currently listed")}</td><td>{t.cycle}</td><td>{stated(t.reason,t.status)}</td></tr>)}</tbody></table></div>
        <p className="subtle small">Date Added and Date Removed record source-verified GEM-stage list membership (including separate re-entry cycles), not trial registration, Phase 3, FDA, or financing dates. A blank removal date means this listing cycle is still active.</p>
      </details>
      <details className="nested-expander">
        <summary>Three-level clinical trials and evidence table · ticker → drug/program → trial</summary>
        <Drilldown rows={rows} />
      </details>
    </section>;
  }

  return <div className="migration-workspace">
    <div className="worktop">
      <button type="button" className={top==="PDUFA"?"nav-selected":""} onClick={()=>setTop("PDUFA")}>PDUFA</button>
      <button type="button" className={top==="CALENDAR"?"nav-selected":""} onClick={()=>setTop("CALENDAR")}>PDUFA Calendar</button>
      <button type="button" className="secondary" disabled={refreshing} onClick={()=>{setRefreshing(true);setFetchVersion(v=>v+1);}}>{refreshing ? "Reloading…" : "Reload published sources"}</button>
      <span className="workspace-stage">Published {snapshot?.asOf||"loading"} · Sources refresh within 5 min · No live orders</span>
    </div>
    {top==="PDUFA" && <div className="nav-wrapper">
      <div className="mobile-nav-toggle">
        <strong>Section: {nav==="GEM_JR"?"GEM JR":nav==="MASTER"?"GOLD MASTER CHART":nav}</strong>
        <button type="button" aria-expanded={mobileNavOpen} aria-controls="pdufa-section-navigation"
          onClick={()=>setMobileNavOpen(current=>!current)}>
          {mobileNavOpen ? "Close menu ×" : "☰ Browse sections"}
        </button>
      </div>
      <nav id="pdufa-section-navigation" className="worknav" aria-label="PDUFA sections" data-open={mobileNavOpen?"true":"false"}>
        {([["PIPELINE","PIPELINE"],["GEM_JR","GEM JR"],["GEM","GEM"],["MASTER","GOLD MASTER CHART"],["SCANS","SCANS"],["WT","WT"]] as [Nav,string][]).map(([key,label])=>
          <button type="button" key={key} className={nav===key?"nav-selected":""} aria-current={nav===key?"page":undefined}
            onClick={()=>{setNav(key);setMobileNavOpen(false);}}>{label}</button>)}
      </nav>
    </div>}
    <div className="workspace-overview">
      <div className="master-quicklink"><strong>Gold reference picture recreated as interactive charts.</strong><button type="button" onClick={()=>{setTop("PDUFA");setNav("MASTER");}}>OPEN GOLD MASTER CHART ↗</button></div>
      <p className="workspace-banner"><strong>{snapshot?.mode === "LIVE_READ_ONLY_GITHUB_SOURCE" ? "Latest published original-system data" : "Source fallback / stale data"}.</strong> {snapshot?.disclaimer || "Loading source health."} No new orders or duplicate scans are activated.</p>
      {snapshot?.sourceHealth && <div className="source-health" role="status"><strong>Source health: {snapshot.sourceHealth.state}</strong><span>{snapshot.sourceHealth.regulatoryRows} regulatory programs · {snapshot.sourceHealth.clinicalRows} published clinical trials</span>{snapshot.sourceHealth.issues.length>0 && <ul>{snapshot.sourceHealth.issues.map(issue=><li key={issue}>{issue}</li>)}</ul>}</div>}
    </div>
    {!snapshot && <div className="panel">{fetchError || "Loading published PIPELINE, GEM JR and GEM candidates…"}</div>}
    {snapshot && top==="PDUFA" && nav==="MASTER" && <MasterChart records={pipeline} gemJr={snapshot.members.GEM_JR.rows} gem={snapshot.members.GEM.rows} history={[...(snapshot.members.GEM_JR.history||[]),...(snapshot.members.GEM.history||[])]} watch={tags.watch} trade={tags.trade} sourceHealth={snapshot.sourceHealth} asOf={snapshot.asOf} selectedId={masterProgram} onSelect={setMasterProgram} onInspect={record => {
      const stage: Stage = snapshot.members.GEM.rows.some(r=>r.id===record.id) ? "GEM" : snapshot.members.GEM_JR.rows.some(r=>r.id===record.id) ? "GEM_JR" : "PIPELINE";
      onInspect(record.ticker,stage,record.programId);
    }} />}
    {snapshot && top==="PDUFA" && nav==="PIPELINE" && <section className="pipeline-page">
      <div className="sectionhead"><div><h2>PIPELINE — Clinical and regulatory stages</h2>
        <p className="subtle">Choose stage, date and trial filters, then press DISPLAY TRIALS to list matching records below.</p>
        <a href="https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/" target="_blank" rel="noopener noreferrer" className="streamlit-fallback">OPEN FULL STREAMLIT PIPELINE ↗</a></div>
        <span className="counter">{possible.length.toLocaleString("en-US")} {onlyBand?"screened candidates":"source-recorded trials / programs"}</span></div>
      <p className="subtle pipeline-reconciliation">
        <strong>Streamlit-equivalent Pipeline source total:</strong> {(snapshot.sourceHealth?.pipelineSourceParity?.exactPrograms??pipeline.length).toLocaleString("en-US")}
        {" · Registered trials and results: "+(snapshot.sourceHealth?.pipelineSourceParity?.clinicalAndResults??snapshot.sourceHealth?.clinicalRows??0).toLocaleString("en-US")}
        {" · Regulatory records: "+(snapshot.sourceHealth?.pipelineSourceParity?.regulatoryPrograms??snapshot.sourceHealth?.regulatoryRows??0).toLocaleString("en-US")}
        {onlyBand?" · Optional $300M–$10B screen enabled":" · Full universe (no cap restriction)"}
        {query?" · Text search active":""}
        {" · As of "+snapshot.asOf}
      </p>
      <div className="pipeline-setup-grid">
      <FullTrialDownload />
      <section className="panel pipeline-filters pipeline-filters-compact" aria-labelledby="pipeline-filters-title">
        <div className="pipeline-filter-heading">
          <h3 id="pipeline-filters-title">PIPELINE FILTERS &amp; COUNTS</h3>
          <span className="pipeline-filter-selection" aria-live="polite">{stageFilters.length ? stageFilters.length + " stages" : "All stages"} · {dateFilters.length ? dateFilters.length + " dates" : "All dates"} · {activeTrialFilters(trialFilters)} trial filters</span>
        </div>
        <div className="pipeline-row pipeline-filter-toolbar">
          <label>Search Program ID, ticker, drug, indication, NCT<input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Optional search" /></label>
          <label className="cap-filter"><input type="checkbox" checked={onlyBand} onChange={e=>setOnlyBand(e.target.checked)} />Market cap $300M–$10B only (optional; off by default)</label>
        </div>
        <details className="pipeline-filter-details" open>
          <summary>Choose stages, PDUFA dates and trial filters <span>{stageFilters.length + dateFilters.length + activeTrialFilters(trialFilters)} selected</span></summary>
          <p className="subtle">Leave a group unchecked to include all records. Selected groups combine together; stage and date counts reflect your trial filters. Trial-checkbox counts show matches with your other selections.</p>
          <div className="filter-columns pipeline-three-filter-columns">
            {[
              { title: "STAGE COUNTS", description: "Available by current stage", total: "PHASE TOTAL", items: stageCounts, selected: stageFilters, setter: setStageFilters },
              { title: "DATE TRIAL COUNTS", description: "Available by PDUFA countdown", total: "DATE TOTAL", items: dateCounts, selected: dateFilters, setter: setDateFilters },
            ].map(group => <fieldset className="filter-count-group" key={group.title}>
              <legend>{group.title}</legend>
              <div className="filter-group-total"><span>{group.description} · {group.total}</span><strong>{possible.length.toLocaleString("en-US")}</strong></div>
              <div className="filter-checks">{group.items.map(item => <label className={group.selected.includes(item.label) ? "filter-option filter-option-selected" : "filter-option"} key={item.label}>
                <input type="checkbox" aria-label={item.label} checked={group.selected.includes(item.label)} onChange={() => toggleFilter(group.selected, item.label, group.setter)} />
                <span className="filter-label-text">{item.label}</span><b className="filter-count" title="Available trials / programs">{item.count.toLocaleString("en-US")}</b>
                <span className="filter-mini-track" aria-hidden="true"><span style={{ width: (item.count / Math.max(1, ...group.items.map(value => value.count)) * 100) + "%" }} /></span>
              </label>)}</div>
            </fieldset>)}
            <TrialQualificationFilters rows={pipeline} countRows={qualificationBase} value={trialFilters} onChange={setTrialFilters} asOf={snapshot.asOf} ready={snapshot.trialFilterSchema === 1} />
          </div>
        </details>
        <div className="pipeline-actions pipeline-display-actions">
          <button type="button" onClick={displayTrials}>DISPLAY TRIALS · {counted.length.toLocaleString("en-US")} matching</button>
          <button type="button" className="secondary" onClick={clearPipelineSelections}>CLEAR SELECTIONS</button>
        </div>
        {selectionsChanged && <p className="filter-pending" role="status">Selections changed — press DISPLAY TRIALS to update the list.</p>}
      </section>
      </div>
      <div ref={pipelineDataRef} className="pipeline-results-anchor">
        {displayFilters ? <PipelineData key={appliedKey + "|" + displayVersion + "|" + snapshot.asOf} rows={displayed}
          filterSummary={"Stages: " + (displayFilters.stages.join(", ") || "All") + " · PDUFA dates: " + (displayFilters.dates.join(", ") || "All")
            + (displayFilters.query ? " · Search: " + displayFilters.query : "") + (displayFilters.onlyBand ? " · Market cap: $300M–$10B" : "")
            + (activeTrialFilters(displayFilters.trial) ? " · " + trialFilterSummary(displayFilters.trial) : "")} /> :
          <section className="panel pipeline-data"><h3>PIPELINE DATA</h3><p className="subtle">Choose stage, date and trial filters above, then press DISPLAY TRIALS to show the matching trials and programs.</p></section>}
      </div>
    </section>}
    {snapshot && top==="PDUFA" && (nav==="GEM_JR" || nav==="GEM") && <div className="gems-page">
      <div className="sectionhead"><div><h2>{nav==="GEM_JR"?"GEM JR":"GEM"} — Candidate research</h2><p className="subtle">The same permanent Program ID follows an exact candidate from Pipeline through GEM JR, GEM and WT. An observed junior does not automatically qualify as GEM.</p></div>
      <label>Find candidate<input value={gemQuery} onChange={e=>setGemQuery(e.target.value)} placeholder="Ticker or drug" /></label></div>
      <div className="gems-two-blocks">{gemBlock(nav==="GEM_JR"?"GEM_JR":"GEM")}</div>
    </div>}
    {snapshot && top==="PDUFA" && nav==="WT" && <div className="wt-page">
      <h2>WT — Permanent Program ID Watchlist & Trading Research</h2>
      <p className="subtle">WT displays the identical GEM JR/GEM entry-strength and exit-risk scores for each permanent Program ID, including evidence coverage and safety overrides. Different drugs and trials remain independent. Research only — no broker orders.</p>
      <p aria-live="polite" className="saveState">{wtStatus}</p>
      <div className="wt-panels">
      {(["watch","trade"] as const).map(kind=><section className="panel" key={kind}>
        <div className="sectionhead"><h3>{kind==="watch"?"WATCHLIST — EXACT PROGRAMS":"TRADING RESEARCH — EXACT PROGRAMS / NO ORDERS"}</h3><span className="counter">{tags[kind].length} tracked programs</span></div>
        {tags[kind].length===0 && <p className="subtle">No exact programs selected yet. Use W/T buttons beside Program IDs in PIPELINE or GEM.</p>}
        <div className="wt-program-masonry">
        {tags[kind].map(programId=>{
          const selectedRecord=byProgram.get(programId);
          const saved=storedIdentities.find(x=>x.programId===programId);
          const ticker=selectedRecord?.ticker||saved?.ticker||"";
          return <div className="wt-stock" key={programId}>
            <div className="wt-identity">
              <strong className="permanent-id">{programId}</strong>
              <h3>{ticker||"SOURCE NOT CURRENT"}</h3>
              <p className="subtle">{stated(selectedRecord?.drug||saved?.drug)} · {stated(selectedRecord?.id||saved?.id,"historical exact program")}</p>
              {!selectedRecord && <p className="subtle">Program remains stored in Neon even when no longer in the latest published source. Historical identity has not been removed.</p>}
              <button type="button" onClick={()=>mark(programId,kind==="watch"?"trade":"watch")}>{kind==="watch"?"MOVE PROGRAM TO TRADING RESEARCH":"RETURN PROGRAM TO WATCHLIST"}</button>
              <button type="button" className="secondary" onClick={()=>mark(programId,"clear")}>REMOVE PROGRAM TAG</button>
              {selectedRecord && <button type="button" className="secondary" onClick={()=>{setMasterProgram(selectedRecord.id);setNav("MASTER");}}>Open program Master Chart</button>}
              {ticker && <button type="button" className="secondary" onClick={()=>onInspect(ticker,"PIPELINE",programId)}>Open exact program checklist</button>}
            </div>
            <div className="wt-research-column">
              {ticker ? <>
                <EntrySignal ticker={ticker} programId={programId}/>
                <AlpacaStockChart ticker={ticker} programId={programId} compact />
                <WTIndicatorDetails programId={programId} record={selectedRecord} ticker={ticker} />
              </> : <p className="subtle">Ticker unavailable in stored identity; price chart withheld.</p>}
            </div>
          </div>;
        })}
        </div>
      </section>)}
      </div>
      {(legacyTags.watch.length>0||legacyTags.trade.length>0) && <section className="panel legacy-tags">
        <h3>Legacy ticker-only selections — preserved for review</h3>
        <p className="subtle">Older WT tags did not identify a particular drug or trial. They remain unchanged; choose an exact permanent Program ID below to add it to the new WT lists. Nothing is assigned automatically.</p>
        {(["watch","trade"] as const).map(kind=>legacyTags[kind].length>0 &&
          <div key={kind}><h4>{kind==="watch"?"Previous WATCH tickers":"Previous TRADING tickers"}</h4>
            {legacyTags[kind].map(ticker=><div key={kind+"|"+ticker} className="legacy-ticker-row">
              <strong>{ticker}</strong>
              {(byTicker.get(ticker)||[]).map(r=><button type="button" key={r.id} disabled={!r.programId||!tagsReady}
                onClick={()=>mark(r.programId||"",kind)}>{stated(r.programId)} · {stated(r.drug,r.id)}</button>)}
              {!byTicker.get(ticker)?.length && <span>Original ticker retained; no current exact-program match in published sources</span>}
            </div>)}
          </div>)}
      </section>}
    </div>}
    {top==="PDUFA" && nav==="SCANS" && <PublishedScansPanel />}
    {snapshot && top==="CALENDAR" && <section className="panel"><h2>PDUFA Calendar — Saved event snapshot</h2>
      <p className="subtle">Reported dates only, not FDA-confirmed future events unless the source explicitly verifies them.</p>
      <div className="table-scroll"><table><thead><tr><th>PDUFA</th><th>Program ID</th><th>Ticker</th><th>Drug</th><th>Program</th><th>Days away</th><th>FDA/source</th></tr></thead>
        <tbody>{pipeline.filter(r=>daysAway(r.pdufaDate)!==null && (daysAway(r.pdufaDate)||0)>=0).sort((a,b)=>(daysAway(a.pdufaDate)||0)-(daysAway(b.pdufaDate)||0)).map(r=><tr key={r.id}><td>{r.pdufaDate}</td><td className="permanent-id">{stated(r.programId)}</td><td>{r.ticker}</td><td>{r.drug}</td><td>{r.id}</td><td>{daysAway(r.pdufaDate)}</td><td>{stated(r.checkStatus)}</td></tr>)}</tbody>
      </table></div></section>}
  </div>;
}
