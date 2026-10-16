"use client";

import { useEffect, useMemo, useRef, useState } from "react";

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
  id: string; eventKey?: string; ticker: string; company?: string;
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
type StageData = { asOf?: string; rows: Candidate[] };
type Snapshot = {
  mode: string; asOf: string; disclaimer: string;
  marketCapRange: { min: number; max: number };
  pipeline: Candidate[]; members: { GEM_JR: StageData; GEM: StageData };
  sourceHealth?: { state: string; issues: string[]; clinicalRows: number; regulatoryRows: number; publishedScan?: { state?: string; finishedAt?: string; complete?: boolean; sources?: Record<string,{status?:string;finished_at?:string}> } | null };
};
type Nav = "PIPELINE" | "GEMS" | "SCANS" | "WT";
type TopNav = "PDUFA" | "CALENDAR";
type Tags = { watch: string[]; trade: string[] };
const TAG_KEY = "pdufa_new_watch_trade_v1";
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
function SourceDetails({ record }: { record: Candidate }) {
  return (
    <div className="program-details">
      <div className="trial-details">
        <div><strong>Exact Pipeline ID</strong><span>{record.id}</span></div>
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
            <summary><strong>{stated(item.drug)}</strong><span>{stated(item.indication, "program research")} · {stated(item.pdufaDate, "no date")}</span></summary>
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
  const [fetchError, setFetchError] = useState("");
  const [top, setTop] = useState<TopNav>("PDUFA");
  const [nav, setNav] = useState<Nav>("PIPELINE");
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
  const [wtStatus, setWtStatus] = useState("Loading saved W/T labels…");
  const wtVersion = useRef(0);
  const wtCurrent = useRef<Tags>({ watch: [], trade: [] });
  const wtQueue = useRef<Promise<void>>(Promise.resolve());

  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/api/workspace", { cache: "no-store", signal: ctrl.signal })
      .then(async r => { if (!r.ok) throw new Error("Published source unavailable: " + r.status); return r.json(); })
      .then((data: Snapshot) => { if (!ctrl.signal.aborted) setSnapshot(data); })
      .catch(error => { if (!ctrl.signal.aborted) setFetchError(String(error)); });
    return () => ctrl.abort();
  }, []);
  useEffect(() => {
    let local: Tags = { watch: [], trade: [] };
    try {
      const saved = JSON.parse(localStorage.getItem(TAG_KEY) || "{}");
      if (Array.isArray(saved.watch) && Array.isArray(saved.trade)) {
        const valid = (s: unknown) => typeof s === "string" && /^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(s);
        const trade = [...new Set<string>(saved.trade.filter(valid))];
        const watch = [...new Set<string>(saved.watch.filter(valid))].filter(t => !trade.includes(t));
        local = { watch, trade };
      }
    } catch { /* local storage might be disabled */ }
    wtCurrent.current = local;
    setTags(local);
    let cancelled = false;
    async function restore() {
      try {
        const response = await fetch("/api/watch-trade", { cache: "no-store" });
        if (!response.ok) throw new Error("WT storage unavailable");
        let remote = await response.json();
        if (!Array.isArray(remote.watch) || !Array.isArray(remote.trade) || !Number.isSafeInteger(remote.version)) {
          throw new Error("WT state invalid");
        }
        if (remote.version === 0 && (local.watch.length || local.trade.length)) {
          const write = await fetch("/api/watch-trade", {
            method: "PUT", headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ ...local, version: 0 })
          });
          if (!write.ok) throw new Error("Unable to migrate browser W/T tags");
          remote = await write.json();
        }
        if (cancelled) return;
        wtVersion.current = remote.version;
        const canonical: Tags = { watch: remote.watch, trade: remote.trade };
        wtCurrent.current = canonical;
        setTags(canonical);
        setWtStatus("W/T labels stored in Neon PostgreSQL");
      } catch {
        if (!cancelled) setWtStatus("W/T database unavailable — browser copy only; not synchronized");
      } finally {
        if (!cancelled) setTagsReady(true);
      }
    }
    void restore();
    return () => { cancelled = true; };
  }, []);
  useEffect(() => {
    if (!tagsReady) return;
    try { localStorage.setItem(TAG_KEY, JSON.stringify(tags)); } catch { /* keep current memory */ }
  }, [tags, tagsReady]);
  function mark(ticker: string, kind: "watch" | "trade" | "clear") {
    if (!tagsReady) return;
    const prev = wtCurrent.current;
    const updated: Tags = {
      watch: kind === "watch" ? [...new Set([...prev.watch.filter(t => t !== ticker), ticker])].sort() : prev.watch.filter(t => t !== ticker),
      trade: kind === "trade" ? [...new Set([...prev.trade.filter(t => t !== ticker), ticker])].sort() : prev.trade.filter(t => t !== ticker),
    };
    wtCurrent.current = updated;
    setTags(updated);
    setWtStatus("Saving W/T to database…");
    wtQueue.current = wtQueue.current.catch(() => {}).then(async () => {
      const response = await fetch("/api/watch-trade", {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ...updated, version: wtVersion.current })
      });
      if (!response.ok) {
        setWtStatus(response.status === 409 ? "W/T conflict: reload before changing more labels" : "W/T save failed — browser copy only; not synchronized");
        return;
      }
      const saved = await response.json();
      wtVersion.current = saved.version;
      setWtStatus("W/T saved in Neon PostgreSQL");
    }).catch(() => { setWtStatus("W/T save failed — browser copy only; not synchronized"); });
  }

  const pipeline = snapshot?.pipeline || [];
  const possible = useMemo(() => pipeline.filter(r =>
    (!onlyBand || r.capInRange) &&
    (!query || [r.ticker,r.company,r.drug,r.indication,r.nctId].some(t => (t || "").toLowerCase().includes(query.toLowerCase())))
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

  function wtButton(ticker: string, kind: "watch" | "trade") {
    const current = tags[kind].includes(ticker);
    return <button type="button" className={current ? "wt-active" : "wt-btn"} aria-pressed={current}
      onClick={() => mark(ticker, current ? "clear" : kind)} title={kind === "watch" ? "Add to Watchlist" : "Add to Trading research"}>{kind === "watch" ? "W" : "T"}{current ? " ✓" : ""}</button>;
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
          <h3>Saved exact-program candidates</h3>
          <div className="table-scroll">
            <table><thead><tr><th>W/T</th><th>Ticker</th><th>Drug / exact program</th><th>PDUFA</th><th>Cap</th><th>Status</th></tr></thead>
              <tbody>{rows.map(r => <tr key={r.id} className={chosen?.id===r.id?"selected-record":""}>
                <td><div className="wt-pair">{wtButton(r.ticker,"watch")}{wtButton(r.ticker,"trade")}</div></td>
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
              <button type="button" onClick={()=>selectCandidate(chosen,stage)}>Open autosaved checklist ↗</button></div>
            <SourceDetails record={chosen} />
            <TechnicalPanel record={chosen} />
          </div>}
        </div>
      </div>
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
      <span className="workspace-stage">Snapshot {snapshot?.asOf||"loading"} · No live orders</span>
    </div>
    {top==="PDUFA" && <nav className="worknav" aria-label="PDUFA sections">
      {([["PIPELINE","PIPELINE"],["GEMS","GEM JR + GEM"],["SCANS","SCANS"],["WT","WT"]] as [Nav,string][]).map(([key,label])=>
        <button type="button" key={key} className={nav===key?"nav-selected":""} onClick={()=>setNav(key)}>{label}</button>)}
    </nav>}
    <p className="workspace-banner"><strong>{snapshot?.mode === "LIVE_READ_ONLY_GITHUB_SOURCE" ? "Latest published original-system data" : "Source fallback / stale data"}.</strong> {snapshot?.disclaimer || "Loading source health."} No new orders or duplicate scans are activated.</p>
    {snapshot?.sourceHealth && <div className="source-health" role="status"><strong>Source health: {snapshot.sourceHealth.state}</strong><span>{snapshot.sourceHealth.regulatoryRows} regulatory programs · {snapshot.sourceHealth.clinicalRows} published clinical trials</span>{snapshot.sourceHealth.issues.length>0 && <ul>{snapshot.sourceHealth.issues.map(issue=><li key={issue}>{issue}</li>)}</ul>}</div>}
    {!snapshot && <div className="panel">{fetchError || "Loading saved Streamlit candidates…"}</div>}
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
        <div className="pipeline-row"><label>Search ticker, drug, indication, NCT<input value={query} onChange={e=>{setQuery(e.target.value);setApplied(false)}} placeholder="Optional search" /></label>
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
        <div className="table-scroll"><table><thead><tr><th>W/T</th><th>Ticker</th><th>Current stage</th><th>Drug</th><th>Indication</th><th>Days</th><th>PDUFA</th><th>Cap</th><th>Evidence</th><th>Program</th></tr></thead>
          <tbody>{visiblePipeline.map(r=><tr key={r.id}><td><div className="wt-pair">{wtButton(r.ticker,"watch")}{wtButton(r.ticker,"trade")}</div></td>
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
        <p className="subtle small">The source snapshot contains regulatory/program rows only; Streamlit's larger live clinical-trial universe will be added during scanner migration. Unknown market caps are excluded from the default screening view.</p>
      </section>
    </section>}
    {snapshot && top==="PDUFA" && nav==="GEMS" && <div className="gems-page">
      <div className="sectionhead"><div><h2>GEM JR + GEM — One research tab, two stage blocks</h2><p className="subtle">The two membership ledgers stay separate. An observed junior does not automatically qualify as GEM.</p></div>
      <label>Find candidate<input value={gemQuery} onChange={e=>setGemQuery(e.target.value)} placeholder="Ticker or drug" /></label></div>
      <div className="gems-two-blocks">{gemBlock("GEM_JR")}{gemBlock("GEM")}</div>
    </div>}
    {snapshot && top==="PDUFA" && nav==="WT" && <div className="wt-page">
      <h2>WT — Watchlist and Trading research</h2>
      <p className="subtle">W/T labels are stored in your new Neon database, with a browser fallback if disconnected. No broker orders are placed. Charts may be delayed.</p><p aria-live="polite" className="saveState">{wtStatus}</p>
      {(["watch","trade"] as const).map(kind=><section className="panel" key={kind}>
        <div className="sectionhead"><h3>{kind==="watch"?"WATCHLIST":"TRADING RESEARCH — NO ORDERS"}</h3><span className="counter">{tags[kind].length} tickers</span></div>
        {tags[kind].length===0 && <p className="subtle">No tickers yet. Use W/T buttons in Pipeline or GEM candidate rows.</p>}
        {tags[kind].map(ticker=><div className="wt-stock" key={ticker}>
          <div className="wt-identity"><h3>{ticker}</h3><p className="subtle">{byTicker.get(ticker)?.length||0} linked source program(s)</p>
            <button type="button" onClick={()=>mark(ticker,kind==="watch"?"trade":"watch")}>{kind==="watch"?"MOVE TO TRADING":"RETURN TO WATCHLIST"}</button>
            <button type="button" className="secondary" onClick={()=>mark(ticker,"clear")}>REMOVE TAG</button>
            <button type="button" className="secondary" onClick={()=>onInspect(ticker,"PIPELINE")}>Open ticker checklist</button>
          </div>
          <Chart ticker={ticker}/>
        </div>)}
      </section>)}
    </div>}
    {snapshot && top==="PDUFA" && nav==="SCANS" && <section className="panel"><h2>SCANS — Published original-system status</h2><p className="subtle">The new dashboard reads published scanner results. The original Streamlit 10 PM Pacific scans continue independently; no second scanner or Alpaca orders are enabled here.</p><p><strong>Last published overnight scan:</strong> {stated(snapshot.sourceHealth?.publishedScan?.finishedAt, "NOT VERIFIED")} · <strong>Status:</strong> {stated(snapshot.sourceHealth?.publishedScan?.state, "NOT AVAILABLE")}</p><p><strong>Live published-source health:</strong> {stated(snapshot.sourceHealth?.state, "UNKNOWN")}</p>{Object.entries(snapshot.sourceHealth?.publishedScan?.sources || {}).map(([name,result])=><div key={name} className="scan-result"><span>{name.replaceAll("_"," ")}</span><strong>{stated(result.status)}</strong></div>)}<p className="subtle">PARTIAL and missing source families are not marked COMPLETE. These are the saved original reports, not proof of a successful new scan.</p></section>}
    {snapshot && top==="CALENDAR" && <section className="panel"><h2>PDUFA Calendar — Saved event snapshot</h2>
      <p className="subtle">Reported dates only, not FDA-confirmed future events unless the source explicitly verifies them.</p>
      <div className="table-scroll"><table><thead><tr><th>PDUFA</th><th>Ticker</th><th>Drug</th><th>Program</th><th>Days away</th><th>FDA/source</th></tr></thead>
        <tbody>{pipeline.filter(r=>daysAway(r.pdufaDate)!==null && (daysAway(r.pdufaDate)||0)>=0).sort((a,b)=>(daysAway(a.pdufaDate)||0)-(daysAway(b.pdufaDate)||0)).map(r=><tr key={r.id}><td>{r.pdufaDate}</td><td>{r.ticker}</td><td>{r.drug}</td><td>{r.id}</td><td>{daysAway(r.pdufaDate)}</td><td>{stated(r.checkStatus)}</td></tr>)}</tbody>
      </table></div></section>}
  </div>;
}
