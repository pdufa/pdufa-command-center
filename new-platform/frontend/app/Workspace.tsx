"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import MasterChart from "./MasterChart";

type Stage = "PIPELINE" | "GEM_JR" | "GEM";
type Factor = { label: string; weight: number; earned: number | null; evidence: string };
type ResearchTechnical = {
  benchmarks?: { phase3: boolean; secondFinancing: boolean; bothConfirmed: boolean; warning: string; readoutDate: string; firstClose: string; secondClose: string };
  tradeCall?: string; tradeReason?: string;
  marketDate?: string; marketSource?: string; eodFresh?: boolean;
  close?: number | null; sma20?: number | null; sma50?: number | null;
  rsi14?: number | null; rvol?: number | null; avgDollarVolume20?: number | null;
  closingSupport20?: number | null; macd?: { macd: number | null; signal: number | null; bullish: boolean } | null;
  base?: { status: string; support: number | null; resistance: number | null; touches: number | null; widthPct: number | null; contractionRatio: number | null; volumeRatio: number | null; breakoutRvol: number | null };
  dataGaps?: string; entry?: number | null; entryCoverage?: number; entryStatus?: string;
  exitRisk?: number | null; exitCoverage?: number; exitStatus?: string;
  entryFactors?: Factor[]; exitFactors?: Factor[];
  runwayMonths?: number | null; runwayGate?: string; runwayReason?: string; runwaySource?: string; runwayAsOf?: string;
  riskAlerts?: string[]; researchOnly?: boolean;
};

