"use client";

import { useMemo, useState } from "react";

type Period = "CURRENT" | "PREVIOUS";
type Decision = "APPROVED" | "CRL" | "EXTENDED" | "PENDING";
type Trial = { nct_id: string; company: string; ticker?: string; drug: string; indication: string; phase3_results?: string; decision: Decision; decision_date?: string; source_url?: string; period: Period };
const NCT = /^NCT\d{8}$/;

export default function Phase3TrialLibrary({ onAnalyze }: { onAnalyze: (nct: string) => void }) {
  const [period, setPeriod] = useState<Period>("CURRENT");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<Decision | "ALL">("ALL");
  const [trials, setTrials] = useState<Trial[]>([]);
  const [notice, setNotice] = useState("No verified trial catalog connected yet. FDA outcomes must be sourced; no example records are shown as real.");
  const [loading, setLoading] = useState(false);
  async function refresh() {
    setLoading(true);
    try {
      const response = await fetch("/api/phase3-trials?period=" + period, { cache: "no-store" });
      if (!response.ok) throw new Error("Catalog unavailable (" + response.status + ")");
      const payload: unknown = await response.json();
      if (!payload || typeof payload !== "object" || !Array.isArray((payload as { trials?: unknown }).trials)) throw new Error("Catalog returned an invalid response.");
      const valid = (payload as { trials: unknown[] }).trials.filter((row): row is Trial => {
        if (!row || typeof row !== "object") return false;
        const t = row as Partial<Trial>;
        return typeof t.nct_id === "string" && NCT.test(t.nct_id) && typeof t.company === "string" && typeof t.drug === "string" && typeof t.indication === "string" && ["APPROVED","CRL","EXTENDED","PENDING"].includes(t.decision || "") && t.period === period;
      });
      setTrials(valid);
      setNotice(valid.length ? "Verified catalog loaded. FDA decisions are distinct from Phase 3 trial results." : "No verified " + period.toLowerCase() + " records available yet.");
    } catch (error) { setTrials([]); setNotice(error instanceof Error ? error.message : "Unable to load verified trial catalog."); }
    finally { setLoading(false); }
  }
  const visible = useMemo(() => trials.filter(t => (filter === "ALL" || t.decision === filter) && [t.company,t.ticker,t.drug,t.nct_id,t.indication].some(v => (v || "").toLowerCase().includes(query.toLowerCase()))), [trials,filter,query]);
  const counts = (["APPROVED","CRL","EXTENDED","PENDING"] as Decision[]).map(k => ({ key:k, count:trials.filter(t=>t.decision===k).length }));
  return <section className="panel" id="phase3-trial-library" aria-label="Phase 3 trial library">
    <h2>Phase 3 Trial Library · FDA decision tracker</h2>
    <p className="subtle">Select a previous or current trial, then Analyze to load its NCT into the same live processing workflow. Actual FDA decisions require verified source evidence; unknown decisions remain PENDING.</p>
    <div style={{display:"flex",gap:12,flexWrap:"wrap",alignItems:"end"}}>
      <label>Search period <select aria-label="Search period" value={period} onChange={e=>{setPeriod(e.target.value as Period);setTrials([]);setFilter("ALL");setNotice("Period changed. Refresh to retrieve its verified records.");}}><option value="CURRENT">Current</option><option value="PREVIOUS">Previous / historical</option></select></label>
      <label>Company, drug, ticker or NCT <input aria-label="Search trials" value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search trials" /></label>
      <button type="button" onClick={()=>void refresh()} disabled={loading}>{loading ? "Loading…" : "Refresh verified trials"}</button>
    </div>
    <div style={{display:"flex",gap:8,flexWrap:"wrap",margin:"14px 0"}} aria-label="FDA decision results">
      <button type="button" className="secondary" onClick={()=>setFilter("ALL")} aria-pressed={filter==="ALL"}>All · {trials.length}</button>
      {counts.map(({key,count})=><button key={key} type="button" className="secondary" aria-pressed={filter===key} onClick={()=>setFilter(key)}>{key==="APPROVED"?"🟢":key==="CRL"?"🔴":key==="EXTENDED"?"🟠":"⚪"} {key} · {count}</button>)}
    </div>
    <p role="status" className="subtle">{notice}</p>
    <div style={{maxHeight:380,overflow:"auto",border:"1px solid #c8d1c8"}}>
      <table style={{width:"100%",borderCollapse:"collapse",minWidth:760}}>
        <thead><tr>{["Company / ticker","Drug / indication","NCT","Phase 3 results","FDA result","Action"].map(h=><th key={h} scope="col" style={{textAlign:"left",padding:10,borderBottom:"1px solid #c8d1c8"}}>{h}</th>)}</tr></thead>
        <tbody>{visible.map(t=><tr key={t.nct_id}>{[t.company+(t.ticker?" · "+t.ticker:""),t.drug+" · "+t.indication,t.nct_id,t.phase3_results||"Not verified"].map((v,i)=><td key={i} style={{padding:10,borderBottom:"1px solid #ddd"}}>{v}</td>)}<td style={{padding:10}}>{t.source_url?<a href={t.source_url} target="_blank" rel="noopener noreferrer">{t.decision}</a>:t.decision==="PENDING"?"PENDING":"Unverified source"}</td><td style={{padding:10}}><button type="button" onClick={()=>onAnalyze(t.nct_id)}>Analyze</button></td></tr>)}
        {!visible.length&&<tr><td colSpan={6} style={{padding:18}}>No matching verified trials. Select a period and refresh when a catalog feed is available.</td></tr>}</tbody>
      </table>
    </div>
    <p className="subtle">Decision categories are application-level outcomes, not clinical trial endpoint results. This library does not grant trading approval.</p>
  </section>;
}
