"use client";

import { useEffect, useMemo, useState } from "react";
import styles from "./DailyResultsPanel.module.css";

type Count = number | null;
type SectionCounts = {
  previous: Count;
  new: Count;
  updated: Count;
  removed: Count;
  total: Count;
  basis?: string;
};
type DailyRow = {
  date_pacific: string;
  run_id: number | null;
  run_url: string | null;
  status: string;
  registered_at_utc: string | null;
  run_started_at_utc?: string;
  scheduled_8pm_pacific_utc?: string;
  start_delay_minutes?: number;
  scan_night_source?: "GUARDED_SCHEDULER_INPUT" | "ACTUAL_START_DATE_FALLBACK";
  sections: Partial<Record<"master"|"pipeline"|"designations"|"gem_jr"|"gem", SectionCounts>>;
  notes?: string[];
};
type DailyLedger = { schema_version: number; updated_at_utc?: string; days: DailyRow[] };
type ApiReport = { daily?: DailyLedger | null };

const groups: {key: keyof DailyRow["sections"]; label: string; note: string}[] = [
  {key:"master",label:"Old + New — Master Trials",note:"Published NCT trial inventory; not Pipeline-qualified"},
  {key:"pipeline",label:"Pipeline",note:"Mandatory publicly traded, Phase 3 and market-cap restrictions"},
  {key:"designations",label:"FDA Special Designations",note:"Only independently verified FDA designation evidence"},
  {key:"gem_jr",label:"GEM JR",note:"Saved qualified members, not newly posted Phase 3 results"},
  {key:"gem",label:"GEM",note:"Saved qualified members; FS and FA unchanged"}
];
const empty: SectionCounts = {previous:null,new:null,updated:null,removed:null,total:null};
function number(value: Count | undefined) {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0
    ? value.toLocaleString("en-US") : "—";
}
function pacificToday() {
  const fields = new Intl.DateTimeFormat("en-US",{timeZone:"America/Los_Angeles",year:"numeric",month:"2-digit",day:"2-digit"})
    .formatToParts(new Date());
  const values=Object.fromEntries(fields.map(x=>[x.type,x.value]));
  return [values.year,values.month,values.day].join("-");
}
function dateLabel(day:string) {
  const at=new Date(day+"T12:00:00Z");
  return Number.isFinite(at.getTime())
    ? new Intl.DateTimeFormat("en-US",{timeZone:"UTC",weekday:"short",month:"short",day:"numeric",year:"numeric"}).format(at)
    : day;
}
function statusLabel(status: string) {
  if (status==="COMPLETE") return "Reported complete — inspect source evidence";
  if (status==="PARTIAL") return "Partial evidence";
  if (status==="RUN_FAILED") return "Scan failed";
  return "Not yet verified";
}

function startLabel(row: DailyRow) {
  if (!row.run_started_at_utc || !Number.isFinite(Date.parse(row.run_started_at_utc))) return "Start time not recorded";
  const time = new Intl.DateTimeFormat("en-US",{
    timeZone:"America/Los_Angeles",hour:"numeric",minute:"2-digit",hour12:true
  }).format(new Date(row.run_started_at_utc));
  const delay = row.start_delay_minutes;
  const offset = typeof delay==="number" && Number.isSafeInteger(delay)
    ? delay===0 ? "at 8 PM target" : delay>0 ? delay+" min after 8 PM target" : Math.abs(delay)+" min before 8 PM target"
    : "start delay not recorded";
  const origin = row.scan_night_source==="GUARDED_SCHEDULER_INPUT"?"guarded Pacific scan night":"scheduler origin unverified";
  return time+" PT · "+offset+" · "+origin;
}

