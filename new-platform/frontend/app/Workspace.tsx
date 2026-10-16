"use client";

import { useEffect, useMemo, useState } from "react";

type Stage = "PIPELINE" | "GEM_JR" | "GEM";
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
};
type StageData = { asOf?: string; rows: Candidate[] };
type Snapshot = {
  mode: string; asOf: string; disclaimer: string;
  marketCapRange: { min: number; max: number };
  pipeline: Candidate[]; members: { GEM_JR: StageData; GEM: StageData };
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
function Goals({ record }: { record: Candidate | null }) {
  const rows = [
    ["Market cap", record?.marketCap == null ? "NOT VERIFIED" : money(record.marketCap), "$300M–$10B", record?.capInRange === true],
    ["Phase 3 primary endpoint", stated(record?.phase3Status), "Issuer/clinical primary source verified", false],
    ["2nd financing closed", stated(record?.financingStatus), "Two distinct post-Phase-3 funded closings for GEM", record?.financingStatus === "VERIFIED_SECOND_POST_PHASE3_FINANCING"],
    ["Cash runway", "NOT IN SNAPSHOT", "≥12 months; verified filings", false],
    ["FDA approval probability", stated(record?.approvalProbability, "NOT SCORED"), "≥75% if model validated; never assume", false],
    ["Relative volume", "NOT IN SNAPSHOT", "≥1.5× provisional; validate", false],
    ["Entry risk/reward", "NOT IN SNAPSHOT", "≥2:1 before research entry", false],
    ["Exit plan", "NOT IN SNAPSHOT", "Hard stop and catalyst policy before entry", false],
  ] as [string, string, string, boolean][];
  return (
    <div className="goal-table">
      <div className="goal-grid goal-header"><span>Indicator</span><span>Current</span><span>Target / desired level</span></div>
      {rows.map(([indicator, current, target, verified]) => (
        <div className="goal-grid" key={indicator}>
          <span>{indicator}</span><span className={verified ? "verified" : "unknown-value"}>{current}</span>
          <span className="gold-goal">{target}</span>
        </div>
      ))}
    </div>
  );
}
function SourceDetails({ record }: { record: Candidate }) {
  return (
    <div className="program-details">
      <div className="trial-details">
        <div><strong>Exact Pipeline ID</strong><span>{record.id}</span></div>
        <div><strong>Drug / indication</strong><span>{stated(record.drug)} / {stated(record.indication)}</span></div>
        <div><strong>ClinicalTrials.gov NCT</strong><span>{stated(record.nctId)}</span></div>
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
  const [gemQuery, setGemQuery] = useState("");
  const [selected, setSelected] = useState<Record<string, string>>({});
  const [tags, setTags] = useState<Tags>({ watch: [], trade: [] });
  const [tagsReady, setTagsReady] = useState(false);

  useEffect(() => {
    const ctrl = new AbortController();
    fetch("/api/workspace", { cache: "no-store", signal: ctrl.signal })
      .then(async r => { if (!r.ok) throw new Error("Source snapshot unavailable: " + r.status); return r.json(); })
      .then((data: Snapshot) => { if (!ctrl.signal.aborted) setSnapshot(data); })
      .catch(error => { if (!ctrl.signal.aborted) setFetchError(String(error)); });
    return () => ctrl.abort();
  }, []);
  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem(TAG_KEY) || "{}");
      if (Array.isArray(saved.watch) && Array.isArray(saved.trade)) {
        const valid = (s: unknown) => typeof s === "string" && /^[A-Z0-9][A-Z0-9.-]{0,14}$/.test(s);
        const trade = [...new Set<string>(saved.trade.filter(valid))];
        const watch = [...new Set<string>(saved.watch.filter(valid))].filter(t => !trade.includes(t));
        setTags({ watch, trade });
      }
    } catch { /* Browser may block local storage; lists remain temporary. */ }
    setTagsReady(true);
  }, []);
  useEffect(() => {
    if (!tagsReady) return;
    try { localStorage.setItem(TAG_KEY, JSON.stringify(tags)); } catch { /* keep live session */ }
  }, [tags, tagsReady]);
  function mark(ticker: string, kind: "watch" | "trade" | "clear") {
    setTags(prev => ({
      watch: kind === "watch" ? [...new Set([...prev.watch, ticker])].sort() : prev.watch.filter(t => t !== ticker),
      trade: kind === "trade" ? [...new Set([...prev.trade, ticker])].sort() : prev.trade.filter(t => t !== ticker),
    }));
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
    <p className="workspace-banner"><strong>Read-only migrated source snapshot.</strong> Stage histories are exact-program evidence, not investment ratings. W/T labels do not place trades or affect the original Streamlit platform.</p>
    {!snapshot && <div className="panel">{fetchError || "Loading saved Streamlit candidates…"}</div>}
    {snapshot && top==="PDUFA" && nav==="PIPELINE" && <section className="pipeline-page">
      <div className="sectionhead"><div><h2>PIPELINE — Clinical and regulatory stages</h2>
        <p className="subtle">Streamlit-compatible workflow: choose both STAGES and DATES, then select SHOW MATCHING TRIALS.</p></div>
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
        <div className="pipeline-actions"><button type="button" disabled={!stageFilters.length||!dateFilters.length} onClick={()=>setApplied(true)}>SHOW MATCHING TRIALS</button>
          <button type="button" className="secondary" onClick={()=>{setApplied(false);setStageFilters([]);setDateFilters([]);setQuery("");setOnlyBand(true)}}>CLEAR STAGE / DATE</button></div>
      </div>
      <div className="count-panels">
        {([[ "STAGE COUNTS",stageCounts ],["DATE TRIAL COUNTS",dateCounts ]] as const).map(([title,group])=>
          <div className="panel" key={title}><h3>{title}</h3><strong className="count-total">{counted.length} recorded programs</strong>
          <div className="count-bars">{group.map(item=><div className="count-row" key={item.label}><span>{item.label}</span><div className="count-track"><div style={{width:(item.count/Math.max(1,counted.length)*100)+"%"}} /></div><b>{item.count}</b></div>)}</div></div>)}
      </div>
      <section className="panel">
        <div className="sectionhead"><h3>PDUFA TRIALS / PROGRAMS</h3><span className="counter">{shown.length} displayed</span></div>
        <p className="subtle">{!applied ? "Nothing is displayed until both filters are chosen and SHOW MATCHING TRIALS is pressed." : "Each table row is an exact program; counts reconcile to displayed rows."}</p>
        <div className="table-scroll"><table><thead><tr><th>W/T</th><th>Ticker</th><th>Current stage</th><th>Drug</th><th>Indication</th><th>Days</th><th>PDUFA</th><th>Cap</th><th>Evidence</th><th>Program</th></tr></thead>
          <tbody>{shown.map(r=><tr key={r.id}><td><div className="wt-pair">{wtButton(r.ticker,"watch")}{wtButton(r.ticker,"trade")}</div></td>
          <td><button type="button" className="ticker-select" onClick={()=>selectCandidate(r,"PIPELINE")}>{r.ticker}</button></td><td>{stated(r.stage)}</td><td>{stated(r.drug)}</td><td>{stated(r.indication)}</td>
          <td>{daysAway(r.pdufaDate)??"—"}</td><td>{stated(r.pdufaDate,"—")}</td><td>{money(r.marketCap)}</td>
          <td>{stated(r.checkStatus)}</td><td><details><summary>Trial/source</summary><SourceDetails record={r} /></details></td></tr>)}</tbody>
        </table></div>
        {applied && <details className="nested-expander"><summary>Three-level Pipeline trial table</summary><Drilldown rows={shown}/></details>}
        <p className="subtle small">The source snapshot contains regulatory/program rows only; Streamlit's larger live clinical-trial universe will be added during scanner migration. Unknown market caps are excluded from the default screening view.</p>
      </section>
    </section>}
    {snapshot && top==="PDUFA" && nav==="GEMS" && <div className="gems-page">
      <div className="sectionhead"><div><h2>GEM JR + GEM — One research tab, two stage blocks</h2><p className="subtle">The two membership ledgers stay separate. An observed junior does not automatically qualify as GEM.</p></div>
      <label>Find candidate<input value={gemQuery} onChange={e=>setGemQuery(e.target.value)} placeholder="Ticker or drug" /></label></div>
      {gemBlock("GEM_JR")}{gemBlock("GEM")}
    </div>}
    {snapshot && top==="PDUFA" && nav==="WT" && <div className="wt-page">
      <h2>WT — Watchlist and Trading research</h2>
      <p className="subtle">W/T selections are saved in this browser on the new site, separately from Streamlit. They are labels, never broker orders. Charts are third-party and may be delayed.</p>
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
    {snapshot && top==="PDUFA" && nav==="SCANS" && <section className="panel"><h2>SCANS — Not yet migrated</h2><p className="subtle">No new-system scanners, emails, Alpaca orders or nightly jobs are enabled. The existing Streamlit 10 PM Pacific scan installation remains unchanged.</p></section>}
    {snapshot && top==="CALENDAR" && <section className="panel"><h2>PDUFA Calendar — Saved event snapshot</h2>
      <p className="subtle">Reported dates only, not FDA-confirmed future events unless the source explicitly verifies them.</p>
      <div className="table-scroll"><table><thead><tr><th>PDUFA</th><th>Ticker</th><th>Drug</th><th>Program</th><th>Days away</th><th>FDA/source</th></tr></thead>
        <tbody>{pipeline.filter(r=>daysAway(r.pdufaDate)!==null && (daysAway(r.pdufaDate)||0)>=0).sort((a,b)=>(daysAway(a.pdufaDate)||0)-(daysAway(b.pdufaDate)||0)).map(r=><tr key={r.id}><td>{r.pdufaDate}</td><td>{r.ticker}</td><td>{r.drug}</td><td>{r.id}</td><td>{daysAway(r.pdufaDate)}</td><td>{stated(r.checkStatus)}</td></tr>)}</tbody>
      </table></div></section>}
  </div>;
}