type Candidate = {
  id: string; programId?: string; eventKey?: string; ticker: string; company?: string;
  drug?: string; indication?: string; nctId?: string; pdufaDate?: string;
  phase3Date?: string; phase3Status?: string; phase3Source?: string;
  stage?: string; outcome?: string; marketCap?: number | null; capInRange?: boolean;
  capChecked?: string; capSource?: string; financingStatus?: string; financingDate?: string;
  financingSource?: string; financingEvidence?: string; fdaSource?: string;
  lastChecked?: string; approvalProbability?: string; checkStatus?: string;
  pValues?: string; evidenceSummary?: string; signal?: string;
  membershipStatus?: string; firstFound?: string; lastSeen?: string; candidateLinked?: boolean;
  technical?: ResearchTechnical;
};
type StageHistory = { id: string; programId?: string; ticker: string; drug: string; enteredOn: string; leftOn: string; reason: string; status: string; cycle: number };
type StageData = { asOf?: string; rows: Candidate[]; history?: StageHistory[] };
type Snapshot = {
  mode: string; asOf: string; disclaimer: string;
  marketCapRange: { min: number; max: number };
  pipeline: Candidate[]; members: { GEM_JR: StageData; GEM: StageData };
  sourceHealth?: { state: string; issues: string[]; clinicalRows: number; regulatoryRows: number; publishedScan?: { state?: string; finishedAt?: string; complete?: boolean; sources?: Record<string,{status?:string;finished_at?:string}> } | null };
};
type Nav = "PIPELINE" | "GEMS" | "MASTER" | "SCANS" | "WT";
type TopNav = "PDUFA" | "CALENDAR";
type Tags = { watch: string[]; trade: string[] };
const TAG_KEY = "pdufa_new_program_watch_trade_v1";
const LEGACY_TAG_KEY = "pdufa_new_watch_trade_v1";
const STAGES = ["Early Phase 1", "Phase 1", "Phase 1/2", "Phase 2", "Phase 2/3", "Phase 3", "Phase 3 Results", "NDA/BLA Submission", "FDA Acceptance", "PDUFA Decision", "Post-Decision", "Phase 4", "Not Applicable", "Unknown"];
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
function uniqueRows(rows: Candidate[]) {
  const seen = new Set<string>();
  return rows.filter(row => { if (!row.id || seen.has(row.id)) return false; seen.add(row.id); return true; });
}
function scoreNum(number?: number | null, digits = 2, suffix = "") {
  return typeof number === "number" && Number.isFinite(number) ? number.toFixed(digits) + suffix : "NOT VERIFIED";
}
function Goals({ record }: { record: Candidate | null }) {
  const tech = record?.technical;
  const pass = (value?: boolean) => value === true;
  const rows: [string,string,string,boolean][] = [
    ["Market capitalization", money(record?.marketCap), "$300M–$10B",pass(record?.capInRange)],
    ["Phase 3 verified positive", tech?.benchmarks?.phase3 ? "PASS — source checked" : stated(record?.phase3Status), "Exact successful primary endpoint + source", pass(tech?.benchmarks?.phase3)],
    ["Second post-readout financing", tech?.benchmarks?.secondFinancing ? "PASS — SEC checked" : "NOT CLEARED", "Two distinct SEC-verified funded closes after readout", pass(tech?.benchmarks?.secondFinancing)],
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
      <span>{label}</span><span className={verified ? "verified" : "unknown-value"}>{observed}</span><span className="gold-goal">{goal}</span>
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
    <p><strong>Entry:</strong> {stated(x.entryStatus)}</p><p><strong>Exit:</strong> {stated(x.exitStatus)}</p>
    <p><strong>Closing base:</strong> {stated(x.base?.status)} · support {scoreNum(x.base?.support,2)} / resistance {scoreNum(x.base?.resistance,2)}</p>
    <p><strong>MACD:</strong> {scoreNum(x.macd?.macd,3)} · Signal {scoreNum(x.macd?.signal,3)} (close-based; no intraday VWAP)</p>
    <p><strong>SEC cash runway:</strong> {stated(x.runwayGate)} · {stated(x.runwayReason)}</p>
    {x.riskAlerts?.length ? <div className="risk-warnings"><strong>Source warnings</strong>{x.riskAlerts.map(alert=><p key={alert}>{alert}</p>)}</div> : null}
    <details><summary>All weighted scoring factors and missing evidence</summary>
      <div className="score-factor-groups">{([["Entry strength",x.entryFactors||[]],["Exit risk",x.exitFactors||[]]] as [string,Factor[]][]).map(([name,items])=>
        <div key={name}><h4>{name}</h4>{items.map(item=><div className="score-factor" key={item.label}><strong>{item.label}</strong>
          <span>{item.earned==null ? "NOT AVAILABLE" : item.earned} / {item.weight}</span>
          <small>{item.evidence}</small></div>)}</div>)}</div>
    </details>
    <p className="subtle small">GEM membership and numerical scores do not authorize trading. No order, stop, ATR, spread or position is inferred. {stated(x.dataGaps,"Missing observations remain unscored.")}</p>
    {evidence(x.marketSource) && <a target="_blank" rel="noopener noreferrer" href={x.marketSource}>Saved market source ↗</a>}
    {evidence(x.runwaySource) && <a target="_blank" rel="noopener noreferrer" href={x.runwaySource}>SEC cash runway evidence ↗</a>}
  </div>;
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
function exportCandidateCsv(rows: Candidate[], name: string) {
  const columns = ["Permanent Program ID","Ticker","Pipeline ID","Drug","Indication","PDUFA","Market cap","Phase 3","Second financing","Entry score","Entry coverage","Exit risk","Exit coverage","Runway","Last seen"];
  const quote = (value: unknown) => '"'+String(value??"").replaceAll('"','""')+'"';
  const data = rows.map(x=>[x.programId,x.ticker,x.id,x.drug,x.indication,x.pdufaDate,x.marketCap,x.phase3Status,x.financingStatus,x.technical?.entry,x.technical?.entryCoverage,x.technical?.exitRisk,x.technical?.exitCoverage,x.technical?.runwayGate,x.lastSeen]);
  const body = [columns,...data].map(a=>a.map(quote).join(",")).join("\r\n");
  const blob = new Blob([body],{type:"text/csv;charset=utf-8"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href=url;
  link.download=name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1200);
}
function SourceDetails({ record }: { record: Candidate }) {
  return (
    <div className="program-details">
      <div className="trial-details">
        <div><strong>Permanent Program ID</strong><span className="permanent-id">{stated(record.programId,"REGISTRY UNAVAILABLE")}</span></div>
        <div><strong>Exact Pipeline source key</strong><span>{record.id}</span></div>
        <div><strong>Drug / indication</strong><span>{stated(record.drug)} / {stated(record.indication)}</span></div>
        <div><strong>ClinicalTrials.gov NCT</strong><span>{stated(record.nctId || (record.id.startsWith("TRIAL|") ? record.id.slice(6) : ""))}</span></div>
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
        {companies.map(item => (
          <details key={item.id} className="drill-program">
            <summary><strong>{stated(item.drug)}</strong><span><strong className="permanent-id">{stated(item.programId)}</strong> · {stated(item.indication, "program research")} · {stated(item.pdufaDate, "no date")}</span></summary>
            <div className="drill-evidence"><strong>Trial details and verification</strong><SourceDetails record={item} /></div>
          </details>
        ))}
      </details>
    ))}
    {grouped.length === 0 && <p className="subtle">No exact-program records match these filters.</p>}
  </div>;
}
function Chart({ ticker }: { ticker: string }) {
  const url = "https://s.tradingview.com/widgetembed/?symbol=" + encodeURIComponent(ticker) + "&interval=D&symboledit=1&saveimage=0&toolbarbg=F1F3F6&theme=light&style=1";
  return <div className="chart-wrap">
    <iframe title={ticker + " TradingView stock chart"} loading="lazy" src={url} referrerPolicy="strict-origin-when-cross-origin" />
    <a href={"https://www.tradingview.com/symbols/" + encodeURIComponent(ticker) + "/"} target="_blank" rel="noopener noreferrer">Open full TradingView chart ↗</a>
  </div>;
}

export default function Workspace({ onInspect }: { onInspect: (ticker: string, stage: Stage) => void }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [fetchVersion, setFetchVersion] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [fetchError, setFetchError] = useState("");
  const [top, setTop] = useState<TopNav>("PDUFA");
  const [nav, setNav] = useState<Nav>("PIPELINE");
  const [masterProgram, setMasterProgram] = useState("");
  const [stageFilters, setStageFilters] = useState<string[]>([]);
  const [dateFilters, setDateFilters] = useState<string[]>([]);
  const [query, setQuery] = useState("");
  const [onlyBand, setOnlyBand] = useState(true);
  const [applied, setApplied] = useState(false);
  const [sort, setSort] = useState("PDUFA");
  const [pipelinePage, setPipelinePage] = useState(0);
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
    fetch("/api/workspace", { cache: "no-store", signal: ctrl.signal })
      .then(async r => { if (!r.ok) throw new Error("Published source unavailable: " + r.status); return r.json(); })
      .then((data: Snapshot) => { if (!ctrl.signal.aborted) { setSnapshot(data); setFetchError(""); setRefreshing(false); } })
      .catch(error => { if (!ctrl.signal.aborted) { setFetchError(String(error)); setRefreshing(false); } });
    return () => ctrl.abort();
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
  const possible = useMemo(() => pipeline.filter(r =>
    (!onlyBand || r.capInRange) &&
    (!query || [r.ticker,r.company,r.drug,r.indication,r.nctId,r.programId,r.id].some(t => (t || "").toLowerCase().includes(query.toLowerCase())))
  ), [pipeline, onlyBand, query]);
  const counted = useMemo(() => possible.filter(r =>
    (stageFilters.length === 0 || stageFilters.includes(r.stage || "Unknown")) &&
    (dateFilters.length === 0 || dateFilters.includes(dateBand(r)))
  ), [possible, stageFilters, dateFilters]);
  const shown = useMemo(() => {
    if (!applied) return [];
    return counted
      .filter(r => stageFilters.includes(r.stage || "Unknown") && dateFilters.includes(dateBand(r)))
      .sort((a,b) => sort === "TICKER" ? a.ticker.localeCompare(b.ticker) : (daysAway(a.pdufaDate) ?? 99999) - (daysAway(b.pdufaDate) ?? 99999));
  }, [applied, counted, stageFilters, dateFilters, sort]);
  const pageSize = 100;
  const pageCount = Math.max(1, Math.ceil(shown.length / pageSize));
  const visiblePipeline = shown.slice(Math.min(pipelinePage, pageCount - 1) * pageSize, (Math.min(pipelinePage, pageCount - 1) + 1) * pageSize);
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
    setApplied(false);
    setPipelinePage(0);
  }
  const stageCounts = STAGES.map(stage => ({label:stage,count:counted.filter(r => r.stage === stage).length})).filter(x => x.count);
  const dateCounts = BANDS.map(band => ({label:band,count:counted.filter(r => dateBand(r) === band).length})).filter(x => x.count);

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
  function selectCandidate(record: Candidate, stage: Stage) { onInspect(record.ticker,stage); }

  function gemBlock(stage: "GEM_JR" | "GEM") {
    const group = snapshot?.members[stage];
    const rows = (group?.rows || []).filter(r => r.ticker.toLowerCase().includes(gemQuery.toLowerCase()) || (r.drug||"").toLowerCase().includes(gemQuery.toLowerCase()));
    const chosen = rows.find(r => r.id === selected[stage]) || rows[0] || null;
    return <section className={"gem-section " + (stage==="GEM" ? "gem-purple" : "gem-blue")} key={stage}>
      <div className="gem-heading">
        <div><h2>{stage==="GEM"?"GEM":"GEM JR"} · Candidate research</h2>
          <p>{stage==="GEM"?"Two-benchmark membership; independent dilution/entry gates still required":"Early evidence watchlist; not GEM-qualified by ticker alone"}</p></div>
        <span className="gem-count">{rows.length} programs · {stated(group?.asOf, "snapshot undated")}</span>
      </div>
      <div className="gem-body">
        <aside className="gem-criteria">
          <h3>Qualification criteria</h3>
          <p className="subtle">Source observations beside target levels for the selected program.</p>
          <Goals record={chosen} />
        </aside>
        <div className="gem-table-panel">
          <div className="sectionhead"><h3>Saved exact-program candidates</h3><button type="button" className="secondary" onClick={()=>exportCandidateCsv(rows,stage.toLowerCase()+"-programs.csv")}>Export CSV</button></div>
          <div className="table-scroll">
            <table><thead><tr><th>W/T</th><th>Program ID</th><th>Ticker</th><th>Drug / exact program</th><th>PDUFA</th><th>Cap</th><th>Status</th></tr></thead>
              <tbody>{rows.map(r => <tr key={r.id} className={chosen?.id===r.id?"selected-record":""}>
                <td><div className="wt-pair">{wtButton(r,"watch")}{wtButton(r,"trade")}</div></td>
                <td><strong className="permanent-id">{stated(r.programId)}</strong></td>
                <td><button type="button" className="ticker-select" onClick={()=>setSelected({...selected,[stage]:r.id})}>{r.ticker}</button></td>
                <td><button type="button" className="record-select" onClick={()=>setSelected({...selected,[stage]:r.id})}>{stated(r.drug)}<small>{r.id}</small></button></td>
                <td>{stated(r.pdufaDate,"—")}</td>
                <td>{money(r.marketCap)}</td>
                <td>{r.candidateLinked===false?"UNLINKED":stated(r.phase3Status)}</td>
              </tr>)}</tbody></table>
            {!rows.length && <p className="subtle">No matching saved GEM candidates.</p>}
          </div>
          {chosen && <div className="gem-profile">
            <div className="sectionhead"><h3>{chosen.ticker} · {stated(chosen.drug)}</h3>
              <button type="button" onClick={()=>{setMasterProgram(chosen.id);setNav("MASTER");window.scrollTo({top:0,behavior:"smooth"});}}>Gold Master Chart ↗</button>
              <button type="button" onClick={()=>selectCandidate(chosen,stage)}>Open autosaved checklist ↗</button></div>
            <SourceDetails record={chosen} />
            <TechnicalPanel record={chosen} />
            <PriorityIndicators record={chosen} />
          </div>}
        </div>
      </div>
      <details className="nested-expander">
        <summary>Historical stage transitions — recorded entries, departures and re-entries ({group?.history?.length||0})</summary>
        <div className="table-scroll"><table><thead><tr><th>Program ID</th><th>Ticker</th><th>Drug</th><th>Entry</th><th>Departure</th><th>Cycle</th><th>Reason / status</th></tr></thead>
          <tbody>{(group?.history||[]).map((t,i)=><tr key={t.id+"|"+t.cycle+"|"+i}><td className="permanent-id">{stated(t.programId)}</td><td>{t.ticker}</td><td>{t.drug}</td><td>{stated(t.enteredOn,"Not recorded")}</td>
            <td>{stated(t.leftOn,"Currently listed")}</td><td>{t.cycle}</td><td>{stated(t.reason,t.status)}</td></tr>)}</tbody></table></div>
        <p className="subtle small">Dates come only from complete published stage snapshots; no historical membership dates are inferred from Phase 3 or SEC evidence.</p>
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
    {top==="PDUFA" && <nav className="worknav" aria-label="PDUFA sections">
      {([["PIPELINE","PIPELINE"],["GEMS","GEM JR + GEM"],["MASTER","GOLD MASTER CHART"],["SCANS","SCANS"],["WT","WT"]] as [Nav,string][]).map(([key,label])=>
        <button type="button" key={key} className={nav===key?"nav-selected":""} onClick={()=>setNav(key)}>{label}</button>)}
    </nav>}
    <div className="master-quicklink"><strong>Gold reference picture recreated as interactive charts.</strong><button type="button" onClick={()=>{setTop("PDUFA");setNav("MASTER");}}>OPEN GOLD MASTER CHART ↗</button></div>
    <p className="workspace-banner"><strong>{snapshot?.mode === "LIVE_READ_ONLY_GITHUB_SOURCE" ? "Latest published original-system data" : "Source fallback / stale data"}.</strong> {snapshot?.disclaimer || "Loading source health."} No new orders or duplicate scans are activated.</p>
    {snapshot?.sourceHealth && <div className="source-health" role="status"><strong>Source health: {snapshot.sourceHealth.state}</strong><span>{snapshot.sourceHealth.regulatoryRows} regulatory programs · {snapshot.sourceHealth.clinicalRows} published clinical trials</span>{snapshot.sourceHealth.issues.length>0 && <ul>{snapshot.sourceHealth.issues.map(issue=><li key={issue}>{issue}</li>)}</ul>}</div>}
    {!snapshot && <div className="panel">{fetchError || "Loading saved Streamlit candidates…"}</div>}
    {snapshot && top==="PDUFA" && nav==="MASTER" && <MasterChart records={pipeline} gemJr={snapshot.members.GEM_JR.rows} gem={snapshot.members.GEM.rows} history={[...(snapshot.members.GEM_JR.history||[]),...(snapshot.members.GEM.history||[])]} watch={tags.watch} trade={tags.trade} sourceHealth={snapshot.sourceHealth} asOf={snapshot.asOf} selectedId={masterProgram} onSelect={setMasterProgram} />}
    {snapshot && top==="PDUFA" && nav==="PIPELINE" && <section className="pipeline-page">
      <div className="sectionhead"><div><h2>PIPELINE — Clinical and regulatory stages</h2>
        <p className="subtle">Streamlit-compatible workflow: choose both STAGES and DATES, then select SHOW MATCHING TRIALS.</p>
        <a href="https://pdufa-command-center-hvtzovdjssqmzhrlzbbhwu.streamlit.app/" target="_blank" rel="noopener noreferrer" className="streamlit-fallback">OPEN FULL STREAMLIT PIPELINE ↗</a></div>
        <span className="counter">{possible.length} recorded programs in current screening scope</span></div>
      <div className="panel pipeline-filters">
        <h3>PIPELINE FILTERS</h3>
        <div className="filter-columns">
          <div><strong>STAGES · current, not historical</strong><div className="filter-checks">{STAGES.map(s=><label key={s}><input type="checkbox" checked={stageFilters.includes(s)} onChange={()=>toggleFilter(stageFilters,s,setStageFilters)} />{s}</label>)}</div></div>
          <div><strong>DATES · PDUFA countdown</strong><div className="filter-checks">{BANDS.map(s=><label key={s}><input type="checkbox" checked={dateFilters.includes(s)} onChange={()=>toggleFilter(dateFilters,s,setDateFilters)} />{s}</label>)}</div></div>
        </div>
        <div className="pipeline-row"><label>Search Program ID, ticker, drug, indication, NCT<input value={query} onChange={e=>{setQuery(e.target.value);setApplied(false)}} placeholder="Optional search" /></label>
          <label>Order<select value={sort} onChange={e=>{setSort(e.target.value);setApplied(false)}}><option value="PDUFA">Closest PDUFA first</option><option value="TICKER">Ticker A–Z</option></select></label>
          <label className="cap-filter"><input type="checkbox" checked={onlyBand} onChange={e=>{setOnlyBand(e.target.checked);setApplied(false)}} />Market cap $300M–$10B only</label></div>
        <div className="pipeline-actions"><button type="button" disabled={!stageFilters.length||!dateFilters.length} onClick={()=>{setPipelinePage(0);setApplied(true);}}>SHOW MATCHING TRIALS</button>
          <button type="button" className="secondary" onClick={()=>{setApplied(false);setPipelinePage(0);setStageFilters([]);setDateFilters([]);setQuery("");setOnlyBand(true)}}>CLEAR STAGE / DATE</button></div>
      </div>
      <div className="count-panels">
        {([[ "STAGE COUNTS",stageCounts ],["DATE TRIAL COUNTS",dateCounts ]] as const).map(([title,group])=>
          <div className="panel" key={title}><h3>{title}</h3><strong className="count-total">{counted.length} recorded programs</strong>
          <div className="count-bars">{group.map(item=><div className="count-row" key={item.label}><span>{item.label}</span><div className="count-track"><div style={{width:(item.count/Math.max(1,counted.length)*100)+"%"}} /></div><b>{item.count}</b></div>)}</div></div>)}
      </div>
      <section className="panel">
        <div className="sectionhead"><h3>PDUFA TRIALS / PROGRAMS</h3><span className="counter">{shown.length} matches · {visiblePipeline.length} shown</span></div>
        <p className="subtle">{!applied ? "Nothing is displayed until both filters are chosen and SHOW MATCHING TRIALS is pressed." : "Results show up to 100 exact programs per page. Match total includes all pages."}</p>
        <div className="table-scroll"><table><thead><tr><th>W/T</th><th>Program ID</th><th>Ticker</th><th>Current stage</th><th>Drug</th><th>Indication</th><th>Days</th><th>PDUFA</th><th>Cap</th><th>Evidence</th><th>Program</th></tr></thead>
          <tbody>{visiblePipeline.map(r=><tr key={r.id}><td><div className="wt-pair">{wtButton(r,"watch")}{wtButton(r,"trade")}</div></td>
          <td><strong className="permanent-id">{stated(r.programId)}</strong></td>
          <td><button type="button" className="ticker-select" onClick={()=>selectCandidate(r,"PIPELINE")}>{r.ticker}</button></td><td>{stated(r.stage)}</td><td>{stated(r.drug)}</td><td>{stated(r.indication)}</td>
          <td>{daysAway(r.pdufaDate)??"—"}</td><td>{stated(r.pdufaDate,"—")}</td><td>{money(r.marketCap)}</td>
          <td>{stated(r.checkStatus)}</td><td><details><summary>Trial/source</summary><SourceDetails record={r} /></details></td></tr>)}</tbody>
        </table></div>
        {applied && pageCount > 1 && <div className="page-controls">
          <button type="button" className="secondary" disabled={pipelinePage<=0} onClick={()=>setPipelinePage(p=>Math.max(0,p-1))}>← Previous 100</button>
          <strong>Page {Math.min(pipelinePage,pageCount-1)+1} / {pageCount}</strong>
          <button type="button" className="secondary" disabled={pipelinePage>=pageCount-1} onClick={()=>setPipelinePage(p=>Math.min(pageCount-1,p+1))}>Next 100 →</button>
        </div>}
        {applied && <details className="nested-expander"><summary>Three-level Pipeline trial table</summary><Drilldown rows={visiblePipeline}/></details>}
        <p className="subtle small">Pipeline loads the latest published clinical-trial and regulatory records from Streamlit's original sources; a PARTIAL scan does not count as a completed scan. Unknown market caps are excluded from the default screening view.</p>
      </section>
    </section>}
    {snapshot && top==="PDUFA" && nav==="GEMS" && <div className="gems-page">
      <div className="sectionhead"><div><h2>GEM JR + GEM — One research tab, two stage blocks</h2><p className="subtle">The same permanent Program ID follows an exact candidate from Pipeline through GEM JR, GEM and WT. An observed junior does not automatically qualify as GEM.</p></div>
      <label>Find candidate<input value={gemQuery} onChange={e=>setGemQuery(e.target.value)} placeholder="Ticker or drug" /></label></div>
      <div className="gems-two-blocks">{gemBlock("GEM_JR")}{gemBlock("GEM")}</div>
    </div>}
    {snapshot && top==="PDUFA" && nav==="WT" && <div className="wt-page">
      <h2>WT — Permanent Program ID Watchlist & Trading Research</h2>
      <p className="subtle">Each WT selection is attached to one immutable Neon-assigned Program ID, not just a ticker. Different drugs or trials from the same company stay independent. Research only — no broker orders.</p>
      <p aria-live="polite" className="saveState">{wtStatus}</p>
      {(["watch","trade"] as const).map(kind=><section className="panel" key={kind}>
        <div className="sectionhead"><h3>{kind==="watch"?"WATCHLIST — EXACT PROGRAMS":"TRADING RESEARCH — EXACT PROGRAMS / NO ORDERS"}</h3><span className="counter">{tags[kind].length} tracked programs</span></div>
        {tags[kind].length===0 && <p className="subtle">No exact programs selected yet. Use W/T buttons beside Program IDs in PIPELINE or GEM.</p>}
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
              {ticker && <button type="button" className="secondary" onClick={()=>onInspect(ticker,"PIPELINE")}>Open ticker checklist (shared at ticker level)</button>}
            </div>
            {ticker && <Chart ticker={ticker}/>}
          </div>;
        })}
      </section>)}
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
    {snapshot && top==="PDUFA" && nav==="SCANS" && <section className="panel"><h2>SCANS — Published original-system status</h2><p className="subtle">The new dashboard reads published scanner results. The original Streamlit 10 PM Pacific scans continue independently; no second scanner or Alpaca orders are enabled here.</p><p><strong>Last published overnight scan:</strong> {stated(snapshot.sourceHealth?.publishedScan?.finishedAt, "NOT VERIFIED")} · <strong>Status:</strong> {stated(snapshot.sourceHealth?.publishedScan?.state, "NOT AVAILABLE")}</p><p><strong>Live published-source health:</strong> {stated(snapshot.sourceHealth?.state, "UNKNOWN")}</p>{Object.entries(snapshot.sourceHealth?.publishedScan?.sources || {}).map(([name,result])=><div key={name} className="scan-result"><span>{name.replaceAll("_"," ")}</span><strong>{stated(result.status)}</strong></div>)}<p className="subtle">PARTIAL and missing source families are not marked COMPLETE. These are the saved original reports, not proof of a successful new scan.</p></section>}
    {snapshot && top==="CALENDAR" && <section className="panel"><h2>PDUFA Calendar — Saved event snapshot</h2>
      <p className="subtle">Reported dates only, not FDA-confirmed future events unless the source explicitly verifies them.</p>
      <div className="table-scroll"><table><thead><tr><th>PDUFA</th><th>Program ID</th><th>Ticker</th><th>Drug</th><th>Program</th><th>Days away</th><th>FDA/source</th></tr></thead>
        <tbody>{pipeline.filter(r=>daysAway(r.pdufaDate)!==null && (daysAway(r.pdufaDate)||0)>=0).sort((a,b)=>(daysAway(a.pdufaDate)||0)-(daysAway(b.pdufaDate)||0)).map(r=><tr key={r.id}><td>{r.pdufaDate}</td><td className="permanent-id">{stated(r.programId)}</td><td>{r.ticker}</td><td>{r.drug}</td><td>{r.id}</td><td>{daysAway(r.pdufaDate)}</td><td>{stated(r.checkStatus)}</td></tr>)}</tbody>
      </table></div></section>}
  </div>;
}