export default function DailyResultsPanel() {
  const [ledger,setLedger]=useState<DailyLedger|null>(null);
  const [problem,setProblem]=useState("");
  const [loading,setLoading]=useState(true);
  const [reload,setReload]=useState(0);
  const [selected,setSelected]=useState<string|null>(null);
  useEffect(()=>{
    const controller=new AbortController();
    setLoading(true);
    fetch("/api/published-scans",{cache:"no-store",signal:controller.signal})
      .then(async response=>{
        if(!response.ok) throw new Error("Daily reports unavailable (HTTP "+response.status+")");
        return response.json() as Promise<ApiReport>;
      })
      .then(result=>{
        if(controller.signal.aborted)return;
        const data=result.daily;
        if(!data || data.schema_version!==1 || !Array.isArray(data.days)) throw new Error("Daily results archive is not published yet");
        setLedger(data);setProblem("");
      })
      .catch(error=>{if(!controller.signal.aborted)setProblem(error instanceof Error?error.message:"Results unavailable");})
      .finally(()=>{if(!controller.signal.aborted)setLoading(false);});
    return ()=>controller.abort();
  },[reload]);
  const today=pacificToday();
  const rows=useMemo(()=>{
    const archived=(ledger?.days||[]).filter(r=>/^\d{4}-\d{2}-\d{2}$/.test(r.date_pacific));
    const known=archived.some(r=>r.date_pacific===today);
    const all=known?archived:[{
      date_pacific:today,run_id:null,run_url:null,status:"NOT_PUBLISHED",
      registered_at_utc:null,sections:{},notes:["Today's completed overnight result has not been published. Previous dated totals are retained."]
    } as DailyRow,...archived];
    return [...all].sort((a,b)=>b.date_pacific.localeCompare(a.date_pacific));
  },[ledger,today]);
  const active=rows.find(r=>r.date_pacific===selected)||rows[0];
  const totals=groups.map(g=>({ ...g, counts:active?.sections?.[g.key]||empty }));
  return <section className={"panel "+styles.page} aria-label="Dated overnight scan results">
    <header className={styles.head}>
      <div>
        <div className={styles.eyebrow}>PDUFA COMMAND CENTER · RESULTS</div>
        <h2>Overnight Scan Results</h2>
        <p>Daily saved totals · old + new, Pipeline, FDA special designations, GEM JR and GEM</p>
      </div>
      <button type="button" className="secondary" onClick={()=>setReload(x=>x+1)} disabled={loading}>
        {loading?"Checking…":"Refresh reports"}
      </button>
    </header>
    <div className={styles.daySelect}>
      <label htmlFor="daily-results-day"><strong>Report date (Pacific)</strong></label>
      <select id="daily-results-day" value={active?.date_pacific||today} onChange={e=>setSelected(e.target.value)}>
        {rows.map(r=><option value={r.date_pacific} key={r.date_pacific}>{dateLabel(r.date_pacific)}{r.date_pacific===today?" · Today":""}</option>)}
      </select>
      <span className={active?.status==="COMPLETE"?styles.success:styles.caution} role="status">
        {statusLabel(active?.status||"NOT_PUBLISHED")}
      </span>
    </div>
    <p className={styles.source}>
      {active?.run_url && active?.run_id
        ? <>Nightly run <a href={active.run_url} target="_blank" rel="noopener noreferrer">#{active.run_id} ↗</a></>
        : <>No completed nightly-run evidence registered for this date</>}
      {" · "}Counts are snapshots recorded for the selected Pacific calendar day, not numbers rolled into the next date.
    </p>
    <p className={styles.source}><strong>Actual workflow start:</strong> {active?startLabel(active):"Unavailable"}. Workflow start timing does not establish that GitHub's scheduled trigger fired on time.</p>
    <div className={styles.cards}>
      {totals.map(({key,label,counts})=><div className={styles.card} key={key}>
        <div className={styles.cardName}>{label}</div>
        <div className={styles.cardNumber}>{number(counts.total)}</div>
        <div className={styles.muted}>Recorded total</div>
        <div className={styles.cardDelta}>
          <span>Old <b>{number(counts.previous)}</b></span>
          <span>New <b>{number(counts.new)}</b></span>
          <span>Updated <b>{number(counts.updated)}</b></span>
          <span>Removed <b>{number(counts.removed)}</b></span>
        </div>
      </div>)}
    </div>
    <h3>Daily comparison — {dateLabel(active?.date_pacific||today)}</h3>
    <div className="table-scroll">
      <table className={styles.table}>
        <thead><tr><th>Report</th><th>Old</th><th>New</th><th>Updated</th><th>Removed</th><th>Today's total</th></tr></thead>
        <tbody>{totals.map(({key,label,counts})=><tr key={key}>
          <th scope="row">{label}</th>
          <td>{number(counts.previous)}</td><td>{number(counts.new)}</td>
          <td>{number(counts.updated)}</td><td>{number(counts.removed)}</td>
          <td><strong>{number(counts.total)}</strong></td>
        </tr>)}</tbody>
      </table>
    </div>
    <details className={styles.details}>
      <summary>What was verified for this day?</summary>
      {totals.map(({key,label,note,counts})=><p key={key}><strong>{label}:</strong> {counts.basis||"No dated, verified total published"} · {note}</p>)}
      {(active?.notes||[]).map((note,index)=><p key={index}>{note}</p>)}
    </details>
    <div className={styles.archive}>
      <h3>Saved Daily Results</h3>
      <p className={styles.muted}>Each evening creates or updates its own dated record. Older days are retained for comparison; failed or incomplete scans are marked, never silently counted as zero.</p>
      <div className="table-scroll">
        <table className={styles.table}>
          <thead><tr><th>Pacific date</th><th>Master</th><th>Pipeline</th><th>Designations</th><th>GEM JR</th><th>GEM</th><th>Evidence status</th><th>Recorded workflow start</th></tr></thead>
          <tbody>{rows.map(r=><tr key={r.date_pacific}>
            <th scope="row"><button type="button" className={styles.dayButton} onClick={()=>setSelected(r.date_pacific)}>{r.date_pacific}</button></th>
            {(["master","pipeline","designations","gem_jr","gem"] as const).map(k=><td key={k}>{number(r.sections?.[k]?.total)}</td>)}
            <td>{statusLabel(r.status)}</td>
            <td>{startLabel(r)}</td>
          </tr>)}</tbody>
        </table>
      </div>
    </div>
    {problem && <p className="risk-line" role="alert">{problem}</p>}
    <p className={styles.muted}>A dash (—) means evidence is missing or unverified, not zero. Master inventory counts do not imply Phase 3 eligibility. GEM JR and GEM remain independent and their FS/FA preset settings are never changed by this report.</p>
  </section>;
}
